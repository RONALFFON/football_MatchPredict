"""数据库仓储。保留现有表结构，隔离旧版 database.py。"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import psycopg2
from psycopg2.extras import RealDictCursor

from app.infrastructure.database import Database


USER_FIELDS = """
    id, username, email, user_type, membership_expires,
    CASE WHEN last_prediction_date < CURRENT_DATE
         THEN 0 ELSE daily_predictions_used END AS daily_predictions_used,
    last_prediction_date, total_predictions
"""


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _json_row(row: dict) -> dict:
    return {key: _json_value(value) for key, value in dict(row).items()}


def _consume_prediction_cursor(cursor, user_id: int) -> dict | None:
    cursor.execute(
        """UPDATE users
           SET daily_predictions_used = CASE
                 WHEN last_prediction_date < CURRENT_DATE THEN 1
                 ELSE daily_predictions_used + 1 END,
               total_predictions = total_predictions + 1,
               last_prediction_date = CURRENT_DATE
         WHERE id = %s AND is_active = TRUE
           AND (user_type = 'premium'
                OR last_prediction_date < CURRENT_DATE)
     RETURNING """ + USER_FIELDS,
        (user_id,),
    )
    row = cursor.fetchone()
    return _json_row(row) if row else None


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, username: str, email: str, password_hash: str) -> bool:
        try:
            with self.db.connection() as conn, conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO users (username, email, password_hash, user_type)
                       VALUES (%s, %s, %s, 'free')""",
                    (username, email, password_hash),
                )
            return True
        except psycopg2.IntegrityError:
            return False

    def find_by_username(self, username: str) -> dict | None:
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                f"SELECT {USER_FIELDS} FROM users WHERE username = %s AND is_active = TRUE",
                (username,),
            )
            row = cursor.fetchone()
            return _json_row(row) if row else None

    def authenticate(self, username: str, password_hash: str) -> dict | None:
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                f"""SELECT {USER_FIELDS}, password_hash
                    FROM users
                    WHERE username = %s AND password_hash = %s AND is_active = TRUE""",
                (username, password_hash),
            )
            row = cursor.fetchone()
            if not row:
                return None

            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s",
                (row['id'],),
            )
            result = dict(row)
            result.pop('password_hash', None)
            return _json_row(result)

    def can_predict(self, user: dict) -> bool:
        return True

    def consume_prediction(self, user_id: int) -> dict | None:
        """原子扣减配额，避免检查和扣减之间产生竞态。"""
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            return _consume_prediction_cursor(cursor, user_id)


class PredictionRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_with_quota(self, data: dict) -> dict:
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            self._insert(cursor, data)
            updated = _consume_prediction_cursor(cursor, data['user_id'])
            if updated is None:
                raise PermissionError('今日免费预测次数已用完，请升级会员')
            return updated

    @staticmethod
    def _insert(cursor, data: dict) -> None:
        cursor.execute(
            """INSERT INTO match_predictions (
                prediction_id, user_id, username, prediction_mode,
                home_team, away_team, league_name, match_time,
                home_odds, draw_odds, away_odds, predicted_result,
                prediction_confidence, ai_analysis, user_ip
            ) VALUES (
                %(prediction_id)s, %(user_id)s, %(username)s, %(prediction_mode)s,
                %(home_team)s, %(away_team)s, %(league_name)s, %(match_time)s,
                %(home_odds)s, %(draw_odds)s, %(away_odds)s, %(predicted_result)s,
                %(prediction_confidence)s, %(ai_analysis)s, %(user_ip)s
            ) ON CONFLICT (prediction_id) DO UPDATE SET
                predicted_result = EXCLUDED.predicted_result,
                prediction_confidence = EXCLUDED.prediction_confidence,
                ai_analysis = EXCLUDED.ai_analysis,
                updated_at = CURRENT_TIMESTAMP""",
            data,
        )

    def stats(self) -> dict:
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """SELECT prediction_mode,
                          COUNT(*) AS total_predictions,
                          COUNT(*) FILTER (WHERE is_correct = TRUE) AS correct_predictions,
                          ROUND(AVG(prediction_confidence), 2) AS avg_confidence
                     FROM match_predictions
                 GROUP BY prediction_mode ORDER BY prediction_mode"""
            )
            mode_stats = [_json_row(row) for row in cursor.fetchall()]
            cursor.execute(
                """SELECT home_team, away_team, predicted_result, is_correct, created_at
                     FROM match_predictions ORDER BY created_at DESC LIMIT 10"""
            )
            recent = [_json_row(row) for row in cursor.fetchall()]
        return {'mode_stats': mode_stats, 'recent_predictions': recent}


class LotteryRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_matches(self, days_ahead: int) -> list[dict]:
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """SELECT match_id, home_team, away_team, league_name,
                          match_date, match_time, match_datetime, match_num,
                          match_status, home_odds, draw_odds, away_odds,
                          goal_line
                     FROM daily_matches
                    WHERE match_date BETWEEN %s AND %s AND is_active = TRUE
                 ORDER BY match_datetime, match_date, match_time""",
                (today, end_date),
            )
            rows = cursor.fetchall()

        matches = []
        for row in rows:
            if row['match_datetime']:
                match_time = row['match_datetime']
            elif row['match_date'] and row['match_time']:
                match_time = datetime.combine(row['match_date'], row['match_time'])
            else:
                match_time = row['match_date']
            time_text = ''
            if isinstance(match_time, datetime):
                time_text = match_time.isoformat(sep=' ')
            elif match_time:
                time_text = match_time.isoformat()
            matches.append({
                'match_id': row['match_id'],
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'league_name': row['league_name'],
                'match_time': time_text,
                'match_date': row['match_date'].isoformat() if row['match_date'] else '',
                'match_num': row['match_num'],
                'status': row['match_status'],
                'source': 'database',
                'odds': {
                    'hhad': {
                        'h': str(row['home_odds'] or 0),
                        'd': str(row['draw_odds'] or 0),
                        'a': str(row['away_odds'] or 0),
                    },
                    'goal_line': row['goal_line'],
                },
            })
        return matches

    def save_matches(self, matches: list[dict]) -> dict[str, int]:
        stats = {'upserted': 0, 'skipped': 0}
        with self.db.connection() as conn, conn.cursor() as cursor:
            for match in matches:
                row = self._match_row(match)
                if row is None:
                    stats['skipped'] += 1
                    continue
                cursor.execute(
                    """INSERT INTO daily_matches (
                        match_id, home_team, away_team, league_name,
                        match_date, match_time, match_datetime, match_num,
                        match_status, home_odds, draw_odds, away_odds,
                        goal_line, data_source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_team = EXCLUDED.home_team,
                        away_team = EXCLUDED.away_team,
                        league_name = EXCLUDED.league_name,
                        match_date = EXCLUDED.match_date,
                        match_time = EXCLUDED.match_time,
                        match_datetime = EXCLUDED.match_datetime,
                        match_num = EXCLUDED.match_num,
                        match_status = EXCLUDED.match_status,
                        home_odds = EXCLUDED.home_odds,
                        draw_odds = EXCLUDED.draw_odds,
                        away_odds = EXCLUDED.away_odds,
                        goal_line = EXCLUDED.goal_line,
                        data_source = EXCLUDED.data_source,
                        updated_at = CURRENT_TIMESTAMP,
                        is_active = TRUE""",
                    row,
                )
                stats['upserted'] += 1
        return stats

    @staticmethod
    def _match_row(match: dict) -> tuple | None:
        match_id = match.get('match_id')
        home_team = match.get('home_team')
        away_team = match.get('away_team')
        if not match_id or not home_team or not away_team:
            return None

        match_datetime = None
        if match.get('match_time'):
            try:
                match_datetime = datetime.fromisoformat(str(match['match_time']))
            except ValueError:
                pass
        match_date = match_datetime.date() if match_datetime else None
        match_time = match_datetime.time() if match_datetime else None
        if match_date is None and match.get('match_date'):
            try:
                match_date = date.fromisoformat(str(match['match_date']))
            except ValueError:
                return None
        if match_date is None:
            return None

        odds = (match.get('odds') or {}).get('hhad') or {}
        try:
            values = tuple(
                float(odds.get(key)) if odds.get(key) else None
                for key in ('h', 'd', 'a')
            )
        except (TypeError, ValueError):
            return None
        return (
            match_id, home_team, away_team, match.get('league_name', ''),
            match_date, match_time, match_datetime, match.get('match_num', ''),
            match.get('status', ''), *values, (match.get('odds') or {}).get('goal_line', ''),
            match.get('source', 'china_lottery'),
        )


def prediction_record(
    *,
    mode: str,
    match_data: dict,
    prediction_result: str,
    confidence: float,
    user: dict,
    user_ip: str,
    ai_analysis: str = '',
) -> dict:
    odds = match_data.get('odds') or {}
    hhad = odds.get('hhad') or {}
    home_odds = match_data.get('home_odds', match_data.get('home', hhad.get('h')))
    draw_odds = match_data.get('draw_odds', match_data.get('draw', hhad.get('d')))
    away_odds = match_data.get('away_odds', match_data.get('away', hhad.get('a')))
    return {
        'prediction_id': f'{mode.lower()}_{uuid4().hex}',
        'user_id': user['id'],
        'username': user['username'],
        'prediction_mode': mode.title(),
        'home_team': match_data.get('home_team', ''),
        'away_team': match_data.get('away_team', ''),
        'league_name': match_data.get('league_name', ''),
        'match_time': None,
        'home_odds': home_odds,
        'draw_odds': draw_odds,
        'away_odds': away_odds,
        'predicted_result': prediction_result,
        'prediction_confidence': confidence,
        'ai_analysis': ai_analysis,
        'user_ip': user_ip,
    }

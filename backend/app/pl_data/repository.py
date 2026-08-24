"""英超专项数据访问：直查 pl_analytics schema。

表不存在时返回统一错误信息（提示先运行同步管道），而不是抛 500。
"""
import psycopg2
import psycopg2.extras

from app.core.deps import prediction_db

TABLE_MISSING = '英超数据表尚未初始化，请先执行 backend/sql/pl_analytics_init.sql 并运行同步管道'


def _connect():
    """复用主站数据库连接参数（schema 逻辑隔离）。"""
    if prediction_db is None:
        raise RuntimeError('数据库未配置')
    return psycopg2.connect(**prediction_db.connection_params)


def query(sql: str, params: tuple = ()) -> list[dict]:
    """执行查询并返回字典列表；表缺失抛出 ValueError 由路由层转友好提示。"""
    try:
        conn = _connect()
    except Exception as e:
        raise ValueError(f'数据库连接失败: {e}') from e
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
    except psycopg2.errors.UndefinedTable as e:
        raise ValueError(TABLE_MISSING) from e
    finally:
        conn.close()


def get_matches(status: str | None, limit: int) -> list[dict]:
    sql = """SELECT match_uid, season, round, home_team, away_team, utc_date, status,
                    home_score, away_score
             FROM pl_analytics.pl_matches"""
    params: list = []
    if status:
        sql += ' WHERE status = %s'
        params.append(status)
    sql += ' ORDER BY utc_date DESC LIMIT %s'
    params.append(limit)
    rows = query(sql, tuple(params))
    for r in rows:
        if r.get('utc_date'):
            r['utc_date'] = str(r['utc_date'])
    return rows


def get_team(name: str) -> dict | None:
    rows = query('SELECT * FROM pl_analytics.pl_teams WHERE name ILIKE %s LIMIT 1', (f'%{name}%',))
    return rows[0] if rows else None


def get_recent_form(team: str, n: int = 5) -> list[dict]:
    rows = query(
        """SELECT match_uid, utc_date, home_team, away_team, home_score, away_score, status
           FROM pl_analytics.pl_matches
           WHERE status = 'FINISHED' AND (home_team ILIKE %s OR away_team ILIKE %s)
           ORDER BY utc_date DESC LIMIT %s""",
        (f'%{team}%', f'%{team}%', n))
    for r in rows:
        if r.get('utc_date'):
            r['utc_date'] = str(r['utc_date'])
    return rows


def get_head_to_head(team_a: str, team_b: str, n: int = 5) -> list[dict]:
    rows = query(
        """SELECT match_uid, utc_date, home_team, away_team, home_score, away_score
           FROM pl_analytics.pl_matches
           WHERE status = 'FINISHED'
             AND ((home_team ILIKE %s AND away_team ILIKE %s)
               OR (home_team ILIKE %s AND away_team ILIKE %s))
           ORDER BY utc_date DESC LIMIT %s""",
        (f'%{team_a}%', f'%{team_b}%', f'%{team_b}%', f'%{team_a}%', n))
    for r in rows:
        if r.get('utc_date'):
            r['utc_date'] = str(r['utc_date'])
    return rows


def get_team_stats(team: str) -> dict:
    """从已完成比赛聚合球队统计（不依赖 pl_features，表最少）。"""
    rows = query(
        """SELECT
             COUNT(*) FILTER (WHERE home_team ILIKE %s) AS home_played,
             AVG(home_score) FILTER (WHERE home_team ILIKE %s) AS home_goals_scored,
             AVG(away_score) FILTER (WHERE home_team ILIKE %s) AS home_goals_conceded,
             COUNT(*) FILTER (WHERE away_team ILIKE %s) AS away_played,
             AVG(away_score) FILTER (WHERE away_team ILIKE %s) AS away_goals_scored,
             AVG(home_score) FILTER (WHERE away_team ILIKE %s) AS away_goals_conceded,
             COUNT(*) FILTER (WHERE status='FINISHED'
               AND ((home_team ILIKE %s AND home_score > away_score)
                 OR (away_team ILIKE %s AND away_score > home_score))) AS wins,
             COUNT(*) FILTER (WHERE status='FINISHED' AND home_score = away_score
               AND (home_team ILIKE %s OR away_team ILIKE %s)) AS draws,
             COUNT(*) FILTER (WHERE status='FINISHED') AS played
           FROM pl_analytics.pl_matches""",
        tuple([f'%{team}%'] * 10))
    if not rows or not rows[0].get('played'):
        raise ValueError(f'没有球队 {team} 的比赛数据')
    stats = rows[0]
    for k, v in list(stats.items()):
        if v is not None and k != 'played' and isinstance(v, (int, float)):
            stats[k] = round(float(v), 2)
    return stats


def get_standings() -> list[dict]:
    return query(
        """SELECT team_name, position, played, won, drawn, lost, goals_for, goals_against, points
           FROM pl_analytics.pl_standings ORDER BY position ASC""")


def get_odds_history(match_uid: str) -> list[dict]:
    rows = query(
        """SELECT bookmaker, home_odds, draw_odds, away_odds, snapshot_at
           FROM pl_analytics.pl_odds_history WHERE match_uid = %s ORDER BY snapshot_at ASC""",
        (match_uid,))
    for r in rows:
        if r.get('snapshot_at'):
            r['snapshot_at'] = str(r['snapshot_at'])
    return rows

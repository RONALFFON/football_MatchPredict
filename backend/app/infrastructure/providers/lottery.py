"""体彩公开比赛数据提供者。"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

import requests


class LotteryProvider:
    endpoint = 'https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry'

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.lottery.gov.cn/',
        })

    def _fetch(self, pool_code: str) -> dict[str, Any]:
        response = self.session.get(
            self.endpoint,
            params={'poolCode': pool_code, 'channel': 'c'},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get('success'):
            raise RuntimeError(data.get('errorMessage', '体彩接口返回失败'))
        return data

    @staticmethod
    def _odds(match: dict[str, Any], pool_code: str) -> dict[str, Any] | None:
        raw = match.get(pool_code)
        if not raw:
            raw = next(
                (item for item in match.get('oddsList') or []
                 if item.get('poolCode') == pool_code.upper()),
                None,
            )
        if not raw or not all(raw.get(key) for key in ('h', 'd', 'a')):
            return None
        try:
            values = {key: str(float(raw[key])) for key in ('h', 'd', 'a')}
        except (TypeError, ValueError):
            return None
        if any(not 1.01 <= float(value) <= 99.99 for value in values.values()):
            return None
        return {
            'hhad': values,
            'type': pool_code,
            'goal_line': raw.get('goalLine', ''),
            'update_time': f"{raw.get('updateDate', '')} {raw.get('updateTime', '')}".strip(),
        }

    @staticmethod
    def _team_name(value: str) -> str:
        return re.sub(r'\s+', ' ', re.sub(r'\[[^]]*\]|\([^)]*\)', '', value or '')).strip()

    def _parse(
        self, data: dict[str, Any], had_odds: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        matches = []
        for day in data.get('value', {}).get('matchInfoList', []):
            for item in day.get('subMatchList', []):
                match_id = str(item.get('matchId', ''))
                odds = had_odds.get(match_id) or self._odds(item, 'hhad')
                match_date = item.get('matchDate') or day.get('businessDate', '')
                if not match_id or not odds or not match_date:
                    continue
                matches.append({
                    'match_id': f'lottery_{match_id}',
                    'home_team': self._team_name(
                        item.get('homeTeamAllName') or item.get('homeTeamAbbName', '')
                    ),
                    'away_team': self._team_name(
                        item.get('awayTeamAllName') or item.get('awayTeamAbbName', '')
                    ),
                    'league_name': item.get('leagueAbbName') or item.get('leagueAllName', ''),
                    'match_time': f"{match_date} {item.get('matchTime', '')}".strip(),
                    'match_date': match_date,
                    'match_num': item.get('matchNumStr', ''),
                    'status': item.get('matchStatus', 'Unknown'),
                    'source': 'china_lottery',
                    'odds': odds,
                })
        return matches

    def get_matches(self, days_ahead: int = 3) -> list[dict[str, Any]]:
        had_odds: dict[str, dict[str, Any]] = {}
        try:
            had = self._fetch('had')
            for day in had.get('value', {}).get('matchInfoList', []):
                for item in day.get('subMatchList', []):
                    odds = self._odds(item, 'had')
                    if odds and item.get('matchId'):
                        had_odds[str(item['matchId'])] = odds
        except (requests.RequestException, RuntimeError, ValueError):
            pass

        matches = self._parse(self._fetch('hhad'), had_odds)
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        result = []
        for match in matches:
            try:
                match_date = datetime.strptime(match['match_date'], '%Y-%m-%d').date()
            except ValueError:
                continue
            if today <= match_date <= end_date:
                result.append(match)
        return result

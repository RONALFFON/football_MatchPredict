"""英超专项数据接口测试（数据层打桩，不依赖真实数据库）。"""
import pytest

from app.pl_data import repository as pl_repository


SAMPLE_PL_MATCH = {
    'match_uid': 'PL-2024-001',
    'season': '2024',
    'round': 'MATCHDAY_1',
    'home_team': 'Arsenal FC',
    'away_team': 'Chelsea FC',
    'utc_date': '2024-08-17 14:00:00',
    'status': 'FINISHED',
    'home_score': 2,
    'away_score': 0,
}


@pytest.fixture()
def patched_repo(monkeypatch):
    """把 pl_data.repository 的查询函数替换为可控桩实现。"""
    calls = {}

    def get_matches(status, limit):
        calls['matches'] = (status, limit)
        return [SAMPLE_PL_MATCH]

    monkeypatch.setattr(pl_repository, 'get_matches', get_matches)
    monkeypatch.setattr(pl_repository, 'get_standings', lambda: [{'team_name': 'Arsenal FC', 'position': 1}])
    monkeypatch.setattr(pl_repository, 'get_team_stats', lambda team: {'played': 38, 'wins': 28})
    monkeypatch.setattr(pl_repository, 'get_recent_form', lambda team, n: [SAMPLE_PL_MATCH])
    monkeypatch.setattr(pl_repository, 'get_odds_history', lambda match_uid: [{'bookmaker': 'bet365', 'home_odds': 1.8}])
    return calls


def test_pl_matches_success(client, patched_repo):
    body = client.get('/api/v1/pl/matches').json()
    assert body['code'] == 0
    assert body['data']['matches'][0]['match_uid'] == 'PL-2024-001'
    assert patched_repo['matches'] == (None, 50)


def test_pl_matches_status_and_limit_passed(client, patched_repo):
    body = client.get('/api/v1/pl/matches', params={'status': 'FINISHED', 'limit': 10}).json()
    assert body['code'] == 0
    assert patched_repo['matches'] == ('FINISHED', 10)


def test_pl_matches_limit_out_of_range(client):
    assert client.get('/api/v1/pl/matches', params={'limit': 0}).status_code == 422
    assert client.get('/api/v1/pl/matches', params={'limit': 201}).status_code == 422


def test_pl_matches_table_missing_friendly_error(client, monkeypatch):
    def boom(status, limit):
        raise ValueError(pl_repository.TABLE_MISSING)

    monkeypatch.setattr(pl_repository, 'get_matches', boom)
    body = client.get('/api/v1/pl/matches').json()
    assert body['code'] == 404
    assert 'pl_analytics_init.sql' in body['message']


def test_pl_standings_success(client, patched_repo):
    body = client.get('/api/v1/pl/standings').json()
    assert body['code'] == 0
    assert body['data']['standings'][0]['team_name'] == 'Arsenal FC'


def test_pl_team_profile_success(client, patched_repo):
    body = client.get('/api/v1/pl/teams/Arsenal').json()
    assert body['code'] == 0
    assert body['data']['team'] == 'Arsenal'
    assert body['data']['stats']['played'] == 38
    assert body['data']['recent_form'][0]['match_uid'] == 'PL-2024-001'


def test_pl_team_not_found(client, monkeypatch):
    def boom(team):
        raise ValueError(f'没有球队 {team} 的比赛数据')

    monkeypatch.setattr(pl_repository, 'get_team_stats', boom)
    body = client.get('/api/v1/pl/teams/NoSuchTeam').json()
    assert body['code'] == 404
    assert '没有球队' in body['message']


def test_pl_odds_history_success(client, patched_repo):
    body = client.get('/api/v1/pl/odds/PL-2024-001').json()
    assert body['code'] == 0
    assert body['data']['history'][0]['bookmaker'] == 'bet365'

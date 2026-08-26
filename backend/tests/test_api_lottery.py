"""体彩比赛数据接口测试：/lottery/matches、/lottery/refresh。"""
SAMPLE_LOTTERY_MATCH = {
    'match_id': '20260825001',
    'home_team': '阿森纳',
    'away_team': '切尔西',
    'league_name': '英超',
    'match_time': '2026-08-25 22:00:00',
    'status': 'SALE',
    'odds': {'hhad': {'h': '1.80', 'd': '3.40', 'a': '4.20'}, 'goal_line': '-1'},
}


def test_lottery_matches_success(client, fake_lottery):
    fake_lottery.matches = [SAMPLE_LOTTERY_MATCH]
    body = client.get('/api/v1/lottery/matches').json()
    assert body['code'] == 0
    assert body['data']['count'] == 1
    assert body['data']['matches'][0]['home_team'] == '阿森纳'


def test_lottery_matches_days_param_passed(client, fake_lottery):
    captured = {}

    def spy(days_ahead):
        captured['days'] = days_ahead
        return [SAMPLE_LOTTERY_MATCH]

    fake_lottery.get_matches = spy
    client.get('/api/v1/lottery/matches', params={'days': 5})
    assert captured['days'] == 5


def test_lottery_matches_days_out_of_range(client):
    assert client.get('/api/v1/lottery/matches', params={'days': 0}).status_code == 422
    assert client.get('/api/v1/lottery/matches', params={'days': 8}).status_code == 422


def test_lottery_matches_empty(client):
    body = client.get('/api/v1/lottery/matches').json()
    assert body['code'] == 404
    assert 'sync_lottery' in body['message']


def test_lottery_matches_db_unavailable(client, fake_db):
    fake_db.configured = False
    body = client.get('/api/v1/lottery/matches').json()
    assert body['code'] == 500
    assert body['message'] == '数据库未配置'


def test_lottery_matches_query_error(client, fake_lottery):
    fake_lottery.error = True
    body = client.get('/api/v1/lottery/matches').json()
    assert body['code'] == 500
    assert '数据库查询失败' in body['message']


def test_lottery_refresh_success(client, fake_lottery_provider):
    fake_lottery_provider.matches = [SAMPLE_LOTTERY_MATCH]
    body = client.post('/api/v1/lottery/refresh').json()
    assert body['code'] == 0
    assert body['message'] == '刷新成功'
    assert body['data']['count'] == 1


def test_lottery_refresh_provider_error(client, fake_lottery_provider):
    fake_lottery_provider.error = True
    body = client.post('/api/v1/lottery/refresh').json()
    assert body['code'] == 500
    assert '刷新数据失败' in body['message']

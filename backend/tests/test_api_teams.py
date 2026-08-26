"""球队基础数据接口测试。"""


def test_get_teams_returns_all_leagues(client):
    response = client.get('/api/v1/teams')
    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['message'] == '球队数据获取成功'
    assert set(body['data']['leagues']) == {'PL', 'PD', 'SA', 'BL1', 'FL1'}
    for league, teams in body['data']['teams'].items():
        assert len(teams) == 8, f'{league} 球队数量不正确'
    assert 'Arsenal FC' in body['data']['teams']['PL']
    assert 'Real Madrid CF' in body['data']['teams']['PD']

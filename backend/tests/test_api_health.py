"""健康检查与元信息接口测试。"""


def test_health_returns_ok(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == 'OK'


def test_meta_reports_capabilities(client):
    response = client.get('/api/v1/meta')
    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['data']['db_ready'] is True
    # 测试环境未配置 GEMINI_API_KEY
    assert body['data']['ai_ready'] is False
    assert 'ai_model' in body['data']

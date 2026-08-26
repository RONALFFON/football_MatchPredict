"""预测接口测试：/predict、/save-prediction、/prediction-stats。"""
from conftest import SAMPLE_MATCH, auth_header


def test_predict_success(client):
    response = client.post('/api/v1/predict', json={'matches': [SAMPLE_MATCH]})
    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['message'] == '简化预测模式'
    prediction = body['data']['individual_predictions'][0]
    assert prediction['home_team'] == 'Arsenal FC'
    assert prediction['recommendation'] in {'主胜', '平局', '客胜'}
    assert abs(sum(prediction['probabilities'].values()) - 1.0) < 1e-9


def test_predict_rejects_zero_odds(client):
    match = {**SAMPLE_MATCH, 'home_odds': 0}
    body = client.post('/api/v1/predict', json={'matches': [match]}).json()
    assert body['code'] != 0
    assert body['message'] == '赔率必须大于0'


def test_predict_empty_matches_rejected(client):
    assert client.post('/api/v1/predict', json={'matches': []}).status_code == 422


def test_predict_missing_home_team_rejected(client):
    match = {k: v for k, v in SAMPLE_MATCH.items() if k != 'home_team'}
    assert client.post('/api/v1/predict', json={'matches': [match]}).status_code == 422


def test_save_prediction_requires_login(client):
    payload = {'mode': 'classic', 'match_data': SAMPLE_MATCH, 'prediction_result': '主胜', 'confidence': 0.8}
    body = client.post('/api/v1/save-prediction', json=payload).json()
    assert body['code'] == 401
    assert body['message'] == '请先登录再进行预测'


def test_save_prediction_success(client, fake_users, fake_predictions):
    fake_users.add('tester')
    payload = {'mode': 'classic', 'match_data': SAMPLE_MATCH, 'prediction_result': '主胜', 'confidence': 0.8}
    body = client.post('/api/v1/save-prediction', json=payload, headers=auth_header('tester')).json()
    assert body['code'] == 0
    assert body['message'] == '预测结果保存成功'
    assert body['data']['user']['daily_predictions_used'] == 1
    assert len(fake_predictions.records) == 1
    record = fake_predictions.records[0]
    assert record['prediction_mode'] == 'Classic'
    assert record['home_team'] == 'Arsenal FC'
    assert record['predicted_result'] == '主胜'
    assert record['prediction_confidence'] == 0.8


def test_save_prediction_unknown_mode(client, fake_users):
    fake_users.add('tester')
    payload = {'mode': 'magic', 'match_data': SAMPLE_MATCH, 'prediction_result': '主胜', 'confidence': 0.8}
    body = client.post('/api/v1/save-prediction', json=payload, headers=auth_header('tester')).json()
    assert body['code'] != 0
    assert body['message'] == '未知的预测模式'


def test_save_prediction_quota_exhausted(client, fake_users, fake_predictions):
    fake_users.add('tester')
    fake_predictions.fail_mode = 'permission'
    payload = {'mode': 'ai', 'match_data': SAMPLE_MATCH, 'prediction_result': '主胜', 'confidence': 0.8}
    body = client.post('/api/v1/save-prediction', json=payload, headers=auth_header('tester')).json()
    assert body['code'] == 403
    assert '会员' in body['message']


def test_save_prediction_storage_error(client, fake_users, fake_predictions):
    fake_users.add('tester')
    fake_predictions.fail_mode = 'error'
    payload = {'mode': 'classic', 'match_data': SAMPLE_MATCH, 'prediction_result': '主胜', 'confidence': 0.8}
    body = client.post('/api/v1/save-prediction', json=payload, headers=auth_header('tester')).json()
    assert body['code'] == 500
    assert '保存失败' in body['message']


def test_save_prediction_db_unavailable(client, fake_users, fake_db):
    fake_users.add('tester')
    fake_db.configured = False
    payload = {'mode': 'classic', 'match_data': SAMPLE_MATCH, 'prediction_result': '主胜', 'confidence': 0.8}
    body = client.post('/api/v1/save-prediction', json=payload, headers=auth_header('tester')).json()
    assert body['code'] == 500
    assert body['message'] == '数据库未配置'


def test_prediction_stats_success(client):
    body = client.get('/api/v1/prediction-stats').json()
    assert body['code'] == 0
    assert set(body['data']) == {'mode_stats', 'recent_predictions'}


def test_prediction_stats_db_unavailable(client, fake_db):
    fake_db.configured = False
    body = client.get('/api/v1/prediction-stats').json()
    assert body['code'] == 500


def test_prediction_stats_query_error(client, fake_predictions, monkeypatch):
    def boom():
        raise RuntimeError('模拟查询失败')

    monkeypatch.setattr(fake_predictions, 'stats', boom)
    body = client.get('/api/v1/prediction-stats').json()
    assert body['code'] == 500
    assert '获取统计信息失败' in body['message']

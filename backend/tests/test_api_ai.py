"""AI 预测接口测试（预测器打桩，不产生真实 Gemini 调用）。"""
import pytest

from app.api.v1 import ai as ai_api
from conftest import SAMPLE_MATCH, auth_header


class FakePredictor:
    def __init__(self, error: bool = False):
        self.error = error
        self.received = None

    def analyze_matches(self, matches):
        self.received = matches
        if self.error:
            raise RuntimeError('模拟模型调用失败')
        return [{'home_team': m['home_team'], 'away_team': m['away_team'], 'recommendation': '主胜', 'status': 'success'}
                for m in matches]


@pytest.fixture()
def fake_predictor(monkeypatch):
    predictor = FakePredictor()
    monkeypatch.setattr(ai_api, '_get_predictor', lambda: predictor)
    return predictor


def test_ai_predict_requires_configuration(client, fake_users, monkeypatch):
    """未配置 GEMINI_API_KEY 且无预测器时给出明确提示。"""
    fake_users.add('tester')
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH]}, headers=auth_header('tester')).json()
    assert body['code'] == 500
    assert 'AI_MODE' in body['message']


def test_ai_predict_success(client, fake_predictor, fake_users):
    fake_users.add('tester')
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH]}, headers=auth_header('tester')).json()
    assert body['code'] == 0
    assert body['data']['count'] == 1
    assert body['data']['predictions'][0]['recommendation'] == '主胜'
    assert fake_predictor.received[0]['home_team'] == 'Arsenal FC'


def test_ai_predict_model_error(client, fake_predictor, fake_users):
    fake_predictor.error = True
    fake_users.add('tester')
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH]}, headers=auth_header('tester')).json()
    assert body['code'] == 500
    assert 'AI预测失败' in body['message']
    assert fake_users.users['tester']['daily_predictions_used'] == 0


def test_ai_predict_invalid_payload(client, fake_predictor):
    assert client.post('/api/v1/ai/predict', json={'matches': []}).status_code == 422


def test_ai_predict_requires_login(client, fake_predictor):
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH]}).json()
    assert body['code'] == 401
    assert fake_predictor.received is None


def test_ai_batch_quota_rejected_before_model(client, fake_predictor, fake_users):
    fake_users.add('tester', daily_used=2)
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH] * 2},
                       headers=auth_header('tester')).json()
    assert body['code'] == 403
    assert fake_predictor.received is None
    assert fake_users.users['tester']['daily_predictions_used'] == 2


def test_ai_partial_failure_refunds_only_failed_matches(client, fake_predictor, fake_users, monkeypatch):
    user = fake_users.add('tester')
    monkeypatch.setattr(fake_predictor, 'analyze_matches', lambda matches: [
        {'status': 'success'}, {'status': 'error'}])
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH] * 2},
                       headers=auth_header('tester')).json()
    assert body['data']['failed_count'] == 1
    assert user['daily_predictions_used'] == 1
    assert user['total_predictions'] == 1

"""AI 预测接口测试（预测器打桩，不产生真实 Gemini 调用）。"""
import pytest

from app.api.v1 import ai as ai_api
from conftest import SAMPLE_MATCH


class FakePredictor:
    def __init__(self, error: bool = False):
        self.error = error
        self.received = None

    def analyze_matches(self, matches):
        self.received = matches
        if self.error:
            raise RuntimeError('模拟模型调用失败')
        return [{'home_team': m['home_team'], 'away_team': m['away_team'], 'recommendation': '主胜'}
                for m in matches]


@pytest.fixture()
def fake_predictor(monkeypatch):
    predictor = FakePredictor()
    monkeypatch.setattr(ai_api, '_get_predictor', lambda: predictor)
    return predictor


def test_ai_predict_requires_gemini_key(client):
    """未配置 GEMINI_API_KEY 且无预测器时给出明确提示。"""
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH]}).json()
    assert body['code'] == 500
    assert 'GEMINI_API_KEY' in body['message']


def test_ai_predict_success(client, fake_predictor):
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH]}).json()
    assert body['code'] == 0
    assert body['data']['count'] == 1
    assert body['data']['predictions'][0]['recommendation'] == '主胜'
    assert fake_predictor.received[0]['home_team'] == 'Arsenal FC'


def test_ai_predict_model_error(client, fake_predictor):
    fake_predictor.error = True
    body = client.post('/api/v1/ai/predict', json={'matches': [SAMPLE_MATCH]}).json()
    assert body['code'] == 500
    assert 'AI预测失败' in body['message']


def test_ai_predict_invalid_payload(client, fake_predictor):
    assert client.post('/api/v1/ai/predict', json={'matches': []}).status_code == 422

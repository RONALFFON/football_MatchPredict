"""英超 Agent 对话接口测试（SSE 流式；LLM 与数据层打桩）。"""
import json

import pytest

from app.api.v1 import agent_pl
from conftest import auth_header


ANSWER_EVENTS = [
    {'type': 'tool_call', 'tool': 'get_recent_form'},
    {'type': 'text_delta', 'text': '阿森纳近期状态出色。'},
    {'type': 'done'},
]


@pytest.fixture()
def stub_agent(monkeypatch):
    """替换 run_agent 与 GeminiClient，避免真实模型调用。"""
    state = {'events': list(ANSWER_EVENTS), 'calls': []}

    def fake_run_agent(message, history, llm=None, provider=None):
        state['calls'].append({'message': message, 'history': history, 'llm': llm, 'provider': provider})
        yield from state['events']

    monkeypatch.setattr(agent_pl, 'run_agent', fake_run_agent)
    monkeypatch.setattr(agent_pl, 'GeminiClient', lambda api_key, model: object())
    return state


def _sse_events(response) -> list[str]:
    return [line[len('data: '):] for line in response.text.splitlines() if line.startswith('data: ')]


def test_agent_requires_login(client):
    body = client.post('/api/v1/pl/agent/chat', json={'message': 'hi'}).json()
    assert body['code'] == 401
    assert body['message'] == '请先登录再使用 AI 分析'


def test_agent_quota_exhausted(client, fake_users):
    fake_users.add('tester', daily_used=3)
    body = client.post('/api/v1/pl/agent/chat', json={'message': 'hi'}, headers=auth_header('tester')).json()
    assert body['code'] == 403
    assert '升级会员' in body['message']


def test_agent_chat_streams_and_consumes_quota(client, fake_users, stub_agent):
    fake_users.add('tester')
    response = client.post(
        '/api/v1/pl/agent/chat',
        json={'message': '阿森纳近况如何？', 'history': [{'role': 'user', 'text': 'hi'}]},
        headers=auth_header('tester'),
    )
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    events = _sse_events(response)
    assert events[-1] == '[DONE]'
    parsed = [json.loads(event) for event in events[:-1]]
    assert [event['type'] for event in parsed] == ['tool_call', 'text_delta', 'done']
    assert '阿森纳' in parsed[1]['text']
    # 有效回答后扣减免费配额
    assert fake_users.users['tester']['daily_predictions_used'] == 1
    # 历史对话与消息透传给 agent
    assert stub_agent['calls'][0]['message'] == '阿森纳近况如何？'
    assert stub_agent['calls'][0]['history'] == [{'role': 'user', 'text': 'hi'}]


def test_agent_premium_no_quota_limit(client, fake_users, stub_agent):
    fake_users.add('tester', user_type='premium', daily_used=99)
    response = client.post('/api/v1/pl/agent/chat', json={'message': 'hi'}, headers=auth_header('tester'))
    assert response.status_code == 200
    assert _sse_events(response)[-1] == '[DONE]'


def test_agent_no_answer_does_not_consume_quota(client, fake_users, stub_agent):
    fake_users.add('tester')
    stub_agent['events'] = [{'type': 'error', 'text': '无可用数据'}]
    response = client.post('/api/v1/pl/agent/chat', json={'message': 'hi'}, headers=auth_header('tester'))
    events = _sse_events(response)
    assert events[-1] == '[DONE]'
    assert fake_users.users['tester']['daily_predictions_used'] == 0

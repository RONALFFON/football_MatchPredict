"""英超 Agent 编排器：Gemini Function Calling + ReAct 循环 + SSE 流式输出。

事件协议（供前端消费）：
  {"type": "tool_call",   "tool": "...", "args": {...}}
  {"type": "tool_result", "tool": "...", "result": {...}}
  {"type": "text_delta",  "text": "..."}
  {"type": "done",        "rounds": n}
  {"type": "error",       "message": "..."}
"""
import json
import logging
from typing import Generator

import requests

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOL_DECLARATIONS, execute_tool
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models'
MAX_TOOL_ROUNDS = 5


def _headers() -> dict:
    return {'Content-Type': 'application/json', 'x-goog-api-key': settings.gemini_api_key}


def _generate(contents: list[dict]) -> dict:
    """单轮 generateContent（带 function 声明）。"""
    payload = {
        'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
        'contents': contents,
        'tools': [{'function_declarations': TOOL_DECLARATIONS}],
        'generationConfig': {'temperature': 0.4, 'maxOutputTokens': 1024},
    }
    resp = requests.post(f'{BASE_URL}/{settings.gemini_model}:generateContent',
                         headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _stream_final(contents: list[dict]) -> Generator[str, None, None]:
    """最终回答走 streamGenerateContent(SSE)，逐块产出文本。"""
    payload = {
        'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
        'contents': contents,
        'generationConfig': {'temperature': 0.5, 'maxOutputTokens': 1024},
    }
    with requests.post(f'{BASE_URL}/{settings.gemini_model}:streamGenerateContent?alt=sse',
                       headers=_headers(), json=payload, timeout=60, stream=True) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith('data:'):
                continue
            try:
                chunk = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            for part in chunk.get('candidates', [{}])[0].get('content', {}).get('parts', []):
                if 'text' in part:
                    yield part['text']


def run_agent(question: str, history: list[dict] | None = None) -> Generator[dict, None, None]:
    """执行一次 Agent 对话，产出事件流。history 为 [{role, text}] 的早期上下文。"""
    if not settings.gemini_api_key:
        yield {'type': 'error', 'message': 'AI服务未配置（缺少 GEMINI_API_KEY）'}
        return

    contents: list[dict] = []
    for msg in (history or [])[-10:]:  # 会话记忆窗口：最近 10 轮
        contents.append({'role': 'user' if msg['role'] == 'user' else 'model',
                         'parts': [{'text': msg['text']}]})
    contents.append({'role': 'user', 'parts': [{'text': question}]})

    try:
        for round_idx in range(MAX_TOOL_ROUNDS):
            data = _generate(contents)
            candidate = data.get('candidates', [{}])[0]
            parts = candidate.get('content', {}).get('parts', [])

            function_calls = [p['functionCall'] for p in parts if 'functionCall' in p]
            if not function_calls:
                # 模型直接给出最终回答 → 用流式接口重新生成以获得打字机体验
                # （若本轮已有文本则直接透出，避免重复消耗）
                inline_text = ''.join(p.get('text', '') for p in parts)
                if inline_text:
                    yield {'type': 'text_delta', 'text': inline_text}
                else:
                    for piece in _stream_final(contents):
                        yield {'type': 'text_delta', 'text': piece}
                yield {'type': 'done', 'rounds': round_idx + 1}
                return

            # 回填 model 的 functionCall，再逐个执行工具
            contents.append({'role': 'model', 'parts': parts})
            for call in function_calls:
                name, args = call.get('name', ''), call.get('args', {}) or {}
                yield {'type': 'tool_call', 'tool': name, 'args': args}
                result = execute_tool(name, args)
                yield {'type': 'tool_result', 'tool': name, 'result': result}
                contents.append({'role': 'user', 'parts': [{
                    'functionResponse': {'name': name, 'response': result}
                }]})

        # 超过工具轮次上限，强制收尾
        for piece in _stream_final(contents):
            yield {'type': 'text_delta', 'text': piece}
        yield {'type': 'done', 'rounds': MAX_TOOL_ROUNDS}

    except requests.HTTPError as e:
        logger.error(f'Gemini API 调用失败: {e.response.status_code} {e.response.text[:200]}')
        yield {'type': 'error', 'message': f'AI 服务暂时不可用（{e.response.status_code}），请稍后重试'}
    except Exception as e:  # pragma: no cover
        logger.error(f'Agent 运行异常: {e}', exc_info=True)
        yield {'type': 'error', 'message': f'Agent 运行异常: {e}'}

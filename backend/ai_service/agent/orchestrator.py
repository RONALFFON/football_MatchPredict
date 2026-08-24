"""英超 Agent 编排器：ReAct 循环（Function Calling）+ 流式事件协议。

事件协议（供前端消费）：
  {"type": "tool_call",   "tool": "...", "args": {...}}
  {"type": "tool_result", "tool": "...", "result": {...}}
  {"type": "text_delta",  "text": "..."}
  {"type": "done",        "rounds": n}
  {"type": "error",       "message": "..."}

依赖注入：llm（GeminiClient）与 provider（PlDataProvider）均由调用方传入，
本模块不感知配置来源与数据来源。
"""
import logging
from typing import Generator, Optional

import requests

from ai_service.agent.prompts import SYSTEM_PROMPT
from ai_service.agent.tools import ToolRegistry
from ai_service.agent.interfaces import PlDataProvider
from ai_service.llm import GeminiClient, extract_text

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


def run_agent(question: str,
              history: Optional[list] = None,
              *,
              llm: GeminiClient,
              provider: PlDataProvider) -> Generator[dict, None, None]:
    """执行一次 Agent 对话，产出事件流。history 为 [{role, text}] 的早期上下文。"""
    if not llm.available:
        yield {'type': 'error', 'message': 'AI服务未配置（缺少 GEMINI_API_KEY）'}
        return

    registry = ToolRegistry(provider)

    contents: list[dict] = []
    for msg in (history or [])[-10:]:  # 会话记忆窗口：最近 10 轮
        contents.append({'role': 'user' if msg['role'] == 'user' else 'model',
                         'parts': [{'text': msg['text']}]})
    contents.append({'role': 'user', 'parts': [{'text': question}]})

    try:
        for round_idx in range(MAX_TOOL_ROUNDS):
            data = llm.generate(contents, system=SYSTEM_PROMPT,
                                tools=registry.declarations, temperature=0.4)
            parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])

            function_calls = [p['functionCall'] for p in parts if 'functionCall' in p]
            if not function_calls:
                # 模型直接给出最终回答：有文本则直接透出，否则走流式补齐打字机体验
                inline_text = extract_text({'candidates': [{'content': {'parts': parts}}]})
                if inline_text:
                    yield {'type': 'text_delta', 'text': inline_text}
                else:
                    for piece in llm.stream_text(contents, system=SYSTEM_PROMPT, temperature=0.5):
                        yield {'type': 'text_delta', 'text': piece}
                yield {'type': 'done', 'rounds': round_idx + 1}
                return

            # 回填 model 的 functionCall，再逐个执行工具
            contents.append({'role': 'model', 'parts': parts})
            for call in function_calls:
                name, args = call.get('name', ''), call.get('args', {}) or {}
                yield {'type': 'tool_call', 'tool': name, 'args': args}
                result = registry.execute(name, args)
                yield {'type': 'tool_result', 'tool': name, 'result': result}
                contents.append({'role': 'user', 'parts': [{
                    'functionResponse': {'name': name, 'response': result}
                }]})

        # 超过工具轮次上限，强制收尾
        for piece in llm.stream_text(contents, system=SYSTEM_PROMPT, temperature=0.5):
            yield {'type': 'text_delta', 'text': piece}
        yield {'type': 'done', 'rounds': MAX_TOOL_ROUNDS}

    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        logger.error(f'Gemini API 调用失败: {status}')
        yield {'type': 'error', 'message': f'AI 服务暂时不可用（{status}），请稍后重试'}
    except Exception as e:  # pragma: no cover
        logger.error(f'Agent 运行异常: {e}', exc_info=True)
        yield {'type': 'error', 'message': f'Agent 运行异常: {e}'}

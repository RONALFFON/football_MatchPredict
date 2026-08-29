"""英超 Agent 编排器：ReAct 循环（Function Calling）+ 流式事件协议。

事件协议（供前端消费）：
  {"type": "tool_call",   "tool": "...", "args": {...}}
  {"type": "tool_result", "tool": "...", "result": {...}}
  {"type": "text_delta",  "text": "..."}
  {"type": "done",        "rounds": n}
  {"type": "error",       "message": "..."}

依赖注入：llm（OpenAICompatibleClient）与 provider（PlDataProvider）均由调用方传入，
本模块不感知配置来源与数据来源。
"""
import logging
import json
from typing import Generator, Optional

import requests

from ai_service.agent.prompts import SYSTEM_PROMPT
from ai_service.agent.tools import ToolRegistry
from ai_service.agent.interfaces import PlDataProvider
from ai_service.llm import OpenAICompatibleClient, extract_text

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5


def run_agent(question: str,
              history: Optional[list] = None,
              *,
              llm: OpenAICompatibleClient,
              provider: PlDataProvider) -> Generator[dict, None, None]:
    """执行一次 Agent 对话，产出事件流。history 为 [{role, text}] 的早期上下文。"""
    if not llm.available:
        yield {'type': 'error', 'message': 'AI服务未配置（请检查 AI_MODE、AI_BASE_URL 和 AI_API_KEY）'}
        return

    registry = ToolRegistry(provider)

    contents: list[dict] = []
    for msg in (history or [])[-10:]:  # 会话记忆窗口：最近 10 轮
        contents.append({'role': 'user' if msg['role'] == 'user' else 'assistant',
                         'content': msg['text']})
    contents.append({'role': 'user', 'content': question})

    try:
        for round_idx in range(MAX_TOOL_ROUNDS):
            data = llm.generate(contents, system=SYSTEM_PROMPT,
                                tools=registry.declarations, temperature=0.4)
            message = (data.get('choices') or [{}])[0].get('message') or {}
            function_calls = message.get('tool_calls') or []
            if not function_calls:
                # 模型直接给出最终回答：有文本则直接透出，否则走流式补齐打字机体验
                inline_text = extract_text(data)
                if inline_text:
                    yield {'type': 'text_delta', 'text': inline_text}
                else:
                    for piece in llm.stream_text(contents, system=SYSTEM_PROMPT, temperature=0.5):
                        yield {'type': 'text_delta', 'text': piece}
                yield {'type': 'done', 'rounds': round_idx + 1}
                return

            # 回填 assistant 的 tool_calls，再逐个执行工具
            contents.append(message)
            for call in function_calls:
                function = call.get('function') or {}
                name = function.get('name', '')
                raw_args = function.get('arguments', '{}')
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    args = {}
                yield {'type': 'tool_call', 'tool': name, 'args': args}
                result = registry.execute(name, args)
                yield {'type': 'tool_result', 'tool': name, 'result': result}
                contents.append({
                    'role': 'tool',
                    'tool_call_id': call.get('id', ''),
                    'name': name,
                    'content': json.dumps(result, ensure_ascii=False),
                })

        # 超过工具轮次上限，强制收尾
        for piece in llm.stream_text(contents, system=SYSTEM_PROMPT, temperature=0.5):
            yield {'type': 'text_delta', 'text': piece}
        yield {'type': 'done', 'rounds': MAX_TOOL_ROUNDS}

    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        logger.error(f'AI API 调用失败: {status}')
        yield {'type': 'error', 'message': f'AI 服务暂时不可用（{status}），请稍后重试'}
    except Exception as e:  # pragma: no cover
        logger.error(f'Agent 运行异常: {e}', exc_info=True)
        yield {'type': 'error', 'message': f'Agent 运行异常: {e}'}

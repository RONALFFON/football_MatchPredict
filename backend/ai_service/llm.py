"""通用 OpenAI 兼容大模型 HTTP 封装：纯传输层，零业务语义。

职责单一：把消息、系统提示和工具声明翻译成 OpenAI 兼容的
Chat Completions API 调用。被 predictor（五大联赛预测）与
agent（英超分析）共同复用。
"""
import json
from typing import Any, Generator, Optional

import requests

DEFAULT_BASE_URL = 'https://token.sensenova.cn/v1'


class OpenAICompatibleClient:
    """OpenAI Chat Completions 兼容客户端（无状态，可安全共享）。"""

    def __init__(self, api_key: str, model_name: str,
                 base_url: str = DEFAULT_BASE_URL, timeout: int = 30):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
        }

    @staticmethod
    def _messages(messages: list[dict], system: Optional[str]) -> list[dict]:
        """将独立的 system 提示合并为 OpenAI 兼容消息列表。"""
        if not system:
            return messages
        return [{'role': 'system', 'content': system}, *messages]

    def _payload(self, messages: list[dict], system: Optional[str], tools: Optional[list[dict]],
                 temperature: float, max_tokens: int, stream: bool = False) -> dict:
        payload: dict = {
            'model': self.model_name,
            'messages': self._messages(messages, system),
            'temperature': temperature,
            'max_tokens': max_tokens,
        }
        if stream:
            payload['stream'] = True
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'
        return payload

    def generate(self, messages: list[dict], *, system: Optional[str] = None,
                 tools: Optional[list[dict]] = None,
                 temperature: float = 0.4, max_tokens: int = 1024) -> dict:
        """非流式生成，返回原始响应 JSON；HTTP 错误抛 requests.HTTPError。"""
        resp = requests.post(
            f'{self.base_url}/chat/completions',
            headers=self._headers(),
            json=self._payload(messages, system, tools, temperature, max_tokens),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def stream_text(self, messages: list[dict], *, system: Optional[str] = None,
                    temperature: float = 0.5, max_tokens: int = 1024) -> Generator[str, None, None]:
        """SSE 流式生成，按序产出文本片段。"""
        resp = requests.post(
            f'{self.base_url}/chat/completions',
            headers=self._headers(),
            json=self._payload(messages, system, None, temperature, max_tokens, stream=True),
            timeout=max(self.timeout, 60),
            stream=True,
        )
        try:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line or not line.startswith('data:'):
                    continue
                payload = line[5:].strip()
                if payload == '[DONE]':
                    break
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = _choices(chunk)
                if not choices:
                    continue
                delta = choices[0].get('delta') or {}
                text = _content_to_text(delta.get('content'))
                if text:
                    yield text
        finally:
            resp.close()


def _content_to_text(content: Any) -> str:
    """兼容纯文本和 OpenAI 风格的内容片段数组。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(
            item.get('text', '') for item in content
            if isinstance(item, dict) and item.get('type') == 'text'
        )
    return ''


def _choices(data: dict) -> list:
    """兼容当前 choices 和部分旧接口 data.choices 两种响应包装。"""
    choices = data.get('choices')
    if isinstance(choices, list):
        return choices
    nested = data.get('data')
    if isinstance(nested, dict) and isinstance(nested.get('choices'), list):
        return nested['choices']
    return []


def extract_text(data: dict) -> str:
    """从 Chat Completions 响应中提取纯文本（模块级工具函数）。"""
    choices = _choices(data)
    if not choices:
        return ''
    message = choices[0].get('message') or {}
    if isinstance(message, str):
        return message
    return _content_to_text(message.get('content'))

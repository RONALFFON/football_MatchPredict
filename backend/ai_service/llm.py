"""Gemini 底层 HTTP 封装：纯传输层，零业务语义。

职责单一：把「contents + system + tools」翻译成 Gemini API 调用。
被 predictor（五大联赛预测）与 agent（英超分析）共同复用。
"""
import json
from typing import Generator, Optional

import requests

DEFAULT_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models'


class GeminiClient:
    """Gemini REST 客户端（无状态，可安全共享）。"""

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
        return {'Content-Type': 'application/json', 'x-goog-api-key': self.api_key}

    def _payload(self, contents: list[dict], system: Optional[str], tools: Optional[list[dict]],
                 temperature: float, max_tokens: int) -> dict:
        payload: dict = {
            'contents': contents,
            'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens},
        }
        if system:
            payload['system_instruction'] = {'parts': [{'text': system}]}
        if tools:
            payload['tools'] = [{'function_declarations': tools}]
        return payload

    def generate(self, contents: list[dict], *, system: Optional[str] = None,
                 tools: Optional[list[dict]] = None,
                 temperature: float = 0.4, max_tokens: int = 1024) -> dict:
        """非流式生成，返回原始响应 JSON；HTTP 错误抛 requests.HTTPError。"""
        resp = requests.post(
            f'{self.base_url}/{self.model_name}:generateContent',
            headers=self._headers(),
            json=self._payload(contents, system, tools, temperature, max_tokens),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def stream_text(self, contents: list[dict], *, system: Optional[str] = None,
                    temperature: float = 0.5, max_tokens: int = 1024) -> Generator[str, None, None]:
        """SSE 流式生成，按序产出文本片段。"""
        resp = requests.post(
            f'{self.base_url}/{self.model_name}:streamGenerateContent?alt=sse',
            headers=self._headers(),
            json=self._payload(contents, system, None, temperature, max_tokens),
            timeout=max(self.timeout, 60),
            stream=True,
        )
        try:
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
        finally:
            resp.close()


def extract_text(data: dict) -> str:
    """从 generateContent 响应中提取纯文本（模块级工具函数）。"""
    parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
    return ''.join(p.get('text', '') for p in parts)

"""统一响应契约：{ code, message, data }，code=0 表示成功。"""
from typing import Any, Optional


def ok(data: Any = None, message: str = 'ok') -> dict:
    return {'code': 0, 'message': message, 'data': data}


def fail(message: str, code: int = 1, data: Any = None) -> dict:
    return {'code': code, 'message': message, 'data': data}

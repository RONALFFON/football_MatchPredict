"""JWT 令牌：前后端分离架构下替代 Flask session cookie。"""
from __future__ import annotations

import time

import jwt

from app.core.config import settings


def create_token(payload: dict) -> str:
    if not settings.jwt_secret:
        raise RuntimeError('JWT_SECRET 未配置')
    data = dict(payload)
    data['exp'] = int(time.time()) + settings.jwt_expire_hours * 3600
    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None

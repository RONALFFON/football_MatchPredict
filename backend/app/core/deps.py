"""依赖注入：桥接根目录 scripts/ 下的既有模块（数据库/爬虫/预测器），避免重复实现。"""
import sys
from pathlib import Path
from typing import Optional

from fastapi import Depends, Header

from app.core.response import fail
from app.core.security import decode_token

# 把项目根目录加入 sys.path，使 `from scripts.xxx import ...` 可用
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.database import prediction_db  # noqa: E402
except Exception:  # pragma: no cover - 数据库不可用时服务仍可启动
    prediction_db = None


def get_db():
    """数据库单例依赖，未配置时返回 None，由路由层给出友好错误。"""
    return prediction_db


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db=Depends(get_db),
) -> Optional[dict]:
    """解析 Bearer Token 并返回最新用户数据；无效/未登录返回 None。"""
    if not authorization or not authorization.lower().startswith('bearer '):
        return None
    payload = decode_token(authorization[7:].strip())
    if not payload:
        return None
    if db is None:
        return None
    return db.get_user_by_username(payload.get('username', ''))


def require_user(user=Depends(get_current_user)):
    """强制登录依赖：未登录直接返回 401 契约体。"""
    if user is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail=fail('请先登录', code=401))
    return user

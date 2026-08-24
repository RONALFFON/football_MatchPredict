"""用户认证：JWT 无状态方案（替代主站 session cookie）。

注意：密码哈希沿用主站 sha256 以兼容存量用户；新用户体系建议后续迁移 bcrypt。
"""
import hashlib
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from app.core.deps import get_db, get_current_user
from app.core.response import fail, ok
from app.core.security import create_token

router = APIRouter(prefix='/api/v1/auth', tags=['用户认证'])
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


def _hash_password(password: str) -> str:
    # 与主站 users 表存量 hash 兼容（历史原因使用裸 sha256）
    return hashlib.sha256(password.encode()).hexdigest()


def _user_payload(user: dict) -> dict:
    expires = user.get('membership_expires')
    return {
        'username': user['username'],
        'email': user.get('email'),
        'user_type': user['user_type'],
        'daily_predictions_used': user['daily_predictions_used'],
        'total_predictions': user['total_predictions'],
        'membership_expires': expires.isoformat() if expires else None,
    }


@router.post('/register')
def register(payload: RegisterRequest, db=Depends(get_db)):
    if db is None:
        return fail('注册失败：数据库服务不可用', code=500)
    username = payload.username.strip()
    if len(username) < 3:
        return fail('用户名长度至少3个字符')
    if len(payload.password) < 6:
        return fail('密码长度至少6个字符')
    try:
        if db.create_user(username, payload.email.strip(), _hash_password(payload.password)):
            return ok(message='注册成功，请登录')
        return fail('注册失败：用户名或邮箱已存在，或数据库写入失败', code=409)
    except Exception as e:  # pragma: no cover
        logger.error(f'用户注册失败: {e}', exc_info=True)
        return fail('注册失败，请稍后重试', code=500)


@router.post('/login')
def login(payload: LoginRequest, db=Depends(get_db)):
    if db is None:
        return fail('登录失败：数据库服务不可用', code=500)
    if not payload.username or not payload.password:
        return fail('请输入用户名和密码')
    try:
        user = db.authenticate_user(payload.username.strip(), _hash_password(payload.password))
        if not user:
            return fail('用户名或密码错误', code=401)
        token = create_token({'user_id': user['id'], 'username': user['username']})
        return ok({'token': token, 'user': _user_payload(user)}, '登录成功')
    except Exception as e:  # pragma: no cover
        logger.error(f'用户登录失败: {e}', exc_info=True)
        return fail('登录失败，请稍后重试', code=500)


@router.get('/me')
def me(user=Depends(get_current_user)):
    """获取当前用户最新状态（含每日配额重置后的数据）。"""
    if user is None:
        return fail('未登录', code=401)
    return ok({'user': _user_payload(user)})


@router.get('/can-predict')
def can_predict(user=Depends(get_current_user), db=Depends(get_db)):
    """检查当前用户是否还有预测配额。"""
    if user is None:
        return fail('未登录', code=401)
    can = db.can_user_predict(user['id'], user['user_type'], user['daily_predictions_used'])
    remaining = max(0, 3 - user['daily_predictions_used']) if user['user_type'] == 'free' else -1
    return ok({'can_predict': can, 'user_type': user['user_type'],
               'daily_used': user['daily_predictions_used'], 'remaining': remaining})

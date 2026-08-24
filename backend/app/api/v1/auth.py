"""用户认证 API。"""
import logging

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, get_db, get_users
from app.core.response import fail, ok
from app.core.security import create_token
from app.infrastructure.repositories import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth import hash_password, user_payload


router = APIRouter(prefix='/api/v1/auth', tags=['用户认证'])
logger = logging.getLogger(__name__)


@router.post('/register')
def register(payload: RegisterRequest, db=Depends(get_db), users: UserRepository = Depends(get_users)):
    if not db.configured:
        return fail('注册失败：数据库服务不可用', code=500)
    try:
        created = users.create(payload.username.strip(), str(payload.email), hash_password(payload.password))
        return ok(message='注册成功，请登录') if created else fail('注册失败：用户名或邮箱已存在', code=409)
    except Exception:
        logger.exception('用户注册失败')
        return fail('注册失败，请稍后重试', code=500)


@router.post('/login')
def login(payload: LoginRequest, db=Depends(get_db), users: UserRepository = Depends(get_users)):
    if not db.configured:
        return fail('登录失败：数据库服务不可用', code=500)
    try:
        user = users.authenticate(payload.username.strip(), hash_password(payload.password))
        if not user:
            return fail('用户名或密码错误', code=401)
        token = create_token({'user_id': user['id'], 'username': user['username']})
        return ok({'token': token, 'user': user_payload(user)}, '登录成功')
    except RuntimeError as exc:
        return fail(str(exc), code=500)
    except Exception:
        logger.exception('用户登录失败')
        return fail('登录失败，请稍后重试', code=500)


@router.get('/me')
def me(user=Depends(get_current_user)):
    return fail('未登录', code=401) if user is None else ok({'user': user_payload(user)})


@router.get('/can-predict')
def can_predict(user=Depends(get_current_user), users: UserRepository = Depends(get_users)):
    if user is None:
        return fail('未登录', code=401)
    remaining = -1 if user['user_type'] == 'premium' else max(0, 3 - user['daily_predictions_used'])
    return ok({
        'can_predict': users.can_predict(user),
        'user_type': user['user_type'],
        'daily_used': user['daily_predictions_used'],
        'remaining': remaining,
    })

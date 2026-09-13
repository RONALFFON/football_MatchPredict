"""个人权益和管理员会员操作；未接入支付渠道。"""
from typing import Literal, Optional
from uuid import UUID

import logging
import psycopg2
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.deps import require_user, require_system_admin, get_predictions, get_memberships
from app.core.config import settings
from app.infrastructure.database import database
from app.core.response import ok
from app.services.auth import user_payload
from app.infrastructure.membership_repository import MembershipNotReady, MembershipConflict

router = APIRouter(prefix='/api/v1', tags=['会员权益'])
logger = logging.getLogger(__name__)


class MembershipChange(BaseModel):
    action: Literal['extend', 'freeze', 'unfreeze', 'revoke']
    plan: Optional[Literal['monthly', 'annual']] = None
    reason: str = Field(min_length=2, max_length=500)
    request_id: UUID

    @field_validator('reason')
    @classmethod
    def reason_required(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError('请填写操作原因')
        return value

    @model_validator(mode='after')
    def plan_for_extension(self):
        if (self.action == 'extend') != (self.plan is not None):
            raise ValueError('只有开通或续期操作需要选择套餐')
        return self


@router.get('/account')
def account(user=Depends(require_user), predictions=Depends(get_predictions),
            offset: int = Query(0, ge=0, le=10000)):
    records = predictions.list_for_user(user['id'], 21, offset)
    return ok({'user': user_payload(user), 'saved_predictions': records[:20],
               'has_more': len(records) > 20})


@router.post('/admin/memberships/{username}')
def update_membership(username: str, payload: MembershipChange,
                      actor=Depends(require_system_admin), memberships=Depends(get_memberships)):
    try:
        return ok(memberships.change(actor, username, payload.action, payload.plan,
                                     payload.reason, str(payload.request_id)), '会员权益已更新')
    except MembershipNotReady as exc:
        raise HTTPException(503, str(exc)) from exc
    except MembershipConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except psycopg2.IntegrityError as exc:
        raise HTTPException(409, '操作冲突，请使用同一请求编号重试') from exc
    except Exception as exc:
        logger.exception('会员变更失败')
        raise HTTPException(503, '会员变更未完成，请使用同一请求编号重试') from exc


@router.get('/admin/memberships/{username}/history')
def membership_history(username: str, actor=Depends(require_system_admin), memberships=Depends(get_memberships)):
    try:
        return ok({'events': memberships.history(username)})
    except MembershipNotReady as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get('/admin/overview')
def admin_overview(actor=Depends(require_system_admin)):
    """系统管理台启动信息，不返回密钥或管理员邮箱。"""
    return ok({
        'role': 'system_admin',
        'database_configured': database.configured,
        'ai_ready': settings.ai_ready,
        'ai_mode': settings.ai_mode,
        'ai_model': settings.ai_model,
        'business_timezone': settings.business_timezone,
        'payment_enabled': False,
        'capabilities': [
            'membership_management',
            'membership_audit',
            'lottery_live_refresh',
        ],
    })

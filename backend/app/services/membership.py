"""会员权益、状态和续期规则；不处理支付或数据库写入。"""
from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
import hmac
from zoneinfo import ZoneInfo

from app.core.config import settings

FREE_DAILY_LIMIT = 3
PLANS = {'monthly': 1, 'annual': 12}


def business_now() -> datetime:
    return datetime.now(ZoneInfo(settings.business_timezone))


def expiry_time(value) -> datetime | None:
    if value is None or value == '':
        return None
    expiry = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    zone = ZoneInfo(settings.business_timezone)
    return expiry.replace(tzinfo=zone) if expiry.tzinfo is None else expiry.astimezone(zone)


def membership_status(user: dict, now: datetime | None = None) -> str:
    state = user.get('membership_state')
    if state in {'frozen', 'revoked'}:
        return state
    if user.get('user_type') != 'premium':
        return 'free'
    try:
        expiry = expiry_time(user.get('membership_expires'))
    except (ValueError, TypeError):
        return 'expired'
    if expiry is None:
        return 'lifetime'
    return 'active' if expiry > (now or business_now()) else 'expired'


def is_premium(user: dict) -> bool:
    return membership_status(user) in {'active', 'lifetime'}


def is_system_admin(user: dict) -> bool:
    configured_email = settings.system_admin_email.strip().casefold()
    user_email = str(user.get('email') or '').strip().casefold()
    if configured_email and hmac.compare_digest(
        user_email.encode('utf-8'), configured_email.encode('utf-8')
    ):
        return True
    ids = {value.strip() for value in settings.admin_user_ids.split(',') if value.strip()}
    return str(user.get('id')) in ids


# 兼容现有调用，权限语义统一为系统管理员。
is_admin = is_system_admin


def entitlement_payload(user: dict) -> dict:
    now = business_now()
    status = membership_status(user, now)
    unlimited = status in {'active', 'lifetime'}
    last_date = str(user.get('last_prediction_date') or '')[:10]
    used = (user.get('daily_predictions_used') or 0) if last_date == now.date().isoformat() else 0
    try:
        expiry = expiry_time(user.get('membership_expires'))
    except (TypeError, ValueError):
        expiry = None
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        'membership_status': status,
        'membership_expires': expiry.isoformat() if expiry else None,
        'daily_limit': None if unlimited else FREE_DAILY_LIMIT,
        'daily_used': used,
        'remaining': None if unlimited else max(0, FREE_DAILY_LIMIT - used),
        'quota_resets_at': tomorrow.isoformat(),
        'timezone': settings.business_timezone,
        'role': 'system_admin' if is_system_admin(user) else 'user',
        'is_admin': is_system_admin(user),
        'rules': {'classic': '免费计算', 'lottery': '免费计算',
                  'ai': '每场比赛计 1 次，失败返还', 'agent': '每次有效回答计 1 次',
                  'save': '保存不消耗 AI 次数'},
        'payment_enabled': False,
    }


def change_membership(user: dict, action: str, plan: str | None,
                      now: datetime | None = None) -> dict:
    now = now or business_now()
    status = membership_status(user, now)
    result = {key: user.get(key) for key in ('user_type', 'membership_expires', 'membership_state')}
    if action == 'extend':
        if plan not in PLANS:
            raise ValueError('请选择月度或年度会员')
        if status == 'lifetime':
            raise ValueError('长期会员无需续期')
        if status == 'frozen':
            raise ValueError('请先解除会员冻结再续期')
        expiry = expiry_time(user.get('membership_expires')) if status == 'active' else None
        start = max(now, expiry) if expiry else now
        index = start.year * 12 + start.month - 1 + PLANS[plan]
        year, month = divmod(index, 12)
        month += 1
        end = start.replace(year=year, month=month, day=min(start.day, monthrange(year, month)[1]))
        result.update(user_type='premium', membership_state='active', membership_expires=end.isoformat())
    elif action == 'freeze':
        if status not in {'active', 'lifetime'}:
            raise ValueError('只有有效会员可以冻结')
        result['membership_state'] = 'frozen'
    elif action == 'unfreeze':
        if status != 'frozen':
            raise ValueError('该会员未被冻结')
        result['membership_state'] = 'active'
    elif action == 'revoke':
        result.update(user_type='free', membership_state='revoked')
    else:
        raise ValueError('不支持的会员操作')
    return result

"""认证相关的纯业务逻辑。"""
from datetime import datetime

import hashlib
import hmac
import secrets

PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """PBKDF2-SHA256：随机盐与迭代次数随哈希保存。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                 salt.encode('ascii'), PASSWORD_ITERATIONS).hex()
    return f'pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}'


def verify_password(password: str, encoded: str) -> bool:
    if not isinstance(encoded, str):
        return False
    if len(encoded) == 64 and all(c in '0123456789abcdef' for c in encoded):
        return hmac.compare_digest(hashlib.sha256(password.encode('utf-8')).hexdigest(), encoded)
    try:
        algorithm, rounds, salt, expected = encoded.split('$')
        iterations = int(rounds)
        if algorithm != 'pbkdf2_sha256' or not 600_000 <= iterations <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                     salt.encode('ascii'), iterations).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, UnicodeError):
        return False


def is_premium(user: dict) -> bool:
    if user.get('user_type') != 'premium':
        return False
    expires = user.get('membership_expires')
    if not expires:
        return True  # 兼容已有长期会员。
    try:
        expiry = datetime.fromisoformat(str(expires).replace('Z', '+00:00'))
    except ValueError:
        return False
    return expiry > datetime.now(expiry.tzinfo)


def user_payload(user: dict) -> dict:
    return {
        'username': user['username'],
        'email': user.get('email'),
        'user_type': 'premium' if is_premium(user) else 'free',
        'daily_predictions_used': user['daily_predictions_used'],
        'total_predictions': user['total_predictions'],
        'membership_expires': user.get('membership_expires'),
    }

"""认证相关的纯业务逻辑。"""
import hashlib


def hash_password(password: str) -> str:
    """兼容现有 users 表的 SHA-256 密码哈希。"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def user_payload(user: dict) -> dict:
    return {
        'username': user['username'],
        'email': user.get('email'),
        'user_type': user['user_type'],
        'daily_predictions_used': user['daily_predictions_used'],
        'total_predictions': user['total_predictions'],
        'membership_expires': user.get('membership_expires'),
    }

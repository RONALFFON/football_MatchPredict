"""接口自动化测试公共夹具。

策略：通过 FastAPI dependency_overrides 把数据库仓储替换为内存假实现，
配置项（JWT/DB/Gemini）固定为测试值，保证测试不依赖真实数据库与外部 API。
"""
import pytest
from fastapi.testclient import TestClient

from app.core import deps
from app.core.config import settings
from app.core.security import create_token
from app.main import app


@pytest.fixture(autouse=True)
def _fixed_settings(monkeypatch):
    """固定测试环境配置：JWT 可用、数据库标记为已配置（真实连接已被假仓储替代）。"""
    monkeypatch.setattr(settings, 'jwt_secret', 'test-secret-key-0123456789abcdef')
    monkeypatch.setattr(settings, 'db_host', 'localhost')
    monkeypatch.setattr(settings, 'db_user', 'test')
    monkeypatch.setattr(settings, 'db_pass', 'test')
    monkeypatch.setattr(settings, 'gemini_api_key', '')


class FakeDb:
    """替代 Database 的配置探测对象。"""

    def __init__(self, configured: bool = True):
        self.configured = configured


class FakeUserRepository:
    """内存版用户仓储。"""

    def __init__(self):
        self.users: dict[str, dict] = {}
        self._next_id = 1

    def add(self, username: str, password_hash: str = '', *, user_type: str = 'free',
            daily_used: int = 0, total: int = 0, email: str = '') -> dict:
        user = {
            'id': self._next_id,
            'username': username,
            'email': email or f'{username}@example.com',
            'password_hash': password_hash,
            'user_type': user_type,
            'membership_expires': None,
            'daily_predictions_used': daily_used,
            'last_prediction_date': None,
            'total_predictions': total,
            'is_active': True,
        }
        self.users[username] = user
        self._next_id += 1
        return user

    def create(self, username: str, email: str, password_hash: str) -> bool:
        if username in self.users or any(u['email'] == email for u in self.users.values()):
            return False
        self.add(username, password_hash, email=email)
        return True

    def find_by_username(self, username: str) -> dict | None:
        return self.users.get(username)

    def authenticate(self, username: str, password_hash: str) -> dict | None:
        user = self.users.get(username)
        if user and user['password_hash'] == password_hash:
            return user
        return None

    def can_predict(self, user: dict) -> bool:
        return user['user_type'] == 'premium' or user['daily_predictions_used'] < 3

    def consume_prediction(self, user_id: int) -> dict | None:
        for user in self.users.values():
            if user['id'] == user_id:
                user['daily_predictions_used'] += 1
                user['total_predictions'] += 1
                return user
        return None


class FakePredictionRepository:
    """内存版预测记录仓储；保存后按 user_id 原子扣配额，与真实仓储行为一致。
    fail_mode 可模拟配额拒绝/保存异常。"""

    def __init__(self, users: 'FakeUserRepository | None' = None, fail_mode: str = ''):
        self.users = users
        self.records: list[dict] = []
        self.fail_mode = fail_mode

    def save_with_quota(self, data: dict) -> dict:
        if self.fail_mode == 'permission':
            raise PermissionError('今日免费预测次数已用完，请升级会员')
        if self.fail_mode == 'error':
            raise RuntimeError('模拟保存失败')
        self.records.append(data)
        updated = self.users.consume_prediction(data['user_id']) if self.users else None
        if updated is None:
            raise PermissionError('今日免费预测次数已用完，请升级会员')
        return updated

    def stats(self) -> dict:
        return {'mode_stats': [], 'recent_predictions': []}


class FakeLotteryRepository:
    def __init__(self, matches: list | None = None, error: bool = False):
        self.matches = matches if matches is not None else []
        self.error = error

    def get_matches(self, days_ahead: int) -> list[dict]:
        if self.error:
            raise RuntimeError('模拟查询失败')
        return self.matches


class FakeLotteryProvider:
    def __init__(self, matches: list | None = None, error: bool = False):
        self.matches = matches if matches is not None else []
        self.error = error

    def get_matches(self, days_ahead: int) -> list[dict]:
        if self.error:
            raise RuntimeError('模拟抓取失败')
        return self.matches


@pytest.fixture()
def fake_db():
    return FakeDb()


@pytest.fixture()
def fake_users():
    return FakeUserRepository()


@pytest.fixture()
def fake_predictions(fake_users):
    return FakePredictionRepository(users=fake_users)


@pytest.fixture()
def fake_lottery():
    return FakeLotteryRepository()


@pytest.fixture()
def fake_lottery_provider():
    return FakeLotteryProvider()


@pytest.fixture()
def client(fake_db, fake_users, fake_predictions, fake_lottery, fake_lottery_provider):
    """注入全部假依赖的测试客户端；退出时清理覆盖，避免用例间污染。"""
    app.dependency_overrides[deps.get_db] = lambda: fake_db
    app.dependency_overrides[deps.get_users] = lambda: fake_users
    app.dependency_overrides[deps.get_predictions] = lambda: fake_predictions
    app.dependency_overrides[deps.get_lottery] = lambda: fake_lottery
    app.dependency_overrides[deps.get_lottery_provider] = lambda: fake_lottery_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(username: str) -> dict:
    """生成登录用户请求头。"""
    return {'Authorization': f'Bearer {create_token({"user_id": 1, "username": username})}'}


SAMPLE_MATCH = {
    'home_team': 'Arsenal FC',
    'away_team': 'Chelsea FC',
    'league_name': '英超',
    'home_odds': 1.8,
    'draw_odds': 3.4,
    'away_odds': 4.2,
}

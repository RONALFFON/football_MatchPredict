"""用户认证接口测试：注册 / 登录 / me / can-predict。"""
import jwt

from app.core.config import settings
from app.services.auth import hash_password
from conftest import auth_header


REGISTER_PAYLOAD = {'username': 'tester', 'email': 'tester@example.com', 'password': 'secret123'}


def test_register_success(client, fake_users):
    response = client.post('/api/v1/auth/register', json=REGISTER_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body['code'] == 0
    assert body['message'] == '注册成功，请登录'
    assert 'tester' in fake_users.users
    # 密码以哈希存储，不落明文
    assert fake_users.users['tester']['password_hash'] == hash_password('secret123')


def test_register_duplicate_username_conflict(client, fake_users):
    fake_users.add('tester', email='other@example.com')
    response = client.post('/api/v1/auth/register', json=REGISTER_PAYLOAD)
    body = response.json()
    assert body['code'] == 409
    assert '已存在' in body['message']


def test_register_invalid_email_rejected(client):
    payload = {**REGISTER_PAYLOAD, 'email': 'not-an-email'}
    assert client.post('/api/v1/auth/register', json=payload).status_code == 422


def test_register_short_username_rejected(client):
    payload = {**REGISTER_PAYLOAD, 'username': 'ab'}
    assert client.post('/api/v1/auth/register', json=payload).status_code == 422


def test_register_db_unavailable(client, fake_db):
    fake_db.configured = False
    body = client.post('/api/v1/auth/register', json=REGISTER_PAYLOAD).json()
    assert body['code'] == 500
    assert '数据库' in body['message']


def test_login_success_returns_token(client, fake_users):
    fake_users.add('tester', hash_password('secret123'))
    response = client.post('/api/v1/auth/login', json={'username': 'tester', 'password': 'secret123'})
    body = response.json()
    assert body['code'] == 0
    token = body['data']['token']
    assert body['data']['user']['username'] == 'tester'
    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert decoded['username'] == 'tester'


def test_login_wrong_password(client, fake_users):
    fake_users.add('tester', hash_password('secret123'))
    body = client.post('/api/v1/auth/login', json={'username': 'tester', 'password': 'wrong'}).json()
    assert body['code'] == 401
    assert body['message'] == '用户名或密码错误'


def test_login_jwt_secret_missing(client, fake_users, monkeypatch):
    fake_users.add('tester', hash_password('secret123'))
    monkeypatch.setattr(settings, 'jwt_secret', '')
    body = client.post('/api/v1/auth/login', json={'username': 'tester', 'password': 'secret123'}).json()
    assert body['code'] == 500
    assert 'JWT_SECRET' in body['message']


def test_me_without_token(client):
    assert client.get('/api/v1/auth/me').json()['code'] == 401


def test_me_with_invalid_token(client):
    body = client.get('/api/v1/auth/me', headers={'Authorization': 'Bearer bad-token'}).json()
    assert body['code'] == 401


def test_me_with_valid_token(client, fake_users):
    fake_users.add('tester', user_type='premium', total=5)
    body = client.get('/api/v1/auth/me', headers=auth_header('tester')).json()
    assert body['code'] == 0
    assert body['data']['user']['username'] == 'tester'
    assert body['data']['user']['user_type'] == 'premium'
    assert body['data']['user']['total_predictions'] == 5


def test_me_when_db_unconfigured(client, fake_users, monkeypatch):
    fake_users.add('tester')
    monkeypatch.setattr(settings, 'db_pass', '')
    body = client.get('/api/v1/auth/me', headers=auth_header('tester')).json()
    assert body['code'] == 401


def test_can_predict_free_user(client, fake_users):
    fake_users.add('tester', daily_used=1)
    body = client.get('/api/v1/auth/can-predict', headers=auth_header('tester')).json()
    assert body['code'] == 0
    assert body['data'] == {
        'can_predict': True,
        'user_type': 'free',
        'daily_used': 1,
        'remaining': 2,
    }


def test_can_predict_quota_exhausted(client, fake_users):
    fake_users.add('tester', daily_used=3)
    body = client.get('/api/v1/auth/can-predict', headers=auth_header('tester')).json()
    assert body['data']['can_predict'] is False
    assert body['data']['remaining'] == 0


def test_can_predict_premium_unlimited(client, fake_users):
    fake_users.add('tester', user_type='premium', daily_used=99)
    body = client.get('/api/v1/auth/can-predict', headers=auth_header('tester')).json()
    assert body['data']['can_predict'] is True
    assert body['data']['remaining'] == -1

"""P0 会员本地回归，不提交，不访问真实数据库。"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from app.core import deps
from app.core.config import settings
from app.core.security import create_token
from app.services.membership import change_membership, membership_status, entitlement_payload, business_now
from app.infrastructure.membership_repository import MembershipNotReady
from conftest import auth_header, SAMPLE_MATCH

ZONE = ZoneInfo('Asia/Shanghai')


@pytest.mark.parametrize('start,plan,expected', [
    ('2026-01-31T10:30:00+08:00', 'monthly', '2026-02-28T10:30:00+08:00'),
    ('2028-02-29T10:30:00+08:00', 'annual', '2029-02-28T10:30:00+08:00'),
    ('2026-12-31T10:30:00+08:00', 'monthly', '2027-01-31T10:30:00+08:00'),
])
def test_calendar_plans(start, plan, expected):
    updated = change_membership({'user_type': 'free'}, 'extend', plan, datetime.fromisoformat(start))
    assert updated['membership_expires'] == expected
    assert updated['membership_state'] == 'active'


def test_renew_preserves_existing_time():
    user = {'user_type': 'premium', 'membership_expires': '2026-12-15T12:00:00+08:00'}
    updated = change_membership(user, 'extend', 'monthly', datetime(2026, 9, 9, tzinfo=ZONE))
    assert updated['membership_expires'] == '2027-01-15T12:00:00+08:00'


def test_expiry_boundary_uses_business_timezone():
    user = {'user_type': 'premium', 'membership_expires': '2026-09-10 00:00:00'}
    assert membership_status(user, datetime.fromisoformat('2026-09-09T15:59:59+00:00')) == 'active'
    assert membership_status(user, datetime.fromisoformat('2026-09-09T16:00:00+00:00')) == 'expired'


def test_frozen_and_revoked_members_have_no_premium_entitlement():
    for state in ('frozen', 'revoked'):
        user = {'user_type': 'premium', 'membership_state': state, 'daily_predictions_used': 3,
                'last_prediction_date': business_now().date().isoformat()}
        assert entitlement_payload(user)['remaining'] == 0
        assert entitlement_payload(user)['membership_status'] == state


def test_unfreeze_does_not_extend_expired_membership():
    user = {'user_type': 'premium', 'membership_state': 'frozen', 'membership_expires': '2020-01-01'}
    updated = change_membership(user, 'unfreeze', None)
    assert membership_status(updated) == 'expired'


def test_existing_lifetime_cannot_be_accidentally_shortened():
    with pytest.raises(ValueError, match='长期会员'):
        change_membership({'user_type': 'premium'}, 'extend', 'monthly')


def test_account_requires_login(client):
    assert client.get('/api/v1/account').status_code == 401


def test_account_only_returns_current_users_records(client, fake_users, fake_predictions):
    first = fake_users.add('first')
    second = fake_users.add('second')
    fake_predictions.records.extend([{'user_id': first['id'], 'prediction_id': 'first'},
                                     {'user_id': second['id'], 'prediction_id': 'second'}])
    body = client.get('/api/v1/account', headers=auth_header('first')).json()['data']
    assert [r['prediction_id'] for r in body['saved_predictions']] == ['first']
    assert body['user']['remaining'] == 3 and body['user']['payment_enabled'] is False


def test_non_admin_cannot_change_or_read_memberships(client, fake_users):
    fake_users.add('tester', user_type='premium')
    payload = {'action': 'extend', 'plan': 'annual', 'reason': '人工开通', 'request_id': str(uuid4())}
    assert client.post('/api/v1/admin/memberships/tester', json=payload,
                       headers=auth_header('tester')).status_code == 403
    assert client.get('/api/v1/admin/memberships/tester/history', headers=auth_header('tester')).status_code == 403


def test_configured_email_is_system_admin_case_insensitively(client, fake_users):
    fake_users.add('root-admin', email='ADMIN@MATCHPREDICT.EXAMPLE')
    response = client.get('/api/v1/admin/overview', headers=auth_header('root-admin'))
    assert response.status_code == 200
    body = response.json()['data']
    assert body['role'] == 'system_admin'
    assert 'membership_management' in body['capabilities']

    account = client.get('/api/v1/account', headers=auth_header('root-admin')).json()['data']
    assert account['user']['is_admin'] is True
    assert account['user']['role'] == 'system_admin'


def test_admin_overview_does_not_expose_configured_email(client, fake_users):
    fake_users.add('root-admin', email=settings.system_admin_email)
    text = client.get('/api/v1/admin/overview', headers=auth_header('root-admin')).text
    assert settings.system_admin_email not in text


def test_missing_migration_fails_closed(client, fake_users, monkeypatch):
    user = fake_users.add('tester')
    monkeypatch.setattr(settings, 'admin_user_ids', str(user['id']))
    class MissingRepository:
        def change(self, *args):
            raise MembershipNotReady('会员管理尚未启用')
    from app.main import app
    app.dependency_overrides[deps.get_memberships] = lambda: MissingRepository()
    payload = {'action': 'extend', 'plan': 'monthly', 'reason': '人工开通', 'request_id': str(uuid4())}
    response = client.post('/api/v1/admin/memberships/tester', json=payload, headers=auth_header('tester'))
    assert response.status_code == 503
    assert user['user_type'] == 'free'


def test_admin_payload_requires_plan_reason_and_request_id(client, fake_users, monkeypatch):
    user = fake_users.add('tester')
    monkeypatch.setattr(settings, 'admin_user_ids', str(user['id']))
    for payload in [
        {'action': 'extend', 'reason': '人工开通', 'request_id': str(uuid4())},
        {'action': 'extend', 'plan': 'monthly', 'reason': '  ', 'request_id': str(uuid4())},
        {'action': 'revoke', 'plan': 'annual', 'reason': '人工撤销', 'request_id': str(uuid4())},
    ]:
        assert client.post('/api/v1/admin/memberships/tester', json=payload,
                           headers=auth_header('tester')).status_code == 422


def test_repeated_save_is_free_and_does_not_trust_client_result(client, fake_users, fake_predictions):
    user = fake_users.add('tester', daily_used=3)
    payload = {'mode': 'classic', 'match_data': SAMPLE_MATCH, 'prediction_result': '伪造结果',
               'confidence': 999, 'request_id': str(uuid4())}
    for _ in range(2):
        body = client.post('/api/v1/save-prediction', json=payload, headers=auth_header('tester')).json()
        assert body['code'] == 0
    assert user['daily_predictions_used'] == 3
    assert len(fake_predictions.records) == 1
    assert fake_predictions.records[0]['predicted_result'] != '伪造结果'
    assert fake_predictions.records[0]['prediction_confidence'] <= 10


def test_ai_receipt_cannot_be_used_for_login_or_by_another_user(client, fake_users, fake_predictions):
    owner = fake_users.add('owner')
    fake_users.add('other')
    receipt = create_token({'purpose': 'prediction_save', 'username': 'owner', 'user_id': owner['id'],
                            'record': {'prediction_id': 'ai_1', 'user_id': owner['id']}})
    assert client.get('/api/v1/account', headers={'Authorization': 'Bearer ' + receipt}).status_code == 401
    payload = {'mode': 'ai', 'save_receipt': receipt}
    assert client.post('/api/v1/save-prediction', json=payload, headers=auth_header('other')).json()['code'] == 403
    for _ in range(2):
        assert client.post('/api/v1/save-prediction', json=payload, headers=auth_header('owner')).json()['code'] == 0
    assert owner['daily_predictions_used'] == 0
    assert len(fake_predictions.records) == 1


class TransactionDb:
    """执行真实仓储方法，模拟提交/回滚与审计失败。"""
    def __init__(self, fail_audit=False):
        self.user = {'id': 7, 'username': 'target', 'user_type': 'free',
                     'membership_state': None, 'membership_expires': None}
        self.events = {}
        self.fail_audit = fail_audit
        self.row = None

    def connection(self):
        from contextlib import contextmanager
        from copy import deepcopy
        @contextmanager
        def transaction():
            snapshot = deepcopy((self.user, self.events))
            try:
                yield self
            except Exception:
                self.user, self.events = snapshot
                raise
        return transaction()

    def cursor(self, **kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=()):
        assert sql.count('%s') == len(params)
        if 'to_regclass' in sql:
            self.row = {'ready': True}
        elif 'FOR UPDATE' in sql:
            self.row = dict(self.user)
        elif 'SELECT fingerprint' in sql:
            self.row = self.events.get(tuple(params))
        elif sql.startswith('UPDATE users'):
            self.user.update(user_type=params[0], membership_state=params[1], membership_expires=params[2])
        elif 'INSERT INTO membership_events' in sql:
            if self.fail_audit:
                raise RuntimeError('审计写入失败')
            self.events[(params[0], params[2])] = {
                'fingerprint': params[3], 'before_state': params[7].adapted, 'after_state': params[8].adapted}
        else:
            raise AssertionError(sql)

    def fetchone(self):
        return self.row


def test_membership_repository_replay_does_not_extend_twice():
    from app.infrastructure.membership_repository import MembershipRepository, MembershipConflict
    db = TransactionDb()
    repo = MembershipRepository(db)
    request_id = str(uuid4())
    first = repo.change({'id': 1}, 'target', 'extend', 'monthly', '人工开通', request_id)
    replay = repo.change({'id': 1}, 'target', 'extend', 'monthly', '人工开通', request_id)
    assert first['after'] == replay['after']
    assert replay['replayed'] is True and len(db.events) == 1
    with pytest.raises(MembershipConflict):
        repo.change({'id': 1}, 'target', 'extend', 'annual', '人工开通', request_id)
    assert len(db.events) == 1


def test_audit_failure_rolls_back_membership_change():
    from app.infrastructure.membership_repository import MembershipRepository
    db = TransactionDb(fail_audit=True)
    with pytest.raises(RuntimeError, match='审计写入失败'):
        MembershipRepository(db).change({'id': 1}, 'target', 'extend', 'monthly', '人工开通', str(uuid4()))
    assert db.user['user_type'] == 'free'
    assert db.user['membership_expires'] is None and db.events == {}

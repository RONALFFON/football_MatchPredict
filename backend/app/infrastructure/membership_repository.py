"""会员变更与审计使用同一事务；缺少迁移时拒绝写入。"""
from __future__ import annotations

import hashlib
import json

from psycopg2.extras import RealDictCursor, Json

from app.infrastructure.repositories import USER_FIELDS, _json_row
from app.services.membership import change_membership, expiry_time


class MembershipNotReady(RuntimeError):
    pass


class MembershipConflict(ValueError):
    pass


class MembershipRepository:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _require_schema(cursor):
        cursor.execute("""SELECT to_regclass('public.membership_events') IS NOT NULL
            AND EXISTS (SELECT 1 FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = 'users'
                          AND column_name = 'membership_state') AS ready""")
        if not cursor.fetchone()['ready']:
            raise MembershipNotReady('会员管理尚未启用，请联系管理员完成数据库迁移')

    def change(self, actor: dict, username: str, action: str, plan: str | None,
               reason: str, request_id: str) -> dict:
        fingerprint = hashlib.sha256(json.dumps(
            [username, action, plan, reason], ensure_ascii=False).encode('utf-8')).hexdigest()
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            self._require_schema(cursor)
            cursor.execute(f'SELECT {USER_FIELDS} FROM users WHERE username = %s AND is_active = TRUE FOR UPDATE',
                           (username,))
            row = cursor.fetchone()
            if row is None:
                raise LookupError('用户不存在或账号已停用')
            user = _json_row(row)
            cursor.execute("""SELECT fingerprint, before_state, after_state, action, created_at
                FROM membership_events WHERE actor_user_id = %s AND request_id = %s""",
                (actor['id'], request_id))
            event = cursor.fetchone()
            if event:
                if event['fingerprint'] != fingerprint:
                    raise MembershipConflict('该请求编号已用于其他操作，请刷新后重试')
                return {'username': username, 'before': event['before_state'],
                        'after': event['after_state'], 'replayed': True}
            before = {key: user.get(key) for key in ('user_type', 'membership_state', 'membership_expires')}
            after = change_membership(user, action, plan)
            cursor.execute("""UPDATE users SET user_type = %s, membership_state = %s,
                membership_expires = %s WHERE id = %s""",
                (after['user_type'], after['membership_state'], expiry_time(after['membership_expires']), user['id']))
            cursor.execute("""INSERT INTO membership_events
                (actor_user_id, user_id, request_id, fingerprint, action, plan, reason, before_state, after_state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (actor['id'], user['id'], request_id, fingerprint, action, plan, reason,
                 Json(before, dumps=lambda v: json.dumps(v, ensure_ascii=False)),
                 Json(after, dumps=lambda v: json.dumps(v, ensure_ascii=False))))
        return {'username': username, 'before': before, 'after': after, 'replayed': False}

    def history(self, username: str) -> list[dict]:
        with self.db.connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cursor:
            self._require_schema(cursor)
            cursor.execute("""SELECT e.actor_user_id, e.action, e.plan, e.reason,
                       e.before_state, e.after_state, e.created_at
                FROM membership_events e JOIN users u ON u.id = e.user_id
                WHERE u.username = %s ORDER BY e.created_at DESC, e.id DESC LIMIT 50""", (username,))
            return [_json_row(row) for row in cursor.fetchall()]

-- 待人工审核后执行。本程序不会自动运行此文件。
-- 要求：既有 public.users 表；会员开通仅为后台管理，不代表收到付款。
BEGIN;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS membership_state VARCHAR(16)
    CHECK (membership_state IN ('active', 'frozen', 'revoked'));
-- NULL 保留既有会员兼容逻辑，不自动给任何人开通会员。
CREATE TABLE IF NOT EXISTS public.membership_events (
    id BIGSERIAL PRIMARY KEY,
    actor_user_id INTEGER NOT NULL REFERENCES public.users(id),
    user_id INTEGER NOT NULL REFERENCES public.users(id),
    request_id UUID NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    action VARCHAR(16) NOT NULL CHECK (action IN ('extend', 'freeze', 'unfreeze', 'revoke')),
    plan VARCHAR(16) CHECK (plan IN ('monthly', 'annual')),
    reason VARCHAR(500) NOT NULL,
    before_state JSONB NOT NULL,
    after_state JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (actor_user_id, request_id)
);
CREATE INDEX IF NOT EXISTS idx_membership_events_user_date
    ON public.membership_events(user_id, created_at DESC, id DESC);
COMMIT;

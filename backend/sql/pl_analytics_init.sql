-- 英超专项分析数据表（逻辑隔离于主站业务表）
-- 用法：psql -h <host> -U <user> -d <db> -f pl_analytics_init.sql

CREATE SCHEMA IF NOT EXISTS pl_analytics;

-- 球队
CREATE TABLE IF NOT EXISTS pl_analytics.pl_teams (
    id          SERIAL PRIMARY KEY,
    api_team_id INTEGER UNIQUE,
    name        VARCHAR(100) NOT NULL,
    short_name  VARCHAR(50),
    crest_url   TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 赛程与结果（match_uid 幂等键）
CREATE TABLE IF NOT EXISTS pl_analytics.pl_matches (
    id         SERIAL PRIMARY KEY,
    match_uid  VARCHAR(64) UNIQUE NOT NULL,
    season     VARCHAR(9) NOT NULL,           -- 如 2024
    round      VARCHAR(20),
    home_team  VARCHAR(100) NOT NULL,
    away_team  VARCHAR(100) NOT NULL,
    utc_date   TIMESTAMP,
    status     VARCHAR(20) DEFAULT 'SCHEDULED', -- SCHEDULED/LIVE/FINISHED
    home_score INTEGER,
    away_score INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pl_matches_date ON pl_analytics.pl_matches (season, utc_date);
CREATE INDEX IF NOT EXISTS idx_pl_matches_status ON pl_analytics.pl_matches (status);

-- 积分榜
CREATE TABLE IF NOT EXISTS pl_analytics.pl_standings (
    id            SERIAL PRIMARY KEY,
    season        VARCHAR(9) NOT NULL,
    team_name     VARCHAR(100) NOT NULL,
    position      INTEGER,
    played        INTEGER DEFAULT 0,
    won           INTEGER DEFAULT 0,
    drawn         INTEGER DEFAULT 0,
    lost          INTEGER DEFAULT 0,
    goals_for     INTEGER DEFAULT 0,
    goals_against INTEGER DEFAULT 0,
    points        INTEGER DEFAULT 0,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (season, team_name)
);

-- 赔率时序快照
CREATE TABLE IF NOT EXISTS pl_analytics.pl_odds_history (
    id         SERIAL PRIMARY KEY,
    match_uid  VARCHAR(64) NOT NULL,
    bookmaker  VARCHAR(50) DEFAULT 'pinnacle',
    home_odds  DECIMAL(6,2),
    draw_odds  DECIMAL(6,2),
    away_odds  DECIMAL(6,2),
    snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pl_odds_match ON pl_analytics.pl_odds_history (match_uid, snapshot_at);

-- Agent 会话与消息（P4 持久化预留）
CREATE TABLE IF NOT EXISTS pl_analytics.pl_ai_sessions (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER,
    username   VARCHAR(50),
    title      VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pl_analytics.pl_ai_messages (
    id         SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES pl_analytics.pl_ai_sessions(id) ON DELETE CASCADE,
    role       VARCHAR(16) NOT NULL,          -- user / assistant / tool
    content    TEXT,
    tool_calls JSONB,
    tokens     INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pl_ai_messages_session
    ON pl_analytics.pl_ai_messages (session_id, created_at);

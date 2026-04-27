-- ============================================================
-- FiAinina AI — PostgreSQL initialization
-- Run once on first container start
--
-- Soft delete convention (applies to ALL tables):
--   • deleted_at TIMESTAMPTZ DEFAULT NULL  → NULL = active, set = deleted
--   • deleted_by UUID                      → who triggered the delete
--   • Never run DELETE — always: UPDATE t SET deleted_at=NOW(), deleted_by=:uid
--   • Every table has a corresponding active_* view that filters deleted rows
--   • ON DELETE RESTRICT on all FKs: you must soft-delete children first
-- ============================================================

-- ─── Users & Roles ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    role          VARCHAR(20) NOT NULL CHECK (role IN ('developer', 'family', 'admin')),
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at    TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    deleted_by    UUID DEFAULT NULL        -- self-reference added after table creation
);

CREATE OR REPLACE VIEW active_users AS
    SELECT * FROM users WHERE deleted_at IS NULL;

-- ─── Elderly persons being monitored ────────────────────────
CREATE TABLE IF NOT EXISTS monitored_persons (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    room        VARCHAR(50),
    camera_id   VARCHAR(50),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at  TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    deleted_by  UUID REFERENCES users(id) ON DELETE RESTRICT DEFAULT NULL
);

CREATE OR REPLACE VIEW active_monitored_persons AS
    SELECT * FROM monitored_persons WHERE deleted_at IS NULL;

-- ─── Link: which family users monitor which persons ─────────
-- Junction table: soft-delete by setting deleted_at (no physical DELETE)
CREATE TABLE IF NOT EXISTS person_watchers (
    user_id     UUID REFERENCES users(id) ON DELETE RESTRICT,
    person_id   UUID REFERENCES monitored_persons(id) ON DELETE RESTRICT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at  TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    deleted_by  UUID REFERENCES users(id) ON DELETE RESTRICT DEFAULT NULL,
    PRIMARY KEY (user_id, person_id)
);

CREATE OR REPLACE VIEW active_person_watchers AS
    SELECT * FROM person_watchers WHERE deleted_at IS NULL;

-- ─── P3: Fall Events (written by alert_service after Redis) ─
-- Events are never truly deleted — confirmed=FALSE marks false alarms.
-- deleted_at is available for admin data-management only.
CREATE TABLE IF NOT EXISTS fall_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       UUID REFERENCES monitored_persons(id) ON DELETE RESTRICT,
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL,
    confidence      FLOAT NOT NULL,
    clip_url        VARCHAR(500),
    landmarks_json  JSONB,
    camera_quality  FLOAT,
    visibility_mode VARCHAR(20) DEFAULT 'full',  -- full | partial | none
    confirmed       BOOLEAN,                      -- NULL=unreviewed, TRUE=real, FALSE=false alarm
    confirmed_by    UUID REFERENCES users(id) ON DELETE RESTRICT,
    confirmed_at    TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at      TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    deleted_by      UUID REFERENCES users(id) ON DELETE RESTRICT DEFAULT NULL
);

CREATE OR REPLACE VIEW active_fall_events AS
    SELECT * FROM fall_events WHERE deleted_at IS NULL;

-- ─── P4: Inactivity Events ──────────────────────────────────
CREATE TABLE IF NOT EXISTS inactivity_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id   UUID REFERENCES monitored_persons(id) ON DELETE RESTRICT,
    timestamp   TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_s  INTEGER NOT NULL,
    emotion     VARCHAR(50),
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at  TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    deleted_by  UUID REFERENCES users(id) ON DELETE RESTRICT DEFAULT NULL
);

CREATE OR REPLACE VIEW active_inactivity_events AS
    SELECT * FROM inactivity_events WHERE deleted_at IS NULL;

-- ─── P2: Long-term memory / user facts ──────────────────────
CREATE TABLE IF NOT EXISTS user_facts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id   UUID REFERENCES monitored_persons(id) ON DELETE RESTRICT,
    key         VARCHAR(100) NOT NULL,
    value       TEXT NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at  TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    deleted_by  UUID REFERENCES users(id) ON DELETE RESTRICT DEFAULT NULL
);

CREATE OR REPLACE VIEW active_user_facts AS
    SELECT * FROM user_facts WHERE deleted_at IS NULL;

-- ─── P5: Alert log ──────────────────────────────────────────
-- Alerts are an audit trail — deleted_at provided but should rarely be used.
CREATE TABLE IF NOT EXISTS alert_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID,
    event_type  VARCHAR(50) NOT NULL,  -- fall | inactivity | emotion
    channel     VARCHAR(20) NOT NULL,  -- email | sms | push
    recipient   VARCHAR(255) NOT NULL,
    status      VARCHAR(20) DEFAULT 'sent',
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at  TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    deleted_by  UUID REFERENCES users(id) ON DELETE RESTRICT DEFAULT NULL
);

CREATE OR REPLACE VIEW active_alert_log AS
    SELECT * FROM alert_log WHERE deleted_at IS NULL;

-- ─── Self-referencing FK on users.deleted_by ─────────────────
-- Added after table creation to avoid forward-reference error
ALTER TABLE users
    ADD CONSTRAINT fk_users_deleted_by
    FOREIGN KEY (deleted_by) REFERENCES users(id) ON DELETE RESTRICT;

-- ─── updated_at auto-trigger ─────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_monitored_persons_updated_at
    BEFORE UPDATE ON monitored_persons
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_fall_events_updated_at
    BEFORE UPDATE ON fall_events
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_user_facts_updated_at
    BEFORE UPDATE ON user_facts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─── Indexes ─────────────────────────────────────────────────
-- Partial indexes only cover active (non-deleted) rows for performance
CREATE INDEX IF NOT EXISTS idx_fall_events_person
    ON fall_events(person_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_fall_events_timestamp
    ON fall_events(timestamp DESC) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_inactivity_person
    ON inactivity_events(person_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_alert_log_event
    ON alert_log(event_id) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_person_watchers_active
    ON person_watchers(user_id, person_id) WHERE deleted_at IS NULL;

-- ─── Seed: default developer account ────────────────────────
-- Password: "admin123" (bcrypt hash — change in production!)
INSERT INTO users (name, email, role, password_hash) VALUES
  ('Admin Developer', 'admin@fiainina.local', 'developer',
   '$2b$12$LQv3c1yqBwEHFr3HGDoMjuG6P6Z.B0j.zN9Mq5KpjPEZGt.TTGQTC')
ON CONFLICT (email) DO NOTHING;
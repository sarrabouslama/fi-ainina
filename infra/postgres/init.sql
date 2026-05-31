-- ============================================================
-- FiAinina AI — PostgreSQL initialization
-- Mirrors companion-backend/app/models.py and alembic/versions/0001_initial.py
-- Run once on first container start
-- ============================================================

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('caregiver', 'elderly', 'admin');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS users (
    id                VARCHAR(36) PRIMARY KEY,
    email             VARCHAR(255) UNIQUE NOT NULL,
    phone             VARCHAR(30),
    hashed_password   VARCHAR(255) NOT NULL,
    full_name         VARCHAR(255) NOT NULL,
    role              user_role NOT NULL,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    consent_given     BOOLEAN NOT NULL DEFAULT FALSE,
    consent_date      TIMESTAMP WITH TIME ZONE,
    preferences       JSON,
    created_at        TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS person_watchers (
    user_id     VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    person_id   VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, person_id)
);

CREATE TABLE IF NOT EXISTS alert_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id    UUID,
    event_type  VARCHAR(50) NOT NULL,
    channel     VARCHAR(20) NOT NULL,
    recipient   VARCHAR(255) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'sent',
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_person_watchers_user_id ON person_watchers(user_id);
CREATE INDEX IF NOT EXISTS idx_person_watchers_person_id ON person_watchers(person_id);
CREATE INDEX IF NOT EXISTS idx_alert_log_event_id ON alert_log(event_id);
CREATE INDEX IF NOT EXISTS idx_alert_log_created_at ON alert_log(created_at DESC);

INSERT INTO users (id, email, phone, hashed_password, full_name, role, is_active, consent_given, consent_date, preferences, created_at)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'admin@fiainina.local',
    '+12345678',
    '$2b$12$LQv3c1yqBwEHFr3HGDoMjuG6P6Z.B0j.zN9Mq5KpjPEZGt.TTGQTC',
    'Admin Developer',
    'admin',
    TRUE,
    FALSE,
    NULL,
    NULL,
    NOW()
)
ON CONFLICT (email) DO NOTHING;
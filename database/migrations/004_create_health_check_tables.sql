-- Migration 004: Create free health check tables
-- Run this in the Supabase SQL editor BEFORE running 003_enable_rls_policies.sql
-- (or re-run 003 after this completes)

-- free_health_checks
-- One row per completed free health check; enforces one check per email.
CREATE TABLE IF NOT EXISTS free_health_checks (
    id                  BIGSERIAL       PRIMARY KEY,
    email               TEXT            NOT NULL UNIQUE,
    file_name           TEXT,
    file_size_bytes     INTEGER,
    row_count           INTEGER,
    column_count        INTEGER,
    quality_score       INTEGER         CHECK (quality_score BETWEEN 0 AND 100),
    result_json         JSONB,
    ip_address          TEXT,
    cta_clicked         TEXT,
    converted_to_trial  BOOLEAN         NOT NULL DEFAULT FALSE,
    uploaded_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hc_email       ON free_health_checks (email);
CREATE INDEX IF NOT EXISTS idx_hc_uploaded_at ON free_health_checks (uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_hc_cta         ON free_health_checks (cta_clicked) WHERE cta_clicked IS NOT NULL;

ALTER TABLE free_health_checks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_full_access_free_health_checks" ON free_health_checks;
CREATE POLICY         "service_role_full_access_free_health_checks" ON free_health_checks
    FOR ALL USING (auth.role() = 'service_role');

-- health_check_events
-- Analytics event stream for the free health check funnel.
CREATE TABLE IF NOT EXISTS health_check_events (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT,
    event_type  TEXT            NOT NULL,
    metadata    JSONB,
    occurred_at TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hce_email        ON health_check_events (email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_hce_event_type   ON health_check_events (event_type);
CREATE INDEX IF NOT EXISTS idx_hce_occurred_at  ON health_check_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_hce_metadata_gin ON health_check_events USING GIN (metadata);

ALTER TABLE health_check_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_full_access_health_check_events" ON health_check_events;
CREATE POLICY         "service_role_full_access_health_check_events" ON health_check_events
    FOR ALL USING (auth.role() = 'service_role');

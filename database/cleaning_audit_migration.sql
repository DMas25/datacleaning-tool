-- ColtraDataAi — Cleaning Audit Trail
-- Run this ONCE in the Supabase SQL editor before deploying the audit-trail feature.
-- All columns are additive — no existing tables are touched.
--
-- Apply steps:
--   1. Supabase dashboard → SQL Editor → New query
--   2. Paste this file, click Run
--   3. Verify table appears under Table Editor

CREATE TABLE IF NOT EXISTS cleaning_audit (
    id               BIGSERIAL    PRIMARY KEY,
    email            TEXT         NOT NULL,
    plan             TEXT         NOT NULL DEFAULT 'free',
    dataset_type     TEXT         NOT NULL DEFAULT 'General',
    rows_in          INTEGER,
    rows_out         INTEGER,
    cols_in          INTEGER,
    cols_out         INTEGER,
    completeness_pct NUMERIC(5,2),
    issues_found     INTEGER      NOT NULL DEFAULT 0,
    steps_log        JSONB,
    run_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Fast lookup by user for history views; fast DESC sort for recent-runs queries.
CREATE INDEX IF NOT EXISTS cleaning_audit_email_idx  ON cleaning_audit (email);
CREATE INDEX IF NOT EXISTS cleaning_audit_run_at_idx ON cleaning_audit (run_at DESC);

-- Row-Level Security: only the service role key (used by the app server) can
-- write audit rows. Individual users cannot read or write each other's records.
ALTER TABLE cleaning_audit ENABLE ROW LEVEL SECURITY;

-- Service-role bypass covers the app's INSERT from Render.
-- No additional policies needed unless you add a customer-facing audit history view.

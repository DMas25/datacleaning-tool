-- =============================================================================
-- ColtraDataAi — Supabase PostgreSQL Schema
-- =============================================================================
-- Generated for: Supabase (PostgreSQL 15+)
-- Target project: ColtraDataAi (Coltrane Ltd)
-- Migration context: Greenfield schema — run top-to-bottom on a fresh Supabase
--   project. No IF NOT EXISTS guards needed; tables must not pre-exist.
--
-- Table groups
-- ────────────────────────────────────────────────────────────────────────────
--  CORE BILLING
--    subscriptions        — one row per customer; single source of truth for
--                           plan, licence key, and LemonSqueezy IDs
--    run_counts           — monthly usage counter per email (rate-limiting)
--    webhook_log          — raw inbound LemonSqueezy webhook payloads for audit
--    invoices             — structured financial records extracted from webhooks
--    renewal_reminders    — deduplication log for renewal reminder emails
--
--  ANALYTICS / TRACKING
--    usage_events         — lightweight event stream (login, run, upgrade, etc.)
--    email_log            — tracks which lifecycle emails have been sent
--    milestone_log        — tracks run-count milestones shown per billing period
--    signal_log           — in-app upsell/nudge signals shown per user (A/B)
--    prompt_evaluations   — user responses to in-app upgrade prompt variants
--
--  ONBOARDING / COMPLIANCE
--    customer_profiles    — extended contact/company data captured at activation
--    compliance_consent   — legal audit trail for T&Cs, privacy, and marketing
-- =============================================================================


-- ===========================================================================
-- SECTION 1: CORE BILLING TABLES
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- subscriptions
-- One row per registered email address. Created on first LemonSqueezy webhook
-- receipt (order_created / subscription_created) or on free-tier self-signup.
-- plan and status are validated via CHECK constraints to prevent dirty data.
-- ---------------------------------------------------------------------------
CREATE TABLE subscriptions (
    id              BIGSERIAL       PRIMARY KEY,
    email           TEXT            NOT NULL UNIQUE,
    plan            TEXT            NOT NULL DEFAULT 'free'
                        CHECK (plan IN ('free', 'starter', 'professional', 'premium', 'enterprise')),
    licence_key     TEXT            UNIQUE,
    subscription_id TEXT,                           -- LemonSqueezy subscription ID
    order_id        TEXT,                           -- LemonSqueezy order ID
    status          TEXT            NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'inactive', 'cancelled', 'paused')),
    -- Profile / telemetry columns (originally added via ALTER TABLE in SQLite)
    profession          TEXT,
    position_level      TEXT,
    industry            TEXT,
    business_activity   TEXT,
    first_used_at       TIMESTAMPTZ,
    -- Timestamps
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Fast lookups by LemonSqueezy IDs (used during webhook processing)
CREATE INDEX idx_sub_subscription_id ON subscriptions (subscription_id);
CREATE INDEX idx_sub_order_id        ON subscriptions (order_id);
CREATE INDEX idx_sub_licence_key     ON subscriptions (licence_key);
CREATE INDEX idx_sub_plan            ON subscriptions (plan);
CREATE INDEX idx_sub_status          ON subscriptions (status);

-- ---------------------------------------------------------------------------
-- run_counts
-- Monthly usage counter per email. month_key format: 'YYYY-MM' (e.g. '2026-07').
-- Incremented atomically by the app on each successful cleaning run.
-- ---------------------------------------------------------------------------
CREATE TABLE run_counts (
    email       TEXT        NOT NULL,
    month_key   TEXT        NOT NULL,   -- 'YYYY-MM'
    count       INTEGER     NOT NULL DEFAULT 0,
    PRIMARY KEY (email, month_key)
);

-- Scan all months for a single user (subscription dashboard)
CREATE INDEX idx_run_counts_email ON run_counts (email);

-- ---------------------------------------------------------------------------
-- webhook_log
-- Append-only log of every raw inbound LemonSqueezy webhook payload.
-- Stored as JSONB for efficient querying of specific event attributes.
-- ---------------------------------------------------------------------------
CREATE TABLE webhook_log (
    id          BIGSERIAL       PRIMARY KEY,
    event_type  TEXT,
    payload     JSONB,                          -- raw webhook body
    received_at TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhook_event_type  ON webhook_log (event_type);
CREATE INDEX idx_webhook_received_at ON webhook_log (received_at DESC);
-- GIN index for querying payload fields (e.g. payload->>'email')
CREATE INDEX idx_webhook_payload_gin ON webhook_log USING GIN (payload);

-- ---------------------------------------------------------------------------
-- invoices
-- Structured financial records extracted from LemonSqueezy webhook payloads.
-- One row per LS order (enforced by UNIQUE on order_id).
-- Amounts stored in pence/cents as integers to avoid floating-point issues.
-- ---------------------------------------------------------------------------
CREATE TABLE invoices (
    id                      BIGSERIAL       PRIMARY KEY,
    email                   TEXT            NOT NULL,
    order_id                TEXT            NOT NULL UNIQUE,    -- LemonSqueezy order ID
    invoice_number          TEXT,
    invoice_date            TIMESTAMPTZ,
    amount_cents            INTEGER         NOT NULL,           -- total incl. tax, in pence
    currency                TEXT            NOT NULL DEFAULT 'GBP',
    tax_amount_cents        INTEGER         NOT NULL DEFAULT 0,
    payment_method          TEXT,                               -- e.g. 'card', 'paypal'
    transaction_reference   TEXT,                               -- payment processor ref
    ls_invoice_url          TEXT,                               -- LemonSqueezy-hosted PDF URL
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invoices_email        ON invoices (email);
CREATE INDEX idx_invoices_invoice_date ON invoices (invoice_date DESC);

-- ---------------------------------------------------------------------------
-- renewal_reminders
-- Deduplication log for renewal reminder emails.
-- UNIQUE constraint on (email, renewal_date, reminder_type) prevents duplicate
-- sends even if the reminder job fires more than once.
-- ---------------------------------------------------------------------------
CREATE TABLE renewal_reminders (
    id              BIGSERIAL       PRIMARY KEY,
    email           TEXT            NOT NULL,
    subscription_id TEXT,                           -- LemonSqueezy subscription ID
    renewal_date    DATE            NOT NULL,
    reminder_type   TEXT            NOT NULL,        -- e.g. '7_day', '3_day', '1_day'
    sent_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (email, renewal_date, reminder_type)
);

CREATE INDEX idx_renewal_email         ON renewal_reminders (email);
CREATE INDEX idx_renewal_date          ON renewal_reminders (renewal_date);
CREATE INDEX idx_renewal_sub_id        ON renewal_reminders (subscription_id);


-- ===========================================================================
-- SECTION 2: ANALYTICS / TRACKING TABLES
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- usage_events
-- Lightweight event stream. One row per discrete action: login, cleaning_run,
-- upgrade_click, plan_change, etc. Used for cohort analysis and churn signals.
-- ---------------------------------------------------------------------------
CREATE TABLE usage_events (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT            NOT NULL,
    event_type  TEXT            NOT NULL,
    plan        TEXT            CHECK (plan IN ('free', 'starter', 'professional', 'premium', 'enterprise')),
    occurred_at TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_email       ON usage_events (email);
CREATE INDEX idx_usage_event_type  ON usage_events (event_type);
CREATE INDEX idx_usage_occurred_at ON usage_events (occurred_at DESC);
-- Composite index for per-user event-type queries (e.g. all 'cleaning_run' for user)
CREATE INDEX idx_usage_email_type  ON usage_events (email, event_type);

-- ---------------------------------------------------------------------------
-- email_log
-- Tracks which lifecycle / transactional emails have been sent.
-- UNIQUE(email, email_type) means each email type is sent once per address
-- (e.g. welcome, trial_expiring). Add a sent_count column if repeat sends needed.
-- ---------------------------------------------------------------------------
CREATE TABLE email_log (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT            NOT NULL,
    email_type  TEXT            NOT NULL,       -- e.g. 'welcome', 'trial_expiring'
    sent_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (email, email_type)
);

CREATE INDEX idx_email_log_email ON email_log (email);

-- ---------------------------------------------------------------------------
-- milestone_log
-- Records run-count milestones (e.g. 10th run, 50th run) shown to users within
-- a billing period. UNIQUE prevents showing the same milestone banner twice.
-- ---------------------------------------------------------------------------
CREATE TABLE milestone_log (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT            NOT NULL,
    milestone   INTEGER         NOT NULL,       -- e.g. 10, 50, 100
    month_key   TEXT            NOT NULL,       -- 'YYYY-MM'
    shown_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    UNIQUE (email, milestone, month_key)
);

CREATE INDEX idx_milestone_email ON milestone_log (email);

-- ---------------------------------------------------------------------------
-- signal_log
-- In-app upsell / nudge signals shown per user. The `variant` column supports
-- A/B testing — every row records which copy variant the user saw.
-- ---------------------------------------------------------------------------
CREATE TABLE signal_log (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT            NOT NULL,
    signal      TEXT            NOT NULL,               -- signal name / slug
    variant     TEXT            NOT NULL DEFAULT 'default',
    shown_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Primary lookup: all signals shown to a user, or all impressions of a signal
CREATE INDEX idx_signal_email        ON signal_log (email);
CREATE INDEX idx_signal_lookup       ON signal_log (email, signal);
CREATE INDEX idx_signal_variant      ON signal_log (signal, variant);
CREATE INDEX idx_signal_shown_at     ON signal_log (shown_at DESC);

-- ---------------------------------------------------------------------------
-- prompt_evaluations
-- Records whether a user engaged with (shown=true/1) an upgrade prompt variant.
-- Used to measure prompt effectiveness and guide A/B test conclusions.
-- ---------------------------------------------------------------------------
CREATE TABLE prompt_evaluations (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT            NOT NULL,
    shown       BOOLEAN         NOT NULL,
    occurred_at TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_prompt_eval_email       ON prompt_evaluations (email);
CREATE INDEX idx_prompt_eval_occurred_at ON prompt_evaluations (occurred_at DESC);


-- ===========================================================================
-- SECTION 3: ONBOARDING / COMPLIANCE TABLES
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- customer_profiles
-- Extended onboarding data captured at licence activation (name, company, etc.).
-- LemonSqueezy webhook payloads do not reliably provide this — it is collected
-- via a post-purchase onboarding form in the app.
-- References subscriptions(email) with cascading delete so removing a
-- subscription record also removes the linked profile.
-- ---------------------------------------------------------------------------
CREATE TABLE customer_profiles (
    id              BIGSERIAL       PRIMARY KEY,
    email           TEXT            NOT NULL UNIQUE REFERENCES subscriptions (email) ON DELETE CASCADE,
    customer_name   TEXT,
    company_name    TEXT,
    phone           TEXT,
    country         TEXT,           -- ISO 3166-1 alpha-2 preferred (e.g. 'GB')
    vat_number      TEXT,           -- for B2B EU / UK VAT compliance
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customer_profiles_email        ON customer_profiles (email);
CREATE INDEX idx_customer_profiles_company_name ON customer_profiles (company_name);

-- ---------------------------------------------------------------------------
-- compliance_consent
-- Legal audit trail for T&Cs acceptance, privacy policy acceptance, and
-- marketing opt-in. One row per email (upsertable via ON CONFLICT).
-- ip_address stores an anonymised IP (last octet zeroed, e.g. '192.168.1.0')
-- to satisfy GDPR data-minimisation requirements.
-- References subscriptions(email) with cascading delete.
-- ---------------------------------------------------------------------------
CREATE TABLE compliance_consent (
    id                      BIGSERIAL       PRIMARY KEY,
    email                   TEXT            NOT NULL UNIQUE REFERENCES subscriptions (email) ON DELETE CASCADE,
    t_and_c_accepted_at     TIMESTAMPTZ,
    privacy_accepted_at     TIMESTAMPTZ,
    marketing_consent       BOOLEAN         NOT NULL DEFAULT FALSE,
    ip_address              TEXT,           -- anonymised last octet (e.g. '203.0.113.0')
    user_agent              TEXT,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_compliance_email               ON compliance_consent (email);
CREATE INDEX idx_compliance_marketing_consent   ON compliance_consent (marketing_consent);


-- ===========================================================================
-- ROW LEVEL SECURITY
-- ===========================================================================
-- RLS is enabled on all tables. Policies are intentionally left empty here —
-- define them per your Supabase project auth setup (e.g. service-role bypass
-- for the webhook server, user-scoped read for the Streamlit app via JWT).
-- ---------------------------------------------------------------------------

ALTER TABLE subscriptions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE run_counts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_log         ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices            ENABLE ROW LEVEL SECURITY;
ALTER TABLE renewal_reminders   ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_events        ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_log           ENABLE ROW LEVEL SECURITY;
ALTER TABLE milestone_log       ENABLE ROW LEVEL SECURITY;
ALTER TABLE signal_log          ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_evaluations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_profiles   ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_consent  ENABLE ROW LEVEL SECURITY;

-- TODO: Define RLS policies per Supabase project auth setup.
-- Example skeleton (replace with real auth logic):
--
-- CREATE POLICY "service_role_full_access" ON subscriptions
--     FOR ALL USING (auth.role() = 'service_role');
--
-- CREATE POLICY "users_read_own_subscription" ON subscriptions
--     FOR SELECT USING (auth.jwt() ->> 'email' = email);


-- ===========================================================================
-- HELPER: updated_at auto-update trigger
-- ===========================================================================
-- Supabase does not auto-update updated_at; this trigger handles it for all
-- tables that carry the column.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_customer_profiles_updated_at
    BEFORE UPDATE ON customer_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_compliance_consent_updated_at
    BEFORE UPDATE ON compliance_consent
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ===========================================================================
-- SECTION 4: AUTHENTICATION — OTP TOKENS
-- ===========================================================================
-- Added: 2026-07-17. Migration script: database/migrations/001_add_otp_tokens.sql
--
-- Passwordless email OTP authentication.  Only the SHA-256 hash of the
-- 6-digit code is stored — no plaintext code, no password, ever.
-- ---------------------------------------------------------------------------
-- NOTE: If running this on a fresh project, this table is included here.
--       On the live project, run the migration script instead.
-- ---------------------------------------------------------------------------

CREATE TABLE otp_tokens (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT            NOT NULL,
    token_hash  TEXT            NOT NULL,       -- SHA-256 hex digest; plaintext never stored
    expires_at  TIMESTAMPTZ     NOT NULL,
    used_at     TIMESTAMPTZ,                    -- NULL = available; set on first valid verification
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_otp_email_unused  ON otp_tokens (email, expires_at DESC) WHERE used_at IS NULL;
CREATE INDEX idx_otp_expires_at    ON otp_tokens (expires_at DESC);

ALTER TABLE otp_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_otp" ON otp_tokens
    FOR ALL USING (auth.role() = 'service_role');


-- ===========================================================================
-- SECTION 5: FREE DATA HEALTH CHECK (LEAD GENERATION)
-- ===========================================================================

-- ---------------------------------------------------------------------------
-- free_health_checks
-- One row per completed free health check. Enforces one check per email via
-- the UNIQUE constraint. Stores only aggregated summary statistics — no raw
-- data is ever persisted.
-- ---------------------------------------------------------------------------
CREATE TABLE free_health_checks (
    id                  BIGSERIAL       PRIMARY KEY,
    email               TEXT            NOT NULL UNIQUE,
    file_name           TEXT,
    file_size_bytes     INTEGER,
    row_count           INTEGER,
    column_count        INTEGER,
    quality_score       INTEGER         CHECK (quality_score BETWEEN 0 AND 100),
    result_json         JSONB,          -- summary stats only, never raw data
    ip_address          TEXT,
    cta_clicked         TEXT,           -- which CTA the user clicked ('trial', 'professional', etc.)
    converted_to_trial  BOOLEAN         NOT NULL DEFAULT FALSE,
    uploaded_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hc_email       ON free_health_checks (email);
CREATE INDEX idx_hc_uploaded_at ON free_health_checks (uploaded_at DESC);
CREATE INDEX idx_hc_cta         ON free_health_checks (cta_clicked) WHERE cta_clicked IS NOT NULL;

ALTER TABLE free_health_checks ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- health_check_events
-- Analytics event stream for the free health check funnel.
-- event_type values: upload_started, upload_completed, report_viewed,
--                    cta_clicked, trial_signup, rate_limited, error
-- ---------------------------------------------------------------------------
CREATE TABLE health_check_events (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT,                           -- nullable until email captured
    event_type  TEXT            NOT NULL,
    metadata    JSONB,                          -- ip_address, cta, error_msg, etc.
    occurred_at TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hce_email       ON health_check_events (email) WHERE email IS NOT NULL;
CREATE INDEX idx_hce_event_type  ON health_check_events (event_type);
CREATE INDEX idx_hce_occurred_at ON health_check_events (occurred_at DESC);
-- GIN index for querying metadata fields (e.g. metadata->>'ip_address')
CREATE INDEX idx_hce_metadata_gin ON health_check_events USING GIN (metadata);

ALTER TABLE health_check_events ENABLE ROW LEVEL SECURITY;

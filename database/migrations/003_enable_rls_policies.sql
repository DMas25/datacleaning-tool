-- =============================================================================
-- Migration 003: Enable RLS and add service_role policies on all tables
-- =============================================================================
-- Run this in the Supabase SQL editor (project: coltradata-ai).
--
-- What this does:
--   1. Enables RLS on api_keys and api_usage_log (the tables Supabase flagged).
--   2. Adds a service_role full-access policy to every table that was missing one.
--
-- Why service_role only?
--   The Streamlit app and Enterprise API both connect with the service_role key
--   (via DATABASE_URL / SUPABASE_ANON_KEY configured as service_role on Render).
--   No end-user JWT access is needed — the app enforces its own auth layer.
--   Anon/authenticated roles get no access, which is the correct posture.
-- =============================================================================


-- ---------------------------------------------------------------------------
-- Step 1: Enable RLS on the two tables that were missing it (Supabase alert)
-- ---------------------------------------------------------------------------

ALTER TABLE api_keys        ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_usage_log   ENABLE ROW LEVEL SECURITY;


-- ---------------------------------------------------------------------------
-- Step 2: Add service_role full-access policies
-- Drop first (idempotent — safe to re-run if policy already exists)
-- ---------------------------------------------------------------------------

-- api_keys
DROP POLICY IF EXISTS "service_role_full_access_api_keys"      ON api_keys;
CREATE POLICY         "service_role_full_access_api_keys"      ON api_keys
    FOR ALL USING (auth.role() = 'service_role');

-- api_usage_log
DROP POLICY IF EXISTS "service_role_full_access_api_usage_log" ON api_usage_log;
CREATE POLICY         "service_role_full_access_api_usage_log" ON api_usage_log
    FOR ALL USING (auth.role() = 'service_role');

-- subscriptions
DROP POLICY IF EXISTS "service_role_full_access_subscriptions"  ON subscriptions;
CREATE POLICY         "service_role_full_access_subscriptions"  ON subscriptions
    FOR ALL USING (auth.role() = 'service_role');

-- run_counts
DROP POLICY IF EXISTS "service_role_full_access_run_counts"     ON run_counts;
CREATE POLICY         "service_role_full_access_run_counts"     ON run_counts
    FOR ALL USING (auth.role() = 'service_role');

-- webhook_log
DROP POLICY IF EXISTS "service_role_full_access_webhook_log"    ON webhook_log;
CREATE POLICY         "service_role_full_access_webhook_log"    ON webhook_log
    FOR ALL USING (auth.role() = 'service_role');

-- invoices
DROP POLICY IF EXISTS "service_role_full_access_invoices"       ON invoices;
CREATE POLICY         "service_role_full_access_invoices"       ON invoices
    FOR ALL USING (auth.role() = 'service_role');

-- renewal_reminders
DROP POLICY IF EXISTS "service_role_full_access_renewal_reminders" ON renewal_reminders;
CREATE POLICY         "service_role_full_access_renewal_reminders" ON renewal_reminders
    FOR ALL USING (auth.role() = 'service_role');

-- usage_events
DROP POLICY IF EXISTS "service_role_full_access_usage_events"   ON usage_events;
CREATE POLICY         "service_role_full_access_usage_events"   ON usage_events
    FOR ALL USING (auth.role() = 'service_role');

-- email_log
DROP POLICY IF EXISTS "service_role_full_access_email_log"      ON email_log;
CREATE POLICY         "service_role_full_access_email_log"      ON email_log
    FOR ALL USING (auth.role() = 'service_role');

-- milestone_log
DROP POLICY IF EXISTS "service_role_full_access_milestone_log"  ON milestone_log;
CREATE POLICY         "service_role_full_access_milestone_log"  ON milestone_log
    FOR ALL USING (auth.role() = 'service_role');

-- signal_log
DROP POLICY IF EXISTS "service_role_full_access_signal_log"     ON signal_log;
CREATE POLICY         "service_role_full_access_signal_log"     ON signal_log
    FOR ALL USING (auth.role() = 'service_role');

-- prompt_evaluations
DROP POLICY IF EXISTS "service_role_full_access_prompt_evaluations" ON prompt_evaluations;
CREATE POLICY         "service_role_full_access_prompt_evaluations" ON prompt_evaluations
    FOR ALL USING (auth.role() = 'service_role');

-- customer_profiles
DROP POLICY IF EXISTS "service_role_full_access_customer_profiles" ON customer_profiles;
CREATE POLICY         "service_role_full_access_customer_profiles" ON customer_profiles
    FOR ALL USING (auth.role() = 'service_role');

-- compliance_consent
DROP POLICY IF EXISTS "service_role_full_access_compliance_consent" ON compliance_consent;
CREATE POLICY         "service_role_full_access_compliance_consent" ON compliance_consent
    FOR ALL USING (auth.role() = 'service_role');

-- free_health_checks
DROP POLICY IF EXISTS "service_role_full_access_free_health_checks" ON free_health_checks;
CREATE POLICY         "service_role_full_access_free_health_checks" ON free_health_checks
    FOR ALL USING (auth.role() = 'service_role');

-- health_check_events
DROP POLICY IF EXISTS "service_role_full_access_health_check_events" ON health_check_events;
CREATE POLICY         "service_role_full_access_health_check_events" ON health_check_events
    FOR ALL USING (auth.role() = 'service_role');

-- user_feedback (already had a policy — idempotent)
DROP POLICY IF EXISTS "service_role_full_access_feedback"       ON user_feedback;
CREATE POLICY         "service_role_full_access_feedback"       ON user_feedback
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================================================
-- Migration 001 — OTP Authentication Tokens
-- =============================================================================
-- Run this in the Supabase SQL editor (Database → SQL Editor → New query).
-- It adds the otp_tokens table used by the passwordless email-OTP login flow.
--
-- Security properties
-- ───────────────────
--   • The 6-digit code itself is NEVER stored — only its SHA-256 hash.
--   • Tokens expire after 10 minutes (enforced by the app before consuming).
--   • Each token is single-use: used_at is set on first successful verification.
--   • Rate limiting (max 3 requests per email per 10 min) is enforced in
--     services/auth_service.py using count_recent_otp_requests().
--   • Expired / used tokens can be purged with the cleanup query at the bottom.
-- =============================================================================

CREATE TABLE otp_tokens (
    id          BIGSERIAL       PRIMARY KEY,
    email       TEXT            NOT NULL,
    token_hash  TEXT            NOT NULL,       -- SHA-256 hex digest; plaintext never stored
    expires_at  TIMESTAMPTZ     NOT NULL,
    used_at     TIMESTAMPTZ,                    -- NULL = available; set on first valid use
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Partial index: only unused tokens matter for login lookups
CREATE INDEX idx_otp_email_unused  ON otp_tokens (email, expires_at DESC)
    WHERE used_at IS NULL;

-- TTL index for periodic cleanup of expired tokens
CREATE INDEX idx_otp_expires_at    ON otp_tokens (expires_at DESC);

ALTER TABLE otp_tokens ENABLE ROW LEVEL SECURITY;

-- Service-role bypass (webhook server + Streamlit app both use the service role)
CREATE POLICY "service_role_full_access_otp" ON otp_tokens
    FOR ALL USING (auth.role() = 'service_role');


-- =============================================================================
-- Optional: scheduled cleanup (run via pg_cron or a nightly Render job)
-- Removes tokens that are either used or expired for more than 24 hours.
-- =============================================================================
-- DELETE FROM otp_tokens
-- WHERE used_at IS NOT NULL
--    OR expires_at < NOW() - INTERVAL '24 hours';

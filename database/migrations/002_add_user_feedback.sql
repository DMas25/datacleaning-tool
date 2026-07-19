-- =============================================================================
-- Migration 002 — User Feedback
-- =============================================================================
-- Run this in the Supabase SQL editor (Database → SQL Editor → New query).
-- Adds the user_feedback table for post-run satisfaction surveys:
--   • Three Likert scores (1–5): ease, data quality, overall satisfaction
--   • NPS score (0–10): likelihood to recommend
--   • Optional free-text comment
--
-- Suppression logic (snooze / never-ask-again) reuses the existing signal_log
-- table via the signals 'feedback_snooze' and 'feedback_never'.
-- =============================================================================

CREATE TABLE user_feedback (
    id              BIGSERIAL       PRIMARY KEY,
    email           TEXT            NOT NULL,
    ease_score      SMALLINT        NOT NULL CHECK (ease_score  BETWEEN 1 AND 5),
    quality_score   SMALLINT        NOT NULL CHECK (quality_score BETWEEN 1 AND 5),
    overall_score   SMALLINT        NOT NULL CHECK (overall_score BETWEEN 1 AND 5),
    nps_score       SMALLINT        NOT NULL CHECK (nps_score   BETWEEN 0 AND 10),
    comment         TEXT,
    submitted_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_email        ON user_feedback (email);
CREATE INDEX idx_feedback_submitted_at ON user_feedback (submitted_at DESC);

ALTER TABLE user_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full_access_feedback" ON user_feedback
    FOR ALL USING (auth.role() = 'service_role');

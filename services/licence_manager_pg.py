"""
Licence Manager — PostgreSQL/Supabase backend.

This is the drop-in replacement for ``services/licence_manager.py`` for the
Supabase migration planned for the week of 2026-07-14.  Every public function
preserves the same name and signature as the SQLite version.

HOW TO SWAP IN ON MIGRATION DAY
================================
In every file that currently does::

    from services.licence_manager import <name>

change the import to::

    from services.licence_manager_pg import <name>

Or, if you prefer a single-file swap with no import changes across the
codebase, rename this file to ``licence_manager.py`` (after archiving the
SQLite original) on migration day.

REQUIREMENTS (add to requirements.txt before deploying)
=========================================================
# psycopg2>=2.9.9
# psycopg2-binary>=2.9.9

psycopg2-binary is used for local/Streamlit Cloud deployments where a
C-level libpq isn't guaranteed.  On Render, the ``psycopg2`` package (without
-binary) is preferred because the build environment provides libpq natively.

SCHEMA
======
Tables are created once by running ``database/supabase_schema.sql`` in the
Supabase SQL editor (or via ``bootstrap_schema()`` below).  This module does
NOT issue CREATE TABLE statements at runtime.

CONNECTION
==========
DATABASE_URL is resolved in this priority order:
  1. Environment variable ``DATABASE_URL`` (set automatically by Render).
  2. ``.streamlit/secrets.toml`` → ``[supabase] database_url = "..."``
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras

from config.plans import get_plan

log = logging.getLogger(__name__)


# ── Connection helpers ─────────────────────────────────────────────────────────

def _get_connection_string() -> str:
    """Resolve the PostgreSQL connection URL.

    Priority:
    1. ``DATABASE_URL`` environment variable (Render sets this automatically).
    2. ``.streamlit/secrets.toml`` → ``[supabase] database_url``.

    Raises ``RuntimeError`` if neither source is configured.
    """
    def _clean(raw: str) -> str:
        """Strip whitespace and any accidental surrounding quote characters."""
        return raw.strip().strip("\"'")

    # 1. Environment variable (Render / CI / local override)
    url = _clean(os.environ.get("DATABASE_URL", ""))
    if url:
        return url

    # 2. Streamlit secrets
    try:
        import streamlit as st
        url = _clean(st.secrets.get("supabase", {}).get("database_url", ""))
        if url:
            return url
    except Exception:
        pass

    raise RuntimeError(
        "No PostgreSQL DATABASE_URL found. "
        "Set the DATABASE_URL environment variable or add "
        "[supabase] database_url = \"...\" to .streamlit/secrets.toml."
    )


@contextmanager
def _conn():
    """Open a psycopg2 connection, yield a RealDictCursor, commit on success,
    rollback on exception, and always close the connection.

    Usage::

        with _conn() as cur:
            cur.execute("SELECT 1")
    """
    dsn = _get_connection_string()
    con = psycopg2.connect(dsn)
    cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield cur
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        cur.close()
        con.close()


def bootstrap_schema(sql_file_path: str) -> None:
    """Run ``database/supabase_schema.sql`` against the target database.

    This is a one-shot utility for the initial Supabase setup.  It is NOT
    called automatically — invoke it manually once during migration day::

        from services.licence_manager_pg import bootstrap_schema
        bootstrap_schema("database/supabase_schema.sql")

    The SQL file is split on semicolons and each statement is executed
    individually so that psycopg2 can handle multi-statement scripts.
    """
    sql = Path(sql_file_path).read_text(encoding="utf-8")
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with _conn() as cur:
        for stmt in statements:
            cur.execute(stmt)
    log.info("bootstrap_schema: executed %d statements from %s", len(statements), sql_file_path)


# ── Timestamps ─────────────────────────────────────────────────────────────────

def _now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime object.

    psycopg2 maps Python ``datetime`` objects with tzinfo directly to
    TIMESTAMPTZ columns — no ISO-string conversion needed.
    """
    return datetime.now(timezone.utc)


def _month_key() -> str:
    """Return the current calendar month as 'YYYY-MM' (e.g. '2026-07')."""
    return date.today().strftime("%Y-%m")


# ── Key generation ─────────────────────────────────────────────────────────────

def generate_licence_key() -> str:
    """Return a cryptographically random XXXX-XXXX-XXXX-XXXX licence key."""
    parts = [secrets.token_hex(2).upper() for _ in range(4)]
    return "-".join(parts)


# ── Write operations ───────────────────────────────────────────────────────────

def upsert_subscription(
    *,
    email: str,
    plan: str,
    subscription_id: str = "",
    order_id: str = "",
    status: str = "active",
    licence_key: Optional[str] = None,
) -> str:
    """Create or update a subscription record. Returns the licence key."""
    email = email.lower().strip()
    with _conn() as cur:
        cur.execute(
            "SELECT licence_key FROM subscriptions WHERE email = %s",
            (email,),
        )
        existing = cur.fetchone()

        key = existing["licence_key"] if existing else None
        if key is None:
            key = licence_key or generate_licence_key()

        now = _now()
        cur.execute(
            """
            INSERT INTO subscriptions
                (email, plan, licence_key, subscription_id, order_id, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                plan            = EXCLUDED.plan,
                licence_key     = COALESCE(subscriptions.licence_key, EXCLUDED.licence_key),
                subscription_id = COALESCE(NULLIF(EXCLUDED.subscription_id, ''), subscriptions.subscription_id),
                order_id        = COALESCE(NULLIF(EXCLUDED.order_id, ''),        subscriptions.order_id),
                status          = EXCLUDED.status,
                updated_at      = EXCLUDED.updated_at
            """,
            (email, plan, key, subscription_id, order_id, status, now, now),
        )

    log.info("upsert_subscription: email=%s plan=%s status=%s", email, plan, status)
    return key


def cancel_subscription(subscription_id: str) -> bool:
    """Downgrade to free and mark inactive. Returns True if a row was found."""
    with _conn() as cur:
        cur.execute(
            """UPDATE subscriptions
               SET plan = 'free', status = 'inactive', updated_at = %s
               WHERE subscription_id = %s""",
            (_now(), subscription_id),
        )
        found = cur.rowcount > 0

    if found:
        log.info("cancel_subscription: subscription_id=%s → downgraded to free", subscription_id)
    else:
        log.warning("cancel_subscription: subscription_id=%s not found", subscription_id)
    return found


# ── Read operations ────────────────────────────────────────────────────────────

def get_by_key(licence_key: str) -> Optional[dict]:
    """Return subscription row as dict, or None."""
    with _conn() as cur:
        cur.execute(
            "SELECT * FROM subscriptions WHERE licence_key = %s",
            (licence_key.strip(),),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def get_by_email(email: str) -> Optional[dict]:
    """Return subscription row as dict, or None."""
    with _conn() as cur:
        cur.execute(
            "SELECT * FROM subscriptions WHERE email = %s",
            (email.lower().strip(),),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def get_by_subscription_id(subscription_id: str) -> Optional[dict]:
    with _conn() as cur:
        cur.execute(
            "SELECT * FROM subscriptions WHERE subscription_id = %s",
            (subscription_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


# ── Local licence validation ───────────────────────────────────────────────────

def validate_local_key(licence_key: str) -> dict:
    """Validate against local DB. Returns {"valid": bool, "plan": str, "error": str | None}."""
    if not licence_key or not licence_key.strip():
        return {"valid": False, "plan": "free", "error": None}

    row = get_by_key(licence_key)
    if not row:
        return {"valid": False, "plan": "free", "error": None}
    if row["status"] != "active":
        return {"valid": False, "plan": "free", "error": "Licence is inactive or cancelled."}

    return {"valid": True, "plan": row["plan"], "error": None}


# ── Persistent run counts ──────────────────────────────────────────────────────

def get_runs(email: str) -> int:
    with _conn() as cur:
        cur.execute(
            "SELECT count FROM run_counts WHERE email = %s AND month_key = %s",
            (email.lower().strip(), _month_key()),
        )
        row = cur.fetchone()
    return row["count"] if row else 0


def get_runs_this_calendar_month(email: str) -> int:
    """'run' events logged this calendar month, from usage_events.

    Used for milestone messaging — distinct from get_runs()/run_counts, which
    is only ever written to by increment_runs() and isn't currently called
    anywhere, so it would always read back 0.
    """
    email = email.lower().strip()
    with _conn() as cur:
        cur.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = %s
                 AND event_type = 'run'
                 AND TO_CHAR(occurred_at::timestamptz, 'YYYY-MM') = %s""",
            (email, _month_key()),
        )
        row = cur.fetchone()
    return row["n"]


def increment_runs(email: str) -> None:
    with _conn() as cur:
        cur.execute(
            """INSERT INTO run_counts (email, month_key, count) VALUES (%s, %s, 1)
               ON CONFLICT (email, month_key) DO UPDATE SET count = run_counts.count + 1""",
            (email.lower().strip(), _month_key()),
        )


# ── Webhook event logging ──────────────────────────────────────────────────────

def log_webhook_event(event_type: str, payload: str) -> None:
    with _conn() as cur:
        cur.execute(
            "INSERT INTO webhook_log (event_type, payload, received_at) VALUES (%s, %s, %s)",
            (event_type, payload, _now()),
        )


# ── Client profile (no names; role/industry categorisation only) ───────────────

def update_subscription_profile(
    email: str,
    *,
    profession: str = "",
    position_level: str = "",
    industry: str = "",
    business_activity: str = "",
) -> None:
    """Attach optional, name-free demographic/industry data to a subscriber."""
    with _conn() as cur:
        cur.execute(
            """UPDATE subscriptions
               SET profession        = COALESCE(NULLIF(%s, ''), profession),
                   position_level    = COALESCE(NULLIF(%s, ''), position_level),
                   industry          = COALESCE(NULLIF(%s, ''), industry),
                   business_activity = COALESCE(NULLIF(%s, ''), business_activity),
                   updated_at        = %s
               WHERE email = %s""",
            (profession, position_level, industry, business_activity, _now(), email.lower().strip()),
        )


# ── Extended onboarding profile ────────────────────────────────────────────────

def update_customer_profile(
    email: str,
    *,
    customer_name: str = "",
    company_name: str = "",
    phone: str = "",
    country: str = "",
    vat_number: str = "",
) -> None:
    """Upsert extended customer profile data into the customer_profiles table.

    In the PostgreSQL schema this data lives in a dedicated ``customer_profiles``
    table (not in ``subscriptions`` as in the SQLite version), so this function
    performs a proper INSERT … ON CONFLICT upsert.
    """
    email = email.lower().strip()
    _FALLBACK = "Not provided"
    now = _now()
    try:
        with _conn() as cur:
            cur.execute(
                """INSERT INTO customer_profiles
                       (email, customer_name, company_name, phone, country, vat_number, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (email) DO UPDATE SET
                       customer_name = COALESCE(NULLIF(EXCLUDED.customer_name, ''), customer_profiles.customer_name),
                       company_name  = COALESCE(NULLIF(EXCLUDED.company_name,  ''), customer_profiles.company_name),
                       phone         = COALESCE(NULLIF(EXCLUDED.phone,         ''), customer_profiles.phone),
                       country       = COALESCE(NULLIF(EXCLUDED.country,       ''), customer_profiles.country),
                       vat_number    = COALESCE(NULLIF(EXCLUDED.vat_number,    ''), customer_profiles.vat_number),
                       updated_at    = EXCLUDED.updated_at""",
                (
                    email,
                    customer_name or _FALLBACK,
                    company_name or _FALLBACK,
                    phone or _FALLBACK,
                    country or _FALLBACK,
                    vat_number or _FALLBACK,
                    now,
                    now,
                ),
            )
    except Exception:
        log.exception("update_customer_profile: unexpected error for email=%s", email)


def save_compliance_consent(
    email: str,
    *,
    t_and_c: bool,
    privacy: bool,
    marketing: bool,
    ip_address: str = "",
) -> None:
    """Insert or update a compliance consent record.

    The PostgreSQL ``compliance_consent`` table stores proper TIMESTAMPTZ
    columns (``t_and_c_accepted_at``, ``privacy_accepted_at``) rather than a
    single ``consented_at`` TEXT column.  When a consent flag is True the
    corresponding accepted_at timestamp is set to NOW(); when False it is
    cleared to NULL.
    """
    email = email.lower().strip()
    now = _now()
    t_and_c_at = now if t_and_c else None
    privacy_at = now if privacy else None
    try:
        with _conn() as cur:
            cur.execute(
                """INSERT INTO compliance_consent
                       (email, t_and_c_accepted_at, privacy_accepted_at,
                        marketing_consent, ip_address, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (email) DO UPDATE SET
                       t_and_c_accepted_at = EXCLUDED.t_and_c_accepted_at,
                       privacy_accepted_at = EXCLUDED.privacy_accepted_at,
                       marketing_consent   = EXCLUDED.marketing_consent,
                       ip_address          = EXCLUDED.ip_address,
                       updated_at          = EXCLUDED.updated_at""",
                (email, t_and_c_at, privacy_at, marketing, ip_address, now, now),
            )
    except Exception:
        log.exception("save_compliance_consent: unexpected error for email=%s", email)


def save_invoice(
    *,
    email: str,
    order_id: str,
    amount_cents: int,
    currency: str = "GBP",
    tax_amount_cents: int = 0,
    payment_method: str = "",
    transaction_reference: str = "",
    ls_invoice_url: str = "",
) -> None:
    """Upsert invoice record from LemonSqueezy webhook payload.

    ``order_id`` is the unique key — if the same order fires a duplicate webhook
    the record is updated in place rather than duplicated.
    """
    now = _now()
    try:
        with _conn() as cur:
            cur.execute(
                """INSERT INTO invoices
                       (email, order_id, invoice_date, amount_cents, currency,
                        tax_amount_cents, payment_method, transaction_reference,
                        ls_invoice_url, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (order_id) DO UPDATE SET
                       amount_cents          = EXCLUDED.amount_cents,
                       currency              = EXCLUDED.currency,
                       tax_amount_cents      = EXCLUDED.tax_amount_cents,
                       payment_method        = EXCLUDED.payment_method,
                       transaction_reference = EXCLUDED.transaction_reference,
                       ls_invoice_url        = EXCLUDED.ls_invoice_url""",
                (
                    email.lower().strip(),
                    order_id,
                    now,
                    amount_cents,
                    currency,
                    tax_amount_cents,
                    payment_method,
                    transaction_reference,
                    ls_invoice_url,
                    now,
                ),
            )
    except Exception:
        log.exception("save_invoice: unexpected error for order_id=%s", order_id)


def get_renewal_reminders_due(days_ahead: int = 7) -> list[dict]:
    """Return subscriptions whose renewal_date is within days_ahead and no reminder sent yet.

    Queries the ``renewal_reminders`` table for rows where ``renewal_date``
    falls between today and today + days_ahead, and no ``sent_at`` value has
    been recorded yet (i.e. the reminder has not been dispatched).
    """
    with _conn() as cur:
        cur.execute(
            """SELECT * FROM renewal_reminders
               WHERE renewal_date BETWEEN CURRENT_DATE AND CURRENT_DATE + (%s * INTERVAL '1 day')
                 AND sent_at IS NULL
               ORDER BY renewal_date""",
            (days_ahead,),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


# ── Usage event logging (internal analytics; no PII beyond email) ──────────────

def log_usage_event(email: str, event_type: str, plan: str = "") -> None:
    """Record a behavioral event (activate/run/export_excel/export_pdf/ai_advisory)."""
    if not email:
        return
    email = email.lower().strip()
    now = _now()
    with _conn() as cur:
        cur.execute(
            "INSERT INTO usage_events (email, event_type, plan, occurred_at) VALUES (%s, %s, %s, %s)",
            (email, event_type, plan, now),
        )
        if event_type == "run":
            cur.execute(
                """UPDATE subscriptions
                   SET first_used_at = COALESCE(first_used_at, %s)
                   WHERE email = %s""",
                (now, email),
            )


_FOLLOW_THROUGH_EVENTS = ("export_excel", "export_pdf", "ai_advisory")


def get_user_behavior(email: str) -> dict:
    """Per-user behavioural signals for targeted upgrade messaging.

    Unlike get_usage_analytics() (aggregated, anonymised), this looks at one
    subscriber's own event history so messaging can reference real actions
    they've taken rather than cohort-wide stats.
    """
    email = email.lower().strip()
    with _conn() as cur:
        cur.execute("SELECT plan FROM subscriptions WHERE email = %s", (email,))
        sub = cur.fetchone()
        plan = sub["plan"] if sub else "free"

        cur.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = %s
                 AND event_type = 'run'
                 AND occurred_at >= NOW() - INTERVAL '30 days'""",
            (email,),
        )
        runs_last_30_days = cur.fetchone()["n"]

        cur.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = %s
                 AND event_type = 'run'
                 AND occurred_at >= NOW() - INTERVAL '1 day'""",
            (email,),
        )
        runs_last_24h = cur.fetchone()["n"]

        placeholders = ",".join(["%s"] * len(_FOLLOW_THROUGH_EVENTS))
        cur.execute(
            f"""SELECT COUNT(*) AS n FROM usage_events
                WHERE email = %s
                  AND event_type IN ({placeholders})
                  AND occurred_at >= NOW() - INTERVAL '30 days'""",
            (email, *_FOLLOW_THROUGH_EVENTS),
        )
        follow_through_last_30_days = cur.fetchone()["n"]

        cur.execute(
            "SELECT COUNT(*) AS n FROM usage_events WHERE email = %s AND event_type = 'run'",
            (email,),
        )
        total_runs = cur.fetchone()["n"]

        cur.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = %s
                 AND event_type = 'export_blocked'
                 AND occurred_at >= NOW() - INTERVAL '30 days'""",
            (email,),
        )
        export_blocked_last_30_days = cur.fetchone()["n"]

        cur.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = %s
                 AND event_type = 'advisory_blocked'
                 AND occurred_at >= NOW() - INTERVAL '30 days'""",
            (email,),
        )
        advisory_blocked_last_30_days = cur.fetchone()["n"]

        cur.execute(
            "SELECT DISTINCT event_type FROM usage_events WHERE email = %s",
            (email,),
        )
        used_events = {r["event_type"] for r in cur.fetchall()}

        cur.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = %s
                 AND event_type = 'ai_advisory'
                 AND occurred_at >= NOW() - INTERVAL '30 days'""",
            (email,),
        )
        ai_advisory_last_30_days = cur.fetchone()["n"]

        cur.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = %s
                 AND event_type = 'ai_advisory'
                 AND occurred_at >= NOW() - INTERVAL '60 days'
                 AND occurred_at <  NOW() - INTERVAL '30 days'""",
            (email,),
        )
        ai_advisory_prior_30_days = cur.fetchone()["n"]

        cur.execute(
            """SELECT COUNT(DISTINCT TO_CHAR(occurred_at::timestamptz, 'YYYY-MM')) AS n
               FROM usage_events
               WHERE email = %s AND event_type = 'run'""",
            (email,),
        )
        active_months = cur.fetchone()["n"]

        cur.execute(
            """SELECT EXTRACT(EPOCH FROM (NOW() - MAX(occurred_at)::timestamptz)) / 86400 AS days
               FROM usage_events
               WHERE email = %s AND event_type = 'run'""",
            (email,),
        )
        last_run_row = cur.fetchone()
        days_since_last_run = (
            round(float(last_run_row["days"]), 1)
            if last_run_row and last_run_row["days"] is not None
            else None
        )

    return {
        "email": email,
        "plan": plan,
        "runs_last_30_days": runs_last_30_days,
        "runs_last_24h": runs_last_24h,
        "follow_through_last_30_days": follow_through_last_30_days,
        "active_months": active_months,
        "total_runs": total_runs,
        "export_blocked_last_30_days": export_blocked_last_30_days,
        "advisory_blocked_last_30_days": advisory_blocked_last_30_days,
        "used_events": used_events,
        "ai_advisory_last_30_days": ai_advisory_last_30_days,
        "ai_advisory_prior_30_days": ai_advisory_prior_30_days,
        "days_since_last_run": days_since_last_run,
    }


# ── Lifecycle email queue ───────────────────────────────────────────────────────

def get_users_needing_activation_nudge(inactivity_days: int = 7) -> list[str]:
    """Emails of subscribers who activated a licence but never ran their first
    dataset, where that gap has lasted at least *inactivity_days*.

    Excludes anyone already sent the 'activation_nudge' email so the lifecycle
    runner can be invoked repeatedly (e.g. daily cron) without double-sending.
    """
    with _conn() as cur:
        cur.execute(
            """SELECT s.email FROM subscriptions s
               WHERE s.status = 'active'
                 AND s.first_used_at IS NULL
                 AND s.created_at <= NOW() - (%s * INTERVAL '1 day')
                 AND NOT EXISTS (
                     SELECT 1 FROM email_log e
                     WHERE e.email = s.email AND e.email_type = 'activation_nudge'
                 )""",
            (inactivity_days,),
        )
        rows = cur.fetchall()
    return [r["email"] for r in rows]


def log_email_sent(email: str, email_type: str) -> None:
    """Record that a lifecycle email was sent, so it isn't sent twice."""
    with _conn() as cur:
        cur.execute(
            """INSERT INTO email_log (email, email_type, sent_at) VALUES (%s, %s, %s)
               ON CONFLICT (email, email_type) DO NOTHING""",
            (email.lower().strip(), email_type, _now()),
        )


# ── In-app run-count milestones (habit reinforcement) ─────────────────────────

def milestone_already_shown(email: str, milestone: int) -> bool:
    """True if this milestone was already celebrated for this email this month."""
    email = email.lower().strip()
    with _conn() as cur:
        cur.execute(
            "SELECT 1 FROM milestone_log WHERE email = %s AND milestone = %s AND month_key = %s",
            (email, milestone, _month_key()),
        )
        row = cur.fetchone()
    return row is not None


def log_milestone_shown(email: str, milestone: int) -> None:
    """Record that a run-count milestone toast was shown, so it only fires once per month."""
    with _conn() as cur:
        cur.execute(
            """INSERT INTO milestone_log (email, milestone, month_key, shown_at)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (email, milestone, month_key) DO NOTHING""",
            (email.lower().strip(), milestone, _month_key(), _now()),
        )


# ── Pricing-prompt cooldown (avoid repeating the same message too soon) ────────

def signal_shown_recently(email: str, signal: str, cooldown_hours: int) -> bool:
    """True if *signal* was already shown to this email within the last cooldown_hours."""
    email = email.lower().strip()
    with _conn() as cur:
        cur.execute(
            """SELECT 1 FROM signal_log
               WHERE email = %s
                 AND signal = %s
                 AND shown_at >= NOW() - (%s * INTERVAL '1 hour')""",
            (email, signal, cooldown_hours),
        )
        row = cur.fetchone()
    return row is not None


def log_signal_shown(email: str, signal: str, variant: str = "default") -> None:
    """Record that a pricing-prompt signal (and which A/B copy variant) was
    shown, for cooldown tracking and per-variant effectiveness."""
    with _conn() as cur:
        cur.execute(
            "INSERT INTO signal_log (email, signal, variant, shown_at) VALUES (%s, %s, %s, %s)",
            (email.lower().strip(), signal, variant, _now()),
        )


# ── Monetisation-messaging dry-spell tracking ──────────────────────────────────

def log_prompt_evaluation(email: str, shown: bool) -> None:
    """Record that the once-per-session targeted-prompt evaluation ran, and
    whether it actually rendered anything."""
    if not email:
        return
    with _conn() as cur:
        cur.execute(
            "INSERT INTO prompt_evaluations (email, shown, occurred_at) VALUES (%s, %s, %s)",
            (email.lower().strip(), shown, _now()),
        )


def sessions_without_prompt(email: str, lookback: int = 3) -> int:
    """Count of consecutive most-recent session evaluations (newest first)
    that showed nothing, stopping at the first one that did."""
    email = email.lower().strip()
    with _conn() as cur:
        cur.execute(
            "SELECT shown FROM prompt_evaluations WHERE email = %s ORDER BY id DESC LIMIT %s",
            (email, lookback),
        )
        rows = cur.fetchall()
    streak = 0
    for row in rows:
        if row["shown"]:
            break
        streak += 1
    return streak


def ensure_free_subscriber(email: str) -> None:
    """Guarantee a subscription row exists for this email on the free plan.

    Called during OTP generation so that any valid email can sign in, even
    before a payment has been made. If a paid subscription already exists it
    is untouched (ON CONFLICT DO NOTHING).
    """
    with _conn() as cur:
        cur.execute(
            """INSERT INTO subscriptions (email, plan, status)
               VALUES (%s, 'free', 'active')
               ON CONFLICT (email) DO NOTHING""",
            (email.lower().strip(),),
        )


# ── Aggregated analytics ───────────────────────────────────────────────────────

def get_usage_analytics() -> dict:
    """Aggregated, anonymised usage/demographic stats for the internal dashboard.

    Returns only counts/medians — never individual subscriber rows.
    """
    with _conn() as cur:
        def _breakdown(column: str) -> dict:
            cur.execute(
                f"""SELECT COALESCE(NULLIF({column}, ''), 'Not provided') AS k, COUNT(*) AS n
                    FROM subscriptions WHERE status = 'active' GROUP BY k ORDER BY n DESC""",
            )
            return {r["k"]: r["n"] for r in cur.fetchall()}

        industry_breakdown = _breakdown("industry")
        profession_breakdown = _breakdown("profession")
        position_breakdown = _breakdown("position_level")
        plan_breakdown = _breakdown("plan")

        cur.execute(
            "SELECT event_type, COUNT(*) AS n FROM usage_events GROUP BY event_type ORDER BY n DESC"
        )
        feature_usage_breakdown = {r["event_type"]: r["n"] for r in cur.fetchall()}

        cur.execute(
            """SELECT EXTRACT(EPOCH FROM (first_used_at::timestamptz - created_at::timestamptz)) / 86400 AS days
               FROM subscriptions
               WHERE first_used_at IS NOT NULL AND status = 'active'"""
        )
        conversion_rows = cur.fetchall()
        conversion_times_days = [
            round(float(r["days"]), 2) for r in conversion_rows if r["days"] is not None
        ]

        cur.execute(
            """SELECT EXTRACT(EPOCH FROM (NOW() - created_at::timestamptz)) / 86400 AS days
               FROM subscriptions WHERE status = 'active'"""
        )
        tenure_rows = cur.fetchall()
        tenure_days = [round(float(r["days"]), 2) for r in tenure_rows if r["days"] is not None]

        cur.execute("SELECT COUNT(*) AS n FROM subscriptions WHERE status = 'active'")
        active_subscribers = cur.fetchone()["n"]

        total_runs = feature_usage_breakdown.get("run", 0)

        cur.execute(
            """SELECT LEFT(occurred_at::text, 10) AS day, COUNT(*) AS n
               FROM usage_events
               WHERE event_type = 'run' AND occurred_at >= NOW() - INTERVAL '30 days'
               GROUP BY day ORDER BY day"""
        )
        runs_last_30_days = {r["day"]: r["n"] for r in cur.fetchall()}

    def _median(values: list[float]) -> float | None:
        if not values:
            return None
        s = sorted(values)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

    return {
        "active_subscribers": active_subscribers,
        "total_runs": total_runs,
        "industry_breakdown": industry_breakdown,
        "profession_breakdown": profession_breakdown,
        "position_breakdown": position_breakdown,
        "plan_breakdown": plan_breakdown,
        "feature_usage_breakdown": feature_usage_breakdown,
        "conversion_times_days": conversion_times_days,
        "median_conversion_days": _median(conversion_times_days),
        "tenure_days": tenure_days,
        "median_tenure_days": _median(tenure_days),
        "runs_last_30_days": runs_last_30_days,
    }


# ── Prompt Effectiveness Score ─────────────────────────────────────────────────

_CONVERSION_EVENT_TYPES = ("order_created", "subscription_created")
PROMPT_ATTRIBUTION_WINDOW_DAYS = 7


def _extract_webhook_email(payload_json: str) -> str:
    """Best-effort email extraction from a raw LemonSqueezy webhook payload."""
    try:
        payload = json.loads(payload_json)
    except (json.JSONDecodeError, TypeError):
        return ""
    attrs = payload.get("data", {}).get("attributes", {})
    meta = payload.get("meta", {})
    email = (
        attrs.get("user_email")
        or attrs.get("customer_email")
        or meta.get("custom_data", {}).get("email")
        or ""
    )
    return email.lower().strip()


def _conversions_by_email(cur: psycopg2.extras.RealDictCursor) -> dict[str, list[datetime]]:
    """email -> [received_at, ...] for every paid-plan webhook event.

    Unlike the SQLite version (which returns ISO strings), this returns proper
    ``datetime`` objects because psycopg2 deserialises TIMESTAMPTZ columns
    automatically.  ``_within_attribution_window`` accepts both forms.
    """
    placeholders = ",".join(["%s"] * len(_CONVERSION_EVENT_TYPES))
    cur.execute(
        f"""SELECT payload, received_at FROM webhook_log
            WHERE event_type IN ({placeholders})""",
        _CONVERSION_EVENT_TYPES,
    )
    result: dict[str, list] = {}
    for row in cur.fetchall():
        email = _extract_webhook_email(row["payload"])
        if email:
            result.setdefault(email, []).append(row["received_at"])
    return result


def _within_attribution_window(shown_at: datetime | str, converted_at: datetime | str, window_days: float) -> bool:
    if isinstance(shown_at, str):
        shown_at = datetime.fromisoformat(shown_at)
    if isinstance(converted_at, str):
        converted_at = datetime.fromisoformat(converted_at)
    # Ensure both are offset-aware so subtraction works regardless of source
    if shown_at.tzinfo is None:
        shown_at = shown_at.replace(tzinfo=timezone.utc)
    if converted_at.tzinfo is None:
        converted_at = converted_at.replace(tzinfo=timezone.utc)
    delta_days = (converted_at - shown_at).total_seconds() / 86400
    return 0 <= delta_days <= window_days


def get_prompt_effectiveness() -> dict[str, dict]:
    """Per-signal (and per-variant) Prompt Effectiveness Score = conversions / impressions.

    Returns {signal: {impressions, conversions, score, variants: {variant: {impressions, conversions, score}}}}
    """
    with _conn() as cur:
        cur.execute("SELECT email, signal, variant, shown_at FROM signal_log")
        impressions = cur.fetchall()
        conversions_by_email = _conversions_by_email(cur)

    stats: dict[str, dict] = {}
    for row in impressions:
        variant = row["variant"] or "default"
        top = stats.setdefault(row["signal"], {"impressions": 0, "conversions": 0, "variants": {}})
        var_stat = top["variants"].setdefault(variant, {"impressions": 0, "conversions": 0})

        top["impressions"] += 1
        var_stat["impressions"] += 1

        converted = any(
            _within_attribution_window(row["shown_at"], converted_at, PROMPT_ATTRIBUTION_WINDOW_DAYS)
            for converted_at in conversions_by_email.get(row["email"], [])
        )
        if converted:
            top["conversions"] += 1
            var_stat["conversions"] += 1

    for top in stats.values():
        top["score"] = round(top["conversions"] / top["impressions"], 4) if top["impressions"] else None
        for var_stat in top["variants"].values():
            var_stat["score"] = (
                round(var_stat["conversions"] / var_stat["impressions"], 4) if var_stat["impressions"] else None
            )

    return stats


# ── Signal effectiveness classification ───────────────────────────────────────
# These thresholds mirror the SQLite version exactly — they're business logic,
# not database logic, so nothing needs translating.

MIN_IMPRESSIONS_FOR_CONFIDENCE = 20
HIGH_NOISE_IMPRESSIONS = 100
HIGH_SCORE_THRESHOLD = 0.15
LOW_SCORE_THRESHOLD = 0.03
HIGH_NOISE_SCORE_THRESHOLD = 0.01
STRATEGIC_SCORE_THRESHOLD = 0.25


def classify_signal_effectiveness(effectiveness: dict | None = None) -> list[dict]:
    """Turn get_prompt_effectiveness() output into a ranked, classified action list.

    Returns a list of dicts (signal, impressions, conversions, score, class,
    action, reason), sorted by score desc, volume as tiebreak.
    """
    effectiveness = effectiveness if effectiveness is not None else get_prompt_effectiveness()
    results = []

    for signal, stat in effectiveness.items():
        impressions = stat["impressions"]
        conversions = stat["conversions"]
        score = stat["score"] or 0.0

        if impressions < MIN_IMPRESSIONS_FOR_CONFIDENCE and not (conversions > 0 and impressions <= 5):
            klass = "insufficient_data"
            action = "Maintain"
            reason = (
                f"Only {impressions} impression(s) — below the {MIN_IMPRESSIONS_FOR_CONFIDENCE}-impression "
                "confidence floor. Score is not yet meaningful; do not change priority or copy on this alone."
            )
        elif impressions >= HIGH_NOISE_IMPRESSIONS and score < HIGH_NOISE_SCORE_THRESHOLD:
            klass = "high_noise"
            action = "Reduce exposure"
            reason = (
                f"{impressions} impressions but only {score:.1%} conversion — high fatigue cost for "
                "near-zero return. Tighten the context filter, extend its cooldown, or drop it down the "
                "priority order rather than letting it keep firing at this volume."
            )
        elif impressions >= MIN_IMPRESSIONS_FOR_CONFIDENCE and score < LOW_SCORE_THRESHOLD:
            klass = "underperforming"
            action = "Optimise messaging"
            reason = (
                f"{impressions} impressions, only {score:.1%} converting — real volume but copy, "
                "placement, or the signal definition itself likely needs rework before changing priority."
            )
        elif impressions < MIN_IMPRESSIONS_FOR_CONFIDENCE and score >= STRATEGIC_SCORE_THRESHOLD:
            klass = "strategic"
            action = "Maintain"
            reason = (
                f"Low volume ({impressions}) but {score:.1%} conversion — a niche, high-intent signal "
                "(e.g. blocked intent). Low volume is expected behaviour here, not a problem to fix; "
                "don't force more exposure just to chase volume."
            )
        elif impressions >= MIN_IMPRESSIONS_FOR_CONFIDENCE and score >= HIGH_SCORE_THRESHOLD:
            klass = "high_performing"
            action = "Increase priority"
            reason = (
                f"{impressions} impressions at {score:.1%} conversion — proven at real volume. "
                "Candidate to move earlier in priority order or expand to adjacent contexts."
            )
        else:
            klass = "moderate"
            action = "Maintain"
            reason = f"{impressions} impressions at {score:.1%} — within normal range, no action indicated."

        results.append(
            {
                "signal": signal,
                "impressions": impressions,
                "conversions": conversions,
                "score": stat["score"],
                "class": klass,
                "action": action,
                "reason": reason,
            }
        )

    results.sort(key=lambda r: (r["score"] or 0, r["impressions"]), reverse=True)
    return results


# ── Conversion funnel: WVRS → revenue ─────────────────────────────────────────

WVRS_WINDOW_MINUTES = 60


def _price_to_number(price_str: str) -> float:
    """'£29/month' -> 29.0.  Strips everything but digits and a decimal point."""
    digits = re.sub(r"[^\d.]", "", price_str or "")
    try:
        return float(digits)
    except ValueError:
        return 0.0


def get_conversion_funnel() -> dict:
    """Funnel from product engagement through to attributed revenue:

        Activated -> Engaged (runs) -> WVRS (value-realised) -> Prompted
        (signal shown) -> Converted -> Revenue
    """
    with _conn() as cur:
        cur.execute(
            "SELECT COUNT(DISTINCT email) AS n FROM usage_events WHERE event_type = 'run'"
        )
        activated_users = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM usage_events WHERE event_type = 'run'")
        total_runs = cur.fetchone()["n"]

        cur.execute(
            "SELECT email, occurred_at FROM usage_events WHERE event_type = 'run'"
        )
        runs = cur.fetchall()

        placeholders = ",".join(["%s"] * len(_FOLLOW_THROUGH_EVENTS))
        cur.execute(
            f"""SELECT email, occurred_at FROM usage_events
                WHERE event_type IN ({placeholders})""",
            _FOLLOW_THROUGH_EVENTS,
        )
        follow_through_rows = cur.fetchall()

        cur.execute("SELECT COUNT(*) AS n FROM signal_log")
        signals_shown = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(DISTINCT email) AS n FROM signal_log")
        prompted_users = cur.fetchone()["n"]

        cur.execute("SELECT email, shown_at FROM signal_log")
        impressions = cur.fetchall()

        conversions_by_email = _conversions_by_email(cur)

        cur.execute(
            "SELECT email, plan FROM subscriptions WHERE status = 'active'"
        )
        plans_by_email = {row["email"]: row["plan"] for row in cur.fetchall()}

    follow_through_by_email: dict[str, list] = {}
    for row in follow_through_rows:
        follow_through_by_email.setdefault(row["email"], []).append(row["occurred_at"])

    def _as_aware(dt: datetime | str) -> datetime:
        """Coerce to a timezone-aware datetime (psycopg2 already returns aware
        datetimes for TIMESTAMPTZ, but guard against edge cases)."""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    wvrs_count = 0
    for row in runs:
        run_at = _as_aware(row["occurred_at"])
        if any(
            0 <= (_as_aware(ft) - run_at).total_seconds() / 60 <= WVRS_WINDOW_MINUTES
            for ft in follow_through_by_email.get(row["email"], [])
        ):
            wvrs_count += 1

    attributed_converting_emails: set[str] = set()
    for row in impressions:
        for converted_at in conversions_by_email.get(row["email"], []):
            if _within_attribution_window(row["shown_at"], converted_at, PROMPT_ATTRIBUTION_WINDOW_DAYS):
                attributed_converting_emails.add(row["email"])
                break

    total_converting_emails = set(conversions_by_email.keys())
    unattributed_converting_emails = total_converting_emails - attributed_converting_emails

    attributed_revenue = sum(
        _price_to_number(get_plan(plans_by_email.get(email, "free"))["price"])
        for email in attributed_converting_emails
    )
    total_revenue = sum(
        _price_to_number(get_plan(plans_by_email.get(email, "free"))["price"])
        for email in total_converting_emails
    )

    return {
        "activated_users": activated_users,
        "total_runs": total_runs,
        "wvrs_count": wvrs_count,
        "wvrs_rate": round(wvrs_count / total_runs, 4) if total_runs else None,
        "signals_shown": signals_shown,
        "prompted_users": prompted_users,
        "converted_users": len(total_converting_emails),
        "attributed_converted_users": len(attributed_converting_emails),
        "unattributed_converted_users": len(unattributed_converting_emails),
        "attributed_monthly_revenue": round(attributed_revenue, 2),
        "total_monthly_revenue": round(total_revenue, 2),
    }

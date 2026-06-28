"""
Licence Manager — SQLite-backed subscription store.

Single source of truth for subscription data written by the webhook server
and read by the Streamlit app when validating licence keys.

Database location (override in .streamlit/secrets.toml):

    [storage]
    db_path = "/absolute/path/to/subscriptions.db"

Default: <project-root>/data/subscriptions.db
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from config.plans import get_plan

log = logging.getLogger(__name__)

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "subscriptions.db"


def _db_path() -> Path:
    try:
        import streamlit as st
        p = st.secrets.get("storage", {}).get("db_path")
        if p:
            return Path(p)
    except Exception:
        pass
    return _DEFAULT_DB


# ── Schema ────────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT    NOT NULL,
    plan            TEXT    NOT NULL DEFAULT 'free',
    licence_key     TEXT    UNIQUE,
    subscription_id TEXT,
    order_id        TEXT,
    status          TEXT    NOT NULL DEFAULT 'active',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_email
    ON subscriptions (email);

CREATE INDEX IF NOT EXISTS idx_sub_subscription_id
    ON subscriptions (subscription_id);

CREATE TABLE IF NOT EXISTS run_counts (
    email       TEXT NOT NULL,
    month_key   TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (email, month_key)
);

CREATE TABLE IF NOT EXISTS webhook_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT,
    payload     TEXT,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    plan        TEXT,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_email ON usage_events (email);
CREATE INDEX IF NOT EXISTS idx_usage_type ON usage_events (event_type);

CREATE TABLE IF NOT EXISTS email_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    email_type  TEXT NOT NULL,
    sent_at     TEXT NOT NULL,
    UNIQUE(email, email_type)
);

CREATE TABLE IF NOT EXISTS milestone_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    milestone   INTEGER NOT NULL,
    month_key   TEXT NOT NULL,
    shown_at    TEXT NOT NULL,
    UNIQUE(email, milestone, month_key)
);

CREATE TABLE IF NOT EXISTS signal_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    signal      TEXT NOT NULL,
    shown_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_signal_log_lookup ON signal_log (email, signal);

CREATE TABLE IF NOT EXISTS prompt_evaluations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL,
    shown       INTEGER NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prompt_eval_email ON prompt_evaluations (email);
"""

# Nullable profile/telemetry columns added after the original subscriptions
# table shipped — SQLite has no "ADD COLUMN IF NOT EXISTS", so each is added
# conditionally based on PRAGMA table_info.
_PROFILE_COLUMNS = {
    "profession": "TEXT",
    "position_level": "TEXT",
    "industry": "TEXT",
    "business_activity": "TEXT",
    "first_used_at": "TEXT",
}


def _ensure_profile_columns(con: sqlite3.Connection) -> None:
    existing = {row["name"] for row in con.execute("PRAGMA table_info(subscriptions)")}
    for column, col_type in _PROFILE_COLUMNS.items():
        if column not in existing:
            con.execute(f"ALTER TABLE subscriptions ADD COLUMN {column} {col_type}")


def _ensure_signal_log_columns(con: sqlite3.Connection) -> None:
    """variant was added after signal_log shipped, for the per-prompt A/B
    testing layer — existing rows backfill to 'default' so effectiveness
    queries can group by (signal, variant) without NULL-handling everywhere."""
    existing = {row["name"] for row in con.execute("PRAGMA table_info(signal_log)")}
    if "variant" not in existing:
        con.execute("ALTER TABLE signal_log ADD COLUMN variant TEXT NOT NULL DEFAULT 'default'")


@contextmanager
def _conn():
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(_SCHEMA)
        _ensure_profile_columns(con)
        _ensure_signal_log_columns(con)
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Key generation ────────────────────────────────────────────────────────────
def generate_licence_key() -> str:
    """Return a cryptographically random XXXX-XXXX-XXXX-XXXX licence key."""
    parts = [secrets.token_hex(2).upper() for _ in range(4)]
    return "-".join(parts)


# ── Write operations ──────────────────────────────────────────────────────────
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
    with _conn() as con:
        existing = con.execute(
            "SELECT licence_key FROM subscriptions WHERE email = ?", (email,)
        ).fetchone()

        key = existing["licence_key"] if existing else None
        if key is None:
            key = licence_key or generate_licence_key()

        now = _now()
        con.execute(
            """
            INSERT INTO subscriptions
                (email, plan, licence_key, subscription_id, order_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                plan            = excluded.plan,
                subscription_id = COALESCE(NULLIF(excluded.subscription_id, ''), subscriptions.subscription_id),
                order_id        = COALESCE(NULLIF(excluded.order_id, ''),        subscriptions.order_id),
                status          = excluded.status,
                updated_at      = excluded.updated_at
            """,
            (email, plan, key, subscription_id, order_id, status, now, now),
        )

    log.info("upsert_subscription: email=%s plan=%s status=%s", email, plan, status)
    return key


def cancel_subscription(subscription_id: str) -> bool:
    """Downgrade to free and mark inactive. Returns True if a row was found."""
    with _conn() as con:
        cur = con.execute(
            """UPDATE subscriptions
               SET plan = 'free', status = 'inactive', updated_at = ?
               WHERE subscription_id = ?""",
            (_now(), subscription_id),
        )
    found = cur.rowcount > 0
    if found:
        log.info("cancel_subscription: subscription_id=%s → downgraded to free", subscription_id)
    else:
        log.warning("cancel_subscription: subscription_id=%s not found", subscription_id)
    return found


# ── Read operations ───────────────────────────────────────────────────────────
def get_by_key(licence_key: str) -> Optional[dict]:
    """Return subscription row as dict, or None."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM subscriptions WHERE licence_key = ?",
            (licence_key.strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_by_email(email: str) -> Optional[dict]:
    """Return subscription row as dict, or None."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM subscriptions WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_by_subscription_id(subscription_id: str) -> Optional[dict]:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM subscriptions WHERE subscription_id = ?",
            (subscription_id,),
        ).fetchone()
    return dict(row) if row else None


# ── Local licence validation ──────────────────────────────────────────────────
def validate_local_key(licence_key: str) -> dict:
    """Validate against local DB. Returns {"valid": bool, "plan": str, "error": str | None}."""
    if not licence_key or not licence_key.strip():
        return {"valid": False, "plan": "free", "error": None}

    row = get_by_key(licence_key)
    if not row:
        return {"valid": False, "plan": "free", "error": None}  # not found locally
    if row["status"] != "active":
        return {"valid": False, "plan": "free", "error": "Licence is inactive or cancelled."}

    return {"valid": True, "plan": row["plan"], "error": None}


# ── Persistent run counts ─────────────────────────────────────────────────────
def _month_key() -> str:
    return date.today().strftime("%Y-%m")


def get_runs(email: str) -> int:
    with _conn() as con:
        row = con.execute(
            "SELECT count FROM run_counts WHERE email = ? AND month_key = ?",
            (email.lower().strip(), _month_key()),
        ).fetchone()
    return row["count"] if row else 0


def get_runs_this_calendar_month(email: str) -> int:
    """'run' events logged this calendar month, from usage_events.

    Used for milestone messaging — distinct from get_runs()/run_counts, which
    is only ever written to by increment_runs() and isn't currently called
    anywhere, so it would always read back 0.
    """
    email = email.lower().strip()
    with _conn() as con:
        row = con.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = ? AND event_type = 'run' AND strftime('%Y-%m', occurred_at) = ?""",
            (email, _month_key()),
        ).fetchone()
    return row["n"]


def increment_runs(email: str) -> None:
    with _conn() as con:
        con.execute(
            """INSERT INTO run_counts (email, month_key, count) VALUES (?, ?, 1)
               ON CONFLICT(email, month_key) DO UPDATE SET count = count + 1""",
            (email.lower().strip(), _month_key()),
        )


# ── Webhook event logging ─────────────────────────────────────────────────────
def log_webhook_event(event_type: str, payload: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO webhook_log (event_type, payload, received_at) VALUES (?, ?, ?)",
            (event_type, payload, _now()),
        )


# ── Client profile (no names; role/industry categorisation only) ──────────────
def update_subscription_profile(
    email: str,
    *,
    profession: str = "",
    position_level: str = "",
    industry: str = "",
    business_activity: str = "",
) -> None:
    """Attach optional, name-free demographic/industry data to a subscriber."""
    with _conn() as con:
        con.execute(
            """UPDATE subscriptions
               SET profession         = COALESCE(NULLIF(?, ''), profession),
                   position_level     = COALESCE(NULLIF(?, ''), position_level),
                   industry           = COALESCE(NULLIF(?, ''), industry),
                   business_activity  = COALESCE(NULLIF(?, ''), business_activity),
                   updated_at         = ?
               WHERE email = ?""",
            (profession, position_level, industry, business_activity, _now(), email.lower().strip()),
        )


# ── Usage event logging (internal analytics; no PII beyond email) ─────────────
def log_usage_event(email: str, event_type: str, plan: str = "") -> None:
    """Record a behavioral event (activate/run/export_excel/export_pdf/ai_advisory)."""
    if not email:
        return
    email = email.lower().strip()
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO usage_events (email, event_type, plan, occurred_at) VALUES (?, ?, ?, ?)",
            (email, event_type, plan, now),
        )
        if event_type == "run":
            con.execute(
                "UPDATE subscriptions SET first_used_at = COALESCE(first_used_at, ?) WHERE email = ?",
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
    with _conn() as con:
        sub = con.execute(
            "SELECT plan FROM subscriptions WHERE email = ?", (email,)
        ).fetchone()
        plan = sub["plan"] if sub else "free"

        runs_last_30_days = con.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = ? AND event_type = 'run' AND occurred_at >= datetime('now', '-30 days')""",
            (email,),
        ).fetchone()["n"]

        runs_last_24h = con.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = ? AND event_type = 'run' AND occurred_at >= datetime('now', '-1 day')""",
            (email,),
        ).fetchone()["n"]

        follow_through_last_30_days = con.execute(
            f"""SELECT COUNT(*) AS n FROM usage_events
                WHERE email = ? AND event_type IN ({",".join("?" * len(_FOLLOW_THROUGH_EVENTS))})
                AND occurred_at >= datetime('now', '-30 days')""",
            (email, *_FOLLOW_THROUGH_EVENTS),
        ).fetchone()["n"]

        total_runs = con.execute(
            "SELECT COUNT(*) AS n FROM usage_events WHERE email = ? AND event_type = 'run'",
            (email,),
        ).fetchone()["n"]

        export_blocked_last_30_days = con.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = ? AND event_type = 'export_blocked' AND occurred_at >= datetime('now', '-30 days')""",
            (email,),
        ).fetchone()["n"]

        advisory_blocked_last_30_days = con.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = ? AND event_type = 'advisory_blocked' AND occurred_at >= datetime('now', '-30 days')""",
            (email,),
        ).fetchone()["n"]

        used_events = {
            r["event_type"]
            for r in con.execute(
                "SELECT DISTINCT event_type FROM usage_events WHERE email = ?", (email,)
            ).fetchall()
        }

        ai_advisory_last_30_days = con.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = ? AND event_type = 'ai_advisory' AND occurred_at >= datetime('now', '-30 days')""",
            (email,),
        ).fetchone()["n"]

        ai_advisory_prior_30_days = con.execute(
            """SELECT COUNT(*) AS n FROM usage_events
               WHERE email = ? AND event_type = 'ai_advisory'
               AND occurred_at >= datetime('now', '-60 days') AND occurred_at < datetime('now', '-30 days')""",
            (email,),
        ).fetchone()["n"]

        active_months = con.execute(
            """SELECT COUNT(DISTINCT substr(occurred_at, 1, 7)) AS n FROM usage_events
               WHERE email = ? AND event_type = 'run'""",
            (email,),
        ).fetchone()["n"]

        last_run_row = con.execute(
            """SELECT julianday('now') - julianday(MAX(occurred_at)) AS days
               FROM usage_events WHERE email = ? AND event_type = 'run'""",
            (email,),
        ).fetchone()
        days_since_last_run = round(last_run_row["days"], 1) if last_run_row["days"] is not None else None

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


# ── Lifecycle email queue ──────────────────────────────────────────────────────
def get_users_needing_activation_nudge(inactivity_days: int = 7) -> list[str]:
    """Emails of subscribers who activated a licence but never ran their first
    dataset, where that gap has lasted at least *inactivity_days*.

    Excludes anyone already sent the 'activation_nudge' email so the lifecycle
    runner can be invoked repeatedly (e.g. daily cron) without double-sending.
    """
    with _conn() as con:
        rows = con.execute(
            """SELECT s.email FROM subscriptions s
               WHERE s.status = 'active'
               AND s.first_used_at IS NULL
               AND s.created_at <= datetime('now', ?)
               AND NOT EXISTS (
                   SELECT 1 FROM email_log e
                   WHERE e.email = s.email AND e.email_type = 'activation_nudge'
               )""",
            (f"-{inactivity_days} days",),
        ).fetchall()
    return [r["email"] for r in rows]


def log_email_sent(email: str, email_type: str) -> None:
    """Record that a lifecycle email was sent, so it isn't sent twice."""
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO email_log (email, email_type, sent_at) VALUES (?, ?, ?)",
            (email.lower().strip(), email_type, _now()),
        )


# ── In-app run-count milestones (habit reinforcement) ──────────────────────────
def milestone_already_shown(email: str, milestone: int) -> bool:
    """True if this milestone was already celebrated for this email this month."""
    email = email.lower().strip()
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM milestone_log WHERE email = ? AND milestone = ? AND month_key = ?",
            (email, milestone, _month_key()),
        ).fetchone()
    return row is not None


def log_milestone_shown(email: str, milestone: int) -> None:
    """Record that a run-count milestone toast was shown, so it only fires once per month."""
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO milestone_log (email, milestone, month_key, shown_at) VALUES (?, ?, ?, ?)",
            (email.lower().strip(), milestone, _month_key(), _now()),
        )


# ── Pricing-prompt cooldown (avoid repeating the same message too soon) ────────
def signal_shown_recently(email: str, signal: str, cooldown_hours: int) -> bool:
    """True if *signal* was already shown to this email within the last cooldown_hours."""
    email = email.lower().strip()
    with _conn() as con:
        row = con.execute(
            """SELECT 1 FROM signal_log
               WHERE email = ? AND signal = ? AND shown_at >= datetime('now', ?)""",
            (email, signal, f"-{cooldown_hours} hours"),
        ).fetchone()
    return row is not None


def log_signal_shown(email: str, signal: str, variant: str = "default") -> None:
    """Record that a pricing-prompt signal (and which A/B copy variant) was
    shown, for cooldown tracking and per-variant effectiveness."""
    with _conn() as con:
        con.execute(
            "INSERT INTO signal_log (email, signal, variant, shown_at) VALUES (?, ?, ?, ?)",
            (email.lower().strip(), signal, variant, _now()),
        )


# ── Monetisation-messaging dry-spell tracking ──────────────────────────────────
def log_prompt_evaluation(email: str, shown: bool) -> None:
    """Record that the once-per-session targeted-prompt evaluation ran, and
    whether it actually rendered anything. Distinct from signal_log (which
    only records successful shows) — this lets us detect sessions where
    nothing was shown at all, e.g. every matching signal was cooldown-suppressed.
    """
    if not email:
        return
    with _conn() as con:
        con.execute(
            "INSERT INTO prompt_evaluations (email, shown, occurred_at) VALUES (?, ?, ?)",
            (email.lower().strip(), int(shown), _now()),
        )


def sessions_without_prompt(email: str, lookback: int = 3) -> int:
    """Count of consecutive most-recent session evaluations (newest first)
    that showed nothing, stopping at the first one that did. Used to trigger
    a fallback so a user can't go indefinitely without ever seeing any
    monetisation messaging just because every signal happened to be on
    cooldown each time they visited."""
    email = email.lower().strip()
    with _conn() as con:
        rows = con.execute(
            "SELECT shown FROM prompt_evaluations WHERE email = ? ORDER BY id DESC LIMIT ?",
            (email, lookback),
        ).fetchall()
    streak = 0
    for row in rows:
        if row["shown"]:
            break
        streak += 1
    return streak


def get_usage_analytics() -> dict:
    """Aggregated, anonymised usage/demographic stats for the internal dashboard.

    Returns only counts/medians — never individual subscriber rows.
    """
    with _conn() as con:
        def _breakdown(column: str) -> dict:
            rows = con.execute(
                f"""SELECT COALESCE(NULLIF({column}, ''), 'Not provided') AS k, COUNT(*) AS n
                    FROM subscriptions WHERE status = 'active' GROUP BY k ORDER BY n DESC""",
            ).fetchall()
            return {r["k"]: r["n"] for r in rows}

        industry_breakdown = _breakdown("industry")
        profession_breakdown = _breakdown("profession")
        position_breakdown = _breakdown("position_level")
        plan_breakdown = _breakdown("plan")

        feature_rows = con.execute(
            "SELECT event_type, COUNT(*) AS n FROM usage_events GROUP BY event_type ORDER BY n DESC"
        ).fetchall()
        feature_usage_breakdown = {r["event_type"]: r["n"] for r in feature_rows}

        conversion_rows = con.execute(
            """SELECT julianday(first_used_at) - julianday(created_at) AS days
               FROM subscriptions
               WHERE first_used_at IS NOT NULL AND status = 'active'"""
        ).fetchall()
        conversion_times_days = [round(r["days"], 2) for r in conversion_rows if r["days"] is not None]

        tenure_rows = con.execute(
            "SELECT julianday('now') - julianday(created_at) AS days FROM subscriptions WHERE status = 'active'"
        ).fetchall()
        tenure_days = [round(r["days"], 2) for r in tenure_rows if r["days"] is not None]

        active_subscribers = con.execute(
            "SELECT COUNT(*) AS n FROM subscriptions WHERE status = 'active'"
        ).fetchone()["n"]

        total_runs = feature_usage_breakdown.get("run", 0)

        trend_rows = con.execute(
            """SELECT substr(occurred_at, 1, 10) AS day, COUNT(*) AS n
               FROM usage_events
               WHERE event_type = 'run' AND occurred_at >= datetime('now', '-30 days')
               GROUP BY day ORDER BY day"""
        ).fetchall()
        runs_last_30_days = {r["day"]: r["n"] for r in trend_rows}

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


# ── Prompt Effectiveness Score ──────────────────────────────────────────────────
_CONVERSION_EVENT_TYPES = ("order_created", "subscription_created")
PROMPT_ATTRIBUTION_WINDOW_DAYS = 7


def _extract_webhook_email(payload_json: str) -> str:
    """Best-effort email extraction from a raw LemonSqueezy webhook payload —
    mirrors services/webhook_server.py's _extract(), since signal_log has no
    direct foreign key into billing events and email is the only join key
    the two systems share."""
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


def _conversions_by_email(con: sqlite3.Connection) -> dict[str, list[str]]:
    """email -> [received_at, ...] for every paid-plan webhook event. Shared
    by get_prompt_effectiveness() and get_conversion_funnel() so both use the
    exact same conversion definition and attribution emails."""
    conversion_rows = con.execute(
        f"""SELECT payload, received_at FROM webhook_log
            WHERE event_type IN ({",".join("?" * len(_CONVERSION_EVENT_TYPES))})""",
        _CONVERSION_EVENT_TYPES,
    ).fetchall()
    result: dict[str, list[str]] = {}
    for row in conversion_rows:
        email = _extract_webhook_email(row["payload"])
        if email:
            result.setdefault(email, []).append(row["received_at"])
    return result


def _within_attribution_window(shown_at_iso: str, converted_at_iso: str, window_days: float) -> bool:
    shown_at = datetime.fromisoformat(shown_at_iso)
    converted_at = datetime.fromisoformat(converted_at_iso)
    delta_days = (converted_at - shown_at).total_seconds() / 86400
    return 0 <= delta_days <= window_days


def get_prompt_effectiveness() -> dict[str, dict]:
    """Per-signal (and per-variant) Prompt Effectiveness Score = conversions / impressions.

    Impressions: rows in signal_log (every time that signal was actually
    rendered to a user). Conversions: a paid-plan webhook event for the same
    email landing within PROMPT_ATTRIBUTION_WINDOW_DAYS after that impression
    — there's no direct link between signal_log and billing events, so email
    + time-window is the closest available attribution, not a guaranteed
    causal link.

    Returns {signal: {impressions, conversions, score, variants: {variant: {impressions, conversions, score}}}}
    — the top-level numbers are the signal's combined total across all its
    A/B copy variants; "variants" is the per-variant breakdown for comparing
    which wording is actually winning.
    """
    with _conn() as con:
        impressions = con.execute(
            "SELECT email, signal, variant, shown_at FROM signal_log"
        ).fetchall()
        conversions_by_email = _conversions_by_email(con)

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


# Thresholds are deliberately coarse — at this app's subscriber scale, a
# precise statistical test (binomial confidence interval, etc.) would mostly
# just measure sample-size noise. These exist to stop premature optimisation
# on tiny samples, not to make a fine-grained call.
MIN_IMPRESSIONS_FOR_CONFIDENCE = 20
HIGH_NOISE_IMPRESSIONS = 100
HIGH_SCORE_THRESHOLD = 0.15
LOW_SCORE_THRESHOLD = 0.03
HIGH_NOISE_SCORE_THRESHOLD = 0.01
STRATEGIC_SCORE_THRESHOLD = 0.25


def classify_signal_effectiveness(effectiveness: dict | None = None) -> list[dict]:
    """Turn get_prompt_effectiveness() output into a ranked, classified
    action list — efficiency (score) and impact (volume) are never collapsed
    into one ranking; a signal can earn attention on either axis but only
    becomes a confident "act on this" once a result clears
    MIN_IMPRESSIONS_FOR_CONFIDENCE.

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


# ── Conversion funnel: WVRS → revenue ───────────────────────────────────────────
# How long after a 'run' a follow-through event still counts as "the same
# sitting" — mirrors the in-app same-session proxy (services.upgrade_messaging's
# follow_through_this_session), just computed retrospectively from
# usage_events timestamps instead of live st.session_state.
WVRS_WINDOW_MINUTES = 60


def _price_to_number(price_str: str) -> float:
    """'£29/month' -> 29.0. Best-effort — config.plans prices are display
    strings, not structured data, so this just strips everything but digits
    and a decimal point."""
    digits = re.sub(r"[^\d.]", "", price_str or "")
    try:
        return float(digits)
    except ValueError:
        return 0.0


def get_conversion_funnel() -> dict:
    """Funnel from product engagement through to attributed revenue:

        Activated -> Engaged (runs) -> WVRS (value-realised) -> Prompted
        (signal shown) -> Converted -> Revenue

    Every stage after "Engaged" is an approximation layered on top of
    whatever the previous gaps in this conversation already flagged:
      - WVRS: a 'run' followed by a qualifying follow-through event for the
        same email within WVRS_WINDOW_MINUTES. Same proxy logic as
        follow_through_this_session, just retrospective over usage_events
        instead of live session_state.
      - Conversion attribution: a webhook conversion event for the same
        email within PROMPT_ATTRIBUTION_WINDOW_DAYS of a signal impression —
        probabilistic, not causal (see get_prompt_effectiveness()).
      - Revenue: each converting email's *current* subscriptions.plan price,
        not the plan at the moment of conversion — wrong for anyone who's
        since upgraded/downgraded again, consistent with this whole metric
        being directional rather than an accounting-grade figure.
    """
    with _conn() as con:
        activated_users = con.execute(
            "SELECT COUNT(DISTINCT email) AS n FROM usage_events WHERE event_type = 'run'"
        ).fetchone()["n"]

        total_runs = con.execute(
            "SELECT COUNT(*) AS n FROM usage_events WHERE event_type = 'run'"
        ).fetchone()["n"]

        runs = con.execute(
            "SELECT email, occurred_at FROM usage_events WHERE event_type = 'run'"
        ).fetchall()

        follow_through_rows = con.execute(
            f"""SELECT email, occurred_at FROM usage_events
                WHERE event_type IN ({",".join("?" * len(_FOLLOW_THROUGH_EVENTS))})""",
            _FOLLOW_THROUGH_EVENTS,
        ).fetchall()

        signals_shown = con.execute("SELECT COUNT(*) AS n FROM signal_log").fetchone()["n"]
        prompted_users = con.execute(
            "SELECT COUNT(DISTINCT email) AS n FROM signal_log"
        ).fetchone()["n"]

        impressions = con.execute("SELECT email, shown_at FROM signal_log").fetchall()
        conversions_by_email = _conversions_by_email(con)

        plans_by_email = {
            row["email"]: row["plan"]
            for row in con.execute(
                "SELECT email, plan FROM subscriptions WHERE status = 'active'"
            ).fetchall()
        }

    follow_through_by_email: dict[str, list[str]] = {}
    for row in follow_through_rows:
        follow_through_by_email.setdefault(row["email"], []).append(row["occurred_at"])

    wvrs_count = 0
    for row in runs:
        run_at = datetime.fromisoformat(row["occurred_at"])
        if any(
            0 <= (datetime.fromisoformat(ft) - run_at).total_seconds() / 60 <= WVRS_WINDOW_MINUTES
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

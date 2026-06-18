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
import logging
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

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
"""


@contextmanager
def _conn():
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db, check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(_SCHEMA)
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

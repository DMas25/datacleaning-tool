"""Persistence and analytics for the Free Data Health Check feature.

All functions degrade gracefully when no database is available:
- has_used_free_check  → False   (relies on session state as fallback)
- record_health_check  → None
- log_event            → no-op
- is_rate_limited      → False

This ensures the feature works in local dev without any DB configuration.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

log = logging.getLogger(__name__)


# ── DB availability ───────────────────────────────────────────────────────────

def _db_available() -> bool:
    if os.environ.get("DATABASE_URL", ""):
        return True
    try:
        import streamlit as st
        return bool(st.secrets.get("supabase", {}).get("database_url", ""))
    except Exception:
        return False


def _conn():
    from services.licence_manager_pg import _conn as _pg_conn
    return _pg_conn()


# ── Rate limiting ─────────────────────────────────────────────────────────────

def is_rate_limited(ip_address: str, max_per_hour: int = 3) -> bool:
    """True if this IP has started more than max_per_hour uploads in the last hour."""
    if not ip_address or not _db_available():
        return False
    try:
        with _conn() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM health_check_events
                WHERE metadata->>'ip_address' = %s
                  AND event_type = 'upload_started'
                  AND occurred_at >= NOW() - INTERVAL '1 hour'
                """,
                (ip_address,),
            )
            row = cur.fetchone()
            return (int(row["cnt"]) >= max_per_hour) if row else False
    except Exception as exc:
        log.warning("is_rate_limited: DB error (%s) — defaulting False", exc)
        return False


# ── Email deduplication ───────────────────────────────────────────────────────

def has_used_free_check(email: str) -> bool:
    """Return True if this email has already completed a free health check."""
    if not _db_available():
        return False
    try:
        with _conn() as cur:
            cur.execute(
                "SELECT 1 FROM free_health_checks WHERE email = %s LIMIT 1",
                (email.lower().strip(),),
            )
            return cur.fetchone() is not None
    except Exception as exc:
        log.warning("has_used_free_check: DB error (%s) — defaulting False", exc)
        return False


# ── Record results ────────────────────────────────────────────────────────────

def record_health_check(
    email: str,
    file_name: str,
    file_size_bytes: int,
    row_count: int,
    column_count: int,
    quality_score: int,
    result_summary: dict,
    ip_address: str = "",
) -> Optional[int]:
    """Insert a row into free_health_checks and return its id (None on failure).

    result_summary must be JSON-serialisable. The '_charts' key (Plotly figures)
    should be stripped before passing this dict.
    """
    if not _db_available():
        return None
    try:
        safe_summary = {k: v for k, v in result_summary.items() if not k.startswith("_")}
        with _conn() as cur:
            cur.execute(
                """
                INSERT INTO free_health_checks
                    (email, file_name, file_size_bytes, row_count, column_count,
                     quality_score, result_json, ip_address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO UPDATE
                    SET file_name       = EXCLUDED.file_name,
                        file_size_bytes = EXCLUDED.file_size_bytes,
                        row_count       = EXCLUDED.row_count,
                        column_count    = EXCLUDED.column_count,
                        quality_score   = EXCLUDED.quality_score,
                        result_json     = EXCLUDED.result_json,
                        ip_address      = EXCLUDED.ip_address,
                        uploaded_at     = NOW()
                RETURNING id
                """,
                (
                    email.lower().strip(),
                    file_name,
                    file_size_bytes,
                    row_count,
                    column_count,
                    quality_score,
                    json.dumps(safe_summary),
                    ip_address,
                ),
            )
            row = cur.fetchone()
            return int(row["id"]) if row else None
    except Exception as exc:
        log.warning("record_health_check: DB error (%s)", exc)
        return None


# ── Analytics ─────────────────────────────────────────────────────────────────

def log_event(email: str, event_type: str, metadata: dict | None = None) -> None:
    """Fire-and-forget analytics event. Never raises."""
    if not _db_available():
        return
    try:
        with _conn() as cur:
            cur.execute(
                """
                INSERT INTO health_check_events (email, event_type, metadata)
                VALUES (%s, %s, %s)
                """,
                (
                    (email or "").lower().strip() or None,
                    event_type,
                    json.dumps(metadata or {}),
                ),
            )
    except Exception as exc:
        log.debug("log_event: DB error (%s)", exc)


def record_cta_click(check_id: Optional[int], cta_name: str, email: str = "") -> None:
    """Record which CTA the user clicked on the health check report."""
    if not _db_available():
        return
    try:
        if check_id:
            with _conn() as cur:
                cur.execute(
                    "UPDATE free_health_checks SET cta_clicked = %s WHERE id = %s",
                    (cta_name, check_id),
                )
        log_event(email, "cta_clicked", {"cta": cta_name, "check_id": check_id})
    except Exception as exc:
        log.debug("record_cta_click: DB error (%s)", exc)

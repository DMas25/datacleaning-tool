"""Health status for ColtraDataAi.

Computes a lightweight health snapshot from the fault log, used by:
  - services/webhook_server.py's /health endpoint (real HTTP, since
    Streamlit itself can't expose arbitrary routes)
  - ui/fault_dashboard.py's top-line summary
  - core/safe_mode.py's fault-rate trigger (via count_recent_faults)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from core.fault_types import Severity
from core.lifecycle import get_uptime_seconds
from core.safe_mode import is_safe_mode_active

_FAULT_LOG_PATH = Path("logs/faults.jsonl")

_ERROR_RATE_WINDOW_MINUTES = 15
_DEGRADED_ERROR_RATE = 0.5   # faults/min — above this with no critical fault: degraded
_DOWN_ERROR_RATE = 2.0       # faults/min — above this (or safe mode): down


def _read_recent_records(window_minutes: int) -> list[dict[str, Any]]:
    """Read fault records newer than *window_minutes* ago from the live
    JSONL file. Rotated/archived days are intentionally excluded — health
    checks only care about "right now"."""
    if not _FAULT_LOG_PATH.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    records = []
    try:
        with _FAULT_LOG_PATH.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = record.get("timestamp")
                try:
                    record_time = datetime.fromisoformat(ts)
                except (TypeError, ValueError):
                    continue
                if record_time >= cutoff:
                    records.append(record)
    except Exception:
        return []
    return records


def count_recent_faults(window_minutes: int = 5) -> int:
    """Used by core.safe_mode to decide whether to trip safe mode."""
    return len(_read_recent_records(window_minutes))


def _last_critical_error_time() -> Any:
    """Scans the live log (not just the rate window) for the most recent
    CRITICAL fault — an operator wants to know this even if it happened
    20 minutes ago and things have been quiet since."""
    if not _FAULT_LOG_PATH.exists():
        return None

    last: str | None = None
    try:
        with _FAULT_LOG_PATH.open(encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("severity") != Severity.CRITICAL.value:
                    continue
                ts = record.get("timestamp", "")
                if last is None or ts > last:
                    last = ts
    except Exception:
        return None
    return last


def get_health_status() -> dict[str, Any]:
    """
    Returns:
        {
            "status": "ok" | "degraded" | "down",
            "safe_mode": bool,
            "error_rate": faults per minute over the last 15 minutes,
            "uptime_seconds": seconds since this process started,
            "last_error_time": ISO8601 string or None,
            "last_critical_error_time": ISO8601 string or None,
        }
    """
    recent = _read_recent_records(_ERROR_RATE_WINDOW_MINUTES)
    error_rate = round(len(recent) / _ERROR_RATE_WINDOW_MINUTES, 3)

    last_error_time = None
    if recent:
        last_error_time = max(r.get("timestamp", "") for r in recent)

    critical_count = sum(1 for r in recent if r.get("severity") == Severity.CRITICAL.value)
    safe_mode = is_safe_mode_active()

    if safe_mode or error_rate >= _DOWN_ERROR_RATE:
        status = "down"
    elif critical_count > 0 or error_rate >= _DEGRADED_ERROR_RATE:
        status = "degraded"
    else:
        status = "ok"

    return {
        "status": status,
        "safe_mode": safe_mode,
        "error_rate": error_rate,
        "uptime_seconds": round(get_uptime_seconds(), 1),
        "last_error_time": last_error_time,
        "last_critical_error_time": _last_critical_error_time(),
    }

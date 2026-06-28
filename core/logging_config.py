"""Structured fault + lifecycle logging for ColtraDataAi.

Provides the canonical JSON Lines loggers used by core/fault_monitor.py
(faults) and core/lifecycle.py + core/safe_mode.py (lifecycle events).
Distinct from utils/logging_helpers.py (which configures the plain-text
application logger): this module is specifically for machine-readable
records that feed the alerting pipeline and ui/fault_dashboard.py.

Fault schema written per line (see log_fault):
    timestamp         ISO8601 UTC string
    incident_id       short id shown to the client
    trace_id          per-session correlation id
    fingerprint       stable hash(error_type+message+component) — see
                       core/fault_types.compute_fingerprint — used for
                       grouping, rate limiting, and alert aggregation
    severity          "critical" | "error" | "warning" | "info"
    component         module where the fault originated (derived from
                       the traceback, not just the caller's label)
    error_type        exception class name
    message           short human-readable summary
    traceback         full traceback string
    user_action       what the user was doing when it happened, if known
    recovery_action   "retry" | "retry_delay" | "reset_state" | "none" | null
    recovery_success  true | false | null (null = outcome not yet known)
    duration_ms       optional execution duration in milliseconds, when the
                       caller is timing an operation rather than reporting
                       an exception (see core/fault_monitor.record_performance)
    metadata          free-form dict for anything else worth capturing

Every fault record is also mirrored as one human-readable line in
logs/app.log (see _ensure_human_readable_handler) — JSONL for tooling
and the dashboard, app.log for a human tailing the file directly.

Lifecycle event schema written per line (see log_event), to a separate
file (logs/events.jsonl) so app_start/app_restart/safe_mode_* entries
don't dilute fault queries:
    timestamp   ISO8601 UTC string
    event       e.g. "app_start", "app_restart", "safe_mode_enabled"
    component   what the event is about (e.g. "app", "safe_mode")
    metadata    free-form dict

Rotation: both logs rotate daily, retaining 14 days. Rotated files are
moved into logs/archive/ instead of piling up alongside the live files.
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Optional

_LOGS_DIR = Path("logs")
_ARCHIVE_DIR = _LOGS_DIR / "archive"
_FAULT_LOG_PATH = _LOGS_DIR / "faults.jsonl"
_EVENT_LOG_PATH = _LOGS_DIR / "events.jsonl"
_APP_LOG_PATH = _LOGS_DIR / "app.log"

_loggers: dict[str, logging.Logger] = {}


def _archive_rotated_file(source: str, dest: str) -> None:
    """Custom rotator: move the rotated file into logs/archive/ instead of
    leaving it next to the live JSONL file."""
    _ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = _ARCHIVE_DIR / Path(dest).name
    shutil.move(source, dest_path)


def _get_rotating_json_logger(name: str, path: Path, formatter: logging.Formatter) -> logging.Logger:
    """Shared factory behind get_fault_logger()/get_event_logger() so the
    rotation/archive policy is defined exactly once."""
    if name in _loggers:
        return _loggers[name]

    _LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # keep JSONL output separate from the app's text log

    if not logger.handlers:
        handler = TimedRotatingFileHandler(
            path, when="midnight", backupCount=14, encoding="utf-8", utc=True,
        )
        handler.rotator = _archive_rotated_file
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _loggers[name] = logger
    return logger


class _FaultJsonFormatter(logging.Formatter):
    """Renders a LogRecord as one JSON object matching the fault schema."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "incident_id": getattr(record, "incident_id", None),
            "trace_id": getattr(record, "trace_id", None),
            "fingerprint": getattr(record, "fingerprint", None),
            "severity": getattr(record, "severity", "error"),
            "component": getattr(record, "component", "unknown"),
            "error_type": getattr(record, "error_type", None),
            "message": record.getMessage(),
            "traceback": getattr(record, "traceback_text", None),
            "user_action": getattr(record, "user_action", None),
            "recovery_action": getattr(record, "recovery_action", None),
            "recovery_success": getattr(record, "recovery_success", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "metadata": getattr(record, "metadata", {}) or {},
        }
        return json.dumps(payload, default=str)


class _HumanReadableFaultFormatter(logging.Formatter):
    """Plain-text mirror of the JSON fault record, for a human tailing
    logs/app.log directly rather than parsing JSONL."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        severity = getattr(record, "severity", "error").upper()
        component = getattr(record, "component", "unknown")
        error_type = getattr(record, "error_type", "") or ""
        incident_id = getattr(record, "incident_id", "") or ""
        duration_ms = getattr(record, "duration_ms", None)
        duration_part = f" duration_ms={duration_ms:.1f}" if duration_ms is not None else ""
        return f"{ts} {severity:<8} [{incident_id}] {component} {error_type}: {record.getMessage()}{duration_part}"


class _EventJsonFormatter(logging.Formatter):
    """Renders a LogRecord as one JSON object matching the lifecycle event schema."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": getattr(record, "event", record.getMessage()),
            "component": getattr(record, "component", "app"),
            "metadata": getattr(record, "metadata", {}) or {},
        }
        return json.dumps(payload, default=str)


def get_fault_logger() -> logging.Logger:
    """Singleton fault logger — daily-rotating JSON file handler, 14-day
    retention, rotated files archived under logs/archive/. Also carries
    a second handler that mirrors every record as plain text in
    logs/app.log (see _ensure_human_readable_handler)."""
    logger = _get_rotating_json_logger("coltradata.faults", _FAULT_LOG_PATH, _FaultJsonFormatter())
    _ensure_human_readable_handler(logger)
    return logger


def _ensure_human_readable_handler(logger: logging.Logger) -> None:
    """Adds the logs/app.log text handler to the fault logger exactly
    once — idempotent so repeated get_fault_logger() calls (which happen
    on every fault) don't pile up duplicate handlers."""
    if any(getattr(h, "_is_human_readable_fault_handler", False) for h in logger.handlers):
        return

    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        _APP_LOG_PATH, when="midnight", backupCount=14, encoding="utf-8", utc=True,
    )
    handler.rotator = _archive_rotated_file
    handler.setFormatter(_HumanReadableFaultFormatter())
    handler._is_human_readable_fault_handler = True
    logger.addHandler(handler)


def get_event_logger() -> logging.Logger:
    """Singleton lifecycle-event logger — same rotation policy, separate file."""
    return _get_rotating_json_logger("coltradata.events", _EVENT_LOG_PATH, _EventJsonFormatter())


def log_fault(
    *,
    incident_id: str,
    severity: str,
    component: str,
    error_type: str,
    message: str,
    traceback_text: str = "",
    trace_id: Optional[str] = None,
    fingerprint: Optional[str] = None,
    user_action: Optional[str] = None,
    recovery_action: Optional[str] = None,
    recovery_success: Optional[bool] = None,
    duration_ms: Optional[float] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Reusable entry point for writing one structured fault record."""
    logger = get_fault_logger()
    logger.info(
        message,
        extra={
            "incident_id": incident_id,
            "trace_id": trace_id,
            "fingerprint": fingerprint,
            "severity": severity,
            "component": component,
            "error_type": error_type,
            "traceback_text": traceback_text,
            "user_action": user_action,
            "recovery_action": recovery_action,
            "recovery_success": recovery_success,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        },
    )


def log_event(event: str, *, component: str = "app", metadata: Optional[dict[str, Any]] = None) -> None:
    """
    Reusable entry point for app lifecycle events (app_start, app_restart,
    safe_mode_enabled, safe_mode_disabled, circuit_breaker_open, ...).
    Written to logs/events.jsonl, kept separate from fault records.
    """
    logger = get_event_logger()
    logger.info(event, extra={"event": event, "component": component, "metadata": metadata or {}})

"""Fault capture for ColtraDataAi.

Central place that records unhandled exceptions to the structured fault
log (see core/logging_config.py), classifies them by severity/category
(core/fault_types.py), fingerprints them for grouping/rate-limiting,
trips the circuit breaker for their component (core/circuit_breaker.py),
tracks the fingerprint's lifecycle in core/incident_registry.py, and
fires an escalating, aggregated internal alert when severity warrants
it (services/alerting.py). Also feeds core/safe_mode.py so a sustained
fault rate automatically degrades the app to a minimal UI rather than
letting every session hit the same broken code path.
"""
from __future__ import annotations

import json
import time
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from core.circuit_breaker import record_failure as _record_breaker_failure
from core.fault_types import Severity, classify_exception, compute_fingerprint, severity_at_least
from core.health_check import count_recent_faults
from core.incident_registry import record_incident as _record_incident
from core.logging_config import log_fault
from core.safe_mode import maybe_activate_from_fault_rate
from utils.logging_helpers import get_logger

logger = get_logger(__name__)

_THROTTLE_PATH = Path("logs/.alert_throttle.json")
_FAULT_LOG_PATH = Path("logs/faults.jsonl")

# Alert aggregation: one alert per fingerprint per window, summarising
# every occurrence seen in that window rather than firing per-occurrence.
# A fingerprint that keeps triggering alerts across consecutive windows
# (no gap longer than _ESCALATION_RESET_SECONDS) escalates: 1st window
# normal, 2nd warning, 3rd+ urgent — see _escalation_level().
_ALERT_AGGREGATION_WINDOW_SECONDS = 10 * 60
_ESCALATION_RESET_SECONDS = _ALERT_AGGREGATION_WINDOW_SECONDS * 2
_SAFE_MODE_FAULT_THRESHOLD = 5      # faults within the window below before tripping safe mode
_SAFE_MODE_WINDOW_MINUTES = 5


def _project_relative_component(exc: BaseException, fallback: str) -> str:
    """
    Derive a granular component name (e.g. "ui.results_panel") from the
    deepest application-code frame in the traceback, so faults aren't
    all lumped under the generic "app._run_app" label the fault
    boundary happens to catch them at. Falls back to *fallback* (the
    caller-supplied context string) if no in-project frame is found.
    """
    try:
        project_root = Path.cwd().resolve()
        for frame in reversed(traceback.extract_tb(exc.__traceback__)):
            # Skip synthetic frames (REPL/-c snippets, exec()/eval()) which
            # report filenames like "<string>" — not real paths, and would
            # otherwise resolve to a bogus path under the cwd.
            if frame.filename.startswith("<"):
                continue
            frame_path = Path(frame.filename).resolve()
            if ".venv" in frame_path.parts or "site-packages" in frame_path.parts:
                continue
            if not frame_path.is_file():
                continue
            try:
                rel = frame_path.relative_to(project_root)
            except ValueError:
                continue
            return str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
    except Exception:
        pass
    return fallback


def _current_trace_id() -> Optional[str]:
    """Best-effort session trace id. Returns None outside a Streamlit
    session (e.g. when called from a standalone script)."""
    try:
        import streamlit as st

        return st.session_state.get("trace_id")
    except Exception:
        return None


def capture_exception(
    exc: BaseException,
    context: str = "",
    *,
    severity: Optional[Severity] = None,
    user_action: Optional[str] = None,
    recovery_action: Optional[str] = None,
    recovery_success: Optional[bool] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> str:
    """
    Log *exc* to the structured fault log, evaluate it against the
    safe-mode fault-rate trigger and that component's circuit breaker,
    and send an aggregated internal alert if the severity meets the
    configured threshold.

    Returns an incident id that can be shown to the client so support
    requests are traceable back to this exact entry in logs/faults.jsonl.
    """
    incident_id = uuid.uuid4().hex[:8]
    component = _project_relative_component(exc, context or "unknown")
    auto_severity, category = classify_exception(exc)
    effective_severity = severity or auto_severity
    error_type = type(exc).__name__
    message = str(exc) or error_type
    fingerprint = compute_fingerprint(error_type, message, component)
    tb_text = traceback.format_exc()
    trace_id = _current_trace_id()

    log_fault(
        incident_id=incident_id,
        severity=effective_severity.value,
        component=component,
        error_type=error_type,
        message=message,
        traceback_text=tb_text,
        trace_id=trace_id,
        fingerprint=fingerprint,
        user_action=user_action,
        recovery_action=recovery_action,
        recovery_success=recovery_success,
        metadata={"category": category.value, "context": context, **(metadata or {})},
    )

    logger.error(
        "Fault [%s] fp=%s severity=%s component=%s — %s",
        incident_id, fingerprint, effective_severity.value, component, exc,
    )

    _record_breaker_failure(component)
    _record_incident(fingerprint, effective_severity.value, component, trace_id)

    recent_count = count_recent_faults(_SAFE_MODE_WINDOW_MINUTES)
    maybe_activate_from_fault_rate(recent_count, threshold=_SAFE_MODE_FAULT_THRESHOLD)

    _maybe_send_aggregated_alert(
        fingerprint=fingerprint,
        incident_id=incident_id,
        trace_id=trace_id,
        severity=effective_severity,
        component=component,
        summary=message,
        traceback_text=tb_text,
    )

    return incident_id


def log_recovery_outcome(incident_id: str, recovery_action: str, recovery_success: bool) -> None:
    """
    Appends a small follow-up record (same incident_id, so the dashboard
    can correlate it back to the original fault) once it's known whether
    the auto-retry actually fixed things. The original fault entry is
    written before the retry happens, so its own recovery_success is
    necessarily unknown at that point — this is the entry that closes
    the loop.
    """
    log_fault(
        incident_id=incident_id,
        severity=Severity.INFO.value,
        component="recovery",
        error_type="RecoveryOutcome",
        message=f"Recovery {'succeeded' if recovery_success else 'failed'} for incident {incident_id}",
        trace_id=_current_trace_id(),
        recovery_action=recovery_action,
        recovery_success=recovery_success,
        metadata={"incident_id_ref": incident_id},
    )


def _fingerprint_occurrences_in_window(fingerprint: str, window_seconds: int) -> int:
    """Count how many fault records with this fingerprint landed within
    the last *window_seconds* — the "aggregated count" in the alert."""
    if not _FAULT_LOG_PATH.exists():
        return 1

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    count = 0
    try:
        with _FAULT_LOG_PATH.open(encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("fingerprint") != fingerprint:
                    continue
                try:
                    record_time = datetime.fromisoformat(record.get("timestamp", ""))
                except ValueError:
                    continue
                if record_time >= cutoff:
                    count += 1
    except Exception:
        return 1
    return count or 1


def _load_throttle() -> dict:
    if not _THROTTLE_PATH.exists():
        return {}
    try:
        return json.loads(_THROTTLE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_throttle(data: dict) -> None:
    try:
        _THROTTLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _THROTTLE_PATH.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        logger.exception("Failed to persist alert throttle state")


def _throttle_entry(throttle: dict, fingerprint: str) -> Optional[dict]:
    """Normalises a throttle entry to the {"last_sent", "window_count"}
    shape — older entries written before escalation tracking existed
    were a bare float timestamp."""
    entry = throttle.get(fingerprint)
    if entry is None:
        return None
    if isinstance(entry, (int, float)):
        return {"last_sent": entry, "window_count": 1}
    return entry


def _escalation_level(window_count: int) -> str:
    if window_count >= 3:
        return "urgent"
    if window_count == 2:
        return "warning"
    return "normal"


def get_escalation_state(fingerprint: str) -> dict[str, Any]:
    """
    Read-only peek at the alert escalation state for *fingerprint*,
    used by ui/fault_dashboard.py so it can display the same
    escalation_level an alert would carry without re-implementing the
    throttle file's parsing logic.
    """
    entry = _throttle_entry(_load_throttle(), fingerprint)
    window_count = entry.get("window_count", 1) if entry else 0
    return {"window_count": window_count, "escalation_level": _escalation_level(window_count) if entry else "normal"}


def _maybe_send_aggregated_alert(
    *,
    fingerprint: str,
    incident_id: str,
    trace_id: Optional[str],
    severity: Severity,
    component: str,
    summary: str,
    traceback_text: str,
) -> None:
    """
    Alert aggregation: faults are grouped by fingerprint over a rolling
    10-minute window. At most one alert goes out per fingerprint per
    window, and it reports the *aggregated* occurrence count for that
    window rather than firing once per individual fault.

    Escalation: if the same fingerprint keeps alerting across
    consecutive windows (no gap longer than _ESCALATION_RESET_SECONDS),
    window_count climbs and the alert's escalation_level rises with it
    (normal -> warning -> urgent) — a fingerprint that goes quiet for a
    while and then recurs much later is treated as a fresh incident,
    not a continuation.
    """
    try:
        import streamlit as st

        min_severity = Severity(st.secrets.get("alerts", {}).get("min_severity", "critical"))
    except Exception:
        min_severity = Severity.CRITICAL

    if not severity_at_least(severity, min_severity):
        return

    throttle = _load_throttle()
    entry = _throttle_entry(throttle, fingerprint)
    now = time.time()
    if entry and now - entry["last_sent"] < _ALERT_AGGREGATION_WINDOW_SECONDS:
        return  # still within this fingerprint's aggregation window — don't alert yet again

    if entry and now - entry["last_sent"] <= _ESCALATION_RESET_SECONDS:
        window_count = entry.get("window_count", 1) + 1
    else:
        window_count = 1  # first alert ever, or a long-enough gap to count as a new incident

    throttle[fingerprint] = {"last_sent": now, "window_count": window_count}
    _save_throttle(throttle)

    escalation_level = _escalation_level(window_count)
    frequency = _fingerprint_occurrences_in_window(fingerprint, _ALERT_AGGREGATION_WINDOW_SECONDS)

    try:
        from services.alerting import send_structured_alert

        send_structured_alert(
            incident_id=incident_id,
            trace_id=trace_id,
            fingerprint=fingerprint,
            severity=severity.value,
            component=component,
            summary=summary,
            traceback_text=traceback_text,
            frequency=frequency,
            escalation_level=escalation_level,
            window_count=window_count,
        )
    except Exception:
        logger.exception("Failed to dispatch fault alert")


def record_performance(component: str, duration_ms: float, *, context: str = "") -> None:
    """
    Optional, opt-in instrumentation: logs *duration_ms* for *component*
    as an INFO-level fault-log entry (no exception involved) so
    ui/fault_dashboard.py can compute slowest components / average
    duration without a separate metrics store. Nothing in the existing
    pipeline calls this automatically — wrap a call site with
    track_duration() (or call this directly) wherever timing a specific
    operation is worth it.
    """
    log_fault(
        incident_id=uuid.uuid4().hex[:8],
        severity=Severity.INFO.value,
        component=component,
        error_type="PerformanceSample",
        message=f"{component} took {duration_ms:.1f}ms",
        trace_id=_current_trace_id(),
        duration_ms=duration_ms,
        metadata={"context": context},
    )


@contextmanager
def track_duration(component: str, *, context: str = ""):
    """Context manager wrapping record_performance() — usage:
    ``with track_duration("core.cleaner"): clean(df)``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        record_performance(component, (time.perf_counter() - start) * 1000, context=context)


_PRESERVE_SESSION_KEYS = {
    "authenticated", "plan_key", "licence_activated", "account_tier",
    "customer_email", "trace_id",
}


def reset_volatile_session_state() -> None:
    """
    Self-repair step: drop everything in session_state except auth/plan
    keys. Clears out any half-built dataframe/widget state that may
    have caused the fault, without forcing the client to log back in
    or lose their subscription tier.
    """
    import streamlit as st

    for key in list(st.session_state.keys()):
        if key not in _PRESERVE_SESSION_KEYS:
            del st.session_state[key]

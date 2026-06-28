"""Lightweight per-component circuit breaker for ColtraDataAi.

A component that keeps failing shouldn't keep getting hit by every new
session while someone investigates — that just produces more identical
fault records and alert noise. This trips a breaker after enough
failures in a short window so app.py can show a "temporarily
unavailable" notice for that one section instead of letting it fail
again, then automatically retries after a cooldown (no half-open
trial traffic — simple enough to reason about, which matters more
here than textbook fidelity to the pattern).

State is file-backed (like core/safe_mode.py) so it's shared across
Streamlit sessions within the same process.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.logging_config import log_event

_STATE_PATH = Path("logs/.circuit_breakers.json")

FAILURE_THRESHOLD = 3       # failures within the window before opening
WINDOW_SECONDS = 5 * 60     # rolling window the threshold is counted over
COOLDOWN_SECONDS = 5 * 60   # how long the breaker stays open before auto-closing


def _load_state() -> dict[str, Any]:
    if not _STATE_PATH.exists():
        return {}
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict[str, Any]) -> None:
    try:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass


def record_failure(component: str) -> None:
    """Call once per fault attributed to *component* (core/fault_monitor.py
    does this for every captured exception). Opens the breaker once
    FAILURE_THRESHOLD failures land within WINDOW_SECONDS of each other."""
    state = _load_state()
    entry = state.get(component, {"failures": [], "opened_at": None})

    now = time.time()
    entry["failures"] = [t for t in entry["failures"] if now - t <= WINDOW_SECONDS]
    entry["failures"].append(now)

    if len(entry["failures"]) >= FAILURE_THRESHOLD and not entry.get("opened_at"):
        entry["opened_at"] = now
        log_event(
            "circuit_breaker_open", component=component,
            metadata={"failures_in_window": len(entry["failures"])},
        )

    state[component] = entry
    _save_state(state)


def is_component_disabled(component: str) -> bool:
    """
    True while the breaker for *component* is open. Auto-recovers (and
    clears the failure history) once COOLDOWN_SECONDS has passed since
    it opened — the next failure starts counting from zero again.
    """
    state = _load_state()
    entry = state.get(component)
    if not entry or not entry.get("opened_at"):
        return False

    if time.time() - entry["opened_at"] > COOLDOWN_SECONDS:
        state[component] = {"failures": [], "opened_at": None}
        _save_state(state)
        log_event("circuit_breaker_closed", component=component)
        return False

    return True


def get_all_breakers() -> list[dict[str, Any]]:
    """
    Snapshot of every component that has ever recorded a failure, for
    ui/fault_dashboard.py's "⚡ Circuit Breakers" panel. Doesn't mutate
    state (no auto-close here) — is_component_disabled() already does
    that the next time it's actually checked; this is read-only so an
    admin loading the dashboard can't accidentally reset a breaker
    that's about to legitimately reopen.
    """
    state = _load_state()
    now = time.time()
    breakers = []

    for component, entry in state.items():
        opened_at = entry.get("opened_at")
        if opened_at:
            cooldown_remaining = max(0.0, COOLDOWN_SECONDS - (now - opened_at))
            status = "open" if cooldown_remaining > 0 else "closed"
            opened_at_iso = datetime.fromtimestamp(opened_at, tz=timezone.utc).isoformat(timespec="seconds")
        else:
            cooldown_remaining = 0.0
            status = "closed"
            opened_at_iso = None

        breakers.append({
            "component": component,
            "status": status,
            "opened_at": opened_at_iso,
            "cooldown_remaining": round(cooldown_remaining, 1),
            "failures_in_window": len(entry.get("failures", [])),
        })

    return sorted(breakers, key=lambda b: b["status"] == "closed")  # open breakers first


def reset(component: str) -> None:
    """Manual override — e.g. an admin clearing a breaker from the dashboard."""
    state = _load_state()
    if component in state:
        del state[component]
        _save_state(state)

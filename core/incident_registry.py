"""Persistent incident registry for ColtraDataAi.

Tracks the lifecycle of each distinct fault fingerprint across its
entire run — not just the rolling windows core/fault_monitor.py uses
for alert aggregation — so an operator (or the dashboard) can answer
"is this still happening, and for how long has it been broken?"
without trawling the raw fault log.

State is one compact JSON object keyed by fingerprint (logs/incidents.json),
not one line per occurrence, so it stays small and fast to read/write
regardless of total fault volume — only the number of *distinct*
fingerprints matters, not how many times each one fired.

Auto-resolution is evaluated lazily, at read time (get_active_incidents
and get_incident_summary both call resolve_stale_incidents() first)
rather than on a background timer, since there's no scheduler in this
stack and the only thing that actually needs an up-to-date answer is
whoever's looking right now (the dashboard, or the next fault for that
fingerprint reopening it).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.logging_config import log_event

_REGISTRY_PATH = Path("logs/incidents.json")
_MAX_TRACE_IDS = 20             # cap per-incident trace id list so it can't grow unbounded
STALE_AFTER_SECONDS = 15 * 60   # no occurrences for this long -> auto-resolve


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict[str, Any]:
    if not _REGISTRY_PATH.exists():
        return {}
    try:
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(registry: dict[str, Any]) -> None:
    try:
        _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _REGISTRY_PATH.write_text(json.dumps(registry), encoding="utf-8")
    except Exception:
        pass


def record_incident(fingerprint: str, severity: str, component: str, trace_id: Optional[str]) -> None:
    """
    Upsert the incident for *fingerprint*: bumps occurrences/last_seen on
    an existing entry (reopening it if it had auto-resolved), or creates
    a fresh "open" one. Called once per captured fault from
    core/fault_monitor.py.
    """
    registry = _load()
    now = _now_iso()
    entry = registry.get(fingerprint)

    if entry is None:
        entry = {
            "fingerprint": fingerprint,
            "status": "open",
            "first_seen": now,
            "last_seen": now,
            "occurrences": 1,
            "last_severity": severity,
            "component": component,
            "trace_ids": [trace_id] if trace_id else [],
        }
    else:
        entry["status"] = "open"  # reopen if it had previously auto-resolved
        entry["last_seen"] = now
        entry["occurrences"] = entry.get("occurrences", 0) + 1
        entry["last_severity"] = severity
        entry["component"] = component
        if trace_id and trace_id not in entry.get("trace_ids", []):
            entry.setdefault("trace_ids", []).append(trace_id)
            entry["trace_ids"] = entry["trace_ids"][-_MAX_TRACE_IDS:]

    registry[fingerprint] = entry
    _save(registry)


def resolve_stale_incidents(stale_after_seconds: int = STALE_AFTER_SECONDS) -> list[str]:
    """
    Marks any "open" incident whose last_seen is older than
    *stale_after_seconds* as "resolved", logging one incident_resolved
    lifecycle event per fingerprint resolved this call. Returns the
    list of fingerprints just resolved.
    """
    registry = _load()
    now = time.time()
    resolved: list[str] = []

    for fingerprint, entry in registry.items():
        if entry.get("status") != "open":
            continue
        try:
            last_seen_ts = datetime.fromisoformat(entry["last_seen"]).timestamp()
            first_seen_ts = datetime.fromisoformat(entry["first_seen"]).timestamp()
        except (KeyError, ValueError):
            continue
        if now - last_seen_ts > stale_after_seconds:
            entry["status"] = "resolved"
            resolved.append(fingerprint)
            log_event(
                "incident_resolved",
                component=entry.get("component", "unknown"),
                metadata={
                    "fingerprint": fingerprint,
                    "duration_seconds": round(last_seen_ts - first_seen_ts, 1),
                },
            )

    if resolved:
        _save(registry)
    return resolved


def get_active_incidents() -> list[dict[str, Any]]:
    """Open incidents, most recently active first. Runs auto-resolution
    first so a stale entry never shows up as "active" just because
    nothing else has triggered a resolution check recently."""
    resolve_stale_incidents()
    registry = _load()
    active = [entry for entry in registry.values() if entry.get("status") == "open"]
    return sorted(active, key=lambda e: e.get("last_seen", ""), reverse=True)


def get_incident_summary() -> dict[str, Any]:
    """Lightweight counts for the dashboard's headline metrics."""
    resolve_stale_incidents()
    registry = _load()
    open_count = sum(1 for e in registry.values() if e.get("status") == "open")
    resolved_count = sum(1 for e in registry.values() if e.get("status") == "resolved")
    return {
        "total_incidents": len(registry),
        "open": open_count,
        "resolved": resolved_count,
    }

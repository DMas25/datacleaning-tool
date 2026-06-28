"""Safe mode for ColtraDataAi.

Safe mode is a process-wide (file-backed, not session-backed) flag so
it survives Streamlit reruns, new sessions, and even a watchdog restart
of the whole process. Two independent triggers can activate it:

  1. In-process fault rate — core/fault_monitor.py calls
     maybe_activate_from_fault_rate() after logging a fault.
  2. The watchdog's crash-loop detector (scripts/run_app_watchdog.ps1)
     writes the same flag file directly when the process itself keeps
     dying before it can log anything meaningful in-app.

Safe mode auto-clears after a cooldown period with no further faults,
so a transient spike doesn't permanently strand the app in minimal
mode — an operator never has to remember to flip it back off.

get_safe_mode_status() is the single source of truth for "is safe mode
on, why, and since when" — app.py's banner and ui/fault_dashboard.py's
banner both read it, so the two surfaces can never show different
reasons or timestamps for the same event.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.logging_config import log_event

_FLAG_PATH = Path("logs/.safe_mode.json")
_COOLDOWN_SECONDS = 10 * 60  # auto-exit safe mode 10 min after the last activation


def activate_safe_mode(reason: str) -> None:
    """No-op if already active — avoids re-logging safe_mode_enabled on
    every single fault while a long incident is ongoing."""
    if is_safe_mode_active():
        return
    _FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FLAG_PATH.write_text(
        json.dumps({"active": True, "activated_at": time.time(), "reason": reason}),
        encoding="utf-8",
    )
    log_event("safe_mode_enabled", component="safe_mode", metadata={"reason": reason})


def deactivate_safe_mode() -> None:
    if _FLAG_PATH.exists():
        _FLAG_PATH.unlink()
        log_event("safe_mode_disabled", component="safe_mode")


def _read_flag() -> Optional[dict]:
    if not _FLAG_PATH.exists():
        return None
    try:
        return json.loads(_FLAG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_safe_mode_active() -> bool:
    """
    True if safe mode was activated and the cooldown window hasn't
    elapsed yet. Past the cooldown, this also clears the flag so the
    next call starts clean.
    """
    flag = _read_flag()
    if not flag or not flag.get("active"):
        return False

    age = time.time() - flag.get("activated_at", 0)
    if age > _COOLDOWN_SECONDS:
        deactivate_safe_mode()
        return False
    return True


def safe_mode_reason() -> Optional[str]:
    flag = _read_flag()
    return flag.get("reason") if flag else None


def get_safe_mode_status() -> dict[str, Any]:
    """
    Single shared payload for rendering the safe-mode banner consistently
    everywhere it appears (app.py's client-facing page, the admin
    dashboard, the /health endpoint):
        {"active": bool, "reason": str | None, "activated_at": ISO8601 | None}
    """
    active = is_safe_mode_active()
    flag = _read_flag() if active else None
    activated_at = None
    if flag and flag.get("activated_at"):
        activated_at = datetime.fromtimestamp(flag["activated_at"], tz=timezone.utc).isoformat(timespec="seconds")
    return {
        "active": active,
        "reason": flag.get("reason") if flag else None,
        "activated_at": activated_at,
    }


def maybe_activate_from_fault_rate(recent_fault_count: int, threshold: int = 5) -> bool:
    """
    Called by core/fault_monitor.py with the number of faults logged in
    its rolling window. Activates safe mode once that count reaches
    *threshold* and returns whether safe mode is now active.
    """
    if recent_fault_count >= threshold:
        activate_safe_mode(f"{recent_fault_count} faults in the last monitoring window")
        return True
    return is_safe_mode_active()

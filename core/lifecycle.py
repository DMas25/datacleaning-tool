"""App lifecycle tracking for ColtraDataAi.

Streamlit re-executes app.py top-to-bottom on every rerun, so anything
that should happen "once per process" can't live in app.py's own
module-level scope — a fresh script execution gets a fresh namespace.
It has to live in an *imported* module, since those stay cached in
sys.modules for the life of the process.

Distinguishes a true first boot from a watchdog-triggered restart using
a marker file: no marker = fresh install/first run ("app_start"); marker
already present = some previous process wrote it and is now gone
("app_restart" — almost always because it crashed and the watchdog
relaunched it).
"""
from __future__ import annotations

import time
from pathlib import Path

from core.logging_config import log_event

_BOOT_MARKER = Path("logs/.app_boot_marker")
_PROCESS_START = time.time()
_start_logged = False


def get_uptime_seconds() -> float:
    return time.time() - _PROCESS_START


def log_app_start_once() -> None:
    """
    Call from app.py's module-level scope (runs every rerun, but the
    guard below means the underlying event is only written once per
    process, thanks to the module-level flag living here rather than
    in app.py).
    """
    global _start_logged
    if _start_logged:
        return
    _start_logged = True

    event = "app_restart" if _BOOT_MARKER.exists() else "app_start"
    try:
        _BOOT_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _BOOT_MARKER.write_text(str(_PROCESS_START), encoding="utf-8")
    except Exception:
        pass

    log_event(event, component="app")

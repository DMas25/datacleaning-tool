"""Local health monitor for the ColtraDataAi Streamlit app.

Checks that the local app is responding on localhost:8501, logs results,
and fires a Windows toast notification when the app goes down or recovers.

Run directly:       python scripts/health_check_local.py
Task Scheduler:     see scripts/setup_health_scheduler.ps1
"""
import http.client
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOCAL_HOST = "localhost"
LOCAL_PORT = 8501
TIMEOUT_S  = 10
LOG_DIR    = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE   = LOG_DIR / "health_local.log"
STATE_FILE = LOG_DIR / "health_local_state.json"  # persists last known status


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _toast(title: str, message: str) -> None:
    """Fire a Windows toast notification (requires PowerShell; silent if unavailable)."""
    try:
        script = (
            f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
            f"ContentType = WindowsRuntime] | Out-Null; "
            f"$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
            f"[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            f"$xml.GetElementsByTagName('text')[0].AppendChild($xml.CreateTextNode('{title}')) | Out-Null; "
            f"$xml.GetElementsByTagName('text')[1].AppendChild($xml.CreateTextNode('{message}')) | Out-Null; "
            f"$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); "
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('ColtraDataAi').Show($toast)"
        )
        subprocess.run(
            ["powershell", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=8
        )
    except Exception:
        pass


def check_local_app() -> dict:
    """Return a status dict for the local Streamlit app."""
    start = time.monotonic()
    try:
        conn = http.client.HTTPConnection(LOCAL_HOST, LOCAL_PORT, timeout=TIMEOUT_S)
        conn.request("GET", "/")
        resp = conn.getresponse()
        elapsed = round(time.monotonic() - start, 2)
        conn.close()
        if resp.status == 200:
            status = "HEALTHY" if elapsed < 8 else "DEGRADED"
        else:
            status = "DOWN"
        return {"status": status, "http": resp.status, "time_s": elapsed, "error": None}
    except Exception as exc:
        elapsed = round(time.monotonic() - start, 2)
        return {"status": "DOWN", "http": None, "time_s": elapsed, "error": str(exc)}


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"last_status": None}


def _save_state(state: dict) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state))
    except Exception:
        pass


def run() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    result  = check_local_app()
    ts      = _timestamp()
    status  = result["status"]
    elapsed = result["time_s"]
    http_code = result["http"] or "N/A"
    error   = result["error"] or ""

    line = f"[{ts}] LOCAL APP: {status} (HTTP {http_code}, {elapsed}s)"
    if error:
        line += f" | ERROR: {error}"
    if status in ("DOWN", "DEGRADED"):
        line = "ALERT: " + line

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    print(line)

    # Toast only on status transition (DOWN/DEGRADED appearing or recovering)
    state = _load_state()
    prev  = state.get("last_status")
    if status in ("DOWN", "DEGRADED") and prev not in ("DOWN", "DEGRADED"):
        _toast(
            "ColtraDataAi local app ALERT",
            f"{status} - {error or f'HTTP {http_code}, {elapsed}s'}"
        )
    elif status == "HEALTHY" and prev in ("DOWN", "DEGRADED"):
        _toast("ColtraDataAi local app recovered", f"HEALTHY - {elapsed}s response time")

    _save_state({"last_status": status})


if __name__ == "__main__":
    run()

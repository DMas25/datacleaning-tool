"""Remote health monitor for the ColtraDataAi Enterprise API.

Queries /health and /health/detail at coltradata-api.onrender.com, logs
results to logs/health_api_endpoints.log, and fires a Windows toast on
status transitions (down / recovered).

Run directly:       python scripts/health_check_api.py
Task Scheduler:     see scripts/setup_health_scheduler.ps1
"""
import http.client
import json
import ssl
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

API_HOST    = "coltradata-api.onrender.com"
API_PORT    = 443
TIMEOUT_S   = 20
LOG_DIR     = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE    = LOG_DIR / "health_api_endpoints.log"
STATE_FILE  = LOG_DIR / "health_api_state.json"

DOMAINS = ["finance", "logistics", "retail", "trade",
           "healthcare", "consultant", "sme", "hospitality"]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _toast(title: str, message: str) -> None:
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


def _get(path: str) -> tuple[int | None, dict | None, float, str | None]:
    """HTTPS GET; returns (status_code, body_dict, elapsed_s, error)."""
    start = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(API_HOST, API_PORT, timeout=TIMEOUT_S, context=ctx)
        conn.request("GET", path, headers={"Accept": "application/json"})
        resp = conn.getresponse()
        body = json.loads(resp.read().decode("utf-8", errors="replace"))
        elapsed = round(time.monotonic() - start, 2)
        conn.close()
        return resp.status, body, elapsed, None
    except Exception as exc:
        return None, None, round(time.monotonic() - start, 2), str(exc)


def check_api() -> dict:
    """Return a status summary derived from /health/detail."""
    code, body, elapsed, err = _get("/health/detail")

    if err or code is None:
        return {
            "status": "DOWN",
            "http": None,
            "time_s": elapsed,
            "error": err,
            "cleaners": {},
            "supabase": "unknown",
            "circuit_breaker": "unknown",
            "uptime_seconds": None,
            "missing_env": [],
        }

    if code != 200:
        return {
            "status": "DOWN",
            "http": code,
            "time_s": elapsed,
            "error": f"Unexpected HTTP {code}",
            "cleaners": {},
            "supabase": "unknown",
            "circuit_breaker": "unknown",
            "uptime_seconds": None,
            "missing_env": [],
        }

    checks   = body.get("checks", {})
    cleaners = checks.get("cleaners", {})
    env      = checks.get("env", {})

    unhealthy_domains = [d for d, s in cleaners.items() if s != "ok"]
    missing_env       = [k for k, v in env.items() if v == "missing"]
    supabase_ok       = checks.get("supabase") == "ok"
    cb_open           = checks.get("circuit_breaker") == "open"

    if not supabase_ok or cb_open or unhealthy_domains:
        status = "DEGRADED"
    elif elapsed > 8:
        status = "DEGRADED"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "http": code,
        "time_s": elapsed,
        "error": None,
        "cleaners": cleaners,
        "supabase": checks.get("supabase", "unknown"),
        "circuit_breaker": checks.get("circuit_breaker", "unknown"),
        "uptime_seconds": body.get("uptime_seconds"),
        "missing_env": missing_env,
    }


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

    result = check_api()
    ts     = _timestamp()
    status = result["status"]

    # Build log line
    cleaner_statuses = ", ".join(
        f"{d}:{s}" for d, s in result["cleaners"].items()
    ) or "N/A"
    uptime_h = (
        f"{result['uptime_seconds'] // 3600}h"
        if result["uptime_seconds"] is not None else "N/A"
    )
    line = (
        f"[{ts}] API: {status} "
        f"(HTTP {result['http'] or 'N/A'}, {result['time_s']}s, uptime {uptime_h}) "
        f"supabase={result['supabase']} cb={result['circuit_breaker']} "
        f"cleaners=[{cleaner_statuses}]"
    )
    if result["missing_env"]:
        line += f" | missing_env={result['missing_env']}"
    if result["error"]:
        line += f" | ERROR: {result['error']}"
    if status in ("DOWN", "DEGRADED"):
        line = "ALERT: " + line

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    print(line)

    # Pretty domain summary
    if result["cleaners"]:
        for domain in DOMAINS:
            s = result["cleaners"].get(domain, "unknown")
            icon = "OK" if s == "ok" else "!!"
            print(f"  [{icon}] /v1/clean/{domain}")

    # Toast on transition
    state = _load_state()
    prev  = state.get("last_status")
    if status in ("DOWN", "DEGRADED") and prev not in ("DOWN", "DEGRADED"):
        detail = result["error"] or f"HTTP {result['http']}, {result['time_s']}s"
        _toast("ColtraDataAi API ALERT", f"{status} - {detail}")
    elif status == "HEALTHY" and prev in ("DOWN", "DEGRADED"):
        _toast("ColtraDataAi API recovered", f"HEALTHY - {result['time_s']}s")

    _save_state({"last_status": status})
    return 0 if status == "HEALTHY" else 1


if __name__ == "__main__":
    sys.exit(run())

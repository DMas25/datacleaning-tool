"""Standalone crash-loop alert, invoked by scripts/run_app_watchdog.ps1.

Runs outside Streamlit (no st.secrets access), so it reads
.streamlit/secrets.toml directly to send an SMTP email when the
watchdog detects the app is crash-looping (restarting repeatedly in a
short window) rather than just a normal close/reopen.
"""
from __future__ import annotations

import smtplib
import ssl
import sys
import tomllib
from email.message import EmailMessage
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_DIR / ".streamlit" / "secrets.toml"


def main() -> int:
    restart_count = sys.argv[1] if len(sys.argv) > 1 else "?"

    if not SECRETS_PATH.exists():
        return 0

    secrets = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    alerts = secrets.get("alerts", {})
    if not alerts.get("enabled", False):
        return 0

    host = alerts.get("smtp_host")
    port = int(alerts.get("smtp_port", 587))
    user = alerts.get("smtp_user")
    password = alerts.get("smtp_password")
    recipient = alerts.get("alert_to")
    if not all([host, user, password, recipient]):
        return 0

    msg = EmailMessage()
    msg["Subject"] = "[ColtraDataAi] App is crash-looping"
    msg["From"] = user
    msg["To"] = recipient
    msg.set_content(
        f"The Streamlit process for ColtraDataAi has restarted {restart_count} times "
        "in a short window. The watchdog is still restarting it automatically, but "
        "this points to a recurring startup failure that needs investigation.\n\n"
        "Check logs/streamlit_watchdog.log and logs/faults.jsonl for details."
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)
    except Exception:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

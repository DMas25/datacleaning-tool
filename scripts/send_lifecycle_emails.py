"""Lifecycle email runner — invoke on a daily schedule (cron / Task Scheduler).

Runs outside Streamlit (no st.secrets access), so it reads
.streamlit/secrets.toml directly, same pattern as scripts/notify_crash_loop.py.
Each (email, email_type) pair is only ever sent once: services.licence_manager
records every send in the email_log table, so re-running this script on a
schedule is safe and won't double-email anyone.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SECRETS_PATH = PROJECT_DIR / ".streamlit" / "secrets.toml"
sys.path.insert(0, str(PROJECT_DIR))

from services import licence_manager  # noqa: E402
from services import lifecycle_emails  # noqa: E402
from services.transactional_email import send_email  # noqa: E402


def main() -> int:
    if not SECRETS_PATH.exists():
        print("No secrets.toml found; skipping.")
        return 0

    secrets = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    cfg = secrets.get("transactional_email", {})
    if not cfg.get("enabled", False):
        print("transactional_email.enabled = false; skipping.")
        return 0

    app_url = cfg.get("app_url", "")
    subject, body = lifecycle_emails.render_activation_nudge(app_url)

    recipients = licence_manager.get_users_needing_activation_nudge()
    print(f"{len(recipients)} subscriber(s) due for the activation-nudge email.")

    sent_count = 0
    for email in recipients:
        if send_email(cfg, email, subject, body):
            licence_manager.log_email_sent(email, lifecycle_emails.ACTIVATION_NUDGE["email_type"])
            sent_count += 1
        else:
            print(f"  failed to send to {email}")

    print(f"Sent {sent_count}/{len(recipients)} activation-nudge email(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

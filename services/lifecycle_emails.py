"""Lifecycle email templates — grounded in the same activation/usage signals
as services/upgrade_messaging.py, but delivered out-of-band by email rather
than as an in-app banner.
"""
from __future__ import annotations

ACTIVATION_NUDGE = {
    "email_type": "activation_nudge",
    "subject": "Get value from your licence in under 2 minutes",
    "body": (
        "You've activated your account but haven't run your first dataset yet. "
        "Start with one file and see results instantly."
    ),
    "cta": "Run your first clean",
}


def render_activation_nudge(app_url: str = "") -> tuple[str, str]:
    """Return (subject, body) for the activation-nudge email, with the CTA
    appended as a plain-text line (and link, if app_url is configured)."""
    subject = ACTIVATION_NUDGE["subject"]
    cta_line = ACTIVATION_NUDGE["cta"]
    if app_url:
        cta_line += f": {app_url}"
    body = f"{ACTIVATION_NUDGE['body']}\n\n{cta_line}"
    return subject, body

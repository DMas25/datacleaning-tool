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


def render_licence_key_email(key: str, plan: str, app_url: str = "") -> tuple[str, str]:
    """Return (subject, body) for a new-purchase licence key delivery email."""
    subject = "Your ColtraDataAi licence key"
    plan_label = plan.capitalize()
    body = (
        f"Thank you for purchasing ColtraDataAi {plan_label}.\n\n"
        f"Your licence key is:\n\n"
        f"    {key}\n\n"
        f"To activate, open the app and enter this key when prompted."
    )
    if app_url:
        body += f"\n\n{app_url}"
    body += "\n\nColtraDataAi by Coltrane Ltd"
    return subject, body


def render_report_delivery_email(app_url: str = "") -> tuple[str, str]:
    """Return (subject, body) for a report-delivery email with PDF attachment."""
    subject = "Your ColtraDataAi cleaned data report"
    body = (
        "Your cleaned data report is attached to this email.\n\n"
        "It includes your full cleaned dataset, quality analysis, and an executive PDF summary.\n\n"
        "To run another report or manage your account, visit the app"
    )
    if app_url:
        body += f": {app_url}"
    body += "\n\nColtraDataAi by Coltrane Ltd"
    return subject, body

"""Resend API sender for customer-facing transactional/lifecycle emails.

Distinct from services/alerting.py, which sends internal ops alerts to one
fixed recipient. This sends to individual subscribers, so the API key is
passed in via cfg dict rather than read from st.secrets directly — that lets
both the Streamlit app and standalone scripts (which have no Streamlit runtime)
share this sender.
"""
from __future__ import annotations

from utils.logging_helpers import get_logger

logger = get_logger(__name__)


def transactional_email_config_complete(cfg: dict) -> bool:
    return bool(cfg.get("resend_api_key"))


def send_email(cfg: dict, to_email: str, subject: str, body: str) -> bool:
    """Send a single transactional email via Resend. Returns True on success."""
    if not transactional_email_config_complete(cfg):
        logger.warning("Resend API key not configured; skipping send to %s.", to_email)
        return False

    try:
        import resend  # deferred so the module loads even without the package installed
        resend.api_key = cfg["resend_api_key"]
        from_name = cfg.get("from_name", "ColtraDataAi")
        from_email = cfg.get("from_email", "support@coltradata.com")
        resend.Emails.send({
            "from": f"{from_name} <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "text": body,
        })
        logger.info("Email sent to %s: %s", to_email, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def send_email_with_attachment(
    cfg: dict,
    to_email: str,
    subject: str,
    body: str,
    attachment_data: bytes,
    attachment_filename: str,
    attachment_mime: str = "application/pdf",
) -> bool:
    """Send a transactional email with a single binary attachment via Resend. Returns True on success."""
    if not transactional_email_config_complete(cfg):
        logger.warning("Resend API key not configured; skipping send to %s.", to_email)
        return False

    try:
        import base64
        import resend
        resend.api_key = cfg["resend_api_key"]
        from_name = cfg.get("from_name", "ColtraDataAi")
        from_email = cfg.get("from_email", "support@coltradata.com")
        resend.Emails.send({
            "from": f"{from_name} <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "text": body,
            "attachments": [
                {
                    "filename": attachment_filename,
                    "content": list(base64.b64encode(attachment_data)),
                }
            ],
        })
        logger.info("Email with attachment sent to %s: %s", to_email, subject)
        return True
    except Exception:
        logger.exception("Failed to send email with attachment to %s", to_email)
        return False

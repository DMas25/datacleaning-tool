"""SMTP sender for customer-facing transactional/lifecycle emails.

Distinct from services/alerting.py, which sends internal ops alerts to one
fixed recipient. This sends to individual subscribers, so the SMTP config is
passed in explicitly (cfg dict) rather than read from st.secrets directly —
that lets both the Streamlit app and standalone scripts (which have no
Streamlit runtime, e.g. scripts/send_lifecycle_emails.py) share this sender.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from utils.logging_helpers import get_logger

logger = get_logger(__name__)


def transactional_email_config_complete(cfg: dict) -> bool:
    return all(cfg.get(k) for k in ("smtp_host", "smtp_user", "smtp_password"))


def send_email(cfg: dict, to_email: str, subject: str, body: str) -> bool:
    """Send a single transactional email. Returns True on success."""
    if not transactional_email_config_complete(cfg):
        logger.warning("Transactional email config incomplete; skipping send to %s.", to_email)
        return False

    host = cfg["smtp_host"]
    port = int(cfg.get("smtp_port", 587))
    user = cfg["smtp_user"]
    password = cfg["smtp_password"]
    from_name = cfg.get("from_name", "ColtraDataAi")
    from_email = cfg.get("from_email", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=10, context=context) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls(context=context)
                server.login(user, password)
                server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send transactional email to %s", to_email)
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
    """Send a transactional email with a single binary attachment. Returns True on success."""
    if not transactional_email_config_complete(cfg):
        logger.warning("Transactional email config incomplete; skipping send to %s.", to_email)
        return False

    host = cfg["smtp_host"]
    port = int(cfg.get("smtp_port", 587))
    user = cfg["smtp_user"]
    password = cfg["smtp_password"]
    from_name = cfg.get("from_name", "ColtraDataAi")
    from_email = cfg.get("from_email", user)

    maintype, subtype = attachment_mime.split("/", 1)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg.set_content(body)
    msg.add_attachment(attachment_data, maintype=maintype, subtype=subtype, filename=attachment_filename)

    try:
        context = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=10, context=context) as server:
                server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls(context=context)
                server.login(user, password)
                server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email with attachment to %s", to_email)
        return False

"""Internal alerting for ColtraDataAi — SMTP email + optional Slack webhook.

Called by core/fault_monitor.py once it has already decided (via
severity threshold + per-signature cooldown) that an alert should go
out. This module's only job is delivery: build the payload, send it
through whichever channels are configured, and never let a delivery
failure propagate back up into the request that triggered it.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

import requests
import streamlit as st

from utils.logging_helpers import get_logger

logger = get_logger(__name__)


def alerts_enabled() -> bool:
    cfg = st.secrets.get("alerts", {})
    return bool(cfg.get("enabled", False))


_ESCALATION_PREFIX = {"normal": "", "warning": "⚠️ WARNING ", "urgent": "🚨 URGENT "}


def send_structured_alert(
    *,
    incident_id: str,
    trace_id: Optional[str],
    fingerprint: str,
    severity: str,
    component: str,
    summary: str,
    traceback_text: str,
    frequency: int,
    escalation_level: str = "normal",
    window_count: int = 1,
) -> bool:
    """
    Build the structured alert payload and deliver it over every
    configured channel (SMTP, Slack). Returns True if at least one
    channel succeeded.

    *frequency* is the aggregated occurrence count for *fingerprint*
    over the alert's aggregation window (see core/fault_monitor.py) —
    this is one alert summarising many occurrences, not one alert per
    occurrence. *escalation_level* / *window_count* reflect how many
    consecutive aggregation windows this fingerprint has kept firing in
    (1st window -> "normal", 2nd -> "warning", 3rd+ -> "urgent").
    """
    cfg = st.secrets.get("alerts", {})
    if not cfg.get("enabled", False):
        return False

    prefix = _ESCALATION_PREFIX.get(escalation_level, "")
    subject = (
        f"[ColtraDataAi] {prefix}{severity.upper()} fault in {component} "
        f"x{frequency} (incident {incident_id})"
    )
    body_lines = [
        f"Incident:         {incident_id}",
        f"Fingerprint:      {fingerprint}",
        f"Trace ID:         {trace_id or 'n/a'}",
        f"Severity:         {severity}",
        f"Escalation level: {escalation_level} (window #{window_count})",
        f"Component:        {component}",
        f"Summary:          {summary}",
        f"Frequency:        {frequency} occurrence(s) in the last 10 minutes",
        "",
        traceback_text,
    ]
    body = "\n".join(body_lines)

    sent = False
    if cfg.get("smtp_host"):
        sent = _send_email(cfg, subject, body) or sent
    if cfg.get("slack_webhook"):
        sent = _send_slack(cfg["slack_webhook"], subject, body_lines) or sent
    return sent


def validate_alert_config() -> None:
    """
    Fail-fast startup check: if alerts.enabled = true in secrets.toml,
    there must be enough configuration to actually deliver something —
    otherwise every captured fault silently fails to alert anyone,
    which is worse than alerting being off outright. Called from
    app.py's module-level scope (outside the fault boundary, so this
    raises uncaught and stops the app from booting on a bad config,
    rather than being swallowed as a runtime fault).
    """
    cfg = st.secrets.get("alerts", {})
    if not cfg.get("enabled", False):
        return

    missing = []
    if not cfg.get("smtp_host"):
        missing.append("smtp_host")
    if not cfg.get("smtp_user"):
        missing.append("smtp_user")
    if not cfg.get("smtp_password") and not cfg.get("slack_webhook"):
        missing.append("smtp_password OR slack_webhook")

    if missing:
        raise RuntimeError(
            "alerts.enabled = true in .streamlit/secrets.toml but required "
            f"config is missing: {', '.join(missing)}. Either fill these in "
            "or set alerts.enabled = false."
        )


def _send_email(cfg, subject: str, body: str) -> bool:
    host = cfg.get("smtp_host")
    port = int(cfg.get("smtp_port", 587))
    user = cfg.get("smtp_user")
    password = cfg.get("smtp_password")
    recipient = cfg.get("alert_to")

    if not all([host, user, password, recipient]):
        logger.warning("Alerting enabled but SMTP config is incomplete; skipping email.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = recipient
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.starttls(context=context)
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send fault alert email")
        return False


def _send_slack(webhook_url: str, subject: str, body_lines: list[str]) -> bool:
    try:
        text = f"*{subject}*\n```{chr(10).join(body_lines[:6])}```"
        response = requests.post(webhook_url, json={"text": text}, timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("Failed to post fault alert to Slack")
        return False


def send_fault_alert(subject: str, body: str) -> bool:
    """Backwards-compatible plain SMTP send, kept for callers that don't
    need the full structured payload (e.g. scripts/notify_crash_loop.py
    builds its own message outside the Streamlit secrets context)."""
    cfg = st.secrets.get("alerts", {})
    if not cfg.get("enabled", False):
        return False
    return _send_email(cfg, subject, body)

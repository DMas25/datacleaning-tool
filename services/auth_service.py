"""Email OTP authentication for ColtraDataAi — Supabase Auth backend.

OTP flow
────────
  issue_otp(email)       → Supabase Auth generates a 6-digit code and emails it.
  verify_otp(email, code) → Supabase Auth validates the submission.

What Supabase Auth handles (replaces the previous custom implementation):
  • Cryptographically secure code generation
  • Secure storage in auth.users (never in application tables)
  • 10-minute expiry (configured in Supabase dashboard → Auth → Settings)
  • Rate limiting (built into Supabase Auth, enforced on Pro plan)
  • Email delivery (via Supabase's email service or custom SMTP / Resend)

The otp_tokens table and the custom rate-limiting, hash-storage, and email-send
code from the previous implementation have been removed — Supabase Auth
replaces all of them.  Drop the otp_tokens table in Supabase SQL editor once
you have confirmed the new flow works end-to-end.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_OTP_DIGITS = 6


def issue_otp(email: str) -> tuple[bool, str]:
    """Ask Supabase Auth to send a 6-digit OTP to *email*.

    Returns:
        (True,  "")               — OTP dispatched; user should check inbox.
        (False, "<error message>") — validation or API error.
    """
    from services.supabase_client import get_supabase_client

    email = email.lower().strip()
    if not email or "@" not in email:
        return False, "Please enter a valid email address."

    try:
        client = get_supabase_client()
        client.auth.sign_in_with_otp({
            "email": email,
            "options": {"should_create_user": True},
        })
        return True, ""
    except Exception as exc:
        log.exception("sign_in_with_otp failed for %s: %s", email, exc)
        return False, "Could not send verification code. Please try again in a moment."


def issue_phone_otp(phone: str) -> tuple[bool, str]:
    """Ask Supabase Auth to send a 6-digit OTP via SMS to *phone* (E.164 format).

    Returns:
        (True,  "")               — OTP dispatched; user should check SMS.
        (False, "<error message>") — validation or API error.
    """
    from services.supabase_client import get_supabase_client

    phone = phone.strip().replace(" ", "")
    if not phone.startswith("+") or len(phone) < 8:
        return False, "Phone number must include a country code, e.g. +44 7700 900000."

    try:
        client = get_supabase_client()
        client.auth.sign_in_with_otp({"phone": phone})
        return True, ""
    except Exception as exc:
        log.exception("sign_in_with_otp (phone) failed for %s: %s", phone, exc)
        return False, "Could not send verification code. Please try again in a moment."


def verify_phone_otp(phone: str, code: str) -> tuple[bool, str, str]:
    """Validate a submitted SMS OTP code via Supabase Auth.

    Returns:
        (True,  email_if_known, "")               — code valid.
        (False, "",             "<error message>") — invalid or expired.
    """
    from services.supabase_client import get_supabase_client

    phone = phone.strip().replace(" ", "")
    code = code.replace(" ", "").strip()

    if len(code) != _OTP_DIGITS or not code.isdigit():
        return False, "", f"Please enter the full {_OTP_DIGITS}-digit code (digits only)."

    try:
        client = get_supabase_client()
        response = client.auth.verify_otp({
            "phone": phone,
            "token": code,
            "type": "sms",
        })
        if response.user:
            return True, response.user.email or "", ""
        return False, "", "That code is invalid or has expired. Please request a new one."
    except Exception as exc:
        log.exception("verify_phone_otp failed for %s: %s", phone, exc)
        return False, "", "That code is invalid or has expired. Please request a new one."


def verify_otp(email: str, code: str) -> tuple[bool, str]:
    """Validate a submitted OTP code via Supabase Auth.

    Returns:
        (True,  "")               — code is valid; caller should authenticate.
        (False, "<error message>") — invalid, expired, or malformed.
    """
    from services.supabase_client import get_supabase_client

    email = email.lower().strip()
    code = code.replace(" ", "").strip()

    if len(code) != _OTP_DIGITS or not code.isdigit():
        return False, f"Please enter the full {_OTP_DIGITS}-digit code (digits only)."

    try:
        client = get_supabase_client()
        response = client.auth.verify_otp({
            "email": email,
            "token": code,
            "type": "email",
        })
        if response.user:
            return True, ""
        return False, "That code is invalid or has expired. Please request a new one."
    except Exception as exc:
        log.exception("verify_otp failed for %s: %s", email, exc)
        return False, "That code is invalid or has expired. Please request a new one."

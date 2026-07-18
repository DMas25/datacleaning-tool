"""Email OTP authentication for ColtraDataAi.

Generates cryptographically secure 6-digit one-time codes, stores only their
SHA-256 hash in Supabase, and validates submissions against that hash.

Security properties
───────────────────
  • 6 digits drawn from secrets.randbelow — cryptographically random.
  • The plaintext code exists only in memory during generation and in the
    email sent to the subscriber.  The database row stores the SHA-256 hash
    only — no admin or backend viewer can recover the original code.
  • Codes expire after OTP_TTL_MINUTES (10 min) and are single-use.
  • Generation is rate-limited: MAX_OTP_REQUESTS_PER_WINDOW requests per
    RATE_LIMIT_WINDOW_MINUTES per email to prevent enumeration/abuse.

Data minimisation
─────────────────
  • No passwords are ever created or stored.
  • The only personal datum captured at sign-in is the subscriber's email —
    which already exists in the subscriptions table from the LemonSqueezy
    webhook, or is auto-created as a free-plan row on first login.
"""
from __future__ import annotations

import hashlib
import secrets

from datetime import datetime, timedelta, timezone

OTP_DIGITS = 6
OTP_TTL_MINUTES = 10
MAX_OTP_REQUESTS_PER_WINDOW = 3
RATE_LIMIT_WINDOW_MINUTES = 10


# ── Internal helpers ──────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_code(code: str) -> str:
    """Return the SHA-256 hex digest of the plaintext OTP code string."""
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_code() -> str:
    """Return a cryptographically random zero-padded 6-digit string."""
    return f"{secrets.randbelow(10 ** OTP_DIGITS):0{OTP_DIGITS}d}"


# ── Public API ────────────────────────────────────────────────────────────────

def issue_otp(email: str) -> tuple[bool, str]:
    """Generate an OTP for *email*, store its hash, and return the plaintext code.

    Returns:
        (True, "<6-digit-code>")   — caller must email the code to the user.
        (False, "<error message>") — rate-limited or DB write failed.

    The caller (ui/homepage.py) is responsible for sending the code by email
    and must NOT log or persist the returned plaintext code.
    """
    from services.licence_manager_pg import (
        count_recent_otp_requests,
        store_otp,
        ensure_free_subscriber,
    )

    email = email.lower().strip()
    if not email or "@" not in email:
        return False, "Please enter a valid email address."

    try:
        recent = count_recent_otp_requests(email, RATE_LIMIT_WINDOW_MINUTES)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("count_recent_otp_requests failed: %s", exc)
        return False, "Could not reach the database. Please try again in a moment."

    if recent >= MAX_OTP_REQUESTS_PER_WINDOW:
        return False, (
            f"Too many verification requests. "
            f"Please wait {RATE_LIMIT_WINDOW_MINUTES} minutes before trying again."
        )

    # Guarantee a subscription row exists (free plan) so the login can proceed
    # even before the user has paid — the plan upgrades automatically on payment.
    try:
        ensure_free_subscriber(email)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("ensure_free_subscriber failed: %s", exc)
        # Non-fatal — subscriber may already exist; proceed to OTP generation.

    code = _generate_code()
    token_hash = _hash_code(code)
    expires_at = _now() + timedelta(minutes=OTP_TTL_MINUTES)

    try:
        store_otp(email, token_hash, expires_at)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("store_otp failed: %s", exc)
        return False, "Could not generate a verification code. Please try again."

    return True, code


def verify_otp(email: str, code: str) -> tuple[bool, str]:
    """Validate a submitted OTP code.

    Returns:
        (True, "")                 — code is valid; caller should authenticate.
        (False, "<error message>") — invalid, expired, already used, or malformed.

    The plaintext code is hashed here before the DB lookup — the hash is the
    only value that ever touches the database.
    """
    from services.licence_manager_pg import consume_otp

    email = email.lower().strip()
    code = code.replace(" ", "").strip()

    if len(code) != OTP_DIGITS or not code.isdigit():
        return False, f"Please enter the full {OTP_DIGITS}-digit code (digits only)."

    token_hash = _hash_code(code)
    consumed = consume_otp(email, token_hash)

    if not consumed:
        return False, "That code is invalid or has expired. Please request a new one."

    return True, ""

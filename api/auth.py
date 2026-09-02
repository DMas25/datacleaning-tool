from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.watchdog import CircuitState, supabase_breaker

_bearer = HTTPBearer()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> dict:
    """
    Dependency: validates Bearer token against Supabase api_keys table.
    Checks the circuit breaker before attempting a Supabase call so that
    a sustained outage fails fast (immediate 503) rather than blocking each
    request for the full Supabase connection timeout.
    """
    if not supabase_breaker.can_attempt():
        raise HTTPException(
            status_code=503,
            detail=(
                "Authentication service is temporarily unavailable. "
                "The fault has been logged and the team has been alerted. "
                "Please retry in a few minutes."
            ),
        )

    key_hash = _hash_key(credentials.credentials)

    try:
        from supabase import create_client
        _url = os.environ["SUPABASE_URL"].strip()
        _key = os.environ["SUPABASE_SERVICE_ROLE_KEY"].strip()
        client = create_client(_url, _key)
        result = (
            client.table("api_keys")
            .select("id, email, label, is_active")
            .eq("key_hash", key_hash)
            .limit(1)
            .execute()
        )
        # Successful Supabase call - let the circuit breaker know
        supabase_breaker.record_success()
    except Exception as exc:
        supabase_breaker.record_failure()
        raise HTTPException(status_code=503, detail=f"Auth service unavailable: {exc}") from exc

    rows = getattr(result, "data", None) or []
    if not rows or not rows[0].get("is_active"):
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")

    record = rows[0]
    try:
        client.table("api_keys").update({
            "last_used_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", record["id"]).execute()
    except Exception:
        pass

    return record


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, key_hash). Store only the hash; give the raw key to the customer."""
    raw = "cdai_" + secrets.token_urlsafe(32)
    return raw, _hash_key(raw)

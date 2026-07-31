from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer()


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> dict:
    """Dependency: validates Bearer token against Supabase api_keys table."""
    key_hash = _hash_key(credentials.credentials)

    from services.supabase_client import get_supabase_client
    try:
        client = get_supabase_client()
        result = (
            client.table("api_keys")
            .select("id, email, label, is_active")
            .eq("key_hash", key_hash)
            .maybe_single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Auth service unavailable.") from exc

    if result.data is None or not result.data.get("is_active"):
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")

    try:
        client.table("api_keys").update({
            "last_used_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", result.data["id"]).execute()
    except Exception:
        pass

    return result.data


def generate_api_key() -> tuple[str, str]:
    """Return (raw_key, key_hash). Store only the hash; give the raw key to the customer."""
    raw = "cdai_" + secrets.token_urlsafe(32)
    return raw, _hash_key(raw)

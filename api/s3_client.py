from __future__ import annotations

import os

from supabase import create_client

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        raise ValueError("SUPABASE_URL environment variable is not set.")
    if not key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set.")

    _client = create_client(url, key)
    return _client


def get_bucket() -> str:
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET")
    if not bucket:
        raise ValueError("SUPABASE_STORAGE_BUCKET environment variable is not set.")
    return bucket


def _extract_url(result) -> str:
    # Handle both object-style and dict-style responses from supabase-py v2
    if hasattr(result, "signed_url") and result.signed_url:
        return result.signed_url
    if isinstance(result, dict):
        return result.get("signedURL") or result.get("signedUrl") or result.get("signed_url") or ""
    raise ValueError(f"Unable to extract signed URL from storage response: {result!r}")


def generate_presigned_upload_url(key: str, expires_in: int = 3600) -> str:
    result = get_client().storage.from_(get_bucket()).create_signed_upload_url(key)
    return _extract_url(result)


def generate_presigned_download_url(key: str, expires_in: int = 3600) -> str:
    result = get_client().storage.from_(get_bucket()).create_signed_url(key, expires_in)
    return _extract_url(result)


def download_object_as_bytes(key: str) -> bytes:
    return get_client().storage.from_(get_bucket()).download(key)


def upload_bytes(key: str, data: bytes, content_type: str = "text/csv") -> None:
    get_client().storage.from_(get_bucket()).upload(key, data, {"content-type": content_type})

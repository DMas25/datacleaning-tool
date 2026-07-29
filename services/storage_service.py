"""Supabase Storage service for ColtraDataAi.

Uploads generated Excel and PDF reports to the private 'reports' bucket and
returns time-limited signed download URLs (valid for 1 hour).

Requires (add to Render env vars and .streamlit/secrets.toml):
  SUPABASE_URL              — already required for Auth
  SUPABASE_SERVICE_ROLE_KEY — service role key (bypasses RLS; server-side only)

The 'reports' bucket must be created in Supabase dashboard before first use:
  Storage → New bucket → Name: "reports" → Private (not public)

Falls back gracefully: if credentials are missing or the upload fails, None is
returned and the caller keeps using the in-memory bytes / local file path.
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime

log = logging.getLogger(__name__)

_BUCKET = "reports"
_URL_EXPIRY_SECONDS = 3600  # signed URLs valid for 1 hour


def _get_service_client():
    """Return a Supabase client using the service role key, or None if not configured."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        try:
            import streamlit as st
            secrets_cfg = st.secrets.get("supabase", {})
            url = url or secrets_cfg.get("url", "").strip()
            key = key or secrets_cfg.get("service_role_key", "").strip()
        except Exception:
            pass
    if not url or not key:
        return None
    return create_client(url, key)


def storage_configured() -> bool:
    """True if service role credentials are present and Storage can be used."""
    return _get_service_client() is not None


def make_run_id(email: str = "") -> str:
    """Generate a unique run identifier used as the storage path prefix."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(4)
    prefix = email.split("@")[0][:12].replace(".", "_") if email else "anon"
    return f"{prefix}_{timestamp}_{rand}"


def upload_excel(excel_path: str, run_id: str) -> str | None:
    """Upload the Excel workbook to Storage. Returns a signed URL or None on failure."""
    client = _get_service_client()
    if not client:
        return None
    try:
        storage_path = f"excel/{run_id}.xlsx"
        with open(excel_path, "rb") as f:
            client.storage.from_(_BUCKET).upload(
                storage_path,
                f,
                file_options={
                    "content-type": (
                        "application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet"
                    ),
                    "upsert": "true",
                },
            )
        result = client.storage.from_(_BUCKET).create_signed_url(
            storage_path, _URL_EXPIRY_SECONDS
        )
        return result.get("signedURL")
    except Exception as exc:
        log.exception("Storage upload failed for excel/%s.xlsx: %s", run_id, exc)
        return None


def upload_pdf(pdf_bytes: bytes, run_id: str) -> str | None:
    """Upload the PDF report to Storage. Returns a signed URL or None on failure."""
    client = _get_service_client()
    if not client:
        return None
    try:
        storage_path = f"pdf/{run_id}.pdf"
        client.storage.from_(_BUCKET).upload(
            storage_path,
            pdf_bytes,
            file_options={
                "content-type": "application/pdf",
                "upsert": "true",
            },
        )
        result = client.storage.from_(_BUCKET).create_signed_url(
            storage_path, _URL_EXPIRY_SECONDS
        )
        return result.get("signedURL")
    except Exception as exc:
        log.exception("Storage upload failed for pdf/%s.pdf: %s", run_id, exc)
        return None

"""Supabase client factory for ColtraDataAi.

Credentials resolved in priority order:
  1. Environment variables — SUPABASE_URL, SUPABASE_ANON_KEY (set on Render).
  2. .streamlit/secrets.toml → [supabase] url / anon_key (local dev).

A new client is created on every call. The supabase-py client is lightweight
(no connection until a request is made) and keeping a module-level singleton
risks leaking auth session tokens across Streamlit user sessions that share
the same server process.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from supabase import ClientOptions, create_client

if TYPE_CHECKING:
    from supabase import Client


def _resolve(env_key: str, secrets_key: str) -> str:
    val = os.environ.get(env_key, "").strip()
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get("supabase", {}).get(secrets_key, "").strip()
    except Exception:
        return ""


def get_supabase_client() -> Client:
    url = _resolve("SUPABASE_URL", "url")
    key = _resolve("SUPABASE_ANON_KEY", "anon_key")

    if not url or not key:
        raise RuntimeError(
            "Supabase credentials missing. Add SUPABASE_URL and SUPABASE_ANON_KEY "
            "to Render env vars, or add [supabase] url / anon_key to "
            ".streamlit/secrets.toml."
        )

    return create_client(url, key, options=ClientOptions(function_client_timeout=10))

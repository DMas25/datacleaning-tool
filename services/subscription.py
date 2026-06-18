"""
Resolves the active user plan for the current session.

Current implementation reads from st.session_state (set by utils.session_helpers
via licence-key validation). When LemonSqueezy auth is live, replace the body of
get_user_plan_from_subscription() to call the LS /v1/subscriptions API and
write the result back via set_plan_key() — all call sites stay the same.

LemonSqueezy swap-in checklist:
  1. Add LEMONSQUEEZY_API_KEY to .streamlit/secrets.toml
  2. After a successful LS checkout, the order webhook delivers a customer_id
     and variant_id — map the variant via VARIANT_PLAN_MAP below.
  3. Call set_plan_key(resolved_plan) from the webhook handler / auth callback.
  4. The session_state key "plan_key" then propagates to all call sites
     automatically — no further changes needed.

Backend store swap-in checklist (load_customer_plan_from_store):
  1. Choose your store: Supabase, Firebase, Airtable, SQL, or a JSON file for testing.
  2. Implement the lookup inside load_customer_plan_from_store() below.
  3. Call it from get_user_plan_from_subscription() by passing the customer email
     stored in st.session_state["customer_email"] (set after login/auth).
  4. The returned plan key propagates to all feature gates automatically.
"""
from __future__ import annotations

import streamlit as st

from config.plans import PLAN_CONFIG
from utils.session_helpers import get_plan_key, set_plan_key

# LemonSqueezy variant ID → plan key.
# Defined centrally in config/lemonsqueezy_config.py — imported here for convenience.
from config.lemonsqueezy_config import VARIANT_PLAN_MAP

_DEFAULT_PLAN = "free"


def load_customer_plan_from_store(customer_email: str) -> str:
    """Look up the active plan for *customer_email* from the local subscription DB.

    The local SQLite database is populated automatically by the webhook server
    (services/webhook_server.py) every time a LemonSqueezy payment event fires.
    No manual data entry required once the webhook is configured.
    """
    try:
        from services.licence_manager import get_by_email
        row = get_by_email(customer_email)
        if row and row.get("status") == "active" and row.get("plan") in PLAN_CONFIG:
            return row["plan"]
    except Exception:
        pass
    return _DEFAULT_PLAN


def get_user_plan_from_subscription() -> str:
    """Return the active plan key for the current session.

    Resolution order:
      1. st.session_state["plan_key"]       — set by licence-key validation or dev override
      2. load_customer_plan_from_store()    — when customer_email is present in session
      3. Falls back to "free" if the key is missing or unrecognised

    To activate backend lookup: store the authenticated user's email in
    st.session_state["customer_email"] after login, then uncomment the block below.
    """
    plan_key = get_plan_key()
    if plan_key in PLAN_CONFIG:
        return plan_key

    # ── Uncomment once login / auth is wired up ───────────────────────────
    # email = st.session_state.get("customer_email")
    # if email:
    #     resolved = load_customer_plan_from_store(email)
    #     if resolved in PLAN_CONFIG:
    #         set_plan_key(resolved)
    #         return resolved

    return _DEFAULT_PLAN


def resolve_plan_from_variant(variant_id: str) -> str:
    """Map a LemonSqueezy variant ID to a plan key.

    Returns "free" if the variant is not in VARIANT_PLAN_MAP.
    Call this from your LS webhook handler, then pass the result to set_plan_key().
    """
    return VARIANT_PLAN_MAP.get(str(variant_id), _DEFAULT_PLAN)

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
"""
from __future__ import annotations

import streamlit as st

from config.plans import PLAN_CONFIG
from utils.session_helpers import get_plan_key

# LemonSqueezy variant ID → plan key.
# Fill these in once your LS account is approved and variant IDs are known.
VARIANT_PLAN_MAP: dict[str, str] = {
    # "123456": "starter",
    # "123457": "professional",
    # "123458": "premium",
    # "123459": "enterprise",
}

_DEFAULT_PLAN = "free"


def get_user_plan_from_subscription() -> str:
    """
    Return the active plan key for the current session.

    Resolution order:
      1. st.session_state["plan_key"]  — set by licence-key validation or dev override
      2. Falls back to "free" if the key is missing or unrecognised
    """
    plan_key = get_plan_key()
    if plan_key not in PLAN_CONFIG:
        return _DEFAULT_PLAN
    return plan_key


def resolve_plan_from_variant(variant_id: str) -> str:
    """
    Map a LemonSqueezy variant ID to a plan key.
    Returns "free" if the variant is not in VARIANT_PLAN_MAP.
    Call this from your LS webhook handler, then pass the result to set_plan_key().
    """
    return VARIANT_PLAN_MAP.get(str(variant_id), _DEFAULT_PLAN)

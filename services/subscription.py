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
# Fill these in once your LS account is approved and variant IDs are known.
VARIANT_PLAN_MAP: dict[str, str] = {
    # "123456": "starter",
    # "123457": "professional",
    # "123458": "premium",
    # "123459": "enterprise",
}

_DEFAULT_PLAN = "free"


def load_customer_plan_from_store(customer_email: str) -> str:
    """Look up the active plan for *customer_email* from your backend data store.

    Replace the stub body with one of the following once your auth layer is wired up:

    ── Supabase ──────────────────────────────────────────────────────────────────
    from supabase import create_client
    client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    row = client.table("subscriptions").select("plan").eq("email", customer_email).single().execute()
    return row.data["plan"] if row.data else "free"

    ── Firebase Firestore ────────────────────────────────────────────────────────
    import firebase_admin; from firebase_admin import firestore
    db  = firestore.client()
    doc = db.collection("subscriptions").document(customer_email).get()
    return doc.to_dict().get("plan", "free") if doc.exists else "free"

    ── Airtable ──────────────────────────────────────────────────────────────────
    from pyairtable import Table
    tbl    = Table(st.secrets["airtable"]["api_key"], st.secrets["airtable"]["base_id"], "Subscriptions")
    records = tbl.all(formula=f"{{Email}}='{customer_email}'")
    return records[0]["fields"].get("Plan", "free") if records else "free"

    ── SQL (SQLAlchemy) ──────────────────────────────────────────────────────────
    from sqlalchemy import create_engine, text
    engine = create_engine(st.secrets["database"]["url"])
    with engine.connect() as conn:
        result = conn.execute(text("SELECT plan FROM subscriptions WHERE email = :e"), {"e": customer_email})
        row = result.fetchone()
    return row[0] if row else "free"

    ── JSON file (testing only — not for production) ─────────────────────────────
    import json, pathlib
    data = json.loads(pathlib.Path("data/subscriptions.json").read_text())
    return data.get(customer_email, "free")
    """
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

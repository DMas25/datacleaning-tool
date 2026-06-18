# Lemon Squeezy configuration.
#
# Fill in every TODO value when your LS account is approved:
#   1. Create your products / variants in the LS dashboard.
#   2. Copy each variant's ID (Products → <product> → <variant> → three-dot menu → Copy ID).
#   3. Copy each variant's checkout URL (same menu → Share → Buy link).
#   4. Paste the buy links into the CHECKOUT_URLS dict below.
#   5. Set webhook_secret in .streamlit/secrets.toml → [lemonsqueezy] webhook_secret = "..."
#
# Nothing in this file is secret — it contains only public IDs and URLs.
# Keep secrets out of this file and in .streamlit/secrets.toml.

STORE_SLUG = "TODO"  # e.g. "coltradata"  (your LS store subdomain)

# ── Variant IDs ────────────────────────────────────────────────────────────
STARTER_VARIANT_ID      = "1790190"
PROFESSIONAL_VARIANT_ID = "1790279"
PREMIUM_VARIANT_ID      = "1790302"
ENTERPRISE_VARIANT_ID   = "1807649"

# ── Variant ID → plan key ──────────────────────────────────────────────────
# Populate once variant IDs are known. Used by the webhook handler and
# licence verifier to map LemonSqueezy variant IDs to internal plan keys.
VARIANT_PLAN_MAP: dict[str, str] = {
    STARTER_VARIANT_ID:      "starter",
    PROFESSIONAL_VARIANT_ID: "professional",
    PREMIUM_VARIANT_ID:      "premium",
    ENTERPRISE_VARIANT_ID:   "enterprise",
}

# Legacy alias used by core/licence_verifier.py
# Maps variant ID → capitalised tier name for the LS API validation path.
VARIANT_TIER_MAP: dict[str, str] = {
    STARTER_VARIANT_ID:      "Starter",
    PROFESSIONAL_VARIANT_ID: "Professional",
    PREMIUM_VARIANT_ID:      "Premium",
    ENTERPRISE_VARIANT_ID:   "Enterprise",
}

# ── Checkout URLs ──────────────────────────────────────────────────────────
# Paste the LemonSqueezy "Buy link" for each plan here.
# Leave as empty string until the account is approved; the UI shows "Coming soon".
CHECKOUT_URLS: dict[str, str] = {
    "Starter":      "https://coltradataai.lemonsqueezy.com/checkout/buy/258cdf5f-37a0-4ce2-b7b5-13c0186db8c1",
    "Professional": "https://coltradataai.lemonsqueezy.com/checkout/buy/d1ced1d8-b649-4804-ab70-b0a95b0180d1",
    "Premium":      "https://coltradataai.lemonsqueezy.com/checkout/buy/6e028361-d420-4410-83d8-c6d2e7c575a5",
    "Enterprise":   "https://coltradataai.lemonsqueezy.com/checkout/buy/3a9ef5ca-68cb-4b1f-b0a5-c656ed9ae236?discount=0",
}


def get_checkout_url(tier_name: str) -> str:
    """Primary checkout URL for the given tier, or '' if not yet configured."""
    return CHECKOUT_URLS.get(tier_name, "")


def is_payments_live() -> bool:
    """True once at least one non-Enterprise checkout URL has been configured."""
    return any(v for k, v in CHECKOUT_URLS.items() if k != "Enterprise")

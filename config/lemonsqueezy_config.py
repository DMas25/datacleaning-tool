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

STORE_SLUG = "coltradataai"

# ── Variant IDs (Live Mode) ────────────────────────────────────────────────
STARTER_VARIANT_ID      = "1969435"
PROFESSIONAL_VARIANT_ID = "1997647"
BUSINESS_VARIANT_ID     = "1997645"
ENTERPRISE_VARIANT_ID   = ""          # Draft — contact-only, no public checkout
API_VARIANT_ID          = "1997676"

# Legacy variant — grandfathered subscribers only. Do not remove.
PREMIUM_VARIANT_ID      = "1888466"

# ── Variant ID → plan key ──────────────────────────────────────────────────
VARIANT_PLAN_MAP: dict[str, str] = {
    STARTER_VARIANT_ID:      "starter",
    PROFESSIONAL_VARIANT_ID: "professional",
    ENTERPRISE_VARIANT_ID:   "enterprise",
    PREMIUM_VARIANT_ID:      "premium",   # legacy grandfathered
    **({BUSINESS_VARIANT_ID: "business"} if BUSINESS_VARIANT_ID else {}),
    **({API_VARIANT_ID:      "api"}       if API_VARIANT_ID      else {}),
}

# Legacy alias used by core/licence_verifier.py
VARIANT_TIER_MAP: dict[str, str] = {
    STARTER_VARIANT_ID:      "Starter",
    PROFESSIONAL_VARIANT_ID: "Professional",
    ENTERPRISE_VARIANT_ID:   "Enterprise",
    PREMIUM_VARIANT_ID:      "Premium",   # legacy grandfathered
    **({BUSINESS_VARIANT_ID: "Business"}      if BUSINESS_VARIANT_ID else {}),
    **({API_VARIANT_ID:      "Enterprise API"} if API_VARIANT_ID      else {}),
}

# ── Checkout URLs ──────────────────────────────────────────────────────────
# Paste the LemonSqueezy "Buy link" for each plan here.
# Leave as empty string until created; the UI hides the button when blank.
CHECKOUT_URLS: dict[str, str] = {
    "Starter":          "https://coltradataai.lemonsqueezy.com/checkout/buy/4b3f6ae6-cbcf-48a6-aa99-63473a3102b0",
    "Professional":     "https://coltradataai.lemonsqueezy.com/checkout/buy/bd8d38f7-f7c9-481a-8735-e0b7f92564fb",
    "Business":         "https://coltradataai.lemonsqueezy.com/checkout/buy/216f4c52-b280-4a7b-8362-07fc05c02115",
    "Enterprise":       "",   # Contact-only — no public checkout; use Book a Demo CTA
    "Enterprise API":   "https://coltradataai.lemonsqueezy.com/checkout/buy/2f0f30f8-88d4-4bea-891c-9852507a439c",
    # Legacy — do not remove
    "Premium":          "https://coltradataai.lemonsqueezy.com/checkout/buy/c4a03a84-0d00-401d-8550-1f4974bc54b0",
}


def get_checkout_url(tier_name: str) -> str:
    """Primary checkout URL for the given tier, or '' if not yet configured."""
    return CHECKOUT_URLS.get(tier_name, "")


def is_payments_live() -> bool:
    """True once at least one non-Enterprise checkout URL has been configured."""
    return any(v for k, v in CHECKOUT_URLS.items() if k != "Enterprise")

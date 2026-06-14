# Lemon Squeezy configuration.
#
# Fill in every TODO value when your LS account is approved:
#   1. Create your products / variants in the LS dashboard.
#   2. Copy each variant's ID (Products → <product> → <variant> → three-dot menu → Copy ID).
#   3. Copy each variant's checkout URL (same menu → Share → Buy link).
#   4. Paste the buy links into the CHECKOUT_URLS dict below.
#
# Nothing in this file is secret — it contains only public IDs and URLs.

STORE_SLUG = "TODO"  # e.g. "coltradata"  (your LS store subdomain)

# ── Variant IDs ────────────────────────────────────────────────────────────
STARTER_VARIANT_ID      = "TODO"
PROFESSIONAL_VARIANT_ID = "TODO"
PREMIUM_VARIANT_ID      = "TODO"
ENTERPRISE_VARIANT_ID   = "TODO"

# ── Checkout URLs ──────────────────────────────────────────────────────────
# Paste the LemonSqueezy "Buy link" for each plan here.
# Leave as empty string until the account is approved; the UI shows "Coming soon".
CHECKOUT_URLS: dict[str, str] = {
    "Starter":      "https://coltradata.lemonsqueezy.com/checkout/buy/STARTER_ID",
    "Professional": "https://coltradata.lemonsqueezy.com/checkout/buy/PRO_ID",
    "Premium":      "https://coltradata.lemonsqueezy.com/checkout/buy/PREMIUM_ID",
    "Enterprise":   "https://coltradata.lemonsqueezy.com/checkout/buy/ENT_ID",
}


def get_checkout_url(tier_name: str) -> str:
    """Primary checkout URL for the given tier, or '' if not yet configured."""
    return CHECKOUT_URLS.get(tier_name, "")


def is_payments_live() -> bool:
    """True once at least one checkout URL has been configured."""
    return any(CHECKOUT_URLS.values())

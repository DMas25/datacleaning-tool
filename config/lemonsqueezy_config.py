# Lemon Squeezy configuration.
#
# Fill in every TODO value when your LS account is approved:
#   1. Create your products / variants in the LS dashboard.
#   2. Copy each variant's ID (Products → <product> → <variant> → three-dot menu → Copy ID).
#   3. Copy each variant's checkout URL (same menu → Share → Buy link).
#   4. Uncomment the VARIANT_TIER_MAP entries below.
#
# Nothing in this file is secret — it contains only public IDs and URLs.

STORE_SLUG = "TODO"  # e.g. "coltradata"  (your LS store subdomain)

# ── Variant IDs ────────────────────────────────────────────────────────────
PRO_MONTHLY_VARIANT_ID = "TODO"
PRO_ANNUAL_VARIANT_ID = "TODO"
ENTERPRISE_VARIANT_ID = "TODO"

# ── Checkout URLs ──────────────────────────────────────────────────────────
# Leave as empty string until account is approved; the UI shows "coming soon".
PRO_MONTHLY_CHECKOUT_URL = ""
PRO_ANNUAL_CHECKOUT_URL = ""
ENTERPRISE_CHECKOUT_URL = ""

# ── Variant → Tier mapping ─────────────────────────────────────────────────
# Uncomment once the variant IDs above are filled in.
VARIANT_TIER_MAP: dict[str, str] = {
    # PRO_MONTHLY_VARIANT_ID: "Pro",
    # PRO_ANNUAL_VARIANT_ID:  "Pro",
    # ENTERPRISE_VARIANT_ID:  "Enterprise",
}


def get_checkout_url(tier_name: str) -> str:
    """Primary checkout URL for the given tier, or '' if not yet configured."""
    if tier_name == "Pro":
        return PRO_MONTHLY_CHECKOUT_URL
    if tier_name == "Enterprise":
        return ENTERPRISE_CHECKOUT_URL
    return ""


def is_payments_live() -> bool:
    """True once at least one checkout URL has been configured."""
    return bool(PRO_MONTHLY_CHECKOUT_URL or ENTERPRISE_CHECKOUT_URL)

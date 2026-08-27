"""
Billing helpers — thin wrapper around LemonSqueezy config.
Add variant IDs to config/lemonsqueezy_config.py to activate checkout links.
"""
from config.lemonsqueezy_config import get_checkout_url, is_payments_live
from config.plans import get_plan, PLAN_ORDER

# Map plan keys to the tier names expected by lemonsqueezy_config.get_checkout_url.
# Update the LS config to add Starter / Professional / Premium variants.
_LS_TIER_MAP = {
    "starter":      "Starter",
    "professional": "Professional",
    "business":     "Business",
    "enterprise":   "Enterprise",
    "enterprise_api": "Enterprise API",
    "premium":      "Premium",  # legacy — grandfathered subscribers only
}


def append_affiliate(url: str) -> str:
    """Append the session's affiliate code to a LemonSqueezy checkout URL.

    Uses ?aff= (LemonSqueezy's native affiliate parameter). Safe to call with
    an empty URL — returns it unchanged. Handles existing query strings with &.
    """
    if not url:
        return url
    from utils.session_helpers import get_affiliate_ref
    ref = get_affiliate_ref()
    if not ref:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}aff={ref}"


def checkout_url(plan_key: str) -> str:
    """Return the LemonSqueezy checkout URL for a plan, or '' if not yet live.

    Automatically appends the affiliate ref from session state when present.
    """
    ls_tier = _LS_TIER_MAP.get(plan_key, "")
    base = get_checkout_url(ls_tier) if ls_tier else ""
    return append_affiliate(base)


def price_label(plan_key: str) -> str:
    return get_plan(plan_key).get("price", "")


def payments_live() -> bool:
    return is_payments_live()


def upgrade_options(current_plan_key: str) -> list[dict]:
    """
    Return a list of plans the user can upgrade to, each with label, price, and checkout_url.
    """
    try:
        current_idx = PLAN_ORDER.index(current_plan_key)
    except ValueError:
        current_idx = 0

    options = []
    for plan_key in PLAN_ORDER[current_idx + 1 :]:
        plan = get_plan(plan_key)
        options.append(
            {
                "key": plan_key,
                "label": plan["label"],
                "price": plan.get("price", ""),
                "checkout_url": checkout_url(plan_key),
            }
        )
    return options

PLAN_CONFIG = {
    "free": {
        "label": "Free",
        "price": "£0/month",
        "can_download_excel": False,
        "can_download_pdf": False,
        "can_view_advanced_insights": False,
        "can_view_premium_charts": False,
        "can_brand_reports": False,
        "monthly_runs": 3,
        "max_rows_backend": 5000,
        "max_file_mb_backend": 10,
        "blurb": "Clean small datasets and explore your data quality — no card required.",
    },
    "starter": {
        "label": "Starter",
        "price": "£9/month",
        "can_download_excel": True,
        "can_download_pdf": False,
        "can_view_advanced_insights": False,
        "can_view_premium_charts": False,
        "can_brand_reports": False,
        "monthly_runs": 20,
        "max_rows_backend": 25000,
        "max_file_mb_backend": 25,
        "blurb": "Process larger datasets and export clean results to Excel.",
    },
    "professional": {
        "label": "Professional",
        "price": "£29/month",
        "can_download_excel": True,
        "can_download_pdf": True,
        "can_view_advanced_insights": True,
        "can_view_premium_charts": False,
        "can_brand_reports": False,
        "monthly_runs": 100,
        "max_rows_backend": 100000,
        "max_file_mb_backend": 75,
        "blurb": "Generate full reports and AI-powered insights to make faster decisions.",
    },
    "premium": {
        "label": "Premium",
        "price": "£59/month",
        "can_download_excel": True,
        "can_download_pdf": True,
        "can_view_advanced_insights": True,
        "can_view_premium_charts": True,
        "can_brand_reports": True,
        "monthly_runs": 300,
        "max_rows_backend": 250000,
        "max_file_mb_backend": 150,
        "blurb": "Scale high-volume data processing with premium charts and branded outputs.",
    },
    "enterprise": {
        "label": "Enterprise",
        "price": "£299/month",
        "can_download_excel": True,
        "can_download_pdf": True,
        "can_view_advanced_insights": True,
        "can_view_premium_charts": True,
        "can_brand_reports": True,
        "monthly_runs": 2000,
        "max_rows_backend": 1000000,
        "max_file_mb_backend": 300,
        "blurb": "2,000 runs/month, API access, custom integrations, and dedicated support.",
    },
}

PLAN_ORDER = ["free", "starter", "professional", "premium", "enterprise"]


def get_plan(plan_key: str) -> dict:
    return PLAN_CONFIG.get(plan_key, PLAN_CONFIG["free"])


def can_feature(plan_key: str, feature: str) -> bool:
    return bool(get_plan(plan_key).get(feature, False))


def is_higher_plan(a: str, b: str) -> bool:
    """True if plan a is strictly higher than plan b."""
    try:
        return PLAN_ORDER.index(a) > PLAN_ORDER.index(b)
    except ValueError:
        return False


def next_plan(plan_key: str) -> str | None:
    """Return the next tier up, or None if already at enterprise."""
    try:
        idx = PLAN_ORDER.index(plan_key)
        return PLAN_ORDER[idx + 1] if idx + 1 < len(PLAN_ORDER) else None
    except ValueError:
        return None


def get_next_paid_plan(plan_key: str) -> str | None:
    """Return the next paid (non-free) plan above plan_key.

    Skips 'free' so calling this from any plan always returns a purchasable tier.
    Returns None if the user is already on the top-tier plan.
    """
    try:
        idx = PLAN_ORDER.index(plan_key)
    except ValueError:
        idx = 0
    for candidate in PLAN_ORDER[idx + 1:]:
        if candidate != "free":
            return candidate
    return None

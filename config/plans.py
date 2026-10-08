PLAN_CONFIG = {
    "free": {
        "label": "Free",
        "price": "£0/month",
        "can_download_excel": False,
        "can_download_pdf": False,
        "can_view_advanced_insights": False,
        "can_view_premium_charts": False,
        "can_brand_reports": False,
        "can_use_api": False,
        "api_rows_per_call": 0,
        "api_calls_per_month": 0,
        "monthly_runs": 3,
        "max_rows_backend": 5000,
        "max_file_mb_backend": 10,
        "blurb": "Clean small datasets and explore your data quality — no card required.",
        "usage_context": "Suited for individuals testing the tool or processing an occasional file.",
    },
    "starter": {
        "label": "Starter",
        "price": "£29/month",
        "can_download_excel": True,
        "can_download_pdf": False,
        "can_view_advanced_insights": True,
        "can_view_premium_charts": False,
        "can_brand_reports": False,
        "can_use_api": False,
        "api_rows_per_call": 0,
        "api_calls_per_month": 0,
        "monthly_runs": 50,
        "max_rows_backend": 50000,
        "max_file_mb_backend": 25,
        "blurb": "For consultants and small businesses — AI insights, Excel export, and 50 runs/month.",
        "usage_context": "Suited for a freelancer or consultant managing 5-10 regular client files.",
    },
    "professional": {
        "label": "Professional",
        "price": "£99/month",
        "can_download_excel": True,
        "can_download_pdf": True,
        "can_view_advanced_insights": True,
        "can_view_premium_charts": True,
        "can_brand_reports": False,
        "can_use_api": True,
        "api_rows_per_call": 1000,
        "api_calls_per_month": 100,
        "monthly_runs": 200,
        "max_rows_backend": 250000,
        "max_file_mb_backend": 75,
        "blurb": "For SMEs and operations teams — full reports, API access, and advanced analytics.",
        "usage_context": "Suited for an SME team running weekly or daily validation across multiple data sources.",
    },
    "business": {
        "label": "Business",
        "price": "£299/month",
        "can_download_excel": True,
        "can_download_pdf": True,
        "can_view_advanced_insights": True,
        "can_view_premium_charts": True,
        "can_brand_reports": True,
        "can_use_api": True,
        "api_rows_per_call": 10000,
        "api_calls_per_month": None,  # unlimited
        "monthly_runs": 1000,
        "max_rows_backend": 1000000,
        "max_file_mb_backend": 200,
        "blurb": "For manufacturing, healthcare, retail, and logistics — industry templates, multi-user, unlimited API calls.",
        "usage_context": "Suited for an operations team with scheduled or automated data workflows.",
    },
    "enterprise": {
        "label": "Enterprise",
        "price": "£999/month",
        "can_download_excel": True,
        "can_download_pdf": True,
        "can_view_advanced_insights": True,
        "can_view_premium_charts": True,
        "can_brand_reports": True,
        "can_use_api": True,
        "api_rows_per_call": None,   # unlimited
        "api_calls_per_month": None, # unlimited
        "monthly_runs": None,        # unlimited
        "max_rows_backend": None,    # unlimited
        "max_file_mb_backend": 500,
        "blurb": "White label, dedicated database, SLA, onboarding, custom AI workflows, and dedicated support.",
        "usage_context": "Suited for organisations with high-volume data, compliance requirements, or multi-team deployment.",
    },
}

PLAN_ORDER = ["free", "starter", "professional", "business", "enterprise"]


def get_plan(plan_key: str) -> dict:
    return PLAN_CONFIG.get(plan_key, PLAN_CONFIG["free"])


def can_feature(plan_key: str, feature: str) -> bool:
    return bool(get_plan(plan_key).get(feature, False))


def is_higher_plan(a: str, b: str) -> bool:
    """True if plan a is strictly higher than plan b."""
    order = PLAN_ORDER
    try:
        return order.index(a) > order.index(b)
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

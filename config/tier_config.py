DEFAULT_TIER = "Free"

# ---------------------------------------------------------------------------
# Tier scaffolding for the SaaS pricing model.
#
# This is structural only — there is no live payment processor wired up.
# `row_limit: None` means unlimited. Feature flags gate which sections of the
# app are unlocked for the active tier.
# ---------------------------------------------------------------------------
TIERS = {
    "Free": {
        "label": "Free",
        "price": "£0/month",
        "row_limit": 5000,
        "features": {
            "advanced_dashboards": False,
            "ai_insights": False,
            "ai_advisory": False,
            "export": False,
        },
        "blurb": "Data cleaning and a basic summary dashboard for datasets up to 5,000 rows.",
    },
    "Pro": {
        "label": "Pro",
        "price": "£20–£50/month",
        "row_limit": 250_000,
        "features": {
            "advanced_dashboards": True,
            "ai_insights": True,
            "ai_advisory": False,
            "export": True,
            "export_pdf": False,
            "export_branding": False,
        },
        "blurb": "Full dashboards, AI data insights, and Excel report downloads for larger datasets.",
    },
    "Enterprise": {
        "label": "Enterprise",
        "price": "£299/month",
        "row_limit": None,
        "features": {
            "advanced_dashboards": True,
            "ai_insights": True,
            "ai_advisory": True,
            "export": True,
            "export_pdf": True,
            "export_branding": True,
            "api_access": True,
            "white_label": True,
            "bulk_upload": True,
        },
        "blurb": "API access, bulk uploads, PDF reports, custom branding, and priority processing.",
    },
}


def get_tier(tier_name: str) -> dict:
    return TIERS.get(tier_name, TIERS[DEFAULT_TIER])


def has_feature(tier_name: str, feature: str) -> bool:
    return bool(get_tier(tier_name)["features"].get(feature, False))


def row_limit_for(tier_name: str):
    return get_tier(tier_name)["row_limit"]

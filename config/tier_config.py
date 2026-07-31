DEFAULT_TIER = "Free"

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
            "api_access": False,
        },
        "blurb": "Data cleaning and a basic summary dashboard for datasets up to 5,000 rows.",
    },
    "Starter": {
        "label": "Starter",
        "price": "£29/month",
        "row_limit": 50_000,
        "features": {
            "advanced_dashboards": False,
            "ai_insights": True,
            "ai_advisory": False,
            "export": True,
            "export_pdf": False,
            "export_branding": False,
            "api_access": False,
        },
        "blurb": "For consultants and small businesses — AI insights, Excel export, and 50 runs/month.",
    },
    "Professional": {
        "label": "Professional",
        "price": "£99/month",
        "row_limit": 250_000,
        "features": {
            "advanced_dashboards": True,
            "ai_insights": True,
            "ai_advisory": False,
            "export": True,
            "export_pdf": True,
            "export_branding": False,
            "api_access": True,
        },
        "blurb": "For SMEs and operations teams — full reports, API access, and advanced analytics.",
    },
    "Business": {
        "label": "Business",
        "price": "£299/month",
        "row_limit": 1_000_000,
        "features": {
            "advanced_dashboards": True,
            "ai_insights": True,
            "ai_advisory": True,
            "export": True,
            "export_pdf": True,
            "export_branding": True,
            "api_access": True,
            "bulk_upload": True,
        },
        "blurb": "For manufacturing, healthcare, retail, and logistics — industry templates, multi-user, unlimited API calls.",
    },
    "Enterprise": {
        "label": "Enterprise",
        "price": "£999/month",
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
            "dedicated_support": True,
            "sla": True,
        },
        "blurb": "White label, dedicated database, SLA, onboarding, custom AI workflows, and dedicated support.",
    },
    # Legacy tier — grandfathered existing subscribers. Not shown on pricing page.
    "Premium": {
        "label": "Premium",
        "price": "£59/month",
        "row_limit": 250_000,
        "features": {
            "advanced_dashboards": True,
            "ai_insights": True,
            "ai_advisory": True,
            "export": True,
            "export_pdf": True,
            "export_branding": True,
            "api_access": False,
        },
        "blurb": "Legacy plan — grandfathered pricing for existing subscribers.",
    },
}


def get_tier(tier_name: str) -> dict:
    return TIERS.get(tier_name, TIERS[DEFAULT_TIER])


def has_feature(tier_name: str, feature: str) -> bool:
    return bool(get_tier(tier_name)["features"].get(feature, False))


def row_limit_for(tier_name: str):
    return get_tier(tier_name)["row_limit"]

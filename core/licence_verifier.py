import requests

_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"


def validate_licence_key(licence_key: str) -> dict:
    """
    Calls the Lemon Squeezy licence-validate endpoint (no auth required).

    Returns {"valid": bool, "tier": str, "error": str | None}
    where tier is one of "Free" / "Pro" / "Enterprise".
    """
    from config.lemonsqueezy_config import VARIANT_TIER_MAP

    key = licence_key.strip() if licence_key else ""
    if not key:
        return {"valid": False, "tier": "Free", "error": None}

    try:
        resp = requests.post(_VALIDATE_URL, data={"license_key": key}, timeout=8)
        data = resp.json()
    except requests.Timeout:
        return {"valid": False, "tier": "Free", "error": "Licence server timed out — please try again."}
    except requests.RequestException as exc:
        return {"valid": False, "tier": "Free", "error": f"Could not reach licence server: {exc}"}

    if not data.get("valid"):
        return {
            "valid": False,
            "tier": "Free",
            "error": data.get("error") or "Invalid or expired licence key.",
        }

    variant_id = str(data.get("meta", {}).get("variant_id", ""))
    tier = VARIANT_TIER_MAP.get(variant_id, "Pro")

    return {"valid": True, "tier": tier, "error": None}

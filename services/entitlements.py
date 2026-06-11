from config.plans import PLAN_CONFIG, PLAN_ORDER


def get_plan(plan_name: str) -> dict:
    return PLAN_CONFIG.get(plan_name, PLAN_CONFIG["free"])


def has_feature(plan_name: str, feature_name: str) -> bool:
    return get_plan(plan_name).get(feature_name, False)


def get_entitlements(plan_key: str) -> dict:
    return get_plan(plan_key)


def monthly_runs_limit(plan_key: str) -> int | None:
    """None means unlimited."""
    return get_plan(plan_key)["monthly_runs"]


def max_rows(plan_key: str) -> int:
    return get_plan(plan_key)["max_rows_backend"]


def max_file_mb(plan_key: str) -> int:
    return get_plan(plan_key)["max_file_mb_backend"]


def first_plan_with_feature(feature: str) -> str | None:
    """Return the lowest plan that unlocks a given feature."""
    for plan_key in PLAN_ORDER:
        if PLAN_CONFIG[plan_key].get(feature):
            return plan_key
    return None


def features_unlocked_at(plan_key: str) -> list[str]:
    """List of boolean feature flags that are True for this plan."""
    plan = get_plan(plan_key)
    return [k for k, v in plan.items() if isinstance(v, bool) and v]

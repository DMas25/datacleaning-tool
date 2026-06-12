from config.plans import get_plan


def can(plan_key: str, feature: str) -> bool:
    """Check whether a plan has a boolean feature flag enabled."""
    return bool(get_plan(plan_key).get(feature, False))


def within_row_limit(plan_key: str, row_count: int) -> bool:
    return row_count <= get_plan(plan_key)["max_rows_backend"]


def within_file_limit(plan_key: str, file_mb: float) -> bool:
    return file_mb <= get_plan(plan_key)["max_file_mb_backend"]


def validate_capacity(plan_name: str, row_count: int, file_size_mb: float) -> tuple[bool, str]:
    """Returns (ok, user-facing upgrade message)."""
    plan = get_plan(plan_name)
    if row_count > plan["max_rows_backend"]:
        return False, (
            "Upgrade your plan to process this dataset in full. "
            f"Advanced plans support significantly larger files and faster processing."
        )
    if file_size_mb > plan["max_file_mb_backend"]:
        return False, (
            "Upgrade your plan to upload larger files. "
            f"Advanced plans support significantly larger uploads and faster processing."
        )
    return True, ""


def check_upload(plan_key: str, row_count: int, file_mb: float) -> tuple[bool, str]:
    """
    Returns (ok, reason). reason is '' when ok is True.
    Use reason as the user-facing error message when ok is False.
    """
    plan = get_plan(plan_key)
    if file_mb > plan["max_file_mb_backend"]:
        return False, (
            f"File is {file_mb:.1f} MB — your **{plan['label']}** plan allows "
            f"up to {plan['max_file_mb_backend']} MB per upload."
        )
    if row_count > plan["max_rows_backend"]:
        return False, (
            f"Dataset has {row_count:,} rows — your **{plan['label']}** plan allows "
            f"up to {plan['max_rows_backend']:,} rows per upload."
        )
    return True, ""

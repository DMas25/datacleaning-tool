from config.plans import get_plan


def can(plan_key: str, feature: str) -> bool:
    """Check whether a plan has a boolean feature flag enabled."""
    return bool(get_plan(plan_key).get(feature, False))


def within_row_limit(plan_key: str, row_count: int) -> bool:
    limit = get_plan(plan_key)["max_rows_backend"]
    return limit is None or row_count <= limit


def within_file_limit(plan_key: str, file_mb: float) -> bool:
    limit = get_plan(plan_key)["max_file_mb_backend"]
    return limit is None or file_mb <= limit


def validate_capacity(plan_name: str, row_count: int, file_size_mb: float) -> tuple[bool, str]:
    """Returns (ok, user-facing upgrade message). None limits mean unlimited."""
    plan = get_plan(plan_name)
    row_limit = plan["max_rows_backend"]
    if row_limit is not None and row_count > row_limit:
        return False, (
            "Upgrade your plan to process this dataset in full. "
            "Advanced plans support significantly larger files and faster processing."
        )
    file_limit = plan["max_file_mb_backend"]
    if file_limit is not None and file_size_mb > file_limit:
        return False, (
            "Upgrade your plan to upload larger files. "
            "Advanced plans support significantly larger uploads and faster processing."
        )
    return True, ""


def check_upload(plan_key: str, row_count: int, file_mb: float) -> tuple[bool, str]:
    """
    Returns (ok, reason). reason is '' when ok is True.
    Use reason as the user-facing error message when ok is False.
    """
    plan = get_plan(plan_key)
    file_limit = plan["max_file_mb_backend"]
    if file_limit is not None and file_mb > file_limit:
        return False, (
            f"File is {file_mb:.1f} MB — your **{plan['label']}** plan allows "
            f"up to {file_limit} MB per upload."
        )
    row_limit = plan["max_rows_backend"]
    if row_limit is not None and row_count > row_limit:
        return False, (
            f"Dataset has {row_count:,} rows — your **{plan['label']}** plan allows "
            f"up to {row_limit:,} rows per upload."
        )
    return True, ""

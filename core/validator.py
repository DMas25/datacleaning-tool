"""Public validator API — thin wrapper over core.data_validator.

All detailed validation logic lives in data_validator.py.  This module
exposes a clean, stable interface so callers import from ``core.validator``
and are insulated from internal naming changes.
"""
from __future__ import annotations

import pandas as pd

from core.data_validator import build_validation_issues   # noqa: F401 — re-exported


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a DataFrame of detected data-quality issues with columns:
    Column | Issue Type | Issue Count | Total Rows
    """
    return build_validation_issues(df)


def has_issues(df: pd.DataFrame) -> bool:
    """True if any validation issues are detected in *df*."""
    return not validate_dataframe(df).empty


def issue_count(df: pd.DataFrame) -> int:
    """Total number of validation issue rows across all columns."""
    issues = validate_dataframe(df)
    if issues.empty or "Issue Count" not in issues.columns:
        return 0
    return int(issues["Issue Count"].sum())

"""Input and data validation helpers for ColtraDataAi.

Pure functions — no Streamlit or pandas side-effects beyond reading.
"""
from __future__ import annotations

import re
from typing import Optional

import pandas as pd


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_KEYWORDS = ("date", "time", "created", "updated", "timestamp", "dob", "dt_")


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(str(value).strip()))


def is_probable_date_column(series: pd.Series) -> bool:
    """Heuristic: column name contains a date keyword AND values parse as dates."""
    name_hit = any(kw in series.name.lower() for kw in DATE_KEYWORDS)
    if not name_hit:
        return False
    sample = series.dropna().head(50)
    if sample.empty:
        return False
    try:
        pd.to_datetime(sample, errors="raise")
        return True
    except Exception:
        return False


def is_probable_numeric(series: pd.Series) -> bool:
    """True if a non-numeric-dtype column is actually numeric after coercion."""
    if pd.api.types.is_numeric_dtype(series):
        return True
    converted = pd.to_numeric(series.dropna().head(100), errors="coerce")
    return converted.notna().mean() >= 0.9


def validate_upload_constraints(
    df: pd.DataFrame,
    max_rows: Optional[int] = None,
    max_cols: int = 500,
) -> list[str]:
    """
    Return a list of human-readable constraint violations.
    An empty list means the dataframe is acceptable.
    """
    issues = []
    if max_rows and len(df) > max_rows:
        issues.append(f"Dataset has {len(df):,} rows; limit is {max_rows:,}.")
    if len(df.columns) > max_cols:
        issues.append(f"Dataset has {len(df.columns)} columns; limit is {max_cols}.")
    if df.empty:
        issues.append("Dataset is empty.")
    return issues

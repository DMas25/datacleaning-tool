"""Dataset profiling — fast, dependency-free summary statistics.

Produces the raw numbers consumed by the preview panel and quality sheet
without performing any cleaning or transformation.
"""
from __future__ import annotations

from typing import Dict, List

import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> Dict:
    """Return a flat summary dict for an arbitrary DataFrame."""
    total_cells = df.shape[0] * df.shape[1]
    missing_total = int(df.isnull().sum().sum())
    return {
        "rows":            len(df),
        "columns":         len(df.columns),
        "missing_total":   missing_total,
        "duplicate_total": int(df.duplicated().sum()),
        "completeness_pct": round((1 - missing_total / max(total_cells, 1)) * 100, 2),
        "memory_mb":       round(df.memory_usage(deep=True).sum() / 1_048_576, 2),
        "dtypes":          df.dtypes.astype(str).to_dict(),
        "missing_by_col":  df.isnull().sum().to_dict(),
        "unique_by_col":   {col: int(df[col].nunique()) for col in df.columns},
    }


def build_quality_summary_df(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame, null_handling: str) -> pd.DataFrame:
    """Build the four-row quality metrics DataFrame used in Quality Checks sheet."""
    missing_after = (
        int(cleaned_df.isnull().sum().sum()) if null_handling == "No Change" else 0
    )
    rows = [
        {"Metric": "Rows",                         "Value": len(cleaned_df)},
        {"Metric": "Columns",                      "Value": len(cleaned_df.columns)},
        {"Metric": "Missing Values",               "Value": missing_after},
        {"Metric": "Duplicate Rows After Cleaning","Value": int(cleaned_df.duplicated().sum())},
    ]
    return pd.DataFrame(rows)


def column_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column summary: dtype, nulls, unique count, sample value."""
    records = []
    for col in df.columns:
        sample = df[col].dropna().iloc[0] if df[col].notna().any() else None
        records.append({
            "Column":       col,
            "Type":         str(df[col].dtype),
            "Null Count":   int(df[col].isnull().sum()),
            "Null %":       round(df[col].isnull().mean() * 100, 2),
            "Unique Values":int(df[col].nunique()),
            "Sample Value": str(sample)[:60] if sample is not None else "",
        })
    return pd.DataFrame(records)


def detect_numeric_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def detect_categorical_columns(df: pd.DataFrame, exclude: List[str] | None = None) -> List[str]:
    exclude = exclude or []
    return [
        c for c in df.columns
        if not pd.api.types.is_numeric_dtype(df[c])
        and c not in exclude
        and df[c].nunique() <= max(50, len(df) * 0.05)
    ]

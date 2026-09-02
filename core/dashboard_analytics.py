from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Pure data-shaping helpers for dashboard chart sections (distribution,
# trend, correlation, top/bottom). These return plain DataFrames/Series so
# the calling UI can render them with whichever charting library it prefers.
# ---------------------------------------------------------------------------


def numeric_columns(df: pd.DataFrame):
    return list(df.select_dtypes(include=[np.number]).columns)


def categorical_columns(df: pd.DataFrame, date_cols=None):
    date_cols = set(date_cols or [])
    return [c for c in df.select_dtypes(include=["object"]).columns if str(c) not in date_cols]


def frequency_table(df: pd.DataFrame, column: str, top_n: int = 10) -> pd.DataFrame:
    series = df[column].dropna().astype(str)
    counts = series.value_counts().head(top_n)
    return pd.DataFrame({str(column): counts.index, "Count": counts.values})


def top_bottom_values(df: pd.DataFrame, column: str, n: int = 5):
    series = df[column].dropna()
    top = series.sort_values(ascending=False).head(n)
    bottom = series.sort_values(ascending=True).head(n)
    return top, bottom


def correlation_matrix(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return None
    return numeric_df.corr(numeric_only=True)


def time_series_counts(df: pd.DataFrame, date_column: str) -> Optional[pd.DataFrame]:
    parsed = pd.to_datetime(df[date_column], errors="coerce", format="mixed", utc=True).dropna()
    if parsed.empty:
        return None

    counts = parsed.dt.tz_convert(None).dt.to_period("D").value_counts().sort_index()
    return pd.DataFrame({"Date": counts.index.astype(str), "Records": counts.values})

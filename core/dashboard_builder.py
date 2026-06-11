"""Public dashboard-analytics API — stable wrapper over dashboard_analytics.

Provides the same functions under cleaner names so UI code imports from
``core.dashboard_builder`` and is decoupled from the internal module.
"""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from core.dashboard_analytics import (          # noqa: F401 — re-exported
    numeric_columns,
    categorical_columns,
    frequency_table,
    top_bottom_values,
    correlation_matrix,
    time_series_counts,
)


def get_numeric_columns(df: pd.DataFrame) -> List[str]:
    return numeric_columns(df)


def get_categorical_columns(df: pd.DataFrame, exclude: Optional[List[str]] = None) -> List[str]:
    return categorical_columns(df, exclude or [])


def get_frequency_table(df: pd.DataFrame, column: str, top_n: Optional[int] = None) -> pd.DataFrame:
    return frequency_table(df, column, top_n=top_n) if top_n else frequency_table(df, column)


def get_top_bottom(df: pd.DataFrame, column: str, n: int = 5):
    return top_bottom_values(df, column, n=n)


def get_correlation_matrix(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    return correlation_matrix(df)


def get_time_series(df: pd.DataFrame, date_column: str) -> Optional[pd.DataFrame]:
    return time_series_counts(df, date_column)

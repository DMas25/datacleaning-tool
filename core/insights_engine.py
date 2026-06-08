from typing import Dict, List

import numpy as np
import pandas as pd

from core.data_validator import detect_outliers, detect_inconsistent_values

# ---------------------------------------------------------------------------
# Rules-based, non-advisory data insights.
#
# Every observation here is a direct, descriptive statement derived from the
# dataset itself (composition, patterns, anomalies, distributions,
# completeness). Nothing here makes recommendations or judgements about what
# the user should do with the data.
# ---------------------------------------------------------------------------

INSIGHT_CATEGORIES = [
    "Data Composition",
    "Key Patterns",
    "Anomalies Detected",
    "Distribution Observations",
    "Data Completeness",
]


def detect_date_columns(df: pd.DataFrame) -> List[str]:
    date_cols = [str(c) for c in df.select_dtypes(include=["datetime64[ns]"]).columns]

    for col in df.select_dtypes(include=["object"]).columns:
        sample = df[col].dropna().head(50)
        if sample.empty:
            continue
        parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
        if parsed.notna().mean() > 0.8:
            date_cols.append(str(col))

    return date_cols


def _truncate_list(values, limit=8) -> str:
    values = [str(v) for v in values]
    shown = ", ".join(values[:limit])
    return shown + ("…" if len(values) > limit else "")


def _data_composition(df: pd.DataFrame, date_cols: List[str]) -> List[str]:
    observations = []
    total_rows, total_cols = len(df), len(df.columns)

    observations.append(f"Dataset contains {total_rows:,} rows across {total_cols} column(s).")

    numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
    text_cols = [c for c in df.select_dtypes(include=["object"]).columns if str(c) not in date_cols]

    if numeric_cols:
        observations.append(
            f"{len(numeric_cols)} column(s) hold numeric data: {_truncate_list(numeric_cols)}."
        )
    if text_cols:
        observations.append(
            f"{len(text_cols)} column(s) hold text/categorical data: {_truncate_list(text_cols)}."
        )
    if date_cols:
        observations.append(
            f"{len(date_cols)} column(s) appear to hold date/time values: {_truncate_list(date_cols)}."
        )

    return observations


def _key_patterns(df: pd.DataFrame, date_cols: List[str]) -> List[str]:
    observations = []
    total_rows = len(df)
    if total_rows == 0:
        return observations

    # Dominant categories within low-cardinality text columns
    text_cols = [c for c in df.select_dtypes(include=["object"]).columns if str(c) not in date_cols]
    for col in text_cols:
        series = df[col].dropna()
        if series.empty or series.nunique() > 30:
            continue
        top_value, top_count = series.value_counts().index[0], series.value_counts().iloc[0]
        share = round((top_count / len(series)) * 100, 1)
        if share >= 25:
            observations.append(
                f"In column '{col}', the value '{top_value}' represents {share}% of all entries."
            )

    # Strong correlations between numeric columns
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] >= 2:
        corr = numeric_df.corr(numeric_only=True)
        seen = set()
        for col_a in corr.columns:
            for col_b in corr.columns:
                if col_a == col_b or (col_b, col_a) in seen:
                    continue
                seen.add((col_a, col_b))
                value = corr.loc[col_a, col_b]
                if pd.notna(value) and abs(value) >= 0.7:
                    direction = "positive" if value > 0 else "negative"
                    observations.append(
                        f"Columns '{col_a}' and '{col_b}' show a strong {direction} correlation "
                        f"(r = {round(float(value), 2)})."
                    )

    if not observations:
        observations.append("No dominant categories or strong numeric correlations were detected.")

    return observations


def _anomalies(df: pd.DataFrame) -> List[str]:
    observations = []
    total_rows = len(df)

    duplicate_count = int(df.duplicated().sum())
    if duplicate_count > 0:
        observations.append(
            f"{duplicate_count:,} duplicate row(s) were detected "
            f"({round((duplicate_count / max(total_rows, 1)) * 100, 1)}% of records)."
        )

    outliers_df = detect_outliers(df)
    for _, row in outliers_df.iterrows():
        pct = round((row["Issue Count"] / max(row["Total Rows"], 1)) * 100, 1)
        observations.append(
            f"Column '{row['Column']}' contains {int(row['Issue Count']):,} statistical outlier value(s) "
            f"({pct}% of records), based on the interquartile range."
        )

    inconsistent_df = detect_inconsistent_values(df)
    for _, row in inconsistent_df.iterrows():
        pct = round((row["Issue Count"] / max(row["Total Rows"], 1)) * 100, 1)
        observations.append(
            f"Column '{row['Column']}' contains {int(row['Issue Count']):,} value(s) that appear "
            f"in multiple casing/whitespace variants ({pct}% of records)."
        )

    if not observations:
        observations.append("No duplicate rows, statistical outliers, or value-format inconsistencies were detected.")

    return observations


def _distribution_observations(df: pd.DataFrame, date_cols: List[str]) -> List[str]:
    observations = []

    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        if len(series) < 2:
            continue

        minimum, maximum, mean = series.min(), series.max(), series.mean()
        std = series.std()
        observations.append(
            f"Column '{col}' ranges from {minimum:,.2f} to {maximum:,.2f}, "
            f"with a mean of {mean:,.2f} and a standard deviation of {std:,.2f}."
        )

    for col in [c for c in df.select_dtypes(include=["object"]).columns if str(c) not in date_cols]:
        series = df[col].dropna()
        if series.empty:
            continue
        unique_count = series.nunique()
        observations.append(
            f"Column '{col}' contains {unique_count:,} unique value(s) across {len(series):,} non-blank entries."
        )

    if not observations:
        observations.append("No numeric or categorical columns were available for distribution analysis.")

    return observations


def _completeness_observations(df: pd.DataFrame) -> List[str]:
    observations = []
    total_rows = len(df)
    if total_rows == 0 or len(df.columns) == 0:
        return ["The dataset contains no rows or columns to assess for completeness."]

    missing_by_col = df.isnull().sum()
    complete_cols = [str(c) for c in missing_by_col.index if missing_by_col[c] == 0]
    incomplete_cols = missing_by_col[missing_by_col > 0].sort_values(ascending=False)

    total_cells = total_rows * len(df.columns)
    overall_missing = int(missing_by_col.sum())
    overall_pct = round((overall_missing / total_cells) * 100, 1) if total_cells else 0
    observations.append(
        f"Overall, {overall_pct}% of all cells in the dataset are missing "
        f"({overall_missing:,} of {total_cells:,})."
    )

    if complete_cols:
        observations.append(
            f"{len(complete_cols)} column(s) have no missing values: {_truncate_list(complete_cols)}."
        )

    for col, count in incomplete_cols.head(8).items():
        pct = round((count / total_rows) * 100, 1)
        observations.append(f"Column '{col}' contains {pct}% missing values ({int(count):,} of {total_rows:,}).")

    return observations


def generate_insights(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Generates structured, non-advisory descriptive observations about a dataset."""
    date_cols = detect_date_columns(df)

    return {
        "Data Composition": _data_composition(df, date_cols),
        "Key Patterns": _key_patterns(df, date_cols),
        "Anomalies Detected": _anomalies(df),
        "Distribution Observations": _distribution_observations(df, date_cols),
        "Data Completeness": _completeness_observations(df),
    }

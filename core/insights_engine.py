from typing import Dict, List

import numpy as np
import pandas as pd

from core.data_validator import detect_inconsistent_values
from core.coltradata_refine_patch import intelligent_outliers

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

    # Value concentration (Pareto): top 20% of records by rank drive what % of total value?
    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        if len(series) < 10 or series.sum() == 0 or (series < 0).any():
            continue
        sorted_vals = series.sort_values(ascending=False)
        top_n = max(1, int(len(sorted_vals) * 0.2))
        top_share = round((sorted_vals.iloc[:top_n].sum() / sorted_vals.sum()) * 100, 1)
        if top_share >= 70:
            observations.append(
                f"Column '{col}' shows Pareto-style concentration: the top 20% of records "
                f"account for {top_share}% of total value — a strong concentration signal."
            )
        break  # one value column is enough for this check

    # Date range span
    for col in date_cols:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce").dropna()
            if len(parsed) >= 2:
                span_days = (parsed.max() - parsed.min()).days
                if span_days > 0:
                    observations.append(
                        f"Date column '{col}' spans {span_days:,} days "
                        f"({parsed.min().strftime('%d %b %Y')} to {parsed.max().strftime('%d %b %Y')})."
                    )
            break
        except Exception:
            continue

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

    outliers_df = intelligent_outliers(df)
    for _, row in outliers_df.iterrows():
        pct = round((row["Issue Count"] / max(row["Total Rows"], 1)) * 100, 1)
        if row["Classification"] == "Valid Extreme Value":
            observations.append(
                f"Column '{row['Column']}' contains {int(row['Issue Count']):,} valid extreme value(s) "
                f"({pct}% of records) — exact quantity × price multiples, not data errors."
            )
        else:
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

    # Zero-value detection in numeric columns (can indicate unposted or placeholder entries)
    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        zero_count = int((series == 0).sum())
        zero_pct = round((zero_count / len(series)) * 100, 1)
        if zero_pct >= 10:
            observations.append(
                f"Column '{col}' contains {zero_count:,} zero value(s) ({zero_pct}% of records). "
                "High zero-value concentration may indicate unposted entries, placeholders, or data gaps."
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
        skew = float(series.skew()) if len(series) >= 3 else 0.0

        skew_note = ""
        if abs(skew) >= 1.5:
            direction = "right (positive)" if skew > 0 else "left (negative)"
            skew_note = f" The distribution is strongly {direction}-skewed (skewness = {skew:.2f}), indicating a long tail of {'higher' if skew > 0 else 'lower'} values."
        elif abs(skew) >= 0.75:
            direction = "right" if skew > 0 else "left"
            skew_note = f" Moderately {direction}-skewed (skewness = {skew:.2f})."

        observations.append(
            f"Column '{col}' ranges from {minimum:,.2f} to {maximum:,.2f}, "
            f"with a mean of {mean:,.2f} and a standard deviation of {std:,.2f}.{skew_note}"
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

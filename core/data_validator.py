import pandas as pd
import numpy as np


def detect_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """IQR-based outlier detection for numeric columns."""
    rows = []
    total_rows = len(df)

    for col in df.select_dtypes(include=[np.number]).columns:
        series = df[col].dropna()
        if len(series) < 4:
            continue

        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())

        if outlier_count > 0:
            rows.append({
                "Column": str(col),
                "Issue Type": "Outliers",
                "Issue Count": outlier_count,
                "Total Rows": total_rows,
            })

    return pd.DataFrame(rows, columns=["Column", "Issue Type", "Issue Count", "Total Rows"])


def detect_inconsistent_values(df: pd.DataFrame, max_unique_ratio: float = 0.5) -> pd.DataFrame:
    """Flags text columns where the same underlying value appears in multiple
    casing/whitespace variants (e.g. "USA", "usa", " USA ")."""
    rows = []
    total_rows = len(df)

    for col in df.select_dtypes(include=["object"]).columns:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue

        # Skip likely free-text/identifier columns where every value is near-unique
        if series.nunique() / len(series) > max_unique_ratio:
            continue

        normalised = series.str.strip().str.lower()
        variant_counts = pd.DataFrame({"raw": series, "norm": normalised}) \
            .groupby("norm")["raw"].nunique()
        inconsistent_norms = variant_counts[variant_counts > 1].index

        if len(inconsistent_norms) > 0:
            affected_count = int(normalised.isin(inconsistent_norms).sum())
            rows.append({
                "Column": str(col),
                "Issue Type": "Inconsistent Values",
                "Issue Count": affected_count,
                "Total Rows": total_rows,
            })

    return pd.DataFrame(rows, columns=["Column", "Issue Type", "Issue Count", "Total Rows"])


def build_validation_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Runs all validation checks and combines results into a single issues table
    in the same shape expected by ReportBuilder's quality/risk pipeline."""
    frames = [detect_outliers(df), detect_inconsistent_values(df)]
    frames = [f for f in frames if not f.empty]

    if not frames:
        return pd.DataFrame(columns=["Column", "Issue Type", "Issue Count", "Total Rows"])

    return pd.concat(frames, ignore_index=True)

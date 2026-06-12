"""coltradata_refine_patch.py
============================
Follow-up refinements to the base coltradata_patch, fixing three further issues
identified after reviewing report ColtraDataAi_Cleaned_Report_20260612_0814:

  1. intelligent_outliers — IQR outlier detection that validates each flagged value
     against the arithmetic relationship qty × price = total.  Values that are exact
     multiples are reclassified as "Valid Extreme Value" rather than "True Outlier",
     so the Insights line switches from "268 anomalies" to "268 valid extreme values
     (exact quantity × price multiples)."

  2. column_risk_levels — collapses the per-(column, issue-type) quality breakdown to
     one row per column, showing the worst risk level and a comma-joined summary of
     all issue types.  Eliminates the duplicated rows (e.g. total_spent appearing
     three times) in the Dashboard Column Risk Levels table.

  3. recommended_action — conditional text that switches between:
       ✅ "Data cleaning complete — no further action required."        (< 5% missing)
       ⚠️ "Cleaning complete — remaining gaps require source data correction"  (≥ 5%)
     reflecting real analyst judgement rather than the static risk-level label.

Integration:
  • intelligent_outliers  → replaces detect_outliers() in data_validator.build_validation_issues
                            and insights_engine._anomalies
  • column_risk_levels    → called inside report_builder._build_dashboard_sheet when
                            writing the Column Risk Levels table
  • recommended_action    → called inside report_builder._build_dashboard_sheet when
                            writing the Recommended Action row
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# INTERNAL CONSTANTS
# ---------------------------------------------------------------------------

_RISK_ORDER: dict[str, int] = {"High": 2, "Medium": 1, "Low": 0}

# Arithmetic column defaults — must match the names produced by header
# standardisation so the validation works after coltradata_patch runs.
_DEFAULT_QTY   = "quantity"
_DEFAULT_PRICE = "price_per_unit"
_DEFAULT_TOTAL = "total_spent"

# Missing-rate threshold below which recommended_action returns the all-clear.
_CLEAN_THRESHOLD_PCT = 5.0


# ---------------------------------------------------------------------------
# 1. INTELLIGENT OUTLIER DETECTION
# ---------------------------------------------------------------------------

def intelligent_outliers(
    df: pd.DataFrame,
    qty:   str = _DEFAULT_QTY,
    price: str = _DEFAULT_PRICE,
    total: str = _DEFAULT_TOTAL,
    tolerance: float = 0.01,
) -> pd.DataFrame:
    """IQR outlier detection with arithmetic validation.

    For each numeric column, detects IQR outliers and then checks whether each
    flagged value is arithmetically consistent with the qty × price = total
    relationship.  Values that satisfy the equation (within *tolerance*) are
    reclassified as "Valid Extreme Value" — a large but genuine order — rather
    than "True Outlier".

    Columns that are not part of the arithmetic triple are classified as
    "True Outlier" or "Valid Extreme Value" based on IQR alone (no arithmetic
    context to validate against).

    Returns
    -------
    DataFrame with columns:
        Column | Issue Type | Classification | Issue Count | Total Rows

    The "Classification" column distinguishes:
        "True Outlier"       — statistically extreme AND not arithmetically justified
        "Valid Extreme Value" — statistically extreme BUT arithmetically consistent
    """
    has_arith = all(c in df.columns for c in [qty, price, total])
    arith_cols = {qty, price, total} if has_arith else set()

    rows: list[dict] = []
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
        outlier_mask  = (series < lower) | (series > upper)
        outlier_idx   = series[outlier_mask].index

        if len(outlier_idx) == 0:
            continue

        if has_arith and col in arith_cols:
            # Validate against qty × price = total for the outlier rows.
            # Only rows where all three columns are non-null can be validated;
            # the rest fall back to "True Outlier".
            subset = df.loc[outlier_idx, [qty, price, total]].dropna(
                subset=[qty, price, total]
            )
            expected = subset[qty] * subset[price]
            is_valid = (expected - subset[total]).abs() <= tolerance

            valid_idx    = is_valid[is_valid].index
            invalid_idx  = outlier_idx.difference(valid_idx)

            if len(valid_idx) > 0:
                rows.append({
                    "Column":         str(col),
                    "Issue Type":     "Outliers",
                    "Classification": "Valid Extreme Value",
                    "Issue Count":    len(valid_idx),
                    "Total Rows":     total_rows,
                })
            if len(invalid_idx) > 0:
                rows.append({
                    "Column":         str(col),
                    "Issue Type":     "Outliers",
                    "Classification": "True Outlier",
                    "Issue Count":    len(invalid_idx),
                    "Total Rows":     total_rows,
                })
        else:
            # No arithmetic context — treat all IQR outliers as true outliers.
            rows.append({
                "Column":         str(col),
                "Issue Type":     "Outliers",
                "Classification": "True Outlier",
                "Issue Count":    len(outlier_idx),
                "Total Rows":     total_rows,
            })

    cols = ["Column", "Issue Type", "Classification", "Issue Count", "Total Rows"]
    return pd.DataFrame(rows, columns=cols)


# ---------------------------------------------------------------------------
# 2. DE-DUPLICATED COLUMN RISK LEVELS
# ---------------------------------------------------------------------------

def column_risk_levels(quality_breakdown_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse a per-(column, issue-type) quality table to one row per column.

    Parameters
    ----------
    quality_breakdown_df : DataFrame produced by ReportBuilder._build_column_quality_breakdown.
        Expected columns: Column, Issue Type, Issue Count, Total Rows, Issue %,
        Weight, Weighted Score, Risk Level.

    Returns
    -------
    DataFrame with one row per column:
        Column | Risk Level | Issue Types | Total Issues

    "Risk Level" is the worst (highest) level across all issue types for that column.
    "Issue Types" is a comma-joined summary so the table remains human-readable.
    """
    if quality_breakdown_df.empty:
        return pd.DataFrame(columns=["Column", "Risk Level", "Issue Types", "Total Issues"])

    rows: list[dict] = []

    # Preserve original column order from the breakdown table.
    seen: dict[str, list] = {}
    for _, r in quality_breakdown_df.iterrows():
        col = str(r["Column"])
        if col not in seen:
            seen[col] = []
        seen[col].append(r)

    for col, group_rows in seen.items():
        worst_risk = max(
            (str(r["Risk Level"]) for r in group_rows),
            key=lambda lvl: _RISK_ORDER.get(lvl, 0),
        )
        issue_types  = ", ".join(str(r["Issue Type"]) for r in group_rows)
        total_issues = sum(int(r["Issue Count"]) for r in group_rows)
        rows.append({
            "Column":       col,
            "Risk Level":   worst_risk,
            "Issue Types":  issue_types,
            "Total Issues": total_issues,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. CONDITIONAL RECOMMENDED ACTION
# ---------------------------------------------------------------------------

def recommended_action(
    cleaned_df: pd.DataFrame,
    missing_threshold_pct: float = _CLEAN_THRESHOLD_PCT,
) -> str:
    """Return an expert-level recommended action string.

    Switches between two states based on the overall missing-cell rate:

    < threshold (default 5 %)
        ✅ "Data cleaning complete — no further action required."

    ≥ threshold
        ⚠️ "Cleaning complete — remaining gaps require source data correction"

    The threshold reflects the point at which all remaining gaps are source-side
    (e.g. location or payment_method never collected at entry) rather than fixable
    by further cleaning.  Adjust *missing_threshold_pct* to suit your data contract.
    """
    total_cells = cleaned_df.shape[0] * cleaned_df.shape[1]
    if total_cells == 0:
        return "✅ Data cleaning complete — no further action required."

    missing_cells = int(cleaned_df.isna().sum().sum())
    missing_pct   = 100 * missing_cells / total_cells

    if missing_pct < missing_threshold_pct:
        return "✅ Data cleaning complete — no further action required."

    return (
        "⚠️ Cleaning complete — remaining gaps require source data correction"
    )

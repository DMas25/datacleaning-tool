"""coltradata_patch.py
===================
Patch module for ColtraData.ai cleaning pipeline.

Fixes three issues identified in report ColtraDataAi_Cleaned_Report_20260612_0814:

  1. Sentinel values (ERROR, UNKNOWN, etc.) surviving the cleaning step,
     which also broke numeric type inference and disabled IQR outlier detection.
  2. Recoverable numeric gaps (Total = Quantity x Price) left unrepaired.
  3. Misleading log/summary entries ("Missing Value Handling: No Change",
     "Avg Issue Rate: 853.25%").

Usage (standalone):
    from core.coltradata_patch import run_patch_pipeline
    cleaned_df, report = run_patch_pipeline(df)

Usage (integrated): call the individual functions in this order inside
your existing cleaning pipeline, BEFORE type inference / quality checks:

    df, sentinel_log = normalise_sentinels(df)
    df, coercion_log = coerce_numeric(df, ["quantity", "price_per_unit", "total_spent"])
    df, recovery_log = recover_arithmetic(df, qty="quantity",
                                          price="price_per_unit",
                                          total="total_spent")
    df, item_log     = recover_item_from_price(df, item_col="item",
                                               price_col="price_per_unit")

No external dependencies beyond pandas / numpy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# 0. HEADER STANDARDISATION (mirrors the existing pipeline step, so this
#    module works whether it receives raw or already-standardised headers)
# ---------------------------------------------------------------------------

def standardise_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.strip("_")
    )
    return df


# ---------------------------------------------------------------------------
# 1. SENTINEL NORMALISATION
# ---------------------------------------------------------------------------

# Configurable. Comparison is case-insensitive after whitespace trimming.
DEFAULT_SENTINELS = [
    "ERROR", "UNKNOWN", "N/A", "NA", "NULL", "NONE", "-", "--", "?", "MISSING",
]


def normalise_sentinels(
    df: pd.DataFrame,
    sentinels: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replace sentinel strings with true NaN across all columns.

    Must run BEFORE type inference, missingness counts and outlier
    detection so that downstream steps see real nulls, not strings.

    Returns
    -------
    (df, log) where log is a per-column DataFrame:
        column | sentinels_replaced | blanks_before | true_missing_after
    """
    if sentinels is None:
        sentinels = DEFAULT_SENTINELS
    sentinel_set = {s.upper() for s in sentinels}

    df = df.copy()
    rows = []
    for col in df.columns:
        blanks_before = int(df[col].isna().sum())
        # Covers legacy object dtype AND pandas >=3.0 default 'str' dtype
        is_texty = pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])
        if is_texty:
            stripped = df[col].astype(str).str.strip()
            mask = stripped.str.upper().isin(sentinel_set)
            replaced = int(mask.sum())
            if replaced:
                df.loc[mask, col] = np.nan
            # Also convert empty strings to NaN
            empty_mask = stripped.eq("") & df[col].notna()
            df.loc[empty_mask, col] = np.nan
        else:
            replaced = 0
        rows.append(
            {
                "column": col,
                "sentinels_replaced": replaced,
                "blanks_before": blanks_before,
                "true_missing_after": int(df[col].isna().sum()),
            }
        )
    return df, pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 2. NUMERIC COERCION (restores dtype so IQR outlier detection can run)
# ---------------------------------------------------------------------------

def coerce_numeric(
    df: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert listed columns to numeric dtype after sentinel removal.

    Values that still fail to parse are set to NaN and counted in the log,
    so nothing is silently dropped.
    """
    df = df.copy()
    rows = []
    for col in columns:
        if col not in df.columns:
            continue
        before_non_null = int(df[col].notna().sum())
        df[col] = pd.to_numeric(df[col], errors="coerce")
        after_non_null = int(df[col].notna().sum())
        rows.append(
            {
                "column": col,
                "unparseable_set_to_nan": before_non_null - after_non_null,
                "dtype_after": str(df[col].dtype),
            }
        )
    return df, pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. ARITHMETIC RECOVERY  (Total = Quantity x Price)
# ---------------------------------------------------------------------------

def recover_arithmetic(
    df: pd.DataFrame,
    qty: str = "quantity",
    price: str = "price_per_unit",
    total: str = "total_spent",
    tolerance: float = 0.005,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Repair any one of {qty, price, total} when the other two are present.

    Exact recovery, not imputation:
        total  = qty * price
        qty    = total / price   (only kept if it lands on a near-integer)
        price  = total / qty

    Also flags rows where all three are present but inconsistent
    (|qty*price - total| > tolerance) WITHOUT altering them — those go to
    the log for human review.
    """
    df = df.copy()
    q, p, t = df[qty], df[price], df[total]

    # total missing, qty & price present
    m_total = t.isna() & q.notna() & p.notna()
    df.loc[m_total, total] = (q * p)[m_total]

    # price missing, qty & total present (avoid division by zero)
    m_price = p.isna() & q.notna() & t.notna() & (q != 0)
    df.loc[m_price, price] = (t / q)[m_price]

    # qty missing, price & total present — only accept near-integer results
    m_qty = q.isna() & p.notna() & t.notna() & (p != 0)
    candidate = (t / p)[m_qty]
    near_int = (candidate - candidate.round()).abs() < tolerance
    accepted_idx = candidate[near_int].index
    df.loc[accepted_idx, qty] = candidate[near_int].round()

    # consistency check on fully-populated rows
    full = df[qty].notna() & df[price].notna() & df[total].notna()
    inconsistent = full & (
        (df[qty] * df[price] - df[total]).abs() > tolerance
    )

    log = pd.DataFrame(
        [
            {"repair": f"{total} recovered (qty x price)", "rows": int(m_total.sum())},
            {"repair": f"{price} recovered (total / qty)", "rows": int(m_price.sum())},
            {"repair": f"{qty} recovered (total / price)", "rows": int(len(accepted_idx))},
            {"repair": f"{qty} candidates rejected (non-integer)", "rows": int(m_qty.sum() - len(accepted_idx))},
            {"repair": "inconsistent rows flagged for review (NOT altered)", "rows": int(inconsistent.sum())},
        ]
    )
    df["_arithmetic_inconsistent"] = inconsistent
    return df, log


# ---------------------------------------------------------------------------
# 4. ITEM RECOVERY FROM PRICE (unambiguous prices only)
# ---------------------------------------------------------------------------

def recover_item_from_price(
    df: pd.DataFrame,
    item_col: str = "item",
    price_col: str = "price_per_unit",
    min_share: float = 0.99,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fill missing item names where a price maps to exactly one item.

    The price->item map is learned from the data itself. A price is only
    used if a single item accounts for >= min_share of its labelled rows
    (default 99%), so ambiguous prices (e.g. two items both at 3.0) are
    never guessed.
    """
    df = df.copy()
    labelled = df[df[item_col].notna() & df[price_col].notna()]

    price_map: dict[float, str] = {}
    ambiguous: list[float] = []
    for pr, grp in labelled.groupby(price_col):
        counts = grp[item_col].value_counts(normalize=True)
        if counts.iloc[0] >= min_share:
            price_map[pr] = counts.index[0]
        else:
            ambiguous.append(pr)

    m = df[item_col].isna() & df[price_col].isin(price_map.keys())
    df.loc[m, item_col] = df.loc[m, price_col].map(price_map)

    log = pd.DataFrame(
        [
            {"detail": "items recovered from unambiguous prices", "value": int(m.sum())},
            {"detail": "unambiguous price points used", "value": len(price_map)},
            {"detail": "ambiguous prices skipped (no guessing)", "value": str(sorted(ambiguous))},
        ]
    )
    return df, log


# ---------------------------------------------------------------------------
# 5. CORRECTED SUMMARY METRICS (fixes the 853.25% bug + log wording)
# ---------------------------------------------------------------------------

def corrected_summary(df: pd.DataFrame) -> dict:
    """Build summary metrics with correct labels.

    Replaces:
      "Avg Issue Rate: 853.25%"  ->  "Avg Missing Cells per Column: 853.25"
                                     and a true "Avg Missing Rate: 8.53%"
      "Missing Value Handling: No Change"
        -> "X missing values detected and flagged (not imputed)"
    """
    total_cells = df.shape[0] * df.shape[1]
    missing_cells = int(df.isna().sum().sum())
    per_col = df.isna().sum()
    return {
        "rows": df.shape[0],
        "columns": df.shape[1],
        "missing_cells": missing_cells,
        "completeness_pct": round(100 * (1 - missing_cells / total_cells), 2),
        # Correctly-labelled versions of the old broken metric:
        "avg_missing_cells_per_column": round(per_col.mean(), 2),
        "avg_missing_rate_pct": round(100 * per_col.mean() / df.shape[0], 2),
        "cleaning_log_missing_entry": (
            f"{missing_cells:,} missing values detected and flagged "
            f"(not imputed)"
        ),
    }


# ---------------------------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------------------------

def run_patch_pipeline(
    df: pd.DataFrame,
    numeric_cols: list[str] | None = None,
    sentinels: list[str] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Run all patch steps in the correct order; returns (df, report dict)."""
    if numeric_cols is None:
        numeric_cols = ["quantity", "price_per_unit", "total_spent"]

    df = standardise_headers(df)
    df, sentinel_log = normalise_sentinels(df, sentinels)
    df, coercion_log = coerce_numeric(df, numeric_cols)
    df, recovery_log = recover_arithmetic(df)
    df, item_log = recover_item_from_price(df)
    summary = corrected_summary(df.drop(columns=["_arithmetic_inconsistent"]))

    report = {
        "sentinel_log": sentinel_log,
        "coercion_log": coercion_log,
        "recovery_log": recovery_log,
        "item_log": item_log,
        "summary": summary,
    }
    return df, report


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "input.xlsx"
    src = (
        pd.read_excel(path, sheet_name="Raw Data", skiprows=1)
        if path.lower().endswith((".xlsx", ".xlsm"))
        else pd.read_csv(path)
    )
    cleaned, rpt = run_patch_pipeline(src)
    print("=== SENTINEL LOG ===\n", rpt["sentinel_log"].to_string(index=False))
    print("\n=== NUMERIC COERCION ===\n", rpt["coercion_log"].to_string(index=False))
    print("\n=== ARITHMETIC RECOVERY ===\n", rpt["recovery_log"].to_string(index=False))
    print("\n=== ITEM RECOVERY ===\n", rpt["item_log"].to_string(index=False))
    print("\n=== CORRECTED SUMMARY ===")
    for k, v in rpt["summary"].items():
        print(f"  {k}: {v}")

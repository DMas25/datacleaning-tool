"""Core dataset cleaning engine for ColtraDataAi.

All transformation logic is isolated here so it can be unit-tested
independently and called from both the Streamlit UI and any future
batch/API surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from core.coltradata_patch import (
    normalise_sentinels,
    coerce_numeric,
    recover_arithmetic,
    recover_item_from_price,
)


@dataclass
class CleaningOptions:
    remove_duplicates:    bool = True
    trim_whitespace:      bool = True
    standardise_headers:  bool = True
    null_handling:        str  = "No Change"   # "No Change" | "Fill with blank" | "Fill with placeholder"
    dataset_type:         str  = "General"     # "General" | "Clinical Research"
    column_preset:        str  = ""            # accounting software preset (see core/presets.py)


@dataclass
class CleaningResult:
    cleaned_df:  pd.DataFrame
    log_df:      pd.DataFrame
    steps_taken: List[Dict]  = field(default_factory=list)


# Columns to attempt numeric coercion on after sentinel normalisation.
# Any column already numeric is skipped automatically by coerce_numeric().
_NUMERIC_COERCE_CANDIDATES = [
    "quantity", "price_per_unit", "total_spent",
    "amount", "value", "price", "cost", "revenue", "units",
]

# Arithmetic recovery column mapping — only runs when all three exist.
_ARITH_QTY   = "quantity"
_ARITH_PRICE = "price_per_unit"
_ARITH_TOTAL = "total_spent"

# Item recovery column names — only runs when both exist.
_ITEM_COL  = "item"
_PRICE_COL = "price_per_unit"


def apply_cleaning(df: pd.DataFrame, options: CleaningOptions) -> CleaningResult:
    """
    Apply the configured cleaning steps to *df* and return a CleaningResult
    containing the cleaned DataFrame, an operation log, and the step details.

    Step order (patch steps inserted between whitespace trimming and duplicate
    removal so they run on standardised, trimmed data but before deduplication
    and type-sensitive quality checks):

        1  File Loaded
        2  Header Standardisation
        3  Whitespace Trimming
        4  Sentinel Normalisation    ← patch: ERROR/UNKNOWN/N/A → NaN
        5  Numeric Coercion          ← patch: restores dtypes for IQR detection
        6  Arithmetic Recovery       ← patch: Total = Qty × Price gaps filled
        7  Item Recovery             ← patch: item names inferred from price
        8  Duplicate Removal
        9  Missing Value Handling
    """
    cleaned = df.copy()
    steps: List[Dict] = []

    # ── Step 1: File loaded ───────────────────────────────────────────────────
    steps.append({"Step": 1, "Action": "File Loaded", "Result": "Completed"})

    # ── Step 2: Header standardisation ───────────────────────────────────────
    if options.standardise_headers:
        cleaned.columns = [
            str(c).strip().replace(" ", "_").lower() for c in cleaned.columns
        ]
    steps.append({
        "Step":   2,
        "Action": "Header Standardisation",
        "Result": "Completed" if options.standardise_headers else "Skipped",
    })

    # ── Step 3: Whitespace trimming ───────────────────────────────────────────
    if options.trim_whitespace:
        cleaned = cleaned.apply(
            lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x)
        )
    steps.append({
        "Step":   3,
        "Action": "Whitespace Trimming",
        "Result": "Completed" if options.trim_whitespace else "Skipped",
    })

    # ── Step 4: Sentinel normalisation ───────────────────────────────────────
    # Converts ERROR, UNKNOWN, N/A, NULL, -, ? etc. to true NaN so that
    # downstream type inference and IQR outlier detection work correctly.
    cleaned, sentinel_log = normalise_sentinels(cleaned)
    total_replaced = int(sentinel_log["sentinels_replaced"].sum())
    steps.append({
        "Step":   4,
        "Action": "Sentinel Normalisation",
        "Result": (
            f"{total_replaced:,} sentinel value(s) converted to missing"
            if total_replaced
            else "No sentinel values detected"
        ),
    })

    # ── Step 5: Numeric coercion ──────────────────────────────────────────────
    # Restores numeric dtype on columns that held mixed text/number values
    # after sentinels have been cleared. Required for IQR outlier detection.
    coerce_targets = [c for c in _NUMERIC_COERCE_CANDIDATES if c in cleaned.columns]
    if coerce_targets:
        cleaned, coercion_log = coerce_numeric(cleaned, coerce_targets)
        unparseable = int(coercion_log["unparseable_set_to_nan"].sum())
        steps.append({
            "Step":   5,
            "Action": "Numeric Coercion",
            "Result": (
                f"{len(coerce_targets)} column(s) coerced; "
                f"{unparseable} unparseable value(s) set to missing"
            ),
        })
    else:
        steps.append({
            "Step": 5, "Action": "Numeric Coercion", "Result": "Skipped (no target columns)",
        })

    # ── Step 6: Arithmetic recovery ───────────────────────────────────────────
    # Fills any one of {quantity, price_per_unit, total_spent} when the other
    # two are present. Only runs when all three columns exist in the dataset.
    _arith_present = all(
        c in cleaned.columns for c in [_ARITH_QTY, _ARITH_PRICE, _ARITH_TOTAL]
    )
    if _arith_present:
        cleaned, recovery_log = recover_arithmetic(
            cleaned, qty=_ARITH_QTY, price=_ARITH_PRICE, total=_ARITH_TOTAL
        )
        recovered = recovery_log[recovery_log["repair"].str.contains("recovered")]["rows"].sum()
        flagged   = int(recovery_log.iloc[-1]["rows"])
        steps.append({
            "Step":   6,
            "Action": "Arithmetic Recovery",
            "Result": (
                f"{int(recovered):,} cell(s) recovered; "
                f"{flagged:,} inconsistent row(s) flagged for review"
            ),
        })
        # Drop internal flag column before any downstream steps see it
        cleaned = cleaned.drop(columns=["_arithmetic_inconsistent"], errors="ignore")
    else:
        steps.append({
            "Step": 6, "Action": "Arithmetic Recovery",
            "Result": "Skipped (qty/price/total columns not all present)",
        })

    # ── Step 7: Item recovery ─────────────────────────────────────────────────
    # Infers missing item names from unambiguous price-to-item mappings.
    # Only runs when both item and price_per_unit columns are present.
    _item_present = _ITEM_COL in cleaned.columns and _PRICE_COL in cleaned.columns
    if _item_present:
        cleaned, item_log = recover_item_from_price(
            cleaned, item_col=_ITEM_COL, price_col=_PRICE_COL
        )
        recovered_items = int(item_log[item_log["detail"] == "items recovered from unambiguous prices"]["value"].iloc[0])
        steps.append({
            "Step":   7,
            "Action": "Item Recovery",
            "Result": (
                f"{recovered_items:,} item name(s) recovered from price mapping"
                if recovered_items
                else "No recoverable item names found"
            ),
        })
    else:
        steps.append({
            "Step": 7, "Action": "Item Recovery",
            "Result": "Skipped (item/price columns not present)",
        })

    # ── Step 8: Duplicate removal ─────────────────────────────────────────────
    if options.remove_duplicates:
        cleaned = cleaned.drop_duplicates()
    steps.append({
        "Step":   8,
        "Action": "Duplicate Removal",
        "Result": "Completed" if options.remove_duplicates else "Skipped",
    })

    # ── Step 9: Missing value handling ───────────────────────────────────────
    if options.null_handling == "Fill with blank":
        cleaned = cleaned.fillna("")
    elif options.null_handling == "Fill with placeholder":
        cleaned = cleaned.fillna("MISSING")

    missing_count = int(cleaned.isnull().sum().sum())
    steps.append({
        "Step":   9,
        "Action": "Missing Value Handling",
        "Result": (
            f"{missing_count:,} missing values detected and flagged (not imputed)"
            if options.null_handling == "No Change"
            else options.null_handling
        ),
    })

    log_df = pd.DataFrame(steps)
    return CleaningResult(cleaned_df=cleaned, log_df=log_df, steps_taken=steps)


def diff_summary(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> Dict:
    """Convenience diff between raw and cleaned datasets."""
    return {
        "rows_original": len(raw_df),
        "rows_cleaned":  len(cleaned_df),
        "rows_removed":  len(raw_df) - len(cleaned_df),
        "cols_original": len(raw_df.columns),
        "cols_cleaned":  len(cleaned_df.columns),
    }

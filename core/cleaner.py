"""Core dataset cleaning engine for ColtraDataAi.

All transformation logic is isolated here so it can be unit-tested
independently and called from both the Streamlit UI and any future
batch/API surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd


@dataclass
class CleaningOptions:
    remove_duplicates:    bool = True
    trim_whitespace:      bool = True
    standardise_headers:  bool = True
    null_handling:        str  = "No Change"   # "No Change" | "Fill with blank" | "Fill with placeholder"


@dataclass
class CleaningResult:
    cleaned_df:  pd.DataFrame
    log_df:      pd.DataFrame
    steps_taken: List[Dict]  = field(default_factory=list)


def apply_cleaning(df: pd.DataFrame, options: CleaningOptions) -> CleaningResult:
    """
    Apply the configured cleaning steps to *df* and return a CleaningResult
    containing the cleaned DataFrame, an operation log, and the step details.
    """
    cleaned = df.copy()
    steps: List[Dict] = []

    # Step 1 is always "file loaded"
    steps.append({"Step": 1, "Action": "File Loaded", "Result": "Completed"})

    # Header standardisation
    if options.standardise_headers:
        cleaned.columns = [
            str(c).strip().replace(" ", "_").lower() for c in cleaned.columns
        ]
    steps.append({
        "Step":   2,
        "Action": "Header Standardisation",
        "Result": "Completed" if options.standardise_headers else "Skipped",
    })

    # Whitespace trimming
    if options.trim_whitespace:
        cleaned = cleaned.apply(
            lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x)
        )
    steps.append({
        "Step":   3,
        "Action": "Whitespace Trimming",
        "Result": "Completed" if options.trim_whitespace else "Skipped",
    })

    # Duplicate removal
    if options.remove_duplicates:
        cleaned = cleaned.drop_duplicates()
    steps.append({
        "Step":   4,
        "Action": "Duplicate Removal",
        "Result": "Completed" if options.remove_duplicates else "Skipped",
    })

    # Missing value handling
    if options.null_handling == "Fill with blank":
        cleaned = cleaned.fillna("")
    elif options.null_handling == "Fill with placeholder":
        cleaned = cleaned.fillna("MISSING")
    steps.append({
        "Step":   5,
        "Action": "Missing Value Handling",
        "Result": options.null_handling,
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

"""Cleaning rule definitions for ColtraDataAi.

Centralises all rule metadata so UI labels, log messages, and report
descriptions share a single source of truth.  Add new rules here; the
cleaner and log builder pick them up automatically by key.
"""
from __future__ import annotations

from typing import Dict

# Each rule: display name, description used in reports, default on/off
CLEANING_RULES: Dict[str, Dict] = {
    "standardise_headers": {
        "label":       "Standardise Headers",
        "description": "Strip whitespace, replace spaces with underscores, convert to lowercase.",
        "default":     True,
        "step":        2,
    },
    "trim_whitespace": {
        "label":       "Trim Whitespace",
        "description": "Remove leading/trailing whitespace from all string cell values.",
        "default":     True,
        "step":        3,
    },
    "remove_duplicates": {
        "label":       "Remove Duplicates",
        "description": "Drop exact-match duplicate rows, keeping the first occurrence.",
        "default":     True,
        "step":        4,
    },
}

# Missing-value handling options for the selectbox
NULL_HANDLING_OPTIONS = [
    "No Change",
    "Fill with blank",
    "Fill with placeholder",
]

NULL_HANDLING_DESCRIPTIONS: Dict[str, str] = {
    "No Change":             "Leave missing cells as null (NaN). Report flags counts only.",
    "Fill with blank":       "Replace all null values with an empty string (\"\").",
    "Fill with placeholder": "Replace all null values with the literal text 'MISSING'.",
}

# Issue weights used in risk scoring (higher = more severe)
ISSUE_WEIGHTS: Dict[str, float] = {
    "missing values":      1.0,
    "missing":             1.0,
    "nulls":               1.0,
    "duplicates":          0.9,
    "duplicate rows":      0.9,
    "invalid format":      1.2,
    "format":              1.2,
    "type mismatch":       1.2,
    "inconsistent values": 1.1,
    "inconsistent text":   1.1,
    "outliers":            0.8,
    "blank strings":       0.9,
    "invalid dates":       1.3,
    "invalid emails":      1.3,
    "invalid numbers":     1.2,
}

# Risk band thresholds
RISK_BANDS = {
    "High":   {"min_pct": 0.30, "min_weighted": 35},
    "Medium": {"min_pct": 0.10, "min_weighted": 12},
    "Low":    {"min_pct": 0.00, "min_weighted":  0},
}

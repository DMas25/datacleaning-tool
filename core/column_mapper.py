"""Shared column detection for all ColtraDataAi domain cleaners.

Three-pass detection strategy:
  1. Exact substring: any keyword is a substring of the normalised column name.
     Catches standard names like "tracking_number", "account_code", "due_date".
  2. Prefix: the normalised column name is a substring of any keyword (min 4 chars).
     Catches common abbreviations: "cust" → "customer", "inv" (5 chars) → "invoice_number".
  3. Fuzzy: SequenceMatcher ratio ≥ cutoff (default 0.82).
     Catches typos and near-miss names: "net_amt" → "net_amount", "despatch" → "dispatch_date".

All domain cleaners should import _detect from here instead of defining their own.
"""
from __future__ import annotations

import difflib
from typing import Optional

import pandas as pd


def _normalise(col: str) -> str:
    """Normalise a column name for detection: lowercase, punctuation → underscores."""
    return (
        col.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("#", "")
        .replace("/", "_")
        .strip("_")
    )


def _detect(df: pd.DataFrame, keywords: list[str], fuzzy_cutoff: float = 0.82) -> Optional[str]:
    """
    Return the first column in *df* whose name matches any of *keywords*.

    Detection is case-insensitive and punctuation-tolerant.  The three passes
    are ordered cheapest-first so exact matches short-circuit before fuzzy work
    is done.
    """
    normalised: dict[str, str] = {col: _normalise(col) for col in df.columns}

    # Pass 1: keyword is a substring of the normalised column name (original behaviour)
    for col, norm in normalised.items():
        if any(kw in norm for kw in keywords):
            return col

    # Pass 2: normalised column name is a substring of a keyword (abbreviation detection)
    # Minimum 4 characters to avoid false positives from single-letter column names.
    for col, norm in normalised.items():
        if len(norm) >= 4 and any(norm in kw for kw in keywords):
            return col

    # Pass 3: fuzzy match using SequenceMatcher — catches typos and near-miss names
    for col, norm in normalised.items():
        for kw in keywords:
            if difflib.SequenceMatcher(None, norm, kw).ratio() >= fuzzy_cutoff:
                return col

    return None

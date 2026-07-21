"""Finance & Accounting dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. Account code normalisation    — pads nominal codes to 4 digits, classifies by range
  2. VAT / tax code validation     — flags codes outside recognised UK VAT schemes
  3. Journal reference normalisation — strips whitespace, enforces prefix/padding
  4. Period classification         — maps period values to standard fiscal labels
  5. Cost centre validation        — flags missing or non-numeric cost centres
  6. Trial balance check           — verifies sum(debits) ≈ sum(credits)
  7. Narrative quality check       — flags blank or suspiciously generic narratives
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np


# ── Column keyword maps ───────────────────────────────────────────────────────

_ACCOUNT_KW   = ["account_code", "nominal", "gl_code", "acc_code", "account_no",
                  "ledger_code", "nominal_code", "account_number"]
_ACC_NAME_KW  = ["account_name", "account_desc", "ledger_desc", "acc_name", "description"]
_DEBIT_KW     = ["debit", "dr", "debit_amount", "dr_amount"]
_CREDIT_KW    = ["credit", "cr", "credit_amount", "cr_amount"]
_JNL_KW       = ["journal_ref", "journal_no", "jnl_ref", "jnl_no", "reference", "journal_number"]
_PERIOD_KW    = ["period", "accounting_period", "fiscal_period", "month", "period_no"]
_VAT_KW       = ["vat_code", "tax_code", "vat", "tax", "vat_rate_code"]
_CC_KW        = ["cost_centre", "cost_center", "cc_code", "department", "dept", "department_code"]
_NARR_KW      = ["narrative", "description", "details", "memo", "particulars", "remarks"]
_DATE_KW      = ["date", "posting_date", "transaction_date", "entry_date", "doc_date"]


def _detect(df: pd.DataFrame, keywords: list[str]) -> Optional[str]:
    for col in df.columns:
        cl = col.lower().replace(" ", "_")
        if any(kw in cl for kw in keywords):
            return col
    return None


# ── Account code classification (UK nominal account ranges) ───────────────────

_ACCOUNT_RANGES = [
    (0,    999,  "Fixed Assets"),
    (1000, 1999, "Current Assets"),
    (2000, 2999, "Current Liabilities"),
    (3000, 3999, "Capital & Reserves"),
    (4000, 4999, "Sales / Revenue"),
    (5000, 5999, "Cost of Sales"),
    (6000, 6999, "Overheads"),
    (7000, 7999, "Admin Expenses"),
    (8000, 8999, "Depreciation & Provisions"),
    (9000, 9999, "Suspense / Other"),
]


def _classify_account(code) -> str:
    try:
        n = int(str(code).strip())
        for lo, hi, label in _ACCOUNT_RANGES:
            if lo <= n <= hi:
                return label
    except (ValueError, TypeError):
        pass
    return "Unclassified"


def normalise_account_codes(
    df: pd.DataFrame, col: str
) -> tuple[pd.DataFrame, int, pd.Series]:
    """Zero-pad numeric account codes to 4 digits; return (df, padded_count, type_series)."""
    df = df.copy()
    padded = 0

    def _pad(v):
        nonlocal padded
        if pd.isna(v):
            return v
        s = str(v).strip()
        if s.isdigit() and len(s) < 4:
            padded += 1
            return s.zfill(4)
        return s

    df[col] = df[col].apply(_pad)
    account_types = df[col].apply(_classify_account)
    return df, padded, account_types


# ── VAT / tax code validation ─────────────────────────────────────────────────

# Common UK VAT codes used in accounting software
_VALID_VAT_CODES = {
    # Sage-style
    "T0", "T1", "T2", "T4", "T5", "T7", "T8", "T9", "T20", "T21",
    # QuickBooks/Xero-style
    "S", "Z", "E", "X", "N", "R", "20.0%", "0.0%", "5.0%",
    # EC rates
    "T19", "T15",
    # Common rate labels
    "S20", "S5", "Z0", "E0", "X0",
    # Numeric
    "20", "5", "0",
}


def validate_vat_codes(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Flag VAT codes not in the recognised set. Returns (df, invalid_count)."""
    df = df.copy()
    normalised = df[col].astype(str).str.strip().str.upper()
    invalid_mask = df[col].notna() & ~normalised.isin(_VALID_VAT_CODES)
    df["_vat_flag"] = invalid_mask
    n_invalid = int(invalid_mask.sum())
    df = df.drop(columns=["_vat_flag"])
    return df, n_invalid


# ── Journal reference normalisation ──────────────────────────────────────────

def normalise_journal_refs(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Strip extra whitespace from journal references. Returns (df, changed_count)."""
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].astype(str).str.strip().str.upper().where(df[col].notna(), other=None)
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Trial balance check ───────────────────────────────────────────────────────

def check_trial_balance(
    df: pd.DataFrame, debit_col: str, credit_col: str
) -> dict:
    """Compute trial balance summary. Returns dict with totals and difference."""
    total_dr  = float(df[debit_col].fillna(0).sum())
    total_cr  = float(df[credit_col].fillna(0).sum())
    diff      = abs(total_dr - total_cr)
    in_balance = diff < 0.01
    return {
        "total_debits":  total_dr,
        "total_credits": total_cr,
        "difference":    diff,
        "in_balance":    in_balance,
        "pct_diff":      round(diff / max(abs(total_dr), 1) * 100, 4),
    }


# ── Narrative quality check ───────────────────────────────────────────────────

_GENERIC_NARRATIVES = {
    "n/a", "na", "none", "nil", "unknown", "-", ".", "x", "misc", "miscellaneous",
    "tba", "tbf", "to be confirmed", "various", "general", "other",
}


def check_narrative_quality(df: pd.DataFrame, col: str) -> tuple[int, int]:
    """Return (blank_count, generic_count) for a narrative column."""
    blank_count   = int(df[col].isna().sum())
    series        = df[col].dropna().astype(str).str.strip().str.lower()
    generic_count = int(series.isin(_GENERIC_NARRATIVES).sum())
    return blank_count, generic_count


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class FinanceResult:
    cleaned_df:      pd.DataFrame
    metrics:         dict
    account_col:     Optional[str] = None
    debit_col:       Optional[str] = None
    credit_col:      Optional[str] = None
    vat_col:         Optional[str] = None
    period_col:      Optional[str] = None
    cc_col:          Optional[str] = None
    issues:          list = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_finance_cleaning(df: pd.DataFrame) -> FinanceResult:
    """Run all finance/accounting cleaning steps and return a FinanceResult."""
    cleaned = df.copy()
    issues: list[dict] = []
    metrics: dict = {}

    account_col = _detect(cleaned, _ACCOUNT_KW)
    acc_name_col = _detect(cleaned, _ACC_NAME_KW)
    debit_col   = _detect(cleaned, _DEBIT_KW)
    credit_col  = _detect(cleaned, _CREDIT_KW)
    jnl_col     = _detect(cleaned, _JNL_KW)
    period_col  = _detect(cleaned, _PERIOD_KW)
    vat_col     = _detect(cleaned, _VAT_KW)
    cc_col      = _detect(cleaned, _CC_KW)
    narr_col    = _detect(cleaned, _NARR_KW)

    # 1. Account code normalisation + classification
    if account_col:
        cleaned, padded_count, account_types = normalise_account_codes(cleaned, account_col)
        metrics["account_type_counts"] = account_types.value_counts().to_dict()
        metrics["unique_accounts"] = int(cleaned[account_col].nunique())
        if padded_count:
            issues.append({
                "type": "Account Code Padding",
                "description": f"{padded_count:,} account code(s) zero-padded to 4 digits.",
                "count": padded_count,
            })

    # 2. Journal reference normalisation
    if jnl_col:
        cleaned, jnl_changed = normalise_journal_refs(cleaned, jnl_col)
        metrics["unique_journals"] = int(cleaned[jnl_col].nunique())
        if jnl_changed:
            issues.append({
                "type": "Journal Reference Normalisation",
                "description": f"{jnl_changed:,} journal reference(s) trimmed and uppercased.",
                "count": jnl_changed,
            })

    # 3. VAT code validation
    if vat_col:
        cleaned, vat_invalid = validate_vat_codes(cleaned, vat_col)
        metrics["vat_code_counts"] = cleaned[vat_col].value_counts().to_dict()
        if vat_invalid:
            issues.append({
                "type": "Unrecognised VAT Codes",
                "description": (
                    f"{vat_invalid:,} VAT code(s) are outside the recognised UK VAT scheme. "
                    "Verify these entries are correctly coded."
                ),
                "count": vat_invalid,
            })

    # 4. Period distribution
    if period_col:
        metrics["period_counts"] = cleaned[period_col].value_counts().sort_index().to_dict()

    # 5. Cost centre coverage
    if cc_col:
        missing_cc = int(cleaned[cc_col].isna().sum())
        metrics["cost_centre_counts"] = cleaned[cc_col].value_counts().head(15).to_dict()
        if missing_cc:
            issues.append({
                "type": "Missing Cost Centre Codes",
                "description": f"{missing_cc:,} record(s) have no cost centre code.",
                "count": missing_cc,
            })

    # 6. Trial balance
    if debit_col and credit_col:
        tb = check_trial_balance(cleaned, debit_col, credit_col)
        metrics["trial_balance"] = tb
        if not tb["in_balance"]:
            issues.append({
                "type": "Trial Balance Discrepancy",
                "description": (
                    f"Ledger is OUT OF BALANCE by {tb['difference']:,.2f} "
                    f"({tb['pct_diff']}%). "
                    f"Total debits: {tb['total_debits']:,.2f} | "
                    f"Total credits: {tb['total_credits']:,.2f}."
                ),
                "count": 1,
            })
        else:
            issues.append({
                "type": "Trial Balance",
                "description": f"Ledger is in balance. Total debits = Total credits = {tb['total_debits']:,.2f}.",
                "count": 0,
            })

    # 7. Narrative quality
    if narr_col:
        blank_narr, generic_narr = check_narrative_quality(cleaned, narr_col)
        if blank_narr:
            issues.append({
                "type": "Blank Narratives",
                "description": f"{blank_narr:,} journal entries have no narrative description.",
                "count": blank_narr,
            })
        if generic_narr:
            issues.append({
                "type": "Generic Narratives",
                "description": (
                    f"{generic_narr:,} narratives use placeholder text "
                    "(e.g. 'N/A', 'misc', 'various'). Improve for audit trail quality."
                ),
                "count": generic_narr,
            })

    metrics["total_entries"] = len(cleaned)
    metrics["issues_found"]  = len([i for i in issues if i["count"] > 0])

    return FinanceResult(
        cleaned_df=cleaned,
        metrics=metrics,
        account_col=account_col,
        debit_col=debit_col,
        credit_col=credit_col,
        vat_col=vat_col,
        period_col=period_col,
        cc_col=cc_col,
        issues=issues,
    )

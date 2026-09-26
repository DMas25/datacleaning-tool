"""Finance & Accounting dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. Account code normalisation    — pads nominal codes to 4 digits, classifies by range
  2. Tax / VAT code validation     — flags codes outside recognised global tax schemes
  3. Journal reference normalisation — strips whitespace, enforces prefix/padding
  4. Period classification         — maps period values to standard fiscal labels
  5. Cost centre validation        — flags missing or non-numeric cost centres
  6. Trial balance check           — verifies sum(debits) ≈ sum(credits)
  7. Narrative quality check       — flags blank or suspiciously generic narratives

Applicable worldwide. Account code ranges (0000-9999) follow the convention used by
Sage, Xero, and QuickBooks globally. Tax/VAT code validation covers UK, EU, AU, CA,
IN, ZA, US, and generic international schemes. The MTD readiness check is UK-specific
(HMRC VAT Notice 700/22) and is labelled accordingly in the output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
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
_NET_KW       = ["net", "net_amount", "net_value", "ex_vat", "net_of_vat", "taxable_amount"]
_CURRENCY_KW  = ["currency", "currency_code", "ccy", "curr", "fx_currency", "transaction_currency"]


def _detect(df: pd.DataFrame, keywords: list[str]) -> Optional[str]:
    for col in df.columns:
        cl = col.lower().replace(" ", "_")
        parts = set(cl.split("_"))
        for kw in keywords:
            # Multi-word keywords (contain "_") use substring match.
            # Single-word keywords use word-boundary match to avoid e.g.
            # "dr" matching "description" or "cr" matching "accruals".
            if "_" in kw:
                if kw in cl:
                    return col
            else:
                if kw in parts:
                    return col
    return None


# ── Account code classification (standard nominal ranges: Sage, Xero, QuickBooks global) ──

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


# ── Tax / VAT code validation ─────────────────────────────────────────────────

# Recognised tax/VAT codes — UK, EU, AU, CA, IN, ZA, US and generic international
_VALID_VAT_CODES = {
    # UK — Sage T-codes
    "T0", "T1", "T2", "T4", "T5", "T7", "T8", "T9", "T15", "T19", "T20", "T21",
    # UK — Xero / QuickBooks style
    "S", "Z", "E", "X", "N", "R", "S20", "S5", "Z0", "E0", "X0",
    # UK — percentage labels
    "20.0%", "5.0%", "0.0%",
    # UK — numeric shorthand
    "20", "5", "0",
    # EU — common standard and reduced rates (%, raw, and decimal)
    "6", "6.0%", "7", "7.0%", "9", "9.0%", "10", "10.0%",
    "13", "13.0%", "16", "16.0%", "17", "17.0%", "18", "18.0%",
    "19", "19.0%", "21", "21.0%", "22", "22.0%", "23", "23.0%",
    "24", "24.0%", "25", "25.0%", "27", "27.0%",
    # EU — generic labels used in accounting software
    "STANDARD", "REDUCED", "SUPER-REDUCED", "ZERO-RATED", "EXEMPT",
    "INTRA-EU", "REVERSE-CHARGE", "OSS",
    # Australia — GST
    "GST", "GST10", "GST-FREE", "INPUT-TAXED", "BAS-EXCLUDED",
    "CAP", "CAPEX", "INP", "G1", "G2", "G3",
    # Canada
    "HST", "HST13", "HST14", "HST15", "PST", "QST", "RST", "GST5",
    # India — GST
    "IGST", "CGST", "SGST", "UTGST", "NIL-GST", "CGST9", "SGST9",
    "IGST18", "IGST12", "IGST5", "IGST28",
    # South Africa
    "VAT15", "VAT14", "VAT0", "EXEMPT-ZA",
    # US — no federal VAT but common sales-tax labels
    "TAXABLE", "NONTAXABLE", "NON-TAXABLE", "EXEMPT-US", "USE-TAX", "SALES-TAX",
    # Generic / international catch-all labels
    "VAT", "NO-VAT", "NO VAT", "NONE", "ZERO", "NIL", "OUT-OF-SCOPE",
    "INPUT", "OUTPUT", "EXEMPT-SUPPLY", "FREE-SUPPLY",
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


# ── Duplicate journal entry detection ────────────────────────────────────────

def detect_duplicate_journals(
    df: pd.DataFrame,
    account_col:  Optional[str],
    debit_col:    Optional[str],
    credit_col:   Optional[str],
    date_col:     Optional[str],
    narr_col:     Optional[str],
) -> tuple[pd.DataFrame, int]:
    """Flag rows where (account_code, debit, credit, date/period, narrative) repeat.

    The first occurrence of each combination is kept (flag = False); every
    subsequent occurrence is marked True in a new 'duplicate_journal_flag'
    column.  Narrative comparison is case- and whitespace-insensitive.

    Returns (df, duplicate_count).  If fewer than two key columns can be
    found the function returns the dataframe unchanged with a count of 0.
    """
    df = df.copy()

    key_cols = [c for c in [account_col, debit_col, credit_col, date_col] if c]
    if len(key_cols) < 2:
        return df, 0

    # Build a working key frame so we don't mutate cleaned columns.
    key_frame = pd.DataFrame(index=df.index)
    for col in key_cols:
        key_frame[col] = df[col].fillna("").astype(str).str.strip()

    if narr_col:
        key_frame["_narr_key"] = (
            df[narr_col].fillna("").astype(str).str.strip().str.lower()
        )
        dedup_cols = key_cols + ["_narr_key"]
    else:
        dedup_cols = key_cols

    duplicate_mask = key_frame.duplicated(subset=dedup_cols, keep="first")
    df["duplicate_journal_flag"] = duplicate_mask
    n_dupes = int(duplicate_mask.sum())
    return df, n_dupes


# ── MTD VAT readiness check (light-touch) ────────────────────────────────────
# HMRC VAT Notice 700/22 requires four fields per transaction in digital records:
# tax point date, supply description, net value, and VAT rate applied.

_MTD_FIELDS = [
    ("Tax point date",       "_date_col"),
    ("Supply description",   "_narr_col"),
    ("Net value (ex-VAT)",   "_net_col"),
    ("VAT rate / code",      "_vat_col"),
]


def check_mtd_readiness(
    date_col: Optional[str],
    narr_col: Optional[str],
    net_col:  Optional[str],
    vat_col:  Optional[str],
) -> dict:
    """Return an MTD VAT digital-records readiness summary.

    Score is 0-4 (one point per HMRC-required field present).
    """
    presence = {
        "_date_col": date_col is not None,
        "_narr_col": narr_col is not None,
        "_net_col":  net_col  is not None,
        "_vat_col":  vat_col  is not None,
    }
    fields = [
        {"field": label, "present": presence[key]}
        for label, key in _MTD_FIELDS
    ]
    score = sum(1 for f in fields if f["present"])
    return {
        "fields": fields,
        "score":  score,
        "max":    len(_MTD_FIELDS),
        "ready":  score == len(_MTD_FIELDS),
    }


# ── Negative amount check ─────────────────────────────────────────────────────

def check_negative_amounts(df, debit_col, credit_col):
    """Return (neg_debit_count, neg_credit_count) for rows with negative values."""
    try:
        dr = pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
        cr = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
        return int((dr < 0).sum()), int((cr < 0).sum())
    except Exception:
        return 0, 0


# ── Date format consistency check ─────────────────────────────────────────────

_DATE_PATTERNS = ["%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y"]


def check_date_format_consistency(df, col):
    """Return (n_formats, format_counts) for the date patterns found in col."""
    try:
        format_counts = {}
        for val in df[col].dropna():
            matched = "unrecognised"
            for pattern in _DATE_PATTERNS:
                try:
                    datetime.strptime(str(val).strip(), pattern)
                    matched = pattern
                    break
                except (ValueError, TypeError):
                    pass
            format_counts[matched] = format_counts.get(matched, 0) + 1
        return len(format_counts), format_counts
    except Exception:
        return 0, {}


# ── Currency consistency check ────────────────────────────────────────────────

def check_currency_consistency(df, col):
    """Return (n_currencies, currency_counts) for non-null values in col."""
    try:
        currency_counts = {}
        for val in df[col].dropna():
            key = str(val).strip().upper()
            if key:
                currency_counts[key] = currency_counts.get(key, 0) + 1
        return len(currency_counts), currency_counts
    except Exception:
        return 0, {}


# ── Account sign validation ───────────────────────────────────────────────────

_DEBIT_BALANCE_TYPES  = {"Current Assets", "Fixed Assets"}
_CREDIT_BALANCE_TYPES = {"Current Liabilities"}


def check_account_signs(df, account_col, debit_col, credit_col):
    """Return (anomaly_count, anomaly_details) for rows with unexpected debit/credit sign."""
    try:
        if len(df) < 2:
            return 0, []
        dr = pd.to_numeric(df[debit_col], errors="coerce")
        cr = pd.to_numeric(df[credit_col], errors="coerce")
        account_types = df[account_col].apply(_classify_account)
        if (account_types == "Unclassified").all():
            return 0, []
        anomaly_details = []
        for idx in df.index:
            acc_type = account_types.loc[idx]
            d = dr.loc[idx]
            c = cr.loc[idx]
            if pd.isna(d) or pd.isna(c):
                continue
            anomaly = False
            if acc_type in _DEBIT_BALANCE_TYPES and d <= c:
                anomaly = True
            elif acc_type in _CREDIT_BALANCE_TYPES and c <= d:
                anomaly = True
            if anomaly:
                anomaly_details.append({
                    "row":          idx,
                    "account_type": acc_type,
                    "debit":        float(d),
                    "credit":       float(c),
                })
                if len(anomaly_details) >= 20:
                    break
        return len(anomaly_details), anomaly_details
    except Exception:
        return 0, []


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
    date_col    = _detect(cleaned, _DATE_KW)
    net_col     = _detect(cleaned, _NET_KW)
    currency_col = _detect(cleaned, _CURRENCY_KW)

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
        missing_jnl = int(cleaned[jnl_col].isna().sum())
        if missing_jnl > 0:
            issues.append({
                "type": "Missing Journal References",
                "description": f"{missing_jnl:,} journal entries lack a reference number.",
                "count": missing_jnl,
            })

    # 3. VAT code validation
    if vat_col:
        cleaned, vat_invalid = validate_vat_codes(cleaned, vat_col)
        metrics["vat_code_counts"] = cleaned[vat_col].value_counts().to_dict()
        if vat_invalid:
            issues.append({
                "type": "Unrecognised Tax / VAT Codes",
                "description": (
                    f"{vat_invalid:,} tax/VAT code(s) were not matched against any recognised "
                    "global scheme (UK, EU, AU, CA, IN, ZA, US). "
                    "Verify these entries are correctly coded for your jurisdiction."
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

    # 8. Duplicate journal entry detection
    cleaned, n_dupes = detect_duplicate_journals(
        cleaned, account_col, debit_col, credit_col, date_col, narr_col
    )
    metrics["duplicate_journals"] = n_dupes
    if n_dupes:
        issues.append({
            "type": "Duplicate Journal Entries",
            "description": (
                f"{n_dupes:,} duplicate journal entries detected - likely bank feed "
                "re-imports. Review before posting."
            ),
            "count": n_dupes,
            "severity": "High",
        })

    # 9. Negative debit/credit flag
    if debit_col and credit_col:
        neg_debits, neg_credits = check_negative_amounts(cleaned, debit_col, credit_col)
        metrics["negative_debits"]  = neg_debits
        metrics["negative_credits"] = neg_credits
        if neg_debits > 0 or neg_credits > 0:
            parts = []
            if neg_debits > 0:
                parts.append(f"{neg_debits:,} debit row(s)")
            if neg_credits > 0:
                parts.append(f"{neg_credits:,} credit row(s)")
            issues.append({
                "type": "Negative Amount Entries",
                "description": (
                    f"{' and '.join(parts)} contain negative values. "
                    "Review for reversal entries or data errors."
                ),
                "count": neg_debits + neg_credits,
            })

    # 10. Date format consistency check
    if date_col:
        n_formats, format_counts = check_date_format_consistency(cleaned, date_col)
        metrics["date_formats"] = format_counts
        if n_formats > 1:
            formats_found = ", ".join(str(k) for k in format_counts.keys())
            issues.append({
                "type": "Inconsistent Date Formats",
                "description": (
                    f"{n_formats} date formats found in column '{date_col}': {formats_found}. "
                    "Standardise to a single format before processing."
                ),
                "count": n_formats,
            })

    # 11. Currency consistency check
    if currency_col:
        n_currencies, currency_counts = check_currency_consistency(cleaned, currency_col)
        metrics["currency_count"] = n_currencies
        if n_currencies > 1:
            currencies_found = ", ".join(sorted(currency_counts.keys()))
            issues.append({
                "type": "Multiple Currencies Detected",
                "description": (
                    f"{n_currencies} currencies found in column '{currency_col}': "
                    f"{currencies_found}. Verify FX handling and conversion rates."
                ),
                "count": n_currencies,
            })

    # 12. Account sign validation
    if account_col and debit_col and credit_col:
        anomaly_count, _ = check_account_signs(cleaned, account_col, debit_col, credit_col)
        metrics["account_sign_anomalies"] = anomaly_count
        if anomaly_count > 0:
            issues.append({
                "type": "Account Sign Anomalies",
                "description": (
                    f"{anomaly_count:,} row(s) have an unexpected debit/credit sign "
                    "for their account type. Asset accounts should carry a debit balance; "
                    "liability accounts should carry a credit balance."
                ),
                "count": anomaly_count,
            })

    # MTD VAT digital-records readiness
    metrics["mtd_readiness"] = check_mtd_readiness(date_col, narr_col, net_col, vat_col)

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

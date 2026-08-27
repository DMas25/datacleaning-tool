"""
Ledger analysis engine for accounting and bookkeeping datasets.

Detects file type from column signatures, then runs applicable audit checks:
- Benford's Law first-digit test
- Round number concentration (ISA 240 fraud indicator)
- Duplicate transaction detection
- Negative value analysis
- Debit/credit balance check (GL exports)
- Duplicate invoice numbers (invoice lists)
- Period-end transaction clustering
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class AuditFlag:
    severity: str                           # "high" | "medium" | "low" | "info"
    check: str                              # short check name
    finding: str                            # human-readable description
    count: int                              # affected records
    detail_df: Optional[pd.DataFrame] = None


@dataclass
class LedgerAnalysis:
    file_type: str                          # "gl" | "bank_statement" | "invoice_list" | "general"
    amount_col: Optional[str]
    date_col: Optional[str]
    flags: list[AuditFlag] = field(default_factory=list)
    benford_df: Optional[pd.DataFrame] = None


# ── Column keyword maps ───────────────────────────────────────────────────────

_AMOUNT_KW   = ["amount", "value", "total", "sum", "net", "gross", "price", "cost", "payment", "receipt", "turnover"]
_DATE_KW     = ["date", "period", "posted", "created", "transaction", "entry", "invoice_date", "doc_date"]
_DESC_KW     = ["desc", "narr", "note", "ref", "detail", "memo", "particulars", "remarks", "narrative"]
_INVOICE_KW  = ["invoice", "inv_no", "inv_num", "voucher", "bill_no", "invoice_number"]
_BALANCE_KW  = ["balance", "running", "closing", "opening"]
_DEBIT_KW    = ["debit", "dr", "debit_amount"]
_CREDIT_KW   = ["credit", "cr", "credit_amount"]
_ACCOUNT_KW  = ["account", "nominal", "ledger", "acc_no", "account_code", "gl_code"]


def _col_lower(col) -> str:
    return str(col).lower().replace(" ", "_")


def _has_any(col_lowers: list[str], keywords: list[str]) -> bool:
    return any(any(kw in c for kw in keywords) for c in col_lowers)


# ── File type detection ───────────────────────────────────────────────────────

def detect_file_type(df: pd.DataFrame) -> str:
    """Infer file type from column signatures."""
    cols = [_col_lower(c) for c in df.columns]

    has_debit   = _has_any(cols, _DEBIT_KW)
    has_credit  = _has_any(cols, _CREDIT_KW)
    has_account = _has_any(cols, _ACCOUNT_KW)
    has_balance = _has_any(cols, _BALANCE_KW)
    has_invoice = _has_any(cols, _INVOICE_KW)

    if has_debit and has_credit and has_account:
        return "gl"
    if has_balance and not has_invoice:
        return "bank_statement"
    if has_invoice:
        return "invoice_list"
    return "general"


def _best_amount_col(df: pd.DataFrame, file_type: str) -> Optional[str]:
    num_cols = list(df.select_dtypes(include=[np.number]).columns)
    if not num_cols:
        return None

    # For GL prefer a net/total column first
    priority = ["net", "total", "amount"] if file_type == "gl" else _AMOUNT_KW
    for kw in priority:
        for col in num_cols:
            if kw in _col_lower(col):
                return col

    return num_cols[0]


def _best_date_col(df: pd.DataFrame) -> Optional[str]:
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    for col in df.columns:
        if any(kw in _col_lower(col) for kw in _DATE_KW):
            return col
    return None


def _best_desc_col(df: pd.DataFrame) -> Optional[str]:
    for col in df.select_dtypes(include=["object"]).columns:
        if any(kw in _col_lower(col) for kw in _DESC_KW):
            return col
    return None


# ── Benford's Law ─────────────────────────────────────────────────────────────

_BENFORD_EXPECTED = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


def _first_digit(x: float) -> int:
    if x <= 0:
        return 0
    exp = math.floor(math.log10(x))
    d = x / (10 ** exp)
    return min(9, max(1, int(d)))


def _run_benford(
    df: pd.DataFrame, amount_col: str
) -> tuple[Optional[AuditFlag], Optional[pd.DataFrame]]:
    series = df[amount_col].dropna()
    series = series[series > 0]
    if len(series) < 50:
        flag = AuditFlag(
            "info", "Benford's Law",
            f"Insufficient data for Benford analysis (need ≥ 50 positive values; found {len(series)}).",
            len(series),
        )
        return flag, None

    first_digits = series.apply(_first_digit)
    first_digits = first_digits[(first_digits >= 1) & (first_digits <= 9)]
    total = len(first_digits)
    observed_counts = first_digits.value_counts().sort_index()

    rows = []
    chi2 = 0.0
    for d in range(1, 10):
        obs = int(observed_counts.get(d, 0))
        exp = _BENFORD_EXPECTED[d] * total
        obs_pct = round((obs / total) * 100, 1)
        exp_pct = round(_BENFORD_EXPECTED[d] * 100, 1)
        rows.append({
            "Digit":        d,
            "Observed %":   obs_pct,
            "Expected %":   exp_pct,
            "Deviation %":  round(obs_pct - exp_pct, 1),
        })
        if exp > 0:
            chi2 += ((obs - exp) ** 2) / exp

    benford_df = pd.DataFrame(rows)

    # χ² critical values (df=8): p<0.05 → 15.51, p<0.01 → 20.09
    if chi2 > 20.09:
        severity = "high"
        finding = (
            f"First-digit distribution in '{amount_col}' deviates significantly from "
            f"Benford's Law (χ² = {chi2:.1f}, p < 0.01). This may indicate data "
            "manipulation, unusual business processes, or a non-organic data source."
        )
    elif chi2 > 15.51:
        severity = "medium"
        finding = (
            f"First-digit distribution in '{amount_col}' shows moderate deviation from "
            f"Benford's Law (χ² = {chi2:.1f}, p < 0.05). Review for unusual transaction patterns."
        )
    else:
        severity = "info"
        finding = (
            f"First-digit distribution in '{amount_col}' is consistent with Benford's Law "
            f"(χ² = {chi2:.1f}). No statistical anomaly detected."
        )

    return AuditFlag(severity=severity, check="Benford's Law", finding=finding, count=total), benford_df


# ── Round number test ─────────────────────────────────────────────────────────

def _run_round_number_test(df: pd.DataFrame, amount_col: str) -> AuditFlag:
    series = df[amount_col].dropna().abs()
    total = len(series)
    if total == 0:
        return AuditFlag("info", "Round Number Test", "No data to analyse.", 0)

    round_100  = int((series % 100  == 0).sum())
    round_1000 = int((series % 1000 == 0).sum())
    pct_100    = round((round_100  / total) * 100, 1)
    pct_1000   = round((round_1000 / total) * 100, 1)

    if pct_100 > 40:
        severity = "high"
        finding = (
            f"{pct_100}% of values in '{amount_col}' are exact multiples of 100 "
            f"({pct_1000}% are multiples of 1,000). Unusually high round-number "
            "concentration is a recognised fraud indicator (ISA 240)."
        )
    elif pct_100 > 20:
        severity = "medium"
        finding = (
            f"{pct_100}% of values in '{amount_col}' are exact multiples of 100 "
            f"({pct_1000}% are multiples of 1,000). Elevated round-number concentration."
        )
    else:
        severity = "info"
        finding = (
            f"{pct_100}% of values in '{amount_col}' are exact multiples of 100. "
            "Round-number concentration is within normal range."
        )

    return AuditFlag(severity=severity, check="Round Number Test", finding=finding, count=round_100)


# ── Duplicate transaction detection ──────────────────────────────────────────

def _run_duplicate_transactions(
    df: pd.DataFrame,
    amount_col: str,
    date_col: Optional[str],
    desc_col: Optional[str],
) -> AuditFlag:
    subset = [amount_col]
    if date_col:
        subset.append(date_col)
    if desc_col:
        subset.append(desc_col)

    dupes = df[df.duplicated(subset=subset, keep=False)]
    n = len(dupes)

    if n == 0:
        return AuditFlag(
            "info", "Duplicate Transactions",
            "No duplicate transactions detected across amount, date, and description.",
            0,
        )

    pct = round((n / len(df)) * 100, 1)
    severity = "high" if pct > 5 else ("medium" if pct > 1 else "low")
    detail = dupes[subset].drop_duplicates().head(20)

    return AuditFlag(
        severity=severity,
        check="Duplicate Transactions",
        finding=(
            f"{n:,} transaction(s) ({pct}% of records) share identical values across "
            "amount, date, and description — potential duplicate postings."
        ),
        count=n,
        detail_df=detail,
    )


# ── Negative value analysis ───────────────────────────────────────────────────

def _run_negative_values(
    df: pd.DataFrame, amount_col: str, file_type: str
) -> Optional[AuditFlag]:
    if file_type == "gl":
        return None  # GL legitimately carries both signs

    series = df[amount_col].dropna()
    negatives = series[series < 0]
    n = len(negatives)
    if n == 0:
        return None

    pct = round((n / len(series)) * 100, 1)
    severity = "medium" if pct > 10 else "low"

    return AuditFlag(
        severity=severity,
        check="Negative Value Analysis",
        finding=(
            f"{n:,} value(s) ({pct}%) in '{amount_col}' are negative. "
            "Review for reversals, refunds, or data entry errors."
        ),
        count=n,
    )


# ── GL debit/credit balance check ─────────────────────────────────────────────

def _run_gl_balance(df: pd.DataFrame) -> Optional[AuditFlag]:
    debit_col = credit_col = None
    for col in df.columns:
        cl = _col_lower(col)
        if pd.api.types.is_numeric_dtype(df[col]):
            if any(kw in cl for kw in _DEBIT_KW) and not debit_col:
                debit_col = col
            if any(kw in cl for kw in _CREDIT_KW) and not credit_col:
                credit_col = col

    if not debit_col or not credit_col:
        return None

    total_dr = df[debit_col].fillna(0).sum()
    total_cr = df[credit_col].fillna(0).sum()
    diff = abs(total_dr - total_cr)
    max_val = max(abs(total_dr), abs(total_cr), 1)
    pct_diff = (diff / max_val) * 100

    if diff < 0.01:
        return AuditFlag(
            "info", "Debit/Credit Balance",
            f"Ledger is in balance. Total debits = Total credits = {total_dr:,.2f}.",
            0,
        )

    severity = "high" if pct_diff > 1 else "medium"
    return AuditFlag(
        severity=severity,
        check="Debit/Credit Balance",
        finding=(
            f"Ledger is OUT OF BALANCE by {diff:,.2f} ({pct_diff:.2f}%). "
            f"Total debits: {total_dr:,.2f} | Total credits: {total_cr:,.2f}."
        ),
        count=1,
    )


# ── Duplicate invoice numbers ─────────────────────────────────────────────────

def _run_duplicate_invoices(df: pd.DataFrame) -> Optional[AuditFlag]:
    inv_col = None
    for col in df.columns:
        if any(kw in _col_lower(col) for kw in _INVOICE_KW):
            inv_col = col
            break

    if not inv_col:
        return None

    series = df[inv_col].dropna()
    dupes = series[series.duplicated(keep=False)]
    n = len(dupes)

    if n == 0:
        return AuditFlag("info", "Duplicate Invoice Numbers", "No duplicate invoice numbers detected.", 0)

    pct = round((n / len(series)) * 100, 1)
    severity = "high" if pct > 5 else "medium"

    return AuditFlag(
        severity=severity,
        check="Duplicate Invoice Numbers",
        finding=(
            f"{n:,} invoice(s) ({pct}%) share a duplicate number in '{inv_col}'. "
            "Verify these are not duplicate payments."
        ),
        count=n,
        detail_df=df.loc[dupes.index, [inv_col]].drop_duplicates().head(20),
    )


# ── Period-end clustering ─────────────────────────────────────────────────────

def _run_period_end_clustering(df: pd.DataFrame, date_col: str) -> Optional[AuditFlag]:
    try:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    except Exception:
        return None

    if len(dates) < 20:
        return None

    is_period_end = dates.dt.day >= (dates.dt.days_in_month - 2)
    n = int(is_period_end.sum())
    pct = round((n / len(dates)) * 100, 1)

    # Statistically ~10% of transactions fall in the last 3 days; flag >25%
    if pct <= 25:
        return None

    return AuditFlag(
        severity="medium",
        check="Period-End Clustering",
        finding=(
            f"{n:,} transactions ({pct}%) fall in the last 3 days of their respective months. "
            "Unusual period-end concentration — review for cut-off manipulation."
        ),
        count=n,
    )


# ── Main entry point ──────────────────────────────────────────────────────────

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def analyse_ledger(df: pd.DataFrame) -> LedgerAnalysis:
    """Run all applicable audit checks and return a LedgerAnalysis."""
    file_type  = detect_file_type(df)
    amount_col = _best_amount_col(df, file_type)
    date_col   = _best_date_col(df)
    desc_col   = _best_desc_col(df)

    flags: list[AuditFlag] = []
    benford_df = None

    if amount_col:
        bf_flag, benford_df = _run_benford(df, amount_col)
        if bf_flag:
            flags.append(bf_flag)

        flags.append(_run_round_number_test(df, amount_col))
        flags.append(_run_duplicate_transactions(df, amount_col, date_col, desc_col))

        neg = _run_negative_values(df, amount_col, file_type)
        if neg:
            flags.append(neg)

    if file_type == "gl":
        gl = _run_gl_balance(df)
        if gl:
            flags.append(gl)

    if file_type == "invoice_list":
        inv = _run_duplicate_invoices(df)
        if inv:
            flags.append(inv)

    if date_col:
        pec = _run_period_end_clustering(df, date_col)
        if pec:
            flags.append(pec)

    flags.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 4))

    return LedgerAnalysis(
        file_type=file_type,
        amount_col=amount_col,
        date_col=date_col,
        flags=flags,
        benford_df=benford_df,
    )

"""SME (Small & Medium Enterprise) dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass for general small business operational data:
  1. UK postcode validation    — regex conformance (format only, no Royal Mail lookup)
  2. NI number validation      — AB123456C pattern, invalid prefix detection
  3. VAT number validation     — GB + 9 digits, or GB + GD/HA + 3 digits (govt/health)
  4. Companies House number    — 8-character, zero-padded
  5. Overdue invoice detection — due date in the past, no payment date recorded
  6. Phone number standardisation — UK numbers → +44 E.164 format
  7. Payment terms normalisation  — Net 30, Net 60, etc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd

from core.column_mapper import _detect  # noqa: F401


# ── Column keyword maps ───────────────────────────────────────────────────────

_POSTCODE_KW    = ["postcode", "post_code", "postal_code", "zip",
                    # Xero / QuickBooks
                    "zip_code", "postal"]
_NI_KW          = ["ni_number", "national_insurance", "ni_no", "nino",
                    "ni_num", "national_ins"]
_VAT_KW         = ["vat_number", "vat_reg", "vat_no", "vat_registration",
                    "vat_reg_no"]
_CH_KW          = ["company_number", "companies_house", "co_number",
                    "company_no", "crn", "registered_number"]
_INV_NO_KW      = ["invoice_number", "invoice_no", "inv_no", "invoice_ref",
                    "inv_number",
                    # Xero / Sage / QuickBooks
                    "invoice", "bill_no", "bill_number", "bill_ref", "txn_number",
                    "transaction_no", "document_no", "doc_no"]
_INV_DATE_KW    = ["invoice_date", "inv_date", "date_of_invoice",
                    # Xero / Sage
                    "bill_date", "transaction_date", "txn_date", "doc_date",
                    "issued_date", "raised_date"]
_DUE_DATE_KW    = ["due_date", "payment_due", "due", "date_due",
                    "payment_due_date",
                    # Xero / QuickBooks
                    "expiry_date", "due_by"]
_PAYMENT_DATE_KW= ["payment_date", "paid_date", "date_paid", "settled_date",
                    "cleared_date",
                    # Xero / Sage
                    "payment_received", "receipt_date", "date_cleared"]
_AMOUNT_KW      = ["amount", "invoice_amount", "total", "value",
                    "net_amount", "gross_amount", "subtotal",
                    # Xero / Sage / QuickBooks
                    "amount_due", "balance_due", "outstanding", "amt",
                    "net", "gross", "balance", "line_amount"]
_PHONE_KW       = ["phone", "telephone", "mobile", "tel", "contact_no",
                    "phone_number", "mob",
                    # Common abbreviations
                    "ph", "cell", "fax", "contact_phone"]
_TERMS_KW       = ["payment_terms", "terms", "credit_terms", "net_terms",
                    # Xero
                    "default_terms", "credit_limit"]
_CUSTOMER_KW    = ["customer", "client", "customer_name", "client_name",
                    "debtor", "account_name",
                    # Xero / Sage: "Contact" is the standard field name
                    "contact", "contact_name", "payee", "payer",
                    "supplier", "vendor"]


# ── UK postcode validation ────────────────────────────────────────────────────

_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][ABD-HJLNP-UW-Z]{2}$",
    re.IGNORECASE,
)


def validate_postcodes(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Normalise postcode case and return (df, invalid_count)."""
    df = df.copy()
    df[col] = (
        df[col].astype(str).str.strip().str.upper()
        .where(df[col].notna(), other=None)
    )
    invalid = int(
        df[col].dropna()
        .apply(lambda v: not bool(_POSTCODE_RE.match(str(v).strip())))
        .sum()
    )
    return df, invalid


# ── NI number validation ──────────────────────────────────────────────────────

_NI_RE = re.compile(r"^[A-CEGHJ-PR-TW-Z]{1}[A-CEGHJ-NPR-TW-Z]{1}\d{6}[A-D]$", re.IGNORECASE)

# Prefixes that are never issued
_NI_INVALID_PREFIXES = {"BG", "GB", "KN", "NK", "NT", "TN", "ZZ"}


def validate_ni_numbers(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Uppercase NI numbers and return (df, invalid_count)."""
    df = df.copy()
    df[col] = (
        df[col].astype(str).str.strip().str.upper().str.replace(" ", "")
        .where(df[col].notna(), other=None)
    )

    def _is_valid(v) -> bool:
        if pd.isna(v):
            return True
        s = str(v).strip().replace(" ", "").upper()
        if not _NI_RE.match(s):
            return False
        if s[:2] in _NI_INVALID_PREFIXES:
            return False
        return True

    invalid = int(df[col].dropna().apply(lambda v: not _is_valid(v)).sum())
    return df, invalid


# ── VAT number validation ─────────────────────────────────────────────────────

_VAT_STANDARD_RE = re.compile(r"^GB\d{9}(\d{3})?$", re.IGNORECASE)
_VAT_GOVHEALTH_RE = re.compile(r"^GB(GD|HA)\d{3}$", re.IGNORECASE)


def validate_vat_numbers(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Normalise VAT numbers (strip spaces/dashes) and return (df, invalid_count)."""
    df = df.copy()
    df[col] = (
        df[col].astype(str).str.strip().str.replace(r"[\s\-]", "", regex=True).str.upper()
        .where(df[col].notna(), other=None)
    )

    def _is_valid(v) -> bool:
        if pd.isna(v):
            return True
        s = str(v).strip()
        return bool(_VAT_STANDARD_RE.match(s) or _VAT_GOVHEALTH_RE.match(s))

    invalid = int(df[col].dropna().apply(lambda v: not _is_valid(v)).sum())
    return df, invalid


# ── Companies House number ────────────────────────────────────────────────────

_CH_ALPHA_PREFIX = re.compile(r"^[A-Z]{2}", re.IGNORECASE)


def validate_companies_house(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Zero-pad numeric Companies House numbers to 8 chars; return (df, invalid_count)."""
    df = df.copy()

    def _normalise(v):
        if pd.isna(v):
            return v
        s = str(v).strip().upper()
        if _CH_ALPHA_PREFIX.match(s):
            return s  # prefix + digits (e.g. SC123456)
        if s.isdigit():
            return s.zfill(8)
        return s

    original = df[col].copy()
    df[col] = df[col].apply(_normalise)

    def _is_valid(v) -> bool:
        if pd.isna(v):
            return True
        s = str(v).strip()
        if len(s) != 8:
            return False
        if _CH_ALPHA_PREFIX.match(s):
            return s[2:].isdigit()
        return s.isdigit()

    invalid = int(df[col].dropna().apply(lambda v: not _is_valid(v)).sum())
    return df, invalid


# ── Overdue invoice detection ─────────────────────────────────────────────────

def detect_overdue_invoices(
    df: pd.DataFrame, due_col: str, payment_col: Optional[str]
) -> tuple[int, float]:
    """Return (overdue_count, avg_days_overdue)."""
    today = pd.Timestamp(date.today())
    due_dates = pd.to_datetime(df[due_col], errors="coerce")

    if payment_col and payment_col in df.columns:
        unpaid = df[payment_col].isna() | (df[payment_col].astype(str).str.strip() == "")
        overdue_mask = due_dates.notna() & (due_dates < today) & unpaid
    else:
        overdue_mask = due_dates.notna() & (due_dates < today)

    overdue_count = int(overdue_mask.sum())
    days_overdue  = (today - due_dates[overdue_mask]).dt.days
    avg_days      = float(days_overdue.mean()) if overdue_count else 0.0
    return overdue_count, round(avg_days, 1)


# ── Phone number standardisation ──────────────────────────────────────────────

_UK_PHONE_STRIP = re.compile(r"[\s\-\(\)\.]")


def standardise_uk_phones(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Convert UK phone numbers to +44 E.164 format where possible."""
    df = df.copy()
    original = df[col].copy()

    def _format(v):
        if pd.isna(v):
            return v
        s = _UK_PHONE_STRIP.sub("", str(v).strip())
        if s.startswith("+44"):
            return s
        if s.startswith("0044"):
            return "+44" + s[4:]
        if s.startswith("07") or s.startswith("01") or s.startswith("02") or s.startswith("08"):
            return "+44" + s[1:]
        return str(v).strip()  # non-UK number — return as-is

    df[col] = df[col].apply(_format)
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Payment terms normalisation ───────────────────────────────────────────────

_TERMS_MAP: dict[str, str] = {
    "net 7": "Net 7", "7 days": "Net 7", "7days": "Net 7",
    "net 14": "Net 14", "14 days": "Net 14",
    "net 30": "Net 30", "30 days": "Net 30", "30days": "Net 30",
    "net 45": "Net 45", "45 days": "Net 45",
    "net 60": "Net 60", "60 days": "Net 60", "60days": "Net 60",
    "net 90": "Net 90", "90 days": "Net 90",
    "immediate": "Immediate", "cod": "Immediate", "cash on delivery": "Immediate",
    "prepay": "Prepayment", "advance": "Prepayment", "upfront": "Prepayment",
    "eom": "End of Month", "end of month": "End of Month",
    "due on receipt": "Due on Receipt", "on receipt": "Due on Receipt",
}


def normalise_payment_terms(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = (
        df[col].astype(str).str.strip().str.lower()
        .map(lambda v: _TERMS_MAP.get(v, v.title() if v not in ("nan", "") else None))
    )
    df.loc[original.isna(), col] = None
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class SMEResult:
    cleaned_df:      pd.DataFrame
    metrics:         dict
    postcode_col:    Optional[str] = None
    ni_col:          Optional[str] = None
    vat_col:         Optional[str] = None
    ch_col:          Optional[str] = None
    due_col:         Optional[str] = None
    payment_col:     Optional[str] = None
    phone_col:       Optional[str] = None
    terms_col:       Optional[str] = None
    issues:          list = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_sme_cleaning(df: pd.DataFrame) -> SMEResult:
    """Run all SME cleaning steps and return an SMEResult."""
    cleaned = df.copy()
    issues: list[dict] = []
    metrics: dict = {}

    postcode_col = _detect(cleaned, _POSTCODE_KW)
    ni_col       = _detect(cleaned, _NI_KW)
    vat_col      = _detect(cleaned, _VAT_KW)
    ch_col       = _detect(cleaned, _CH_KW)
    inv_no_col   = _detect(cleaned, _INV_NO_KW)
    due_col      = _detect(cleaned, _DUE_DATE_KW)
    payment_col  = _detect(cleaned, _PAYMENT_DATE_KW)
    amount_col   = _detect(cleaned, _AMOUNT_KW)
    phone_col    = _detect(cleaned, _PHONE_KW)
    terms_col    = _detect(cleaned, _TERMS_KW)
    customer_col = _detect(cleaned, _CUSTOMER_KW)

    # 1. UK postcode validation
    if postcode_col:
        cleaned, pc_invalid = validate_postcodes(cleaned, postcode_col)
        if pc_invalid:
            issues.append({
                "type": "Invalid UK Postcodes",
                "description": (
                    f"{pc_invalid:,} postcode(s) do not match UK postcode format — "
                    "may cause mail, delivery or geographic reporting issues."
                ),
                "count": pc_invalid,
            })

    # 2. NI number validation
    if ni_col:
        cleaned, ni_invalid = validate_ni_numbers(cleaned, ni_col)
        if ni_invalid:
            issues.append({
                "type": "Invalid NI Numbers",
                "description": (
                    f"{ni_invalid:,} National Insurance number(s) do not match the "
                    "standard AB123456C format — verify against HMRC records."
                ),
                "count": ni_invalid,
            })

    # 3. VAT number validation
    if vat_col:
        cleaned, vat_invalid = validate_vat_numbers(cleaned, vat_col)
        if vat_invalid:
            issues.append({
                "type": "Invalid VAT Numbers",
                "description": (
                    f"{vat_invalid:,} VAT number(s) do not match GB format — "
                    "check against HMRC VAT register."
                ),
                "count": vat_invalid,
            })

    # 4. Companies House number
    if ch_col:
        cleaned, ch_invalid = validate_companies_house(cleaned, ch_col)
        metrics["unique_companies"] = int(cleaned[ch_col].nunique())
        if ch_invalid:
            issues.append({
                "type": "Invalid Companies House Numbers",
                "description": f"{ch_invalid:,} company number(s) are not 8 characters long.",
                "count": ch_invalid,
            })

    # 5. Invoice amounts
    if amount_col:
        amounts = pd.to_numeric(cleaned[amount_col], errors="coerce")
        metrics["total_invoice_value"] = round(float(amounts.sum()), 2)
        metrics["avg_invoice_value"]   = round(float(amounts.mean()), 2) if amounts.notna().any() else None
        neg_amounts = int((amounts < 0).sum())
        if neg_amounts:
            issues.append({
                "type": "Negative Invoice Amounts",
                "description": f"{neg_amounts:,} invoice(s) have a negative amount — may represent credit notes.",
                "count": neg_amounts,
            })

    # 6. Overdue invoices
    if due_col:
        overdue_count, avg_days_overdue = detect_overdue_invoices(cleaned, due_col, payment_col)
        metrics["overdue_invoices"]   = overdue_count
        metrics["avg_days_overdue"]   = avg_days_overdue
        if overdue_count:
            issues.append({
                "type": "Overdue Invoices",
                "description": (
                    f"{overdue_count:,} invoice(s) are past their due date with no payment recorded "
                    f"(average {avg_days_overdue:.0f} days overdue)."
                ),
                "count": overdue_count,
            })

    # 7. Phone number standardisation
    if phone_col:
        cleaned, phone_changed = standardise_uk_phones(cleaned, phone_col)
        if phone_changed:
            issues.append({
                "type": "Phone Number Standardisation",
                "description": f"{phone_changed:,} UK phone number(s) converted to +44 E.164 format.",
                "count": phone_changed,
            })

    # 8. Payment terms normalisation
    if terms_col:
        cleaned, terms_changed = normalise_payment_terms(cleaned, terms_col)
        metrics["terms_counts"] = cleaned[terms_col].value_counts().to_dict()
        if terms_changed:
            issues.append({
                "type": "Payment Terms Normalisation",
                "description": f"{terms_changed:,} payment terms value(s) standardised.",
                "count": terms_changed,
            })

    # 9. Customer distribution
    if customer_col:
        metrics["customer_counts"]  = cleaned[customer_col].value_counts().head(10).to_dict()
        metrics["unique_customers"] = int(cleaned[customer_col].nunique())

    # 10. Duplicate invoice numbers
    if inv_no_col:
        dup_inv = int(cleaned[inv_no_col].duplicated(keep=False).sum())
        if dup_inv:
            issues.append({
                "type": "Duplicate Invoice Numbers",
                "description": (
                    f"{dup_inv:,} record(s) share a duplicate invoice number — "
                    "may indicate double-billing or data entry errors."
                ),
                "count": dup_inv,
            })

    metrics["total_records"] = len(cleaned)
    metrics["issues_found"]  = len([i for i in issues if i["count"] > 0])

    return SMEResult(
        cleaned_df=cleaned,
        metrics=metrics,
        postcode_col=postcode_col,
        ni_col=ni_col,
        vat_col=vat_col,
        ch_col=ch_col,
        due_col=due_col,
        payment_col=payment_col,
        phone_col=phone_col,
        terms_col=terms_col,
        issues=issues,
    )

"""Healthcare (Operational) dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass for NHS and private healthcare operational data
(NOT clinical trial registers — use Clinical Research mode for those):
  1. NHS number validation    — Modulus 11 check digit verification
  2. ICD-10 code format       — letter + 2 digits + optional decimal extension
  3. Appointment status       — maps variants to canonical status labels
  4. Waiting time calculation — referral date → appointment date (days)
  5. Staff category           — standardises role/grade labels
  6. UK postcode validation   — regex conformance check
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import pandas as pd


# ── Column keyword maps ───────────────────────────────────────────────────────

_NHS_KW      = ["nhs_number", "nhs_no", "nhs_num", "patient_id", "nhs"]
_ICD_KW      = ["icd", "diagnosis_code", "icd10", "icd_code", "diagnosis",
                  "primary_diagnosis", "condition_code"]
_APT_STATUS  = ["status", "appointment_status", "att_status", "attendance",
                  "attendance_status", "appt_status"]
_REF_DATE_KW = ["referral_date", "referred_date", "ref_date", "date_referred",
                  "referral"]
_APT_DATE_KW = ["appointment_date", "appt_date", "date_of_appointment",
                  "scheduled_date", "visit_date"]
_STAFF_KW    = ["staff_category", "job_title", "role", "grade", "band",
                  "staff_role", "position", "job_role"]
_POSTCODE_KW = ["postcode", "post_code", "zip", "postal_code"]
_WARD_KW     = ["ward", "department", "specialty", "clinic", "division"]
_PATIENT_KW  = ["patient_name", "name", "patient", "forename", "surname"]


def _detect(df: pd.DataFrame, keywords: list[str]) -> Optional[str]:
    for col in df.columns:
        cl = col.lower().replace(" ", "_")
        if any(kw in cl for kw in keywords):
            return col
    return None


# ── NHS number validation (Modulus 11) ───────────────────────────────────────

_WEIGHTS = [10, 9, 8, 7, 6, 5, 4, 3, 2]


def _validate_nhs_number(v) -> bool:
    if pd.isna(v):
        return True  # blanks are a separate issue, not an invalid format
    s = str(v).strip().replace(" ", "").replace("-", "")
    if len(s) != 10 or not s.isdigit():
        return False
    total = sum(int(d) * w for d, w in zip(s[:9], _WEIGHTS))
    remainder = total % 11
    if remainder == 1:
        return False  # always invalid
    check = 0 if remainder == 0 else 11 - remainder
    return check == int(s[9])


def validate_nhs_numbers(df: pd.DataFrame, col: str) -> tuple[int, int, pd.Series]:
    """Return (invalid_format_count, blank_count, valid_flag_series).

    valid_flag_series is a boolean Series indexed to df: True = valid or blank,
    False = present but fails Modulus 11. Blanks are marked True (separate issue).
    """
    blank_count = int(df[col].isna().sum())
    valid_flags = df[col].apply(_validate_nhs_number)
    invalid = int((~valid_flags & df[col].notna()).sum())
    return invalid, blank_count, valid_flags


# ── ICD-10 code validation ────────────────────────────────────────────────────

_ICD10_RE = re.compile(r"^[A-Z]\d{2}(\.\d{1,4})?$", re.IGNORECASE)


def validate_icd10_codes(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Uppercase ICD codes and return (df, invalid_count)."""
    df = df.copy()
    df[col] = df[col].astype(str).str.strip().str.upper().where(df[col].notna(), other=None)
    invalid = int(
        df[col].dropna()
        .apply(lambda v: not bool(_ICD10_RE.match(str(v).strip())))
        .sum()
    )
    return df, invalid


# ── Appointment status standardisation ───────────────────────────────────────

_STATUS_MAP: dict[str, str] = {
    "attended": "Attended", "att": "Attended", "seen": "Attended",
    "present": "Attended", "a": "Attended",
    "dna": "Did Not Attend", "did not attend": "Did Not Attend",
    "did_not_attend": "Did Not Attend", "no show": "Did Not Attend",
    "no_show": "Did Not Attend", "missed": "Did Not Attend", "n": "Did Not Attend",
    "cancelled": "Cancelled", "canceled": "Cancelled",
    "cancelled by patient": "Cancelled (Patient)",
    "cancelled by hospital": "Cancelled (Hospital)",
    "cancelled by clinician": "Cancelled (Hospital)",
    "booked": "Booked", "scheduled": "Booked", "confirmed": "Booked",
    "waiting": "Waiting", "on waiting list": "Waiting", "pending": "Waiting",
    "referred": "Referred", "in pathway": "Referred",
    "discharged": "Discharged", "dc": "Discharged",
}


def standardise_appointment_status(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()

    def _map(v):
        if pd.isna(v):
            return None
        key = str(v).strip().lower()
        if key in ("nan", ""):
            return None
        return _STATUS_MAP.get(key, str(v).strip())  # return original (stripped) when unmapped

    df[col] = df[col].apply(_map)
    changed = int((df[col].fillna("__NULL__") != original.fillna("__NULL__")).sum())
    return df, changed


# ── Waiting time calculation ──────────────────────────────────────────────────

def calculate_waiting_times(
    df: pd.DataFrame, referral_col: str, appointment_col: str
) -> tuple[pd.DataFrame, int, int]:
    """Add waiting_days column; return (df, calculated_count, impossible_count)."""
    df = df.copy()
    ref  = pd.to_datetime(df[referral_col],    errors="coerce")
    appt = pd.to_datetime(df[appointment_col], errors="coerce")
    df["waiting_days"] = (appt - ref).dt.days
    both_present = ref.notna() & appt.notna()
    calculated   = int(both_present.sum())
    impossible   = int((df["waiting_days"] < 0).sum())
    return df, calculated, impossible


# ── Staff category standardisation ───────────────────────────────────────────

_STAFF_MAP: dict[str, str] = {
    "doctor": "Doctor", "dr": "Doctor", "physician": "Doctor", "gp": "GP",
    "general practitioner": "GP", "consultant": "Consultant",
    "nurse": "Nurse", "registered nurse": "Nurse", "rn": "Nurse",
    "staff nurse": "Nurse", "specialist nurse": "Specialist Nurse",
    "healthcare assistant": "HCA", "hca": "HCA",
    "midwife": "Midwife", "allied health": "AHP", "ahp": "AHP",
    "physiotherapist": "Physiotherapist", "physio": "Physiotherapist",
    "pharmacist": "Pharmacist", "radiographer": "Radiographer",
    "admin": "Admin", "administrator": "Admin",
    "receptionist": "Admin", "clerical": "Admin",
    "manager": "Manager", "ward manager": "Ward Manager",
    "band 2": "Band 2", "band 3": "Band 3", "band 4": "Band 4",
    "band 5": "Band 5", "band 6": "Band 6", "band 7": "Band 7",
    "band 8": "Band 8", "band 9": "Band 9",
}


def standardise_staff_category(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()

    def _map(v):
        if pd.isna(v):
            return None
        key = str(v).strip().lower()
        if key in ("nan", ""):
            return None
        return _STAFF_MAP.get(key, str(v).strip())  # return original (stripped) when unmapped

    df[col] = df[col].apply(_map)
    changed = int((df[col].fillna("__NULL__") != original.fillna("__NULL__")).sum())
    return df, changed


# ── UK postcode validation ────────────────────────────────────────────────────

_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}[0-9][0-9A-Z]?\s?[0-9][ABD-HJLNP-UW-Z]{2}$",
    re.IGNORECASE,
)


def validate_postcodes(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Uppercase and space-normalise postcodes; return (df, invalid_count)."""
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


# ── Row-level audit diff ──────────────────────────────────────────────────────

def _diff_changes(
    before: pd.DataFrame,
    after: pd.DataFrame,
    rule: str,
    run_id: str,
    timestamp: str,
) -> pd.DataFrame:
    """Return one row per changed cell between two DataFrames for audit logging."""
    records = []
    shared_cols = [c for c in before.columns if c in after.columns]
    for col in shared_cols:
        b = before[col].fillna("__NULL__")
        a = after[col].fillna("__NULL__")
        changed_idx = before.index[b != a]
        for idx in changed_idx:
            records.append({
                "run_id":    run_id,
                "timestamp": timestamp,
                "row":       int(idx),
                "column":    col,
                "before":    before.at[idx, col],
                "after":     after.at[idx, col],
                "rule":      rule,
            })
    if records:
        return pd.DataFrame(records, columns=["run_id", "timestamp", "row", "column", "before", "after", "rule"])
    return pd.DataFrame(columns=["run_id", "timestamp", "row", "column", "before", "after", "rule"])


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class HealthcareResult:
    cleaned_df:       pd.DataFrame
    metrics:          dict
    nhs_col:          Optional[str] = None
    icd_col:          Optional[str] = None
    status_col:       Optional[str] = None
    referral_col:     Optional[str] = None
    appointment_col:  Optional[str] = None
    staff_col:        Optional[str] = None
    postcode_col:     Optional[str] = None
    issues:           list = field(default_factory=list)
    flags_df:         Optional[pd.DataFrame] = None              # per-row validity flags for audit
    audit_log:        pd.DataFrame = field(default_factory=pd.DataFrame)  # row-level change log
    run_id:           str = field(default_factory=lambda: str(uuid.uuid4()))
    cleaned_at:       str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_healthcare_cleaning(df: pd.DataFrame) -> HealthcareResult:
    """Run all healthcare operational cleaning steps and return a HealthcareResult."""
    run_id     = str(uuid.uuid4())
    cleaned_at = datetime.now(timezone.utc).isoformat()
    cleaned = df.copy()
    audit_frames: list[pd.DataFrame] = []
    issues: list[dict] = []
    metrics: dict = {}
    _nhs_flags: Optional[pd.Series] = None

    nhs_col          = _detect(cleaned, _NHS_KW)
    icd_col          = _detect(cleaned, _ICD_KW)
    status_col       = _detect(cleaned, _APT_STATUS)
    referral_col     = _detect(cleaned, _REF_DATE_KW)
    appointment_col  = _detect(cleaned, _APT_DATE_KW)
    staff_col        = _detect(cleaned, _STAFF_KW)
    postcode_col     = _detect(cleaned, _POSTCODE_KW)
    ward_col         = _detect(cleaned, _WARD_KW)

    # 1. NHS number validation (flags only — does not mutate cleaned)
    if nhs_col:
        nhs_invalid, nhs_blank, _nhs_flags = validate_nhs_numbers(cleaned, nhs_col)
        metrics["nhs_blank_count"] = nhs_blank
        if nhs_invalid:
            issues.append({
                "type": "Invalid NHS Numbers",
                "description": (
                    f"{nhs_invalid:,} NHS number(s) fail the Modulus 11 check digit validation — "
                    "verify these identifiers against the source system."
                ),
                "count": nhs_invalid,
            })
        if nhs_blank:
            issues.append({
                "type": "Missing NHS Numbers",
                "description": f"{nhs_blank:,} record(s) have no NHS number.",
                "count": nhs_blank,
            })

    # 2. ICD-10 code validation
    if icd_col:
        _before = cleaned.copy()
        cleaned, icd_invalid = validate_icd10_codes(cleaned, icd_col)
        audit_frames.append(_diff_changes(_before, cleaned, "icd10_normalisation", run_id, cleaned_at))
        metrics["unique_icd_codes"] = int(cleaned[icd_col].nunique())
        metrics["top_diagnoses"]    = cleaned[icd_col].value_counts().head(10).to_dict()
        if icd_invalid:
            issues.append({
                "type": "Invalid ICD-10 Codes",
                "description": (
                    f"{icd_invalid:,} diagnosis code(s) do not match ICD-10 format "
                    "(letter + 2 digits + optional decimal extension)."
                ),
                "count": icd_invalid,
            })

    # 3. Appointment status standardisation
    if status_col:
        _before = cleaned.copy()
        cleaned, status_changed = standardise_appointment_status(cleaned, status_col)
        audit_frames.append(_diff_changes(_before, cleaned, "appointment_status_standardisation", run_id, cleaned_at))
        metrics["status_counts"] = cleaned[status_col].value_counts().to_dict()
        dna_count = int((cleaned[status_col] == "Did Not Attend").sum())
        total_apts = len(cleaned)
        metrics["dna_rate_pct"] = round(dna_count / max(total_apts, 1) * 100, 1)
        if status_changed:
            issues.append({
                "type": "Appointment Status Standardisation",
                "description": f"{status_changed:,} status value(s) normalised to canonical labels.",
                "count": status_changed,
            })
        if dna_count and metrics["dna_rate_pct"] >= 10:
            issues.append({
                "type": "High DNA Rate",
                "description": (
                    f"Did Not Attend rate is {metrics['dna_rate_pct']}% ({dna_count:,} records) — "
                    "above the 10% threshold that typically triggers NHS improvement reviews."
                ),
                "count": dna_count,
            })

    # 4. Waiting time calculation
    if referral_col and appointment_col:
        _before = cleaned.copy()
        cleaned, calc_count, impossible_count = calculate_waiting_times(
            cleaned, referral_col, appointment_col
        )
        audit_frames.append(_diff_changes(_before, cleaned, "waiting_time_calculation", run_id, cleaned_at))
        wt = cleaned["waiting_days"].dropna()
        metrics["waiting_time_stats"] = {
            "min_days":  int(wt.min()) if len(wt) else None,
            "avg_days":  round(float(wt.mean()), 1) if len(wt) else None,
            "max_days":  int(wt.max()) if len(wt) else None,
            "over_18wk": int((wt > 126).sum()),
        }
        if impossible_count:
            issues.append({
                "type": "Impossible Waiting Dates",
                "description": (
                    f"{impossible_count:,} record(s) have an appointment date before their "
                    "referral date — likely a data entry or system error."
                ),
                "count": impossible_count,
            })
        over_18wk = metrics["waiting_time_stats"]["over_18wk"]
        if over_18wk:
            issues.append({
                "type": "18-Week RTT Breaches",
                "description": (
                    f"{over_18wk:,} patient(s) have waited more than 18 weeks (NHS RTT standard). "
                    "These may require escalation."
                ),
                "count": over_18wk,
            })

    # 5. Staff category standardisation
    if staff_col:
        _before = cleaned.copy()
        cleaned, staff_changed = standardise_staff_category(cleaned, staff_col)
        audit_frames.append(_diff_changes(_before, cleaned, "staff_category_standardisation", run_id, cleaned_at))
        metrics["staff_counts"] = cleaned[staff_col].value_counts().to_dict()
        if staff_changed:
            issues.append({
                "type": "Staff Category Standardisation",
                "description": f"{staff_changed:,} staff category value(s) normalised.",
                "count": staff_changed,
            })

    # 6. Postcode validation
    if postcode_col:
        _before = cleaned.copy()
        cleaned, pc_invalid = validate_postcodes(cleaned, postcode_col)
        audit_frames.append(_diff_changes(_before, cleaned, "postcode_normalisation", run_id, cleaned_at))
        if pc_invalid:
            issues.append({
                "type": "Invalid UK Postcodes",
                "description": (
                    f"{pc_invalid:,} postcode(s) do not match valid UK postcode format — "
                    "may cause issues with geographic reporting or patient contact."
                ),
                "count": pc_invalid,
            })

    # 7. Ward/department distribution
    if ward_col:
        metrics["ward_counts"] = cleaned[ward_col].value_counts().head(15).to_dict()

    metrics["total_records"] = len(cleaned)
    metrics["issues_found"]  = len([i for i in issues if i["count"] > 0])

    # Build per-row NHS validity flag DataFrame for audit
    flags_df: Optional[pd.DataFrame] = (
        pd.DataFrame({"_nhs_valid": _nhs_flags}, index=cleaned.index)
        if _nhs_flags is not None else None
    )

    audit_log = (
        pd.concat(audit_frames, ignore_index=True)
        if audit_frames
        else pd.DataFrame(columns=["run_id", "timestamp", "row", "column", "before", "after", "rule"])
    )

    return HealthcareResult(
        cleaned_df=cleaned,
        metrics=metrics,
        nhs_col=nhs_col,
        icd_col=icd_col,
        status_col=status_col,
        referral_col=referral_col,
        appointment_col=appointment_col,
        staff_col=staff_col,
        postcode_col=postcode_col,
        issues=issues,
        flags_df=flags_df,
        audit_log=audit_log,
        run_id=run_id,
        cleaned_at=cleaned_at,
    )

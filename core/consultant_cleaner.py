"""Consultants & Professional Services dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. Timesheet validation    — flags daily hours > 24 and weekly totals
  2. Rate sanity checks      — flags zero or negative day/hourly rates
  3. Project code formatting — uppercase + strip whitespace
  4. Utilisation rate        — billable hours / total hours × 100
  5. Overrun detection       — actual hours vs budgeted hours
  6. Status standardisation  — maps variants to canonical engagement statuses
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


# ── Column keyword maps ───────────────────────────────────────────────────────

_PROJECT_KW    = ["project", "matter", "engagement", "project_code", "project_id",
                   "matter_no", "project_no", "job_code", "job_no"]
_CLIENT_KW     = ["client", "customer", "client_name", "account", "client_id"]
_CONSULTANT_KW = ["consultant", "employee", "staff", "resource", "fee_earner",
                   "advisor", "adviser", "analyst", "associate"]
_BILL_HRS_KW   = ["billable_hours", "billable", "chargeable", "charged_hours",
                   "fee_hours", "billed_hours", "invoiceable"]
_TOTAL_HRS_KW  = ["total_hours", "hours_worked", "actual_hours", "logged_hours",
                   "time_logged", "hours", "duration"]
_BUDGET_HRS_KW = ["budget_hours", "budgeted_hours", "estimated_hours",
                   "planned_hours", "budget", "estimate"]
_DAY_RATE_KW   = ["day_rate", "daily_rate", "rate_per_day", "charge_rate",
                   "daily_charge", "rate_day"]
_HOURLY_KW     = ["hourly_rate", "rate_per_hour", "hour_rate", "hourly_charge"]
_DATE_KW       = ["date", "work_date", "timesheet_date", "entry_date",
                   "period_date", "week_ending"]
_STATUS_KW     = ["status", "project_status", "engagement_status",
                   "matter_status", "job_status"]


def _detect(df: pd.DataFrame, keywords: list[str]) -> Optional[str]:
    for col in df.columns:
        cl = col.lower().replace(" ", "_")
        if any(kw in cl for kw in keywords):
            return col
    return None


# ── Status standardisation ────────────────────────────────────────────────────

_STATUS_MAP: dict[str, str] = {
    "active": "Active", "in progress": "Active", "in_progress": "Active",
    "live": "Active", "ongoing": "Active", "open": "Active",
    "completed": "Completed", "complete": "Completed", "finished": "Completed",
    "closed": "Completed", "done": "Completed", "delivered": "Completed",
    "on hold": "On Hold", "on_hold": "On Hold", "paused": "On Hold",
    "suspended": "On Hold", "deferred": "On Hold",
    "cancelled": "Cancelled", "canceled": "Cancelled", "terminated": "Cancelled",
    "won": "Won", "awarded": "Won", "signed": "Won",
    "lost": "Lost", "not awarded": "Lost",
    "proposal": "Proposal", "tendering": "Proposal", "bid": "Proposal",
    "pipeline": "Pipeline", "prospect": "Pipeline",
}


def standardise_status(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = (
        df[col]
        .astype(str).str.strip().str.lower()
        .map(lambda v: _STATUS_MAP.get(v, v.title() if v not in ("nan", "") else None))
    )
    df.loc[original.isna(), col] = None
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Project code formatting ────────────────────────────────────────────────────

def format_project_codes(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].astype(str).str.strip().str.upper().where(df[col].notna(), other=None)
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Timesheet validation ───────────────────────────────────────────────────────

def validate_hours(df: pd.DataFrame, hours_col: str) -> tuple[int, int]:
    """Return (over_24_count, zero_count)."""
    hours = pd.to_numeric(df[hours_col], errors="coerce")
    over_24 = int((hours > 24).sum())
    zero    = int((hours == 0).sum())
    return over_24, zero


# ── Rate sanity checks ────────────────────────────────────────────────────────

def validate_rates(df: pd.DataFrame, col: str) -> tuple[int, int]:
    """Return (zero_rate_count, negative_rate_count)."""
    rates = pd.to_numeric(df[col], errors="coerce")
    zero     = int((rates == 0).sum())
    negative = int((rates < 0).sum())
    return zero, negative


# ── Utilisation rate ──────────────────────────────────────────────────────────

def calculate_utilisation(
    df: pd.DataFrame, billable_col: str, total_col: str
) -> tuple[pd.DataFrame, float]:
    """Add utilisation_pct column; return (df, overall_utilisation_pct)."""
    df = df.copy()
    billable = pd.to_numeric(df[billable_col], errors="coerce")
    total    = pd.to_numeric(df[total_col],    errors="coerce")
    valid    = total.notna() & billable.notna() & (total > 0)
    df["utilisation_pct"] = (billable / total * 100).where(valid).round(1)
    overall = float((billable[valid].sum() / total[valid].sum()) * 100) if valid.any() else 0.0
    return df, round(overall, 1)


# ── Duplicate timesheet detection ────────────────────────────────────────────

def detect_duplicate_timesheets(
    df: pd.DataFrame,
    consultant_col: str,
    project_col: str,
    date_col: str,
    hours_col: str,
) -> tuple[pd.DataFrame, int]:
    """Flag duplicate (consultant, project, date, hours) combinations.

    Returns (df_with_flag_column, duplicate_count).
    The flag column ``duplicate_timesheet_flag`` is True for every row that is
    the second or later occurrence of the same combination.
    """
    df = df.copy()
    key_cols = [consultant_col, project_col, date_col, hours_col]
    duplicated_mask = df.duplicated(subset=key_cols, keep="first")
    df["duplicate_timesheet_flag"] = duplicated_mask
    return df, int(duplicated_mask.sum())


# ── Weekly 48-hour cap (UK Working Time Regulations 1998) ─────────────────────

def detect_weekly_hour_breaches(
    df: pd.DataFrame,
    consultant_col: str,
    date_col: str,
    hours_col: str,
) -> tuple[int, int]:
    """Return (breach_count, distinct_consultants_over_48h).

    Groups by (consultant, ISO week) and sums hours.  Any consultant-week pair
    exceeding 48 hours is counted as a breach.
    """
    hours = pd.to_numeric(df[hours_col], errors="coerce")
    dates = pd.to_datetime(df[date_col], errors="coerce")

    valid = hours.notna() & dates.notna()
    if not valid.any():
        return 0, 0

    tmp = pd.DataFrame({
        "consultant": df.loc[valid, consultant_col].values,
        "iso_week":   dates[valid].dt.isocalendar().week.values,
        "iso_year":   dates[valid].dt.isocalendar().year.values,
        "hours":      hours[valid].values,
    })

    weekly = tmp.groupby(["consultant", "iso_year", "iso_week"], as_index=False)["hours"].sum()
    breaches = weekly[weekly["hours"] > 48]
    breach_count = len(breaches)
    distinct_consultants = int(breaches["consultant"].nunique()) if breach_count else 0
    return breach_count, distinct_consultants


# ── Overrun detection ─────────────────────────────────────────────────────────

def detect_overruns(
    df: pd.DataFrame, actual_col: str, budget_col: str
) -> tuple[int, float]:
    """Return (overrun_count, avg_overrun_pct)."""
    actual = pd.to_numeric(df[actual_col], errors="coerce")
    budget = pd.to_numeric(df[budget_col], errors="coerce")
    both   = actual.notna() & budget.notna() & (budget > 0)
    overrun_mask = both & (actual > budget)
    overrun_count = int(overrun_mask.sum())
    pct_over = ((actual[overrun_mask] - budget[overrun_mask]) / budget[overrun_mask] * 100)
    avg_overrun = float(pct_over.mean()) if len(pct_over) else 0.0
    return overrun_count, round(avg_overrun, 1)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ConsultantResult:
    cleaned_df:     pd.DataFrame
    metrics:        dict
    project_col:    Optional[str] = None
    client_col:     Optional[str] = None
    bill_hrs_col:   Optional[str] = None
    total_hrs_col:  Optional[str] = None
    budget_hrs_col: Optional[str] = None
    day_rate_col:   Optional[str] = None
    hourly_col:     Optional[str] = None
    issues:         list = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_consultant_cleaning(df: pd.DataFrame) -> ConsultantResult:
    """Run all consultant/professional-services cleaning steps."""
    cleaned = df.copy()
    issues: list[dict] = []
    metrics: dict = {}

    project_col    = _detect(cleaned, _PROJECT_KW)
    client_col     = _detect(cleaned, _CLIENT_KW)
    consultant_col = _detect(cleaned, _CONSULTANT_KW)
    bill_hrs_col   = _detect(cleaned, _BILL_HRS_KW)
    total_hrs_col  = _detect(cleaned, _TOTAL_HRS_KW)
    budget_hrs_col = _detect(cleaned, _BUDGET_HRS_KW)
    day_rate_col   = _detect(cleaned, _DAY_RATE_KW)
    hourly_col     = _detect(cleaned, _HOURLY_KW)
    status_col     = _detect(cleaned, _STATUS_KW)

    # 1. Project code formatting
    if project_col:
        cleaned, proj_changed = format_project_codes(cleaned, project_col)
        metrics["unique_projects"] = int(cleaned[project_col].nunique())
        if proj_changed:
            issues.append({
                "type": "Project Code Formatting",
                "description": f"{proj_changed:,} project code(s) standardised to uppercase.",
                "count": proj_changed,
            })

    # 2. Client distribution
    if client_col:
        metrics["client_counts"] = cleaned[client_col].value_counts().head(10).to_dict()
        metrics["unique_clients"] = int(cleaned[client_col].nunique())

    # 3. Status standardisation
    if status_col:
        cleaned, status_changed = standardise_status(cleaned, status_col)
        metrics["status_counts"] = cleaned[status_col].value_counts().to_dict()
        if status_changed:
            issues.append({
                "type": "Status Standardisation",
                "description": f"{status_changed:,} status value(s) normalised to canonical labels.",
                "count": status_changed,
            })

    # 4. Timesheet validation (total hours)
    if total_hrs_col:
        over24, zero_hrs = validate_hours(cleaned, total_hrs_col)
        hrs = pd.to_numeric(cleaned[total_hrs_col], errors="coerce")
        metrics["total_hours_logged"] = round(float(hrs.sum()), 1)
        metrics["avg_hours_per_row"]  = round(float(hrs.mean()), 2) if hrs.notna().any() else None
        if over24:
            issues.append({
                "type": "Hours Exceeding 24 Per Day",
                "description": (
                    f"{over24:,} timesheet row(s) log more than 24 hours in a single entry — "
                    "possible data entry error or multi-day entries recorded as one day."
                ),
                "count": over24,
            })
        if zero_hrs:
            issues.append({
                "type": "Zero-Hour Entries",
                "description": f"{zero_hrs:,} timesheet row(s) log zero hours.",
                "count": zero_hrs,
            })

    # 5. Billable hours validation
    if bill_hrs_col:
        b_over24, b_zero = validate_hours(cleaned, bill_hrs_col)
        b_hrs = pd.to_numeric(cleaned[bill_hrs_col], errors="coerce")
        metrics["total_billable_hours"] = round(float(b_hrs.sum()), 1)
        if b_over24:
            issues.append({
                "type": "Billable Hours Exceeding 24",
                "description": f"{b_over24:,} row(s) log more than 24 billable hours in one entry.",
                "count": b_over24,
            })

    # 6. Utilisation rate
    if bill_hrs_col and total_hrs_col:
        cleaned, utilisation = calculate_utilisation(cleaned, bill_hrs_col, total_hrs_col)
        metrics["utilisation_pct"] = utilisation
        if utilisation < 60:
            issues.append({
                "type": "Low Utilisation Rate",
                "description": (
                    f"Overall utilisation is {utilisation:.1f}% — below a typical 60–70% target. "
                    "Review non-billable time allocation."
                ),
                "count": 1,
            })

    # 7. Overrun detection
    if total_hrs_col and budget_hrs_col:
        overrun_count, avg_overrun_pct = detect_overruns(cleaned, total_hrs_col, budget_hrs_col)
        metrics["overrun_count"]   = overrun_count
        metrics["avg_overrun_pct"] = avg_overrun_pct
        if overrun_count:
            issues.append({
                "type": "Budget Overruns",
                "description": (
                    f"{overrun_count:,} project/entry(ies) have exceeded their budgeted hours "
                    f"(average overrun: {avg_overrun_pct:.1f}%)."
                ),
                "count": overrun_count,
            })

    # 8. Day rate sanity
    if day_rate_col:
        zero_dr, neg_dr = validate_rates(cleaned, day_rate_col)
        rates = pd.to_numeric(cleaned[day_rate_col], errors="coerce")
        metrics["avg_day_rate"] = round(float(rates.mean()), 2) if rates.notna().any() else None
        if zero_dr:
            issues.append({
                "type": "Zero Day Rates",
                "description": f"{zero_dr:,} record(s) have a day rate of zero — may be missing fees.",
                "count": zero_dr,
            })
        if neg_dr:
            issues.append({
                "type": "Negative Day Rates",
                "description": f"{neg_dr:,} record(s) have a negative day rate.",
                "count": neg_dr,
            })

    # 9. Hourly rate sanity
    if hourly_col:
        zero_hr, neg_hr = validate_rates(cleaned, hourly_col)
        rates = pd.to_numeric(cleaned[hourly_col], errors="coerce")
        metrics["avg_hourly_rate"] = round(float(rates.mean()), 2) if rates.notna().any() else None
        if zero_hr:
            issues.append({
                "type": "Zero Hourly Rates",
                "description": f"{zero_hr:,} record(s) have an hourly rate of zero.",
                "count": zero_hr,
            })

    # 10. Duplicate timesheet entry detection
    date_col = _detect(cleaned, _DATE_KW)
    if consultant_col and project_col and date_col and total_hrs_col:
        cleaned, dup_count = detect_duplicate_timesheets(
            cleaned, consultant_col, project_col, date_col, total_hrs_col
        )
        metrics["duplicate_timesheet_entries"] = dup_count
        if dup_count:
            issues.append({
                "type": "Duplicate Timesheet Entries",
                "severity": "High",
                "description": (
                    f"{dup_count:,} duplicate timesheet entries detected (same consultant, "
                    "project, date and hours). Review for double-submission."
                ),
                "count": dup_count,
            })

    # 11. Weekly 48-hour cap (UK Working Time Regulations 1998)
    if consultant_col and date_col and total_hrs_col:
        breach_count, consultants_over = detect_weekly_hour_breaches(
            cleaned, consultant_col, date_col, total_hrs_col
        )
        metrics["working_time_breaches"]  = breach_count
        metrics["consultants_over_48h"]   = consultants_over
        if breach_count:
            issues.append({
                "type": "Working Time Regulations Breach",
                "severity": "Medium",
                "description": (
                    f"{breach_count:,} consultant-week(s) exceed the 48-hour Working Time "
                    "Regulations threshold. Confirm opt-out agreements are in place."
                ),
                "count": breach_count,
            })

    metrics["total_rows"]    = len(cleaned)
    metrics["issues_found"]  = len([i for i in issues if i["count"] > 0])

    return ConsultantResult(
        cleaned_df=cleaned,
        metrics=metrics,
        project_col=project_col,
        client_col=client_col,
        bill_hrs_col=bill_hrs_col,
        total_hrs_col=total_hrs_col,
        budget_hrs_col=budget_hrs_col,
        day_rate_col=day_rate_col,
        hourly_col=hourly_col,
        issues=issues,
    )

"""Hospitality & Accommodation dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. Booking reference standardisation  — strips spaces, enforces uppercase
  2. Duplicate booking reference detection
  3. Check-in / check-out date validation — flags impossible dates (checkout ≤ checkin)
  4. Length-of-stay analysis             — avg/min/max nights; flags zero-night stays
  5. Room type standardisation           — common abbreviations → canonical labels
  6. Booking status standardisation      — Confirmed / Cancelled / No-Show / etc.
  7. Booking channel standardisation     — OTA / Direct / Corporate / etc.
  8. Guest count validation              — zero or negative guest counts
  9. Revenue & ADR summary               — total revenue, average daily rate
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from core.column_mapper import _detect  # noqa: F401


# ── Column keyword maps ───────────────────────────────────────────────────────

_BOOKING_REF_KW = ["booking_ref", "reservation_id", "booking_id", "res_no",
                    "reservation_no", "conf_no", "confirmation", "res_id",
                    "booking_number", "ref_number"]
_CHECKIN_KW     = ["check_in", "checkin", "arrival", "arrival_date",
                    "check_in_date", "date_arrival", "date_checkin"]
_CHECKOUT_KW    = ["check_out", "checkout", "departure", "departure_date",
                    "check_out_date", "date_departure", "date_checkout"]
_ROOM_TYPE_KW   = ["room_type", "room_category", "accommodation_type",
                    "room_class", "room_name", "bed_type", "room_desc"]
_RATE_KW        = ["rate", "nightly_rate", "room_rate", "daily_rate", "adr",
                    "tariff", "rack_rate", "night_rate"]
_REVENUE_KW     = ["revenue", "total_revenue", "booking_revenue",
                    "total_amount", "gross_revenue", "booking_total",
                    "total_charge", "amount"]
_GUESTS_KW      = ["guests", "guest_count", "num_guests", "occupants",
                    "pax", "adults", "no_guests", "number_of_guests"]
_STATUS_KW      = ["status", "booking_status", "reservation_status",
                    "res_status", "booking_state"]
_CHANNEL_KW     = ["channel", "booking_channel", "source", "booking_source",
                    "origin", "distribution_channel", "res_source"]
_PROPERTY_KW    = ["property", "hotel", "venue", "property_name",
                    "hotel_name", "venue_name", "site"]


# ── Room type standardisation ─────────────────────────────────────────────────

_ROOM_TYPE_MAP: dict[str, str] = {
    "sgl": "Single", "single": "Single", "single room": "Single",
    "dbl": "Double", "double": "Double", "double room": "Double",
    "twn": "Twin", "twin": "Twin", "twin room": "Twin",
    "std": "Standard", "standard": "Standard", "standard room": "Standard",
    "sup dbl": "Superior Double", "superior dbl": "Superior Double",
    "superior double": "Superior Double",
    "deluxe dbl": "Deluxe Double", "deluxe double": "Deluxe Double",
    "dlx dbl": "Deluxe Double", "deluxe": "Deluxe Double",
    "suite": "Suite", "ste": "Suite",
    "exec suite": "Executive Suite", "executive suite": "Executive Suite",
    "exec ste": "Executive Suite",
    "jnr suite": "Junior Suite", "junior suite": "Junior Suite",
    "jr suite": "Junior Suite",
    "fam": "Family", "family": "Family", "family room": "Family",
    "king": "King", "king room": "King",
    "queen": "Queen", "queen room": "Queen",
    "triple": "Triple", "trp": "Triple", "triple room": "Triple",
    "quad": "Quad", "quad room": "Quad",
    "penthouse": "Penthouse",
    "studio": "Studio",
    "accessible": "Accessible", "disabled": "Accessible",
    "apartment": "Apartment", "apt": "Apartment",
}


def standardise_room_types(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = (
        df[col].astype(str).str.strip()
        .map(lambda v: _ROOM_TYPE_MAP.get(v.lower(), v.title()) if pd.notna(v) and v.lower() not in ("nan", "") else v)
        .where(original.notna(), other=None)
    )
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Booking status standardisation ────────────────────────────────────────────

_STATUS_MAP: dict[str, str] = {
    "confirmed": "Confirmed", "conf": "Confirmed", "active": "Confirmed",
    "booked": "Confirmed", "reserved": "Confirmed",
    "cancelled": "Cancelled", "canceled": "Cancelled",
    "cnx": "Cancelled", "cancel": "Cancelled", "cnxl": "Cancelled",
    "no show": "No-Show", "no-show": "No-Show",
    "noshow": "No-Show", "ns": "No-Show", "no_show": "No-Show",
    "checked in": "Checked-In", "check-in": "Checked-In",
    "checkin": "Checked-In", "arrived": "Checked-In", "in-house": "Checked-In",
    "checked out": "Checked-Out", "check-out": "Checked-Out",
    "checkout": "Checked-Out", "departed": "Checked-Out", "closed": "Checked-Out",
    "waitlist": "Waitlisted", "waitlisted": "Waitlisted", "waiting": "Waitlisted",
    "tentative": "Tentative", "provisional": "Tentative", "option": "Tentative",
    "on request": "On Request", "pending": "On Request",
}


def standardise_booking_status(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = (
        df[col].astype(str).str.strip()
        .map(lambda v: _STATUS_MAP.get(v.lower().strip(), v.title().strip()) if pd.notna(v) and v.lower() not in ("nan", "") else v)
        .where(original.notna(), other=None)
    )
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Channel standardisation ───────────────────────────────────────────────────

_CHANNEL_MAP: dict[str, str] = {
    "direct": "Direct", "direct booking": "Direct",
    "walk in": "Walk-In", "walk-in": "Walk-In",
    "walkin": "Walk-In", "walk_in": "Walk-In",
    "ota": "OTA", "online travel agent": "OTA",
    "booking.com": "OTA", "expedia": "OTA", "airbnb": "OTA",
    "hotels.com": "OTA", "agoda": "OTA", "online": "OTA",
    "corporate": "Corporate", "corp": "Corporate", "business": "Corporate",
    "corporate account": "Corporate",
    "travel agent": "Travel Agent", "ta": "Travel Agent",
    "agent": "Travel Agent", "travel agency": "Travel Agent",
    "group": "Group", "groups": "Group", "event": "Group",
    "conference": "Group", "group booking": "Group",
    "phone": "Phone / Email", "email": "Phone / Email",
    "telephone": "Phone / Email", "call centre": "Phone / Email",
    "website": "Website", "web": "Website", "online direct": "Website",
    "gds": "GDS", "global distribution": "GDS",
    "wholesale": "Wholesale", "wholesaler": "Wholesale",
}


def standardise_channels(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = (
        df[col].astype(str).str.strip()
        .map(lambda v: _CHANNEL_MAP.get(v.lower().strip(), v.title().strip()) if pd.notna(v) and v.lower() not in ("nan", "") else v)
        .where(original.notna(), other=None)
    )
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Booking reference standardisation ────────────────────────────────────────

def standardise_booking_refs(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].astype(str).str.strip().str.upper().where(df[col].notna(), other=None)
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


def detect_duplicate_booking_refs(df: pd.DataFrame, col: str) -> int:
    return int(df[col].duplicated(keep=False).sum())


# ── Date / stay validation ────────────────────────────────────────────────────

def validate_stay_dates(
    df: pd.DataFrame, checkin_col: str, checkout_col: str
) -> tuple[int, int, dict]:
    """Return (impossible_count, zero_night_count, stay_stats)."""
    checkin  = pd.to_datetime(df[checkin_col],  errors="coerce")
    checkout = pd.to_datetime(df[checkout_col], errors="coerce")

    both_present = checkin.notna() & checkout.notna()
    nights = (checkout - checkin).dt.days

    impossible   = int((both_present & (checkout <= checkin)).sum())
    zero_nights  = int((both_present & (nights == 0)).sum())

    valid_stays = nights[both_present & (nights > 0) & (nights <= 365)]
    stay_stats: dict = {}
    if not valid_stays.empty:
        stay_stats["avg_nights"] = round(float(valid_stays.mean()), 1)
        stay_stats["min_nights"] = int(valid_stays.min())
        stay_stats["max_nights"] = int(valid_stays.max())
        stay_stats["over_30_nights"] = int((valid_stays > 30).sum())

    return impossible, zero_nights, stay_stats


# ── Guest count validation ────────────────────────────────────────────────────

def validate_guest_counts(df: pd.DataFrame, col: str) -> tuple[int, int]:
    """Return (zero_guest_count, negative_guest_count)."""
    guests = pd.to_numeric(df[col], errors="coerce")
    zero_guests     = int((guests == 0).sum())
    negative_guests = int((guests < 0).sum())
    return zero_guests, negative_guests


# ── Revenue & ADR summary ─────────────────────────────────────────────────────

def summarise_revenue(df: pd.DataFrame, revenue_col: str) -> dict:
    rev = pd.to_numeric(df[revenue_col], errors="coerce")
    return {
        "total_revenue": round(float(rev.sum()), 2) if rev.notna().any() else None,
        "avg_revenue":   round(float(rev.mean()), 2) if rev.notna().any() else None,
        "neg_revenue":   int((rev < 0).sum()),
    }


def summarise_adr(df: pd.DataFrame, rate_col: str) -> dict:
    rate = pd.to_numeric(df[rate_col], errors="coerce")
    return {
        "avg_daily_rate": round(float(rate.mean()), 2) if rate.notna().any() else None,
        "min_rate":       round(float(rate.min()), 2)  if rate.notna().any() else None,
        "max_rate":       round(float(rate.max()), 2)  if rate.notna().any() else None,
        "zero_rates":     int((rate == 0).sum()),
    }


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class HospitalityResult:
    cleaned_df:    pd.DataFrame
    metrics:       dict
    booking_col:   Optional[str] = None
    checkin_col:   Optional[str] = None
    checkout_col:  Optional[str] = None
    room_type_col: Optional[str] = None
    status_col:    Optional[str] = None
    channel_col:   Optional[str] = None
    guests_col:    Optional[str] = None
    rate_col:      Optional[str] = None
    revenue_col:   Optional[str] = None
    issues:        list = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_hospitality_cleaning(df: pd.DataFrame) -> HospitalityResult:
    """Run all hospitality cleaning steps and return a HospitalityResult."""
    cleaned = df.copy()
    issues: list[dict] = []
    metrics: dict = {}

    booking_col   = _detect(cleaned, _BOOKING_REF_KW)
    checkin_col   = _detect(cleaned, _CHECKIN_KW)
    checkout_col  = _detect(cleaned, _CHECKOUT_KW)
    room_type_col = _detect(cleaned, _ROOM_TYPE_KW)
    rate_col      = _detect(cleaned, _RATE_KW)
    revenue_col   = _detect(cleaned, _REVENUE_KW)
    guests_col    = _detect(cleaned, _GUESTS_KW)
    status_col    = _detect(cleaned, _STATUS_KW)
    channel_col   = _detect(cleaned, _CHANNEL_KW)
    property_col  = _detect(cleaned, _PROPERTY_KW)

    # 1. Booking reference standardisation
    if booking_col:
        cleaned, ref_changed = standardise_booking_refs(cleaned, booking_col)
        if ref_changed:
            issues.append({
                "type": "Booking Reference Standardisation",
                "description": f"{ref_changed:,} booking reference(s) trimmed and uppercased.",
                "count": ref_changed,
            })
        dup_refs = detect_duplicate_booking_refs(cleaned, booking_col)
        metrics["unique_bookings"] = int(cleaned[booking_col].nunique())
        if dup_refs:
            issues.append({
                "type": "Duplicate Booking References",
                "description": (
                    f"{dup_refs:,} record(s) share a duplicate booking reference — "
                    "may indicate double-billing or system import errors."
                ),
                "count": dup_refs,
            })

    # 2. Stay date validation
    if checkin_col and checkout_col:
        impossible, zero_nights, stay_stats = validate_stay_dates(
            cleaned, checkin_col, checkout_col
        )
        metrics["stay_stats"] = stay_stats
        if impossible:
            issues.append({
                "type": "Impossible Stay Dates",
                "description": (
                    f"{impossible:,} booking(s) have a check-out date on or before check-in — "
                    "these records cannot represent valid stays."
                ),
                "count": impossible,
            })
        if zero_nights:
            issues.append({
                "type": "Zero-Night Stays",
                "description": (
                    f"{zero_nights:,} booking(s) show check-in and check-out on the same day — "
                    "verify whether same-day bookings are expected in this dataset."
                ),
                "count": zero_nights,
            })
        over_30 = stay_stats.get("over_30_nights", 0)
        if over_30:
            issues.append({
                "type": "Extended Stays (>30 Nights)",
                "description": (
                    f"{over_30:,} booking(s) exceed 30 nights — "
                    "review for data entry errors or long-stay rate compliance."
                ),
                "count": over_30,
            })

    # 3. Room type standardisation
    if room_type_col:
        cleaned, rt_changed = standardise_room_types(cleaned, room_type_col)
        metrics["room_type_counts"] = cleaned[room_type_col].value_counts().head(15).to_dict()
        if rt_changed:
            issues.append({
                "type": "Room Type Standardisation",
                "description": f"{rt_changed:,} room type value(s) standardised to canonical labels.",
                "count": rt_changed,
            })

    # 4. Status standardisation & cancellation / no-show rates
    if status_col:
        cleaned, st_changed = standardise_booking_status(cleaned, status_col)
        metrics["status_counts"] = cleaned[status_col].value_counts().to_dict()
        total = len(cleaned)
        cancelled = int((cleaned[status_col] == "Cancelled").sum())
        no_shows  = int((cleaned[status_col] == "No-Show").sum())
        metrics["cancellation_rate_pct"] = round(cancelled / total * 100, 1) if total else 0.0
        metrics["no_show_rate_pct"]      = round(no_shows  / total * 100, 1) if total else 0.0
        if st_changed:
            issues.append({
                "type": "Booking Status Standardisation",
                "description": f"{st_changed:,} status value(s) normalised to standard labels.",
                "count": st_changed,
            })
        if cancelled:
            issues.append({
                "type": "Cancelled Bookings",
                "description": (
                    f"{cancelled:,} booking(s) have a Cancelled status "
                    f"({metrics['cancellation_rate_pct']}% of total)."
                ),
                "count": cancelled,
            })
        if no_shows:
            issues.append({
                "type": "No-Show Bookings",
                "description": (
                    f"{no_shows:,} booking(s) recorded as No-Show "
                    f"({metrics['no_show_rate_pct']}% of total) — "
                    "review for deposit/penalty policy compliance."
                ),
                "count": no_shows,
            })

    # 5. Channel standardisation
    if channel_col:
        cleaned, ch_changed = standardise_channels(cleaned, channel_col)
        metrics["channel_counts"] = cleaned[channel_col].value_counts().to_dict()
        if ch_changed:
            issues.append({
                "type": "Booking Channel Standardisation",
                "description": f"{ch_changed:,} booking channel value(s) standardised.",
                "count": ch_changed,
            })

    # 6. Guest count validation
    if guests_col:
        zero_g, neg_g = validate_guest_counts(cleaned, guests_col)
        guests_num = pd.to_numeric(cleaned[guests_col], errors="coerce")
        metrics["avg_guests"] = round(float(guests_num.mean()), 1) if guests_num.notna().any() else None
        if zero_g:
            issues.append({
                "type": "Zero Guest Count",
                "description": f"{zero_g:,} booking(s) have a guest count of zero — verify data entry.",
                "count": zero_g,
            })
        if neg_g:
            issues.append({
                "type": "Negative Guest Count",
                "description": f"{neg_g:,} booking(s) show a negative guest count — likely a data error.",
                "count": neg_g,
            })

    # 7. Rate / ADR summary
    if rate_col:
        adr_stats = summarise_adr(cleaned, rate_col)
        metrics.update(adr_stats)
        if adr_stats.get("zero_rates"):
            issues.append({
                "type": "Zero Nightly Rates",
                "description": (
                    f"{adr_stats['zero_rates']:,} booking(s) have a nightly rate of zero — "
                    "may indicate complimentary stays or missing rate data."
                ),
                "count": adr_stats["zero_rates"],
            })

    # 8. Revenue summary
    if revenue_col:
        rev_stats = summarise_revenue(cleaned, revenue_col)
        metrics["total_revenue"] = rev_stats["total_revenue"]
        metrics["avg_revenue"]   = rev_stats["avg_revenue"]
        if rev_stats.get("neg_revenue"):
            issues.append({
                "type": "Negative Revenue",
                "description": (
                    f"{rev_stats['neg_revenue']:,} booking(s) show negative revenue — "
                    "may represent refunds or credit adjustments."
                ),
                "count": rev_stats["neg_revenue"],
            })

    # 9. Property distribution
    if property_col:
        metrics["property_counts"] = cleaned[property_col].value_counts().head(10).to_dict()

    metrics["total_bookings"] = len(cleaned)
    metrics["issues_found"]   = len([i for i in issues if i["count"] > 0])

    return HospitalityResult(
        cleaned_df=cleaned,
        metrics=metrics,
        booking_col=booking_col,
        checkin_col=checkin_col,
        checkout_col=checkout_col,
        room_type_col=room_type_col,
        status_col=status_col,
        channel_col=channel_col,
        guests_col=guests_col,
        rate_col=rate_col,
        revenue_col=revenue_col,
        issues=issues,
    )

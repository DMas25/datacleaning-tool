"""Logistics & Supply Chain dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. Status standardisation       — maps status variants to canonical values
  2. Carrier standardisation      — normalises carrier names and codes
  3. Weight unit normalisation    — kg/lbs/g → canonical labels
  4. Transit time calculation     — derives transit_days from dispatch/delivery dates
  5. Date order validation        — flags rows where delivery precedes dispatch
  6. Duplicate tracking detection — identifies potential duplicate shipments
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np

from core.column_mapper import _detect  # noqa: F401 — re-exported for callers


# ── Column keyword maps ───────────────────────────────────────────────────────

_SHIPMENT_KW  = ["shipment_id", "shipment", "consignment", "ship_id", "order_id", "parcel_id"]
_TRACKING_KW  = ["tracking", "awb", "waybill", "track_no", "tracking_no", "tracking_number"]
_STATUS_KW    = ["status", "shipment_status", "delivery_status", "state", "current_status"]
_CARRIER_KW   = ["carrier", "courier", "freight", "transport", "shipper", "operator"]
_ORIGIN_KW    = ["origin", "sender", "from_", "departure", "source", "collect", "ship_from"]
_DEST_KW      = ["destination", "dest", "receiver", "deliver", "consignee", "ship_to"]
_DISPATCH_KW  = ["dispatch", "ship_date", "sent_date", "collection_date", "despatch", "pickup_date"]
_DELIVERY_KW  = ["delivery_date", "delivered_date", "received_date", "actual_delivery", "arrival_date"]
_WEIGHT_KW    = ["weight", "gross_weight", "net_weight", "kg", "mass"]


# ── Status standardisation ────────────────────────────────────────────────────

_STATUS_MAP: dict[str, str] = {
    "delivered": "Delivered", "dlvd": "Delivered", "complete": "Delivered",
    "completed": "Delivered", "del": "Delivered",
    "in transit": "In Transit", "in_transit": "In Transit", "intransit": "In Transit",
    "transit": "In Transit", "on the way": "In Transit", "dispatched": "In Transit",
    "shipped": "In Transit", "on route": "In Transit",
    "out for delivery": "Out for Delivery", "ofd": "Out for Delivery",
    "with driver": "Out for Delivery",
    "pending": "Pending", "awaiting": "Pending", "processing": "Pending",
    "booked": "Pending", "created": "Pending", "new": "Pending",
    "collected": "Collected", "picked up": "Collected", "collection": "Collected",
    "delayed": "Delayed", "late": "Delayed", "exception": "Delayed",
    "on hold": "Delayed", "held": "Delayed",
    "failed": "Failed", "undelivered": "Failed", "failed delivery": "Failed",
    "not delivered": "Failed", "unsuccessful": "Failed",
    "returned": "Returned", "rts": "Returned", "return to sender": "Returned",
    "returned to sender": "Returned", "refused": "Returned",
    "cancelled": "Cancelled", "canceled": "Cancelled", "void": "Cancelled",
}


def standardise_status(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Map status column variants to canonical values. Returns df and count of changes."""
    df = df.copy()
    original = df[col].copy()
    df[col] = (
        df[col]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda v: _STATUS_MAP.get(v, v.title() if v not in ("nan", "") else None))
    )
    df.loc[original.isna(), col] = None
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Carrier standardisation ───────────────────────────────────────────────────

_CARRIER_MAP: dict[str, str] = {
    "dhl express": "DHL", "dhl": "DHL",
    "fedex": "FedEx", "federal express": "FedEx", "fedex express": "FedEx",
    "ups": "UPS", "united parcel service": "UPS",
    "dpd": "DPD", "dpd uk": "DPD",
    "royal mail": "Royal Mail", "rm": "Royal Mail", "royalmail": "Royal Mail",
    "parcelforce": "Parcelforce", "parcel force": "Parcelforce",
    "evri": "Evri", "hermes": "Evri", "myhermes": "Evri",
    "yodel": "Yodel", "home delivery network": "Yodel",
    "amazon logistics": "Amazon", "amazon": "Amazon", "amzl": "Amazon",
    "tnt": "TNT", "tnt express": "TNT",
    "db schenker": "DB Schenker", "schenker": "DB Schenker",
    "kuehne nagel": "Kuehne+Nagel", "kuehne+nagel": "Kuehne+Nagel", "kn": "Kuehne+Nagel",
    "panalpina": "Kuehne+Nagel",
    "geodis": "Geodis",
    "dsv": "DSV",
    "ceva": "CEVA",
    "gls": "GLS",
    "dphl": "DHL",
}


def standardise_carrier(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = (
        df[col]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda v: _CARRIER_MAP.get(v, v.upper() if v not in ("nan", "") else None))
    )
    df.loc[original.isna(), col] = None
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Weight unit normalisation ─────────────────────────────────────────────────

_WEIGHT_UNIT_MAP: dict[str, str] = {
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "lbs": "lbs", "lb": "lbs", "pound": "lbs", "pounds": "lbs",
    "g": "g", "gram": "g", "grams": "g",
    "t": "metric_ton", "tonne": "metric_ton", "mt": "metric_ton",
    "oz": "oz", "ounce": "oz", "ounces": "oz",
}


def standardise_weight_units(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Detect and standardise unit strings embedded in a weight column if it's text."""
    if pd.api.types.is_numeric_dtype(df[col]):
        return df, 0
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].astype(str).str.strip().str.lower().map(
        lambda v: _WEIGHT_UNIT_MAP.get(v, v)
    )
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Transit time calculation ──────────────────────────────────────────────────

def calculate_transit_days(
    df: pd.DataFrame, dispatch_col: str, delivery_col: str
) -> tuple[pd.DataFrame, int, int]:
    """Add transit_days column; return (df, calculated_count, impossible_count).

    Impossible = delivery before dispatch (negative transit time).
    """
    df = df.copy()
    try:
        dispatch = pd.to_datetime(df[dispatch_col], errors="coerce")
        delivery = pd.to_datetime(df[delivery_col], errors="coerce")
    except Exception:
        return df, 0, 0

    transit = (delivery - dispatch).dt.days
    df["transit_days"] = transit

    both_present = dispatch.notna() & delivery.notna()
    calculated  = int(both_present.sum())
    impossible  = int((transit < 0).sum())

    return df, calculated, impossible


# ── Duplicate tracking detection ──────────────────────────────────────────────

def detect_duplicate_tracking(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Flag duplicate tracking numbers; returns df with _dup_tracking boolean and count."""
    df = df.copy()
    series = df[col].dropna()
    dup_mask = df[col].duplicated(keep=False) & df[col].notna()
    df["_dup_tracking"] = dup_mask
    return df, int(dup_mask.sum())


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class LogisticsResult:
    cleaned_df:    pd.DataFrame
    metrics:       dict
    shipment_col:  Optional[str] = None
    tracking_col:  Optional[str] = None
    status_col:    Optional[str] = None
    carrier_col:   Optional[str] = None
    dispatch_col:  Optional[str] = None
    delivery_col:  Optional[str] = None
    issues:        list = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_logistics_cleaning(df: pd.DataFrame) -> LogisticsResult:
    """Run all logistics-specific cleaning steps and return a LogisticsResult."""
    cleaned = df.copy()
    issues: list[dict] = []
    metrics: dict = {}

    shipment_col  = _detect(cleaned, _SHIPMENT_KW)
    tracking_col  = _detect(cleaned, _TRACKING_KW)
    status_col    = _detect(cleaned, _STATUS_KW)
    carrier_col   = _detect(cleaned, _CARRIER_KW)
    dispatch_col  = _detect(cleaned, _DISPATCH_KW)
    delivery_col  = _detect(cleaned, _DELIVERY_KW)
    weight_col    = _detect(cleaned, _WEIGHT_KW)

    # 1. Status standardisation
    if status_col:
        cleaned, status_changes = standardise_status(cleaned, status_col)
        metrics["status_counts"] = cleaned[status_col].value_counts().to_dict()
        if status_changes:
            issues.append({
                "type": "Status Standardisation",
                "description": f"{status_changes:,} status values normalised to canonical labels.",
                "count": status_changes,
            })

    # 2. Carrier standardisation
    if carrier_col:
        cleaned, carrier_changes = standardise_carrier(cleaned, carrier_col)
        metrics["carrier_counts"] = cleaned[carrier_col].value_counts().head(10).to_dict()
        if carrier_changes:
            issues.append({
                "type": "Carrier Standardisation",
                "description": f"{carrier_changes:,} carrier names normalised.",
                "count": carrier_changes,
            })

    # 3. Weight unit normalisation
    if weight_col:
        cleaned, weight_changes = standardise_weight_units(cleaned, weight_col)
        if weight_changes:
            issues.append({
                "type": "Weight Unit Normalisation",
                "description": f"{weight_changes:,} weight unit strings standardised.",
                "count": weight_changes,
            })

    # 4. Transit time calculation + date order validation
    if dispatch_col and delivery_col:
        cleaned, calc_count, impossible_count = calculate_transit_days(
            cleaned, dispatch_col, delivery_col
        )
        transit_valid = cleaned["transit_days"].dropna()
        metrics["transit_stats"] = {
            "min_days":  int(transit_valid.min()) if len(transit_valid) else None,
            "avg_days":  round(float(transit_valid.mean()), 1) if len(transit_valid) else None,
            "max_days":  int(transit_valid.max()) if len(transit_valid) else None,
            "calculated": calc_count,
        }
        if impossible_count:
            issues.append({
                "type": "Impossible Date Order",
                "description": (
                    f"{impossible_count:,} shipment(s) have a delivery date before "
                    "their dispatch date — likely data entry errors."
                ),
                "count": impossible_count,
            })

    # 5. Duplicate tracking detection
    if tracking_col:
        cleaned, dup_count = detect_duplicate_tracking(cleaned, tracking_col)
        cleaned = cleaned.drop(columns=["_dup_tracking"], errors="ignore")
        if dup_count:
            issues.append({
                "type": "Duplicate Tracking Numbers",
                "description": (
                    f"{dup_count:,} record(s) share a duplicate tracking number — "
                    "potential duplicate shipments or re-use of tracking IDs."
                ),
                "count": dup_count,
            })

    # 6. Missing shipment IDs
    if shipment_col:
        missing_ids = int(cleaned[shipment_col].isna().sum())
        if missing_ids:
            issues.append({
                "type": "Missing Shipment IDs",
                "description": f"{missing_ids:,} record(s) have no shipment ID.",
                "count": missing_ids,
            })

    metrics["total_shipments"] = len(cleaned)
    metrics["issues_found"] = len([i for i in issues if i["count"] > 0])

    return LogisticsResult(
        cleaned_df=cleaned,
        metrics=metrics,
        shipment_col=shipment_col,
        tracking_col=tracking_col,
        status_col=status_col,
        carrier_col=carrier_col,
        dispatch_col=dispatch_col,
        delivery_col=delivery_col,
        issues=issues,
    )

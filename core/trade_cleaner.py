"""Import / Export & Trade dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. HS code validation & formatting  — 6/8/10 digit numeric, zero-padded
  2. Country code normalisation       — maps names to ISO 3166-1 alpha-2
  3. Currency code standardisation    — 3-letter ISO 4217 codes
  4. Unit of measure standardisation  — kg, mt, pcs, ltrs, etc.
  5. Trade direction detection        — import vs export classification
  6. Value sanity checks              — flags negative or zero declared values
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from core.column_mapper import _detect  # noqa: F401


# ── Column keyword maps ───────────────────────────────────────────────────────

_HS_KW       = ["hs_code", "hscode", "hs", "commodity_code", "tariff_code",
                 "harmonised", "harmonized", "cn_code", "taric"]
_ORIGIN_KW   = ["country_of_origin", "origin_country", "coo", "exporter_country",
                 "country_origin", "origin", "export_country"]
_DEST_KW     = ["destination_country", "dest_country", "importer_country",
                 "consignee_country", "destination", "import_country", "country_dest"]
_VALUE_KW    = ["value", "customs_value", "declared_value", "invoice_value",
                "fob_value", "cif_value", "statistical_value", "trade_value"]
_CURRENCY_KW = ["currency", "ccy", "currency_code", "invoice_currency"]
_UNIT_KW     = ["unit", "uom", "unit_of_measure", "measure", "stat_unit", "quantity_unit"]
_QTY_KW      = ["quantity", "qty", "net_weight", "gross_weight", "volume"]
_DATE_KW     = ["date", "declaration_date", "entry_date", "clearance_date", "export_date"]
_DIR_KW      = ["direction", "trade_direction", "flow", "trade_flow", "type"]
_CUSTOMS_KW  = ["customs_ref", "entry_ref", "declaration_ref", "mrn", "customs_no"]


# ── HS Code validation ────────────────────────────────────────────────────────

_HS_RE = re.compile(r"^\d{6,10}$")


def validate_hs_codes(
    df: pd.DataFrame, col: str
) -> tuple[pd.DataFrame, int, int]:
    """Validate and zero-pad HS codes to 6 digits.

    Returns (df, fixed_count, invalid_count).
    invalid = non-numeric or non-standard length after padding.
    """
    df = df.copy()
    valid_count = fixed_count = invalid_count = 0

    def _fix(v):
        nonlocal fixed_count, invalid_count
        if pd.isna(v):
            return v
        s = str(v).strip().replace(".", "").replace(" ", "")
        # Remove common prefixes
        s = re.sub(r"^(hs|hs:|cn|taric)[\s-]*", "", s, flags=re.IGNORECASE)
        if s.isdigit():
            if len(s) < 6:
                fixed_count += 1
                return s.zfill(6)
            if len(s) in (6, 8, 10):
                return s
        invalid_count += 1
        return v  # keep original, flagged below

    df[col] = df[col].apply(_fix)
    df["_hs_valid"] = df[col].apply(
        lambda v: bool(_HS_RE.match(str(v).strip())) if pd.notna(v) else True
    )
    n_invalid = int((~df["_hs_valid"] & df[col].notna()).sum())
    df = df.drop(columns=["_hs_valid"])
    return df, fixed_count, n_invalid


# ── Country code normalisation ────────────────────────────────────────────────

_COUNTRY_MAP: dict[str, str] = {
    "united kingdom": "GB", "uk": "GB", "great britain": "GB", "england": "GB",
    "united states": "US", "usa": "US", "u.s.a.": "US", "america": "US",
    "germany": "DE", "deutschland": "DE",
    "france": "FR",
    "spain": "ES",
    "italy": "IT",
    "netherlands": "NL", "holland": "NL",
    "belgium": "BE",
    "poland": "PL",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "austria": "AT",
    "switzerland": "CH",
    "portugal": "PT",
    "ireland": "IE",
    "greece": "GR",
    "czech republic": "CZ", "czechia": "CZ",
    "hungary": "HU",
    "romania": "RO",
    "turkey": "TR", "türkiye": "TR",
    "china": "CN", "prc": "CN", "peoples republic of china": "CN",
    "hong kong": "HK",
    "japan": "JP",
    "south korea": "KR", "korea": "KR",
    "india": "IN",
    "singapore": "SG",
    "taiwan": "TW",
    "malaysia": "MY",
    "indonesia": "ID",
    "thailand": "TH",
    "vietnam": "VN",
    "philippines": "PH",
    "bangladesh": "BD",
    "pakistan": "PK",
    "sri lanka": "LK",
    "australia": "AU",
    "new zealand": "NZ",
    "canada": "CA",
    "mexico": "MX",
    "brazil": "BR",
    "argentina": "AR",
    "colombia": "CO",
    "chile": "CL",
    "south africa": "ZA",
    "nigeria": "NG",
    "kenya": "KE",
    "ghana": "GH",
    "ethiopia": "ET",
    "egypt": "EG",
    "morocco": "MA",
    "saudi arabia": "SA", "ksa": "SA",
    "uae": "AE", "united arab emirates": "AE",
    "israel": "IL",
    "russia": "RU", "russian federation": "RU",
    "ukraine": "UA",
}


def normalise_country_codes(
    df: pd.DataFrame, col: str
) -> tuple[pd.DataFrame, int]:
    """Map country names to ISO 3166-1 alpha-2 codes. Returns (df, changed_count)."""
    df = df.copy()
    original = df[col].copy()

    def _map(v):
        if pd.isna(v):
            return v
        s = str(v).strip()
        mapped = _COUNTRY_MAP.get(s.lower())
        if mapped:
            return mapped
        # Already a 2-letter code — uppercase it
        if len(s) == 2 and s.isalpha():
            return s.upper()
        return s

    df[col] = df[col].apply(_map)
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Currency code standardisation ─────────────────────────────────────────────

_CURRENCY_MAP: dict[str, str] = {
    "£": "GBP", "gbp": "GBP", "sterling": "GBP", "pound": "GBP",
    "$": "USD", "usd": "USD", "us dollar": "USD", "dollar": "USD",
    "€": "EUR", "eur": "EUR", "euro": "EUR",
    "¥": "JPY", "jpy": "JPY", "yen": "JPY",
    "cny": "CNY", "rmb": "CNY", "renminbi": "CNY",
    "inr": "INR", "rupee": "INR",
    "aud": "AUD", "a$": "AUD",
    "cad": "CAD", "c$": "CAD",
    "chf": "CHF", "franc": "CHF",
    "sek": "SEK", "nok": "NOK", "dkk": "DKK",
    "sgd": "SGD", "s$": "SGD",
    "hkd": "HKD", "hk$": "HKD",
    "krw": "KRW", "won": "KRW",
    "aed": "AED", "dirham": "AED",
    "sar": "SAR", "riyal": "SAR",
    "try": "TRY", "lira": "TRY",
    "brl": "BRL", "real": "BRL",
    "mxn": "MXN", "peso": "MXN",
    "zar": "ZAR", "rand": "ZAR",
}


def standardise_currency(
    df: pd.DataFrame, col: str
) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].apply(
        lambda v: _CURRENCY_MAP.get(str(v).strip().lower(), str(v).strip().upper())
        if pd.notna(v) else v
    )
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Unit of measure standardisation ──────────────────────────────────────────

_UOM_MAP: dict[str, str] = {
    "kg": "KG", "kgs": "KG", "kilogram": "KG", "kilograms": "KG",
    "g": "G", "gram": "G", "grams": "G",
    "t": "MT", "tonne": "MT", "mt": "MT", "metric ton": "MT", "metric_ton": "MT",
    "lbs": "LBS", "lb": "LBS", "pound": "LBS",
    "pcs": "PCS", "piece": "PCS", "pieces": "PCS", "each": "PCS", "units": "PCS",
    "l": "LTR", "ltr": "LTR", "litre": "LTR", "liter": "LTR", "ltrs": "LTR",
    "ml": "ML", "millilitre": "ML", "milliliter": "ML",
    "m3": "M3", "cbm": "M3", "cubic meter": "M3", "cubic metre": "M3",
    "m2": "M2", "sqm": "M2", "square meter": "M2",
    "m": "M", "metre": "M", "meter": "M",
    "ft": "FT", "feet": "FT", "foot": "FT",
    "doz": "DOZ", "dozen": "DOZ",
    "pair": "PAIR", "pairs": "PAIR",
}


def standardise_uom(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].apply(
        lambda v: _UOM_MAP.get(str(v).strip().lower(), str(v).strip().upper())
        if pd.notna(v) else v
    )
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── HS chapter lookup ─────────────────────────────────────────────────────────

_HS_CHAPTERS: dict[str, str] = {
    "01": "Live Animals", "02": "Meat & Offal", "03": "Fish",
    "04": "Dairy & Eggs", "05": "Animal Products", "06": "Plants",
    "07": "Vegetables", "08": "Fruit & Nuts", "09": "Coffee & Spices",
    "10": "Cereals", "11": "Milling Products", "12": "Oil Seeds",
    "15": "Animal/Veg Fats", "16": "Prepared Meat/Fish", "17": "Sugar",
    "18": "Cocoa", "19": "Cereal Preparations", "20": "Vegetable Preparations",
    "21": "Misc Food", "22": "Beverages", "23": "Food Residues",
    "24": "Tobacco", "25": "Salt & Minerals", "26": "Ores",
    "27": "Fuels & Oils", "28": "Chemicals (Inorganic)", "29": "Chemicals (Organic)",
    "30": "Pharmaceuticals", "31": "Fertilisers", "32": "Pigments & Dyes",
    "33": "Cosmetics", "34": "Soaps", "35": "Glues & Enzymes",
    "39": "Plastics", "40": "Rubber", "41": "Hides & Skins",
    "42": "Leather Goods", "43": "Furs", "44": "Wood",
    "47": "Pulp", "48": "Paper", "49": "Printed Matter",
    "50": "Silk", "51": "Wool", "52": "Cotton",
    "54": "Man-made Filaments", "55": "Man-made Fibres",
    "61": "Knitted Clothing", "62": "Woven Clothing",
    "63": "Textiles (Other)", "64": "Footwear", "65": "Headgear",
    "69": "Ceramics", "70": "Glass", "71": "Precious Stones & Metals",
    "72": "Iron & Steel", "73": "Iron/Steel Articles", "74": "Copper",
    "75": "Nickel", "76": "Aluminium", "79": "Zinc",
    "84": "Machinery", "85": "Electrical Equipment",
    "86": "Railway", "87": "Vehicles", "88": "Aircraft",
    "89": "Ships", "90": "Optical/Medical Instruments",
    "91": "Clocks & Watches", "92": "Musical Instruments",
    "94": "Furniture", "95": "Toys", "96": "Misc Manufactures",
}


def hs_chapter(code: str) -> str:
    if pd.isna(code) or len(str(code)) < 2:
        return "Unknown"
    return _HS_CHAPTERS.get(str(code)[:2], f"Chapter {str(code)[:2]}")


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class TradeResult:
    cleaned_df:      pd.DataFrame
    metrics:         dict
    hs_col:          Optional[str] = None
    origin_col:      Optional[str] = None
    dest_col:        Optional[str] = None
    value_col:       Optional[str] = None
    currency_col:    Optional[str] = None
    issues:          list = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_trade_cleaning(df: pd.DataFrame) -> TradeResult:
    """Run all trade/import-export cleaning steps and return a TradeResult."""
    cleaned = df.copy()
    issues: list[dict] = []
    metrics: dict = {}

    hs_col       = _detect(cleaned, _HS_KW)
    origin_col   = _detect(cleaned, _ORIGIN_KW)
    dest_col     = _detect(cleaned, _DEST_KW)
    value_col    = _detect(cleaned, _VALUE_KW)
    currency_col = _detect(cleaned, _CURRENCY_KW)
    unit_col     = _detect(cleaned, _UNIT_KW)
    dir_col      = _detect(cleaned, _DIR_KW)

    # 1. HS code validation
    if hs_col:
        cleaned, hs_fixed, hs_invalid = validate_hs_codes(cleaned, hs_col)
        if hs_fixed:
            issues.append({
                "type": "HS Code Zero-Padding",
                "description": f"{hs_fixed:,} HS code(s) zero-padded to 6 digits.",
                "count": hs_fixed,
            })
        if hs_invalid:
            issues.append({
                "type": "Invalid HS Codes",
                "description": f"{hs_invalid:,} HS code(s) are non-numeric or non-standard length.",
                "count": hs_invalid,
            })
        # Chapter breakdown
        valid_codes = cleaned[hs_col].dropna().astype(str)
        if not valid_codes.empty:
            chapters = valid_codes.apply(hs_chapter).value_counts().head(10)
            metrics["hs_chapters"] = chapters.to_dict()

    # 2. Country of origin normalisation
    if origin_col:
        cleaned, origin_changed = normalise_country_codes(cleaned, origin_col)
        metrics["origin_counts"] = cleaned[origin_col].value_counts().head(10).to_dict()
        if origin_changed:
            issues.append({
                "type": "Origin Country Normalisation",
                "description": f"{origin_changed:,} country name(s) converted to ISO codes.",
                "count": origin_changed,
            })

    # 3. Destination country normalisation
    if dest_col:
        cleaned, dest_changed = normalise_country_codes(cleaned, dest_col)
        metrics["dest_counts"] = cleaned[dest_col].value_counts().head(10).to_dict()
        if dest_changed:
            issues.append({
                "type": "Destination Country Normalisation",
                "description": f"{dest_changed:,} destination country name(s) converted to ISO codes.",
                "count": dest_changed,
            })

    # 4. Currency standardisation
    if currency_col:
        cleaned, ccy_changed = standardise_currency(cleaned, currency_col)
        metrics["currency_counts"] = cleaned[currency_col].value_counts().to_dict()
        if ccy_changed:
            issues.append({
                "type": "Currency Standardisation",
                "description": f"{ccy_changed:,} currency value(s) standardised to ISO 4217.",
                "count": ccy_changed,
            })

    # 5. Unit of measure standardisation
    if unit_col:
        cleaned, uom_changed = standardise_uom(cleaned, unit_col)
        metrics["uom_counts"] = cleaned[unit_col].value_counts().to_dict()
        if uom_changed:
            issues.append({
                "type": "Unit of Measure Standardisation",
                "description": f"{uom_changed:,} unit of measure value(s) standardised.",
                "count": uom_changed,
            })

    # 6. Value sanity check
    if value_col and pd.api.types.is_numeric_dtype(cleaned[value_col]):
        negative_vals = int((cleaned[value_col] < 0).sum())
        zero_vals     = int((cleaned[value_col] == 0).sum())
        total_value   = float(cleaned[value_col].sum())
        metrics["total_declared_value"] = total_value
        metrics["avg_value"] = float(cleaned[value_col].mean())
        if negative_vals:
            issues.append({
                "type": "Negative Declared Values",
                "description": f"{negative_vals:,} record(s) have a negative declared value — verify customs declarations.",
                "count": negative_vals,
            })
        if zero_vals:
            issues.append({
                "type": "Zero Declared Values",
                "description": f"{zero_vals:,} record(s) have a zero declared value — may indicate gifts, samples, or missing data.",
                "count": zero_vals,
            })

    # 7. Trade direction summary
    if dir_col:
        metrics["direction_counts"] = cleaned[dir_col].value_counts().to_dict()

    metrics["total_records"] = len(cleaned)
    metrics["issues_found"]  = len([i for i in issues if i["count"] > 0])

    return TradeResult(
        cleaned_df=cleaned,
        metrics=metrics,
        hs_col=hs_col,
        origin_col=origin_col,
        dest_col=dest_col,
        value_col=value_col,
        currency_col=currency_col,
        issues=issues,
    )

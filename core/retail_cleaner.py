"""Retail & Inventory dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. SKU standardisation        — strips spaces, enforces uppercase
  2. Price / cost validation    — flags where cost > selling price (negative margin)
  3. Negative stock detection   — flags on-hand quantities below zero
  4. Below-reorder alerts       — flags items at or below reorder point
  5. Barcode format validation  — checks EAN-13 / UPC-A digit structure and check digit
  6. Category standardisation   — title-cases category values
  7. Duplicate SKU detection    — identifies SKU conflicts
  8. Zero price detection       — unpriced items that would cause revenue issues
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np

from core.column_mapper import _detect  # noqa: F401


# ── Column keyword maps ───────────────────────────────────────────────────────

_SKU_KW       = ["sku", "product_code", "item_code", "article", "product_id",
                  "item_id", "stock_code", "part_no", "part_number"]
_NAME_KW      = ["product_name", "name", "description", "product_desc",
                  "item_name", "product_title", "article_name"]
_PRICE_KW     = ["price", "selling_price", "retail_price", "unit_price",
                  "rrp", "sale_price", "list_price"]
_COST_KW      = ["cost", "unit_cost", "buying_price", "cost_price",
                  "purchase_price", "landed_cost", "net_cost"]
_STOCK_KW     = ["stock", "quantity", "qty", "inventory", "stock_level",
                  "on_hand", "available", "qty_on_hand", "stock_on_hand"]
_REORDER_KW   = ["reorder_point", "reorder_level", "min_stock", "safety_stock",
                  "reorder_qty", "min_qty"]
_CATEGORY_KW  = ["category", "product_category", "department", "product_group",
                  "category_name", "section", "class"]
_SUPPLIER_KW  = ["supplier", "vendor", "supplier_name", "vendor_name",
                  "supplier_code", "vendor_code", "manufacturer"]
_BARCODE_KW   = ["barcode", "ean", "upc", "gtin", "ean13", "upc_a", "isbn",
                  "barcode_no"]




# ── SKU standardisation ───────────────────────────────────────────────────────

def standardise_skus(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Strip whitespace and uppercase SKUs. Returns (df, changed_count)."""
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].astype(str).str.strip().str.upper().where(df[col].notna(), other=None)
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Duplicate SKU detection ───────────────────────────────────────────────────

def detect_duplicate_skus(df: pd.DataFrame, col: str) -> int:
    """Return count of rows with a duplicated SKU value."""
    return int(df[col].duplicated(keep=False).sum())


# ── Price / cost margin check ─────────────────────────────────────────────────

def check_price_cost_margin(
    df: pd.DataFrame, price_col: str, cost_col: str
) -> tuple[int, int, float]:
    """Return (negative_margin_count, zero_price_count, avg_margin_pct)."""
    price = pd.to_numeric(df[price_col], errors="coerce")
    cost  = pd.to_numeric(df[cost_col],  errors="coerce")

    both_present      = price.notna() & cost.notna()
    negative_margin   = int(((cost > price) & both_present).sum())
    zero_price        = int((price == 0).sum())

    # Gross margin % = (price - cost) / price * 100
    valid = both_present & (price > 0)
    avg_margin = float(((price[valid] - cost[valid]) / price[valid] * 100).mean()) if valid.any() else 0.0

    return negative_margin, zero_price, round(avg_margin, 1)


# ── Stock level checks ────────────────────────────────────────────────────────

def check_stock_levels(
    df: pd.DataFrame, stock_col: str, reorder_col: Optional[str]
) -> tuple[int, int]:
    """Return (negative_stock_count, below_reorder_count)."""
    stock = pd.to_numeric(df[stock_col], errors="coerce")
    negative_stock = int((stock < 0).sum())

    below_reorder = 0
    if reorder_col and reorder_col in df.columns:
        reorder = pd.to_numeric(df[reorder_col], errors="coerce")
        below_reorder = int((stock.notna() & reorder.notna() & (stock <= reorder)).sum())

    return negative_stock, below_reorder


# ── Barcode validation ────────────────────────────────────────────────────────

def _ean13_check_digit(digits: str) -> bool:
    """Validate EAN-13 check digit (last digit)."""
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = sum(
        int(d) * (1 if i % 2 == 0 else 3)
        for i, d in enumerate(digits[:12])
    )
    expected = (10 - (total % 10)) % 10
    return int(digits[12]) == expected


def _upca_check_digit(digits: str) -> bool:
    """Validate UPC-A check digit (12 digits)."""
    if len(digits) != 12 or not digits.isdigit():
        return False
    total = sum(
        int(d) * (3 if i % 2 == 0 else 1)
        for i, d in enumerate(digits[:11])
    )
    expected = (10 - (total % 10)) % 10
    return int(digits[11]) == expected


def validate_barcodes(df: pd.DataFrame, col: str) -> tuple[int, int]:
    """Return (invalid_format_count, invalid_check_digit_count)."""
    invalid_format = 0
    invalid_check  = 0

    for v in df[col].dropna():
        s = str(v).strip().replace(" ", "").replace("-", "")
        if not s.isdigit():
            invalid_format += 1
            continue
        if len(s) == 13:
            if not _ean13_check_digit(s):
                invalid_check += 1
        elif len(s) == 12:
            if not _upca_check_digit(s):
                invalid_check += 1
        elif len(s) not in (8, 14):
            invalid_format += 1

    return invalid_format, invalid_check


# ── Category standardisation ──────────────────────────────────────────────────

def standardise_categories(df: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Title-case category values and strip whitespace."""
    df = df.copy()
    original = df[col].copy()
    df[col] = df[col].astype(str).str.strip().str.title().where(df[col].notna(), other=None)
    changed = int((df[col].fillna("") != original.fillna("")).sum())
    return df, changed


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class RetailResult:
    cleaned_df:  pd.DataFrame
    metrics:     dict
    sku_col:     Optional[str] = None
    price_col:   Optional[str] = None
    cost_col:    Optional[str] = None
    stock_col:   Optional[str] = None
    reorder_col: Optional[str] = None
    cat_col:     Optional[str] = None
    issues:      list = field(default_factory=list)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def apply_retail_cleaning(df: pd.DataFrame) -> RetailResult:
    """Run all retail/inventory cleaning steps and return a RetailResult."""
    cleaned = df.copy()
    issues: list[dict] = []
    metrics: dict = {}

    sku_col      = _detect(cleaned, _SKU_KW)
    name_col     = _detect(cleaned, _NAME_KW)
    price_col    = _detect(cleaned, _PRICE_KW)
    cost_col     = _detect(cleaned, _COST_KW)
    stock_col    = _detect(cleaned, _STOCK_KW)
    reorder_col  = _detect(cleaned, _REORDER_KW)
    cat_col      = _detect(cleaned, _CATEGORY_KW)
    supplier_col = _detect(cleaned, _SUPPLIER_KW)
    barcode_col  = _detect(cleaned, _BARCODE_KW)

    # 1. SKU standardisation
    if sku_col:
        cleaned, sku_changed = standardise_skus(cleaned, sku_col)
        if sku_changed:
            issues.append({
                "type": "SKU Standardisation",
                "description": f"{sku_changed:,} SKU(s) trimmed and uppercased.",
                "count": sku_changed,
            })
        # Duplicate SKUs
        dup_skus = detect_duplicate_skus(cleaned, sku_col)
        metrics["unique_skus"] = int(cleaned[sku_col].nunique())
        if dup_skus:
            issues.append({
                "type": "Duplicate SKUs",
                "description": (
                    f"{dup_skus:,} record(s) share a duplicate SKU — potential data entry "
                    "errors or product variants that need separate codes."
                ),
                "count": dup_skus,
            })

    # 2. Category standardisation
    if cat_col:
        cleaned, cat_changed = standardise_categories(cleaned, cat_col)
        metrics["category_counts"] = cleaned[cat_col].value_counts().head(15).to_dict()
        if cat_changed:
            issues.append({
                "type": "Category Standardisation",
                "description": f"{cat_changed:,} category values standardised to title case.",
                "count": cat_changed,
            })

    # 3. Supplier distribution
    if supplier_col:
        metrics["supplier_counts"] = cleaned[supplier_col].value_counts().head(10).to_dict()

    # 4. Price / cost margin
    if price_col and cost_col:
        neg_margin, zero_price, avg_margin = check_price_cost_margin(
            cleaned, price_col, cost_col
        )
        metrics["avg_gross_margin_pct"] = avg_margin
        price_num = pd.to_numeric(cleaned[price_col], errors="coerce")
        cost_num  = pd.to_numeric(cleaned[cost_col],  errors="coerce")
        metrics["avg_price"] = round(float(price_num.mean()), 2) if price_num.notna().any() else None
        metrics["avg_cost"]  = round(float(cost_num.mean()),  2) if cost_num.notna().any()  else None

        if neg_margin:
            issues.append({
                "type": "Negative Margin Items",
                "description": (
                    f"{neg_margin:,} item(s) have a cost price higher than selling price — "
                    "these will generate a loss on every sale."
                ),
                "count": neg_margin,
            })
        if zero_price:
            issues.append({
                "type": "Zero Selling Price",
                "description": f"{zero_price:,} item(s) have a selling price of zero — may be missing or incorrectly entered.",
                "count": zero_price,
            })
    elif price_col:
        price_num = pd.to_numeric(cleaned[price_col], errors="coerce")
        zero_price = int((price_num == 0).sum())
        metrics["avg_price"] = round(float(price_num.mean()), 2) if price_num.notna().any() else None
        if zero_price:
            issues.append({
                "type": "Zero Selling Price",
                "description": f"{zero_price:,} item(s) have a selling price of zero.",
                "count": zero_price,
            })

    # 5. Stock level checks
    if stock_col:
        neg_stock, below_reorder = check_stock_levels(cleaned, stock_col, reorder_col)
        stock_num = pd.to_numeric(cleaned[stock_col], errors="coerce")
        metrics["total_stock_units"] = int(stock_num.sum()) if stock_num.notna().any() else None
        metrics["avg_stock"]         = round(float(stock_num.mean()), 1) if stock_num.notna().any() else None

        if neg_stock:
            issues.append({
                "type": "Negative Stock Levels",
                "description": f"{neg_stock:,} item(s) show negative on-hand stock — review for data entry errors or unprocessed returns.",
                "count": neg_stock,
            })
        if below_reorder:
            issues.append({
                "type": "Below Reorder Point",
                "description": (
                    f"{below_reorder:,} item(s) are at or below their reorder point — "
                    "these should be flagged for replenishment."
                ),
                "count": below_reorder,
            })

    # 6. Barcode validation
    if barcode_col:
        invalid_fmt, invalid_chk = validate_barcodes(cleaned, barcode_col)
        if invalid_fmt:
            issues.append({
                "type": "Invalid Barcode Format",
                "description": f"{invalid_fmt:,} barcode(s) are not standard EAN-13, UPC-A, or EAN-8 format.",
                "count": invalid_fmt,
            })
        if invalid_chk:
            issues.append({
                "type": "Invalid Barcode Check Digit",
                "description": f"{invalid_chk:,} barcode(s) have an incorrect check digit — may cause scanner errors.",
                "count": invalid_chk,
            })

    # 7. Missing product names
    if name_col:
        missing_names = int(cleaned[name_col].isna().sum())
        if missing_names:
            issues.append({
                "type": "Missing Product Names",
                "description": f"{missing_names:,} item(s) have no product name.",
                "count": missing_names,
            })

    metrics["total_products"] = len(cleaned)
    metrics["issues_found"]   = len([i for i in issues if i["count"] > 0])

    return RetailResult(
        cleaned_df=cleaned,
        metrics=metrics,
        sku_col=sku_col,
        price_col=price_col,
        cost_col=cost_col,
        stock_col=stock_col,
        reorder_col=reorder_col,
        cat_col=cat_col,
        issues=issues,
    )

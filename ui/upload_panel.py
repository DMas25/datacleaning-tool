"""Step 1: File upload panel for ColtraDataAi."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from config.plans import get_next_paid_plan
from core.file_loader import load_file, apply_row_limit
from services.access_control import validate_capacity
from services.ledger_analyser import detect_file_type
from ui.branding_components import render_step_header
from ui.paywall import paywall_card, render_upgrade_cta_button
from utils.session_helpers import get_plan_key

_TIER_TO_PLAN_KEY: dict[str, str] = {
    "free": "free", "starter": "starter",
    "pro": "professional", "professional": "professional",
    "premium": "premium", "enterprise": "enterprise",
}

_FILE_TYPE_LABELS = {
    "gl":             ("General Ledger Export", "Debit/credit balance check, Benford's Law, and period-end analysis will run."),
    "bank_statement": ("Bank Statement",         "Duplicate payment detection, round-number testing, and cash flow analysis will run."),
    "invoice_list":   ("Invoice / Purchase List","Duplicate invoice detection, supplier concentration, and VAT-sensitive amount checks will run."),
    "general":        ("General Dataset",        "Standard cleaning and statistical analysis will run."),
}


def render_upload_panel(branding: dict, tier_row_limit: Optional[int], tier_name: str = "Free") -> Optional[pd.DataFrame]:
    """
    Render the file upload widget and return a loaded DataFrame on success,
    or None if no file has been uploaded yet.

    Row-limit truncation is applied here using the active plan's limit.
    """
    render_step_header(
        1,
        "Upload Dataset",
        "Supported file types: CSV · XLSX · XLS &nbsp;·&nbsp; Max 200 MB",
        branding,
    )

    uploaded_file = st.file_uploader(
        "Upload your file",
        type=["csv", "xlsx", "xls"],
        help="Accepted formats: CSV, Excel (.xlsx or .xls). Max 200 MB.",
    )

    if uploaded_file is None:
        return None

    df = load_file(uploaded_file)

    if df is None:
        st.error("Could not read the file. Please check it is a valid CSV or Excel file and try again.")
        return None

    try:
        file_size_mb = uploaded_file.size / (1024 * 1024)
    except Exception:
        file_size_mb = 0.0

    row_count = len(df)

    valid_capacity, reason = validate_capacity(get_plan_key(), row_count, file_size_mb)
    if not valid_capacity:
        paywall_card("Unlock Full Dataset Processing", reason)
        render_upgrade_cta_button(get_next_paid_plan(get_plan_key()), key_suffix="capacity")
        st.stop()

    df = apply_row_limit(df, tier_row_limit, tier_name)

    # ── Instant file summary ──────────────────────────────────────────────────
    file_type = detect_file_type(df)
    type_label, type_hint = _FILE_TYPE_LABELS.get(file_type, _FILE_TYPE_LABELS["general"])

    st.success(f"File loaded: **{uploaded_file.name}**")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rows", f"{len(df):,}")
    m2.metric("Columns", str(len(df.columns)))
    m3.metric("File size", f"{file_size_mb:.1f} MB")
    m4.metric("Type detected", type_label)

    st.caption(f"**{type_label}** detected — {type_hint}")

    with st.expander("Preview first 5 rows", expanded=False):
        st.dataframe(df.head(5), use_container_width=True)

    return df

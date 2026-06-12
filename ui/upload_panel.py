"""Step 1: File upload panel for ColtraDataAi."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from config.plans import get_next_paid_plan
from core.file_loader import load_file, apply_row_limit
from services.access_control import validate_capacity
from ui.branding_components import render_step_header
from ui.paywall import paywall_card, render_upgrade_cta_button
from utils.session_helpers import get_plan_key

_TIER_TO_PLAN_KEY: dict[str, str] = {
    "free": "free", "starter": "starter",
    "pro": "professional", "professional": "professional",
    "premium": "premium", "enterprise": "enterprise",
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

    try:
        file_size_mb = uploaded_file.size / (1024 * 1024)
    except Exception:
        file_size_mb = 0.0

    row_count = len(df) if df is not None else 0

    valid_capacity, reason = validate_capacity(get_plan_key(), row_count, file_size_mb)
    if not valid_capacity:
        paywall_card("Unlock Full Dataset Processing", reason)
        render_upgrade_cta_button(get_next_paid_plan(get_plan_key()), key_suffix="capacity")
        st.stop()

    df = apply_row_limit(df, tier_row_limit, tier_name)
    return df

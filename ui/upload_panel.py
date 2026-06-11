"""Step 1: File upload panel for ColtraDataAi."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from core.file_loader import load_file, apply_row_limit
from services.access_control import validate_capacity
from ui.branding_components import render_step_header

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

    file_mb = uploaded_file.size / (1024 * 1024)
    plan_key = _TIER_TO_PLAN_KEY.get(tier_name.lower(), "free")
    ok, reason = validate_capacity(plan_key, len(df), file_mb)
    if not ok:
        st.error(reason)
        return None

    df = apply_row_limit(df, tier_row_limit, tier_name)
    return df

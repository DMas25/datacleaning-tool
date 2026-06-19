"""Centralised file-loading layer for ColtraDataAi.

Accepts a Streamlit UploadedFile object, detects the format from the
extension, and returns a validated pandas DataFrame.  All format-specific
engine selection is handled here so callers never need to branch on type.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services.access_control import validate_capacity
from services.subscription import get_user_plan_from_subscription
from ui.paywall import paywall_card


SUPPORTED_EXTENSIONS: tuple[str, ...] = ("csv", "xlsx", "xls")
MAX_ROWS_PREVIEW = 5_000_000   # hard ceiling before memory warnings


def load_file(uploaded_file) -> pd.DataFrame:
    """
    Read *uploaded_file* (st.UploadedFile) into a DataFrame.

    Raises ``ValueError`` on unsupported extension.
    Calls ``st.error`` + ``st.stop`` on read failure so callers don't need
    to wrap this in a try/except.
    """
    ext = _get_extension(uploaded_file.name)

    try:
        if ext == "csv":
            df = pd.read_csv(uploaded_file)
        elif ext == "xls":
            df = pd.read_excel(uploaded_file, engine="xlrd")
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")
    except Exception as exc:
        st.error(
            f"Could not read **{uploaded_file.name}**. "
            "Please check the file isn't corrupted, password-protected, or in an unsupported format."
        )
        st.stop()

    if df.empty or len(df.columns) == 0:
        st.error("The uploaded file contains no data. Please upload a non-empty file.")
        st.stop()

    return df


def apply_row_limit(df: pd.DataFrame, limit: int | None, tier_name: str) -> pd.DataFrame:
    """
    Truncate *df* to *limit* rows and warn the user.
    Returns *df* unchanged if *limit* is None or not exceeded.
    """
    user_plan = get_user_plan_from_subscription()

    row_count = len(df)
    valid, message = validate_capacity(user_plan, row_count, file_size_mb=0.0)

    if not valid:
        paywall_card("Upgrade required", message)
        st.stop()

    if limit is None or row_count <= limit:
        return df

    return df.head(limit)


def _get_extension(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '.{ext}'. "
            f"Accepted formats: {', '.join(SUPPORTED_EXTENSIONS)}."
        )
    return ext

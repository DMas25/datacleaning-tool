"""Step 2: Cleaning configuration panel for ColtraDataAi."""
from __future__ import annotations

import streamlit as st

from core.cleaner import CleaningOptions
from ui.branding_components import render_step_header


def render_cleaning_options(branding: dict) -> CleaningOptions:
    """
    Render the cleaning configuration widgets and return a CleaningOptions
    dataclass populated from user selections.
    """
    render_step_header(2, "Configure Cleaning Options", branding=branding)

    c1, c2, c3 = st.columns(3)

    with c1:
        remove_duplicates = st.checkbox("Remove duplicates", value=True)
    with c2:
        trim_whitespace = st.checkbox("Trim whitespace", value=True)
    with c3:
        standardise_headers = st.checkbox("Standardise headers", value=True)

    null_handling = st.selectbox(
        "Missing values handling",
        ["No Change", "Fill with blank", "Fill with placeholder"],
    )

    return CleaningOptions(
        remove_duplicates=remove_duplicates,
        trim_whitespace=trim_whitespace,
        standardise_headers=standardise_headers,
        null_handling=null_handling,
    )

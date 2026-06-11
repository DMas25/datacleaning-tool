"""Step 3: Raw data preview and file summary panel for ColtraDataAi."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.profiler import profile_dataframe
from ui.branding_components import render_step_header


def render_preview_panel(df: pd.DataFrame, branding: dict) -> None:
    """Render a two-column layout: raw data preview (left) + key metrics (right)."""
    render_step_header(3, "Preview and Summary", branding=branding)

    profile = profile_dataframe(df)

    p1, p2 = st.columns([2, 1])

    with p1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Raw Data Preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with p2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### File Summary")
        st.metric("Rows",            f"{profile['rows']:,}")
        st.metric("Columns",         profile["columns"])
        st.metric("Missing Values",  f"{profile['missing_total']:,}")
        st.metric("Duplicate Rows",  f"{profile['duplicate_total']:,}")
        st.metric("Completeness",    f"{profile['completeness_pct']}%")
        st.markdown('</div>', unsafe_allow_html=True)

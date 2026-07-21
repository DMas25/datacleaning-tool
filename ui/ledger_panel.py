"""Audit Intelligence panel — renders ledger analysis results for accounting/bookkeeping files."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.ledger_analyser import LedgerAnalysis


_FILE_TYPE_LABELS = {
    "gl":             "General Ledger Export",
    "bank_statement": "Bank Statement",
    "invoice_list":   "Invoice / Purchase List",
    "general":        "General Financial Data",
}

_SEVERITY = {
    "high":   {"icon": "🔴", "label": "High Risk",  "colour": "#DC2626"},
    "medium": {"icon": "🟡", "label": "Medium",     "colour": "#D97706"},
    "low":    {"icon": "🔵", "label": "Low",        "colour": "#2563EB"},
    "info":   {"icon": "🟢", "label": "Clear",      "colour": "#059669"},
}


def render_ledger_panel(analysis: LedgerAnalysis, branding: dict) -> None:
    from ui.branding_components import render_section_divider, render_step_header

    render_section_divider(branding=branding)
    render_step_header(
        6, "Audit Intelligence",
        "Rules-based audit checks for bookkeeping and accounting datasets. "
        "Flags are observational — not a substitute for professional audit judgement.",
        branding,
    )

    # ── File type + column detection ──────────────────────────────────────────
    file_label = _FILE_TYPE_LABELS.get(analysis.file_type, "Financial Data")
    st.info(f"File type detected: **{file_label}**")

    if analysis.amount_col or analysis.date_col:
        caption_parts = []
        if analysis.amount_col:
            caption_parts.append(f"Amount column: `{analysis.amount_col}`")
        if analysis.date_col:
            caption_parts.append(f"Date column: `{analysis.date_col}`")
        st.caption(" · ".join(caption_parts))

    # ── Risk summary badges ───────────────────────────────────────────────────
    counts = {sev: 0 for sev in _SEVERITY}
    for flag in analysis.flags:
        if flag.severity in counts:
            counts[flag.severity] += 1

    badge_cols = st.columns(4)
    for col, (sev, cfg) in zip(badge_cols, _SEVERITY.items()):
        with col:
            st.metric(f"{cfg['icon']} {cfg['label']}", counts[sev])

    if not analysis.flags:
        st.info("No audit checks were run — no numeric columns detected in this dataset.")
        return

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Benford's Law chart ───────────────────────────────────────────────────
    if analysis.benford_df is not None:
        st.markdown("#### Benford's Law — First Digit Distribution")
        with st.container(border=True):
            bdf = analysis.benford_df
            fig = go.Figure()
            fig.add_bar(
                x=bdf["Digit"].astype(str),
                y=bdf["Observed %"],
                name="Observed",
                marker_color=branding.get("primary_colour", "#1F4E79"),
            )
            fig.add_scatter(
                x=bdf["Digit"].astype(str),
                y=bdf["Expected %"],
                mode="lines+markers",
                name="Expected (Benford)",
                line=dict(color="#DC2626", dash="dash", width=2),
                marker=dict(size=6),
            )
            fig.update_layout(
                height=340,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="First Significant Digit",
                yaxis_title="Frequency %",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "In naturally occurring financial data, digit 1 should lead ~30% of the time, "
                "digit 2 ~18%, and so on. Significant deviation from this curve can indicate "
                "manipulation, estimation, or a non-organic data source."
            )

    # ── Individual audit flags ────────────────────────────────────────────────
    st.markdown("#### Audit Flags")

    high_flags = [f for f in analysis.flags if f.severity == "high"]
    if high_flags:
        st.warning(f"{len(high_flags)} high-risk finding(s) require attention — see details below.")

    for flag in analysis.flags:
        cfg = _SEVERITY.get(flag.severity, _SEVERITY["info"])
        with st.expander(
            f"{cfg['icon']} {flag.check} — {cfg['label']}",
            expanded=(flag.severity == "high"),
        ):
            st.markdown(flag.finding)
            if flag.detail_df is not None and not flag.detail_df.empty:
                st.caption("Sample affected records (up to 20 shown):")
                st.dataframe(flag.detail_df, use_container_width=True, hide_index=True)

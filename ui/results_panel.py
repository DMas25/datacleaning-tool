"""Steps 4–7: Process, Dashboard, Insights and Download panel for ColtraDataAi.

Processing results are cached in st.session_state so interactive widgets
(chart selectors, distribution dropdowns) do not wipe the results on rerun.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from core.cleaner import CleaningOptions, apply_cleaning
from core.profiler import build_quality_summary_df
from core.insights_engine import generate_insights, detect_date_columns
from core.ai_advisor import generate_ai_advisory
from core.export_manager import generate_reports, build_chart_and_risk
from core.feature_gate import feature_unlocked
from services.entitlements import has_feature
from services.subscription import get_user_plan_from_subscription
from ui.paywall import paywall_card, render_upgrade_cta_button
from core.dashboard_builder import (
    get_numeric_columns,
    get_categorical_columns,
    get_frequency_table,
    get_top_bottom,
    get_correlation_matrix,
    get_time_series,
)
from ui.branding_components import (
    render_step_header,
    render_kpi_row,
    render_risk_kpi,
    render_section_divider,
)

_RESULT_KEY = "coltradata_result"
_INPUT_SHAPE_KEY = "coltradata_input_shape"
_AI_ADVISORY_KEY = "coltradata_ai_advisory"


def render_results_panel(
    df: pd.DataFrame,
    options: CleaningOptions,
    account_tier: str,
    branding: dict,
) -> None:
    """Render Steps 4–7: process button → dashboard → insights → downloads."""
    user_plan = get_user_plan_from_subscription()

    # ── Step 4: Process ───────────────────────────────────────────────────
    render_step_header(4, "Process Dataset", branding=branding)

    # Invalidate stale cached result if the uploaded file changed
    if st.session_state.get(_INPUT_SHAPE_KEY) != df.shape:
        st.session_state.pop(_RESULT_KEY, None)
        st.session_state.pop(_AI_ADVISORY_KEY, None)

    if st.button("Generate Clean Report"):
        with st.spinner("Processing dataset…"):
            result = _run_processing(df, options, branding)
        st.session_state[_RESULT_KEY] = result
        st.session_state[_INPUT_SHAPE_KEY] = df.shape

    result = st.session_state.get(_RESULT_KEY)
    if result is None:
        return

    # ── Post-processing KPI banner ────────────────────────────────────────
    cleaned_df       = result["cleaned_df"]
    risk_summary     = result["risk_summary"]
    total_cells      = cleaned_df.shape[0] * cleaned_df.shape[1]
    missing_post     = int(cleaned_df.isnull().sum().sum())
    completeness_pct = round((1 - missing_post / max(total_cells, 1)) * 100, 1)

    st.success("Report generated successfully.")

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        render_kpi_row([("Original Rows", f"{len(df):,}")], branding)
    with kpi_cols[1]:
        render_kpi_row([("Cleaned Rows", f"{len(cleaned_df):,}")], branding)
    with kpi_cols[2]:
        render_kpi_row([("Rows Removed", f"{len(df) - len(cleaned_df):,}")], branding)
    with kpi_cols[3]:
        render_kpi_row([("Completeness", f"{completeness_pct}%")], branding)
    with kpi_cols[4]:
        render_risk_kpi(risk_summary["overall_risk"])

    st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)

    # ── Step 5: Dashboard Results ─────────────────────────────────────────
    render_step_header(5, "Dashboard Results", branding=branding)
    _render_base_charts(df, cleaned_df, branding)

    # ── Premium chart gallery (Premium+) ─────────────────────────────────
    st.subheader("Premium Chart Gallery")

    if has_feature(user_plan, "can_view_premium_charts"):
        _render_premium_gallery(result, branding)
    else:
        paywall_card(
            "Premium visual analytics are locked",
            "Upgrade to Premium or above to unlock enhanced visual storytelling and premium charts.",
        )
        render_upgrade_cta_button("premium", key_suffix="charts_lock")

    # ── Distribution & trend analysis (Professional+) ─────────────────────
    if has_feature(user_plan, "can_view_advanced_insights"):
        _render_distribution_analysis(cleaned_df, result["date_cols"], branding)
    else:
        paywall_card(
            "Advanced Dashboard Analysis",
            "Distribution, trend, correlation and top/bottom analysis are part of the full reporting suite.",
        )
        render_upgrade_cta_button("professional", key_suffix="dashboard_lock")

    st.markdown("#### Cleaned Data Preview")
    st.dataframe(cleaned_df.head(10), use_container_width=True)

    # ── Step 6: Data Insights ─────────────────────────────────────────────
    render_section_divider(branding=branding)
    render_step_header(
        6, "Data Insights",
        "Structured, descriptive observations generated directly from the data. Observational only — not advice.",
        branding,
    )

    st.subheader("Advanced Data Insights")

    if has_feature(user_plan, "can_view_advanced_insights"):
        insights = generate_insights(cleaned_df)
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        for category, lines in insights.items():
            st.markdown(f"**{category}**")
            for line in lines:
                st.markdown(f"- {line}")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        paywall_card(
            "Advanced insights are locked",
            "Upgrade to Professional or above to unlock deeper diagnostics and richer analysis.",
        )
        render_upgrade_cta_button("professional", key_suffix="insights_lock")

    # ── AI Advisory ───────────────────────────────────────────────────────
    render_section_divider(branding=branding)
    render_step_header(
        6, "AI Advisory",
        "Claude-powered interpretation of your cleaned data — patterns, anomalies, quality risks, and concrete next steps.",
        branding,
    )

    st.subheader("AI Advisory")

    if has_feature(user_plan, "can_view_advanced_insights"):
        advisory = st.session_state.get(_AI_ADVISORY_KEY)
        if advisory is None:
            with st.spinner("Generating AI advisory…"):
                advisory = generate_ai_advisory(cleaned_df)
            st.session_state[_AI_ADVISORY_KEY] = advisory

        if advisory:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(advisory)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info(
                "AI Advisory is unavailable — check that an Anthropic API key is configured in secrets.toml."
            )
    else:
        paywall_card(
            "Advanced insights are locked",
            "Upgrade to Professional or above to unlock deeper diagnostics and richer analysis.",
        )
        render_upgrade_cta_button("professional", key_suffix="advisory_lock")

    # ── Step 7: Download Reports ──────────────────────────────────────────
    render_section_divider(branding=branding)
    render_step_header(7, "Download Reports", branding=branding)

    can_export     = has_feature(user_plan, "can_download_excel")
    can_export_pdf = has_feature(user_plan, "can_download_pdf")
    can_branding   = has_feature(user_plan, "can_brand_reports")

    # ── Excel export ──────────────────────────────────────────────────────
    st.subheader("Excel Report Export")

    if can_export:
        with open(result["excel_path"], "rb") as excel_file_bytes:
            st.download_button(
                label="Download cleaned Excel report",
                data=excel_file_bytes,
                file_name=result["excel_path"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        st.caption(
            "Full multi-sheet workbook: cleaned data, quality log, summary statistics, "
            "and an embedded premium chart gallery."
        )
    else:
        paywall_card(
            "Excel report download is locked",
            "Upgrade to Starter or above to download the full cleaned dataset and structured Excel report.",
        )
        render_upgrade_cta_button("starter", key_suffix="excel_lock")

    # ── PDF export ────────────────────────────────────────────────────────
    st.subheader("PDF Report Export")

    if can_export_pdf:
        branding_note = " Produced with your custom branding." if can_branding else ""
        st.download_button(
            label="Download PDF summary report",
            data=result["pdf_bytes"],
            file_name=result["pdf_filename"],
            mime="application/pdf",
            use_container_width=True,
        )
        st.caption(
            f"Portable executive summary with the same premium charts as the Excel report.{branding_note}"
        )
    else:
        paywall_card(
            "PDF reporting is locked",
            "Upgrade to Professional or above to unlock downloadable PDF reporting.",
        )
        render_upgrade_cta_button("professional", key_suffix="pdf_lock")

    # ── Branded report outputs ────────────────────────────────────────────
    st.subheader("Branded Report Outputs")

    if can_branding:
        st.success("Branding is enabled on this plan. Client-ready branded outputs can be applied.")
        # Place your logo / theme / report styling logic here
    else:
        paywall_card(
            "Branded report outputs are locked",
            "Upgrade to Premium or Enterprise to unlock branded reports and client-facing presentation outputs.",
        )
        render_upgrade_cta_button("premium", key_suffix="branding_lock")


# ── Private helpers ───────────────────────────────────────────────────────────

def _run_processing(df: pd.DataFrame, options: CleaningOptions, branding: dict) -> dict:
    """Apply cleaning, build quality metrics, generate reports, return result dict."""
    cleaning_result      = apply_cleaning(df, options)
    cleaned_df           = cleaning_result.cleaned_df
    log_df               = cleaning_result.log_df

    quality_df           = build_quality_summary_df(df, cleaned_df, options.null_handling)
    date_cols            = detect_date_columns(cleaned_df)

    quality_breakdown_df, risk_summary, chart_assets = build_chart_and_risk(
        branding, df, cleaned_df, date_cols=date_cols
    )

    export = generate_reports(
        branding=branding,
        raw_df=df,
        cleaned_df=cleaned_df,
        log_df=log_df,
        quality_df=quality_df,
        quality_breakdown_df=quality_breakdown_df,
        chart_assets=chart_assets,
        risk_summary=risk_summary,
    )

    return {
        "cleaned_df":           cleaned_df,
        "log_df":               log_df,
        "quality_df":           quality_df,
        "quality_breakdown_df": quality_breakdown_df,
        "date_cols":            date_cols,
        "chart_assets":         chart_assets,
        "risk_summary":         risk_summary,
        "excel_path":           export.excel_path,
        "pdf_bytes":            export.pdf_bytes,
        "pdf_filename":         export.pdf_filename,
    }


def _render_base_charts(df: pd.DataFrame, cleaned_df: pd.DataFrame, branding: dict) -> None:
    """Always-visible baseline charts: missing values + original vs cleaned."""
    d1, d2 = st.columns(2)

    missing_by_col = cleaned_df.isnull().sum().sort_values(ascending=False)
    missing_by_col = missing_by_col[missing_by_col > 0]

    with d1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Missing Values by Column")
        if not missing_by_col.empty:
            fig = px.bar(
                x=missing_by_col.index,
                y=missing_by_col.values,
                labels={"x": "Column", "y": "Missing Values"},
                color=missing_by_col.values,
                color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]],
            )
            fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=80), coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No missing values detected.")
        st.markdown('</div>', unsafe_allow_html=True)

    with d2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### Original vs Cleaned Rows")
        rows_compare = pd.DataFrame({"Stage": ["Original", "Cleaned"], "Rows": [len(df), len(cleaned_df)]})
        fig = px.bar(
            rows_compare, x="Stage", y="Rows", color="Stage",
            color_discrete_map={"Original": branding["secondary_colour"], "Cleaned": branding["primary_colour"]},
        )
        fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


def _render_premium_gallery(result: dict, branding: dict) -> None:
    render_section_divider("Premium Chart Gallery", branding)
    st.markdown("#### Premium Chart Gallery")
    st.caption(
        "High-quality charts generated automatically from your cleaned dataset — the same "
        "visuals are embedded in the Excel Executive Summary and the downloadable PDF report."
    )
    gallery_cols = st.columns(2)
    for idx, (card, _) in enumerate(result["chart_assets"]):
        with gallery_cols[idx % 2]:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown(f"##### {card.title}")
            st.caption(card.description)
            st.plotly_chart(card.figure, use_container_width=True, key=f"gallery_{card.key}")
            st.markdown('</div>', unsafe_allow_html=True)


def _render_distribution_analysis(cleaned_df: pd.DataFrame, date_cols: list, branding: dict) -> None:
    num_cols = get_numeric_columns(cleaned_df)
    cat_cols = get_categorical_columns(cleaned_df, exclude=date_cols)

    st.markdown("#### Distribution Analysis")
    dist1, dist2 = st.columns(2)

    with dist1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### Numerical Distribution")
        if num_cols:
            sel_num = st.selectbox("Select a numeric column", num_cols, key="dist_numeric")
            fig = px.histogram(cleaned_df, x=sel_num, nbins=30, color_discrete_sequence=[branding["primary_colour"]])
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric columns available.")
        st.markdown('</div>', unsafe_allow_html=True)

    with dist2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### Categorical Frequency")
        if cat_cols:
            sel_cat = st.selectbox("Select a categorical column", cat_cols, key="dist_categorical")
            freq_df = get_frequency_table(cleaned_df, sel_cat, top_n=8)
            fig = px.bar(freq_df, x=str(sel_cat), y="Count", color_discrete_sequence=[branding["secondary_colour"]])
            fig.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=80))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No categorical columns available.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Trend analysis
    if date_cols:
        st.markdown("#### Trend Analysis")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        sel_date = st.selectbox("Select a date column", date_cols, key="trend_date")
        trend_df = get_time_series(cleaned_df, sel_date)
        if trend_df is not None and not trend_df.empty:
            fig = px.line(trend_df, x="Date", y="Records", color_discrete_sequence=[branding["primary_colour"]])
            fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Selected column does not contain enough valid date values for a trend chart.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Correlation heatmap
    corr = get_correlation_matrix(cleaned_df)
    if corr is not None:
        st.markdown("#### Correlation Analysis")
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        fig = px.imshow(
            corr, text_auto=".2f",
            color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]],
            aspect="auto",
        )
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Top / Bottom analysis
    st.markdown("#### Top / Bottom Analysis")
    tb1, tb2 = st.columns(2)

    with tb1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### Top Categories")
        if cat_cols:
            sel_top_cat = st.selectbox("Select a categorical column", cat_cols, key="top_categorical")
            st.dataframe(get_frequency_table(cleaned_df, sel_top_cat, top_n=5), use_container_width=True, hide_index=True)
        else:
            st.info("No categorical columns available.")
        st.markdown('</div>', unsafe_allow_html=True)

    with tb2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("##### Highest / Lowest Values")
        if num_cols:
            sel_top_num = st.selectbox("Select a numeric column", num_cols, key="top_numeric")
            top_vals, bottom_vals = get_top_bottom(cleaned_df, sel_top_num, n=5)
            hl1, hl2 = st.columns(2)
            with hl1:
                st.caption("Highest")
                st.dataframe(top_vals.reset_index(drop=True).to_frame(name=str(sel_top_num)), use_container_width=True)
            with hl2:
                st.caption("Lowest")
                st.dataframe(bottom_vals.reset_index(drop=True).to_frame(name=str(sel_top_num)), use_container_width=True)
        else:
            st.info("No numeric columns available.")
        st.markdown('</div>', unsafe_allow_html=True)

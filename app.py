import base64

import streamlit as st
import pandas as pd
import plotly.express as px

from core.report_builder import ReportBuilder
from core.insights_engine import generate_insights, detect_date_columns
from core.chart_gallery import build_chart_gallery
from core.pdf_report import build_pdf_report
from core.dashboard_analytics import (
    numeric_columns,
    categorical_columns,
    frequency_table,
    top_bottom_values,
    correlation_matrix,
    time_series_counts,
)
from core.feature_gate import render_tier_selector, render_locked_feature, feature_unlocked
from config.tier_config import row_limit_for
from config.branding_config import branding

st.set_page_config(page_title=branding["app_name"], layout="wide")

# ---------------------------
# CUSTOM CSS
# ---------------------------
st.markdown(f"""
<style>
    .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}

    .metric-card {{
        background-color: white;
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #E6ECF0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }}

    .section-card {{
        background-color: #FFFFFF;
        padding: 1.2rem;
        border-radius: 14px;
        border: 1px solid #E6ECF0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }}

    .stButton>button {{
        width: 100%;
        border-radius: 10px;
        height: 46px;
        background-color: {branding["primary_colour"]};
        color: white;
        font-weight: 600;
        border: none;
    }}

    .stDownloadButton>button {{
        width: 100%;
        border-radius: 10px;
        height: 46px;
        background-color: {branding["secondary_colour"]};
        color: white;
        font-weight: 600;
        border: none;
    }}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Secure login — gates the entire app via st.secrets
# ---------------------------------------------------------------------------
def _get_configured_password():
    # st.secrets raises StreamlitSecretNotFoundError on access (even via
    # .get) when no secrets.toml exists at all, e.g. a fresh Codespace
    # clone — treat that the same as "no password configured".
    try:
        return st.secrets["credentials"]["password"]
    except (KeyError, st.errors.StreamlitSecretNotFoundError):
        return None


def _check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        f"""
        <div style="max-width:420px;margin:80px auto 0 auto;text-align:center;">
            <div style="font-size:38px;font-weight:800;color:{branding['primary_colour']};margin-bottom:4px;">
                {branding['app_name']}
            </div>
            <div style="font-size:12px;letter-spacing:.26em;color:#657286;text-transform:uppercase;margin-bottom:36px;">
                {branding['tagline']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("##### Sign in to continue")
        pwd = st.text_input(
            "Password",
            type="password",
            label_visibility="collapsed",
            placeholder="Enter password",
        )
        if st.button("Sign in", use_container_width=True, type="primary"):
            configured_password = _get_configured_password()
            if configured_password is None:
                st.error(
                    "No login password is configured. Add a "
                    "[credentials] password to .streamlit/secrets.toml "
                    "(see .streamlit/secrets.toml.example)."
                )
            elif pwd == configured_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
    return False


if not _check_password():
    st.stop()

builder = ReportBuilder(branding)
account_tier = render_tier_selector(branding)
tier_row_limit = row_limit_for(account_tier)

# ---------------------------
# HEADER
# ---------------------------
with open("assets/logo/coltradata_logo.png", "rb") as logo_file:
    logo_b64 = base64.b64encode(logo_file.read()).decode()

st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:0; padding:32px 0 12px 0;">
        <img src="data:image/png;base64,{logo_b64}"
             style="width:234px; height:auto; display:block; flex-shrink:0; border:none; outline:none;" />
        <div style="width:1.5px; height:68px; background:#C8D6DF; margin:0 22px; flex-shrink:0; align-self:center;"></div>
        <div style="display:flex; flex-direction:column; align-items:center; max-width:340px;">
            <h3 style="margin:0; color:{branding['primary_colour']}; letter-spacing:1.5px; font-size:1.05em; text-align:center; white-space:nowrap;">
                DATA &nbsp;&bull;&nbsp; INSIGHTS &nbsp;&bull;&nbsp; INTELLIGENCE
            </h3>
            <p style="margin:6px 0 0 0; color:#657286; font-size:0.82em; line-height:1.5; text-align:center;">
                Generate Structured Cleaned Datasets,<br/>Validation Reports And Visual Data Summaries.
            </p>
        </div>
    </div>
    <hr style="margin:0 0 16px 0; border:none; border-top:1px solid #E6ECF0;" />
    """,
    unsafe_allow_html=True,
)

# ---------------------------
# STEP 1: UPLOAD
# ---------------------------
st.subheader("Step 1: Upload Dataset")
st.caption("Supported file types: CSV, XLSX")

uploaded_file = st.file_uploader("Upload your file", type=["csv", "xlsx"])

if uploaded_file:
    # Load file
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Tier row-limit gate — datasets beyond the active plan's limit are
    # truncated for processing, with an upgrade prompt shown to the user.
    if tier_row_limit is not None and len(df) > tier_row_limit:
        st.warning(
            f"This dataset has {len(df):,} rows, which exceeds the {account_tier} plan limit of "
            f"{tier_row_limit:,} rows. Only the first {tier_row_limit:,} rows will be processed. "
            f"Upgrade your plan to process the full dataset."
        )
        df = df.head(tier_row_limit)

    # ---------------------------
    # STEP 2: CONFIGURE
    # ---------------------------
    st.subheader("Step 2: Configure")
    c1, c2, c3 = st.columns(3)

    with c1:
        remove_duplicates = st.checkbox("Remove duplicates", value=True)

    with c2:
        trim_whitespace = st.checkbox("Trim whitespace", value=True)

    with c3:
        standardise_headers = st.checkbox("Standardise headers", value=True)

    null_handling = st.selectbox(
        "Missing values handling",
        ["No Change", "Fill with blank", "Fill with placeholder"]
    )

    # ---------------------------
    # STEP 3: PREVIEW + SUMMARY
    # ---------------------------
    st.subheader("Step 3: Preview and Summary")

    p1, p2 = st.columns([2, 1])

    with p1:
        with st.container():
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("#### Raw Data Preview")
            st.dataframe(df.head(10), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with p2:
        missing_total = int(df.isnull().sum().sum())
        duplicate_total = int(df.duplicated().sum())

        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown("#### File Summary")
        st.metric("Rows", len(df))
        st.metric("Columns", len(df.columns))
        st.metric("Missing Values", missing_total)
        st.metric("Duplicate Rows", duplicate_total)
        st.markdown('</div>', unsafe_allow_html=True)

    # ---------------------------
    # STEP 4: PROCESS
    # ---------------------------
    st.subheader("Step 4: Process")
    process = st.button("Generate Clean Report")

    if process:
        with st.spinner("Processing dataset..."):
            cleaned_df = df.copy()

            if standardise_headers:
                cleaned_df.columns = [str(c).strip().replace(" ", "_").lower() for c in cleaned_df.columns]

            if trim_whitespace:
                cleaned_df = cleaned_df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))

            if remove_duplicates:
                cleaned_df = cleaned_df.drop_duplicates()

            if null_handling == "Fill with blank":
                cleaned_df = cleaned_df.fillna("")
            elif null_handling == "Fill with placeholder":
                cleaned_df = cleaned_df.fillna("MISSING")

            # Build log dataframe
            log_rows = [
                {"Step": 1, "Action": "File Loaded", "Result": "Completed"},
                {"Step": 2, "Action": "Header Standardisation" if standardise_headers else "Header Standardisation", "Result": "Completed" if standardise_headers else "Skipped"},
                {"Step": 3, "Action": "Whitespace Trimming" if trim_whitespace else "Whitespace Trimming", "Result": "Completed" if trim_whitespace else "Skipped"},
                {"Step": 4, "Action": "Duplicate Removal" if remove_duplicates else "Duplicate Removal", "Result": "Completed" if remove_duplicates else "Skipped"},
                {"Step": 5, "Action": "Missing Value Handling", "Result": null_handling},
            ]
            log_df = pd.DataFrame(log_rows)

            quality_df = pd.DataFrame({
                "Metric": ["Rows", "Columns", "Missing Values", "Duplicate Rows After Cleaning"],
                "Value": [
                    len(cleaned_df),
                    len(cleaned_df.columns),
                    int(cleaned_df.isnull().sum().sum()) if null_handling == "No Change" else 0,
                    int(cleaned_df.duplicated().sum())
                ]
            })

            # Shared analysis used to drive the dashboard, the Excel Executive
            # Summary sheet and the downloadable PDF report — computed once so
            # all three surfaces stay in sync and charts aren't re-rendered.
            date_cols = detect_date_columns(cleaned_df)
            quality_breakdown_df = builder.build_quality_breakdown(cleaned_df)
            risk_summary = builder.build_risk_summary(quality_breakdown_df)
            chart_assets = builder.build_chart_assets(df, cleaned_df, quality_breakdown_df, date_cols=date_cols)

            report_file = builder.build_report(
                df, cleaned_df, log_df, quality_df,
                quality_breakdown_df=quality_breakdown_df,
                chart_assets=chart_assets,
            )
            pdf_report_bytes = build_pdf_report(branding, df, cleaned_df, risk_summary, chart_assets)
            pdf_file_name = report_file.rsplit(".", 1)[0] + ".pdf"

        st.success("Report generated successfully.")

        # ---------------------------
        # STEP 5: DASHBOARD RESULTS
        # ---------------------------
        st.subheader("Step 5: Dashboard Results")

        d1, d2 = st.columns(2)

        # Missing values by column
        missing_by_col = cleaned_df.isnull().sum().sort_values(ascending=False)
        missing_by_col = missing_by_col[missing_by_col > 0]

        with d1:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("#### Missing Values by Column")
            if not missing_by_col.empty:
                fig_missing = px.bar(
                    x=missing_by_col.index,
                    y=missing_by_col.values,
                    labels={"x": "Column", "y": "Missing Values"},
                    color=missing_by_col.values,
                    color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]]
                )
                fig_missing.update_layout(
                    height=380,
                    margin=dict(l=20, r=20, t=30, b=80),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_missing, use_container_width=True)
            else:
                st.info("No missing values detected.")
            st.markdown('</div>', unsafe_allow_html=True)

        with d2:
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown("#### Original vs Cleaned Rows")

            rows_compare = pd.DataFrame({
                "Stage": ["Original", "Cleaned"],
                "Rows": [len(df), len(cleaned_df)]
            })

            fig_rows = px.bar(
                rows_compare,
                x="Stage",
                y="Rows",
                color="Stage",
                color_discrete_map={
                    "Original": branding["secondary_colour"],
                    "Cleaned": branding["primary_colour"]
                }
            )
            fig_rows.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
            st.plotly_chart(fig_rows, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        if feature_unlocked(account_tier, "advanced_dashboards"):
            # ---------------------------
            # PREMIUM CHART GALLERY (auto-generated)
            # ---------------------------
            st.markdown("#### Premium Chart Gallery")
            st.caption(
                "High-quality charts generated automatically from your cleaned dataset — the same "
                "visuals are embedded in the Excel Executive Summary and the downloadable PDF report."
            )
            gallery_cols = st.columns(2)
            for idx, (card, _) in enumerate(chart_assets):
                with gallery_cols[idx % 2]:
                    st.markdown('<div class="section-card">', unsafe_allow_html=True)
                    st.markdown(f"##### {card.title}")
                    st.caption(card.description)
                    st.plotly_chart(card.figure, use_container_width=True, key=f"gallery_{card.key}")
                    st.markdown('</div>', unsafe_allow_html=True)

            # ---------------------------
            # EXTENDED DASHBOARD ANALYSIS (interactive drill-down)
            # ---------------------------
            num_cols = numeric_columns(cleaned_df)
            cat_cols = categorical_columns(cleaned_df, date_cols)

            st.markdown("#### Distribution Analysis")
            dist1, dist2 = st.columns(2)

            with dist1:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown("##### Numerical Distribution")
                if num_cols:
                    selected_num_col = st.selectbox("Select a numeric column", num_cols, key="dist_numeric")
                    fig_hist = px.histogram(
                        cleaned_df, x=selected_num_col,
                        color_discrete_sequence=[branding["primary_colour"]]
                    )
                    fig_hist.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.info("No numeric columns available for distribution analysis.")
                st.markdown('</div>', unsafe_allow_html=True)

            with dist2:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown("##### Categorical Frequency")
                if cat_cols:
                    selected_cat_col = st.selectbox("Select a categorical column", cat_cols, key="dist_categorical")
                    freq_df = frequency_table(cleaned_df, selected_cat_col)
                    fig_freq = px.bar(
                        freq_df, x=str(selected_cat_col), y="Count",
                        color_discrete_sequence=[branding["secondary_colour"]]
                    )
                    fig_freq.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=80))
                    st.plotly_chart(fig_freq, use_container_width=True)
                else:
                    st.info("No categorical columns available for frequency analysis.")
                st.markdown('</div>', unsafe_allow_html=True)

            # Trend analysis (only shown when a date-like column is detected)
            if date_cols:
                st.markdown("#### Trend Analysis")
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                selected_date_col = st.selectbox("Select a date column", date_cols, key="trend_date")
                trend_df = time_series_counts(cleaned_df, selected_date_col)
                if trend_df is not None and not trend_df.empty:
                    fig_trend = px.line(
                        trend_df, x="Date", y="Records",
                        color_discrete_sequence=[branding["primary_colour"]]
                    )
                    fig_trend.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("Selected column does not contain enough valid date values for a trend chart.")
                st.markdown('</div>', unsafe_allow_html=True)

            # Correlation analysis (only shown with 2+ numeric columns)
            corr_matrix = correlation_matrix(cleaned_df)
            if corr_matrix is not None:
                st.markdown("#### Correlation Analysis")
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto=".2f",
                    color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]],
                    aspect="auto"
                )
                fig_corr.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_corr, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # Top / bottom analysis
            st.markdown("#### Top / Bottom Analysis")
            tb1, tb2 = st.columns(2)

            with tb1:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown("##### Top Categories")
                if cat_cols:
                    selected_top_cat_col = st.selectbox("Select a categorical column", cat_cols, key="top_categorical")
                    top_freq_df = frequency_table(cleaned_df, selected_top_cat_col, top_n=5)
                    st.dataframe(top_freq_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No categorical columns available for top-category analysis.")
                st.markdown('</div>', unsafe_allow_html=True)

            with tb2:
                st.markdown('<div class="section-card">', unsafe_allow_html=True)
                st.markdown("##### Highest / Lowest Values")
                if num_cols:
                    selected_top_num_col = st.selectbox("Select a numeric column", num_cols, key="top_numeric")
                    top_vals, bottom_vals = top_bottom_values(cleaned_df, selected_top_num_col, n=5)
                    hl1, hl2 = st.columns(2)
                    with hl1:
                        st.caption("Highest")
                        st.dataframe(top_vals.reset_index(drop=True).to_frame(name=str(selected_top_num_col)), use_container_width=True)
                    with hl2:
                        st.caption("Lowest")
                        st.dataframe(bottom_vals.reset_index(drop=True).to_frame(name=str(selected_top_num_col)), use_container_width=True)
                else:
                    st.info("No numeric columns available for highest/lowest value analysis.")
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            render_locked_feature(
                "Advanced Dashboard Analysis",
                "Distribution, trend, correlation and top/bottom analysis are part of the full reporting suite.",
                required_tier="Pro",
            )

        # Additional detail section
        st.markdown("#### Cleaned Data Preview")
        st.dataframe(cleaned_df.head(10), use_container_width=True)

        # ---------------------------
        # STEP 6: AI DATA INSIGHTS (NON-ADVISORY)
        # ---------------------------
        st.subheader("Step 6: Data Insights")
        st.caption("Structured, descriptive observations generated directly from the data. Observational only — not advice.")

        if feature_unlocked(account_tier, "ai_insights"):
            insights = generate_insights(cleaned_df)

            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            for category, lines in insights.items():
                st.markdown(f"**{category}**")
                for line in lines:
                    st.markdown(f"- {line}")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            render_locked_feature(
                "AI Data Insights",
                "Structured, non-advisory observations on data composition, patterns, anomalies, distributions and completeness.",
                required_tier="Pro",
            )

        # Download
        st.subheader("Step 7: Download")
        if feature_unlocked(account_tier, "export"):
            dl1, dl2 = st.columns(2)
            with dl1:
                with open(report_file, "rb") as f:
                    st.download_button(
                        "Download Structured Excel Report",
                        data=f,
                        file_name=report_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            with dl2:
                st.download_button(
                    "Download Executive Summary (PDF)",
                    data=pdf_report_bytes,
                    file_name=pdf_file_name,
                    mime="application/pdf"
                )
            st.caption(
                "The Excel report contains the full multi-sheet workbook with an embedded chart gallery. "
                "The PDF is a portable executive summary featuring the same premium charts."
            )
        else:
            render_locked_feature(
                "Report Export (Excel & PDF)",
                "Download the full multi-sheet Excel report and a portable PDF executive summary, both featuring an embedded premium chart gallery.",
                required_tier="Pro",
            )

# ---------------------------
# FOOTER
# ---------------------------
st.markdown("---")
st.markdown(
    f"""
    **{branding["app_name"]}**
    Structured data cleaning, validation and dashboard reporting
    Contact: {branding["contact_email"]}
    """
)

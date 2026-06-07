import streamlit as st
import pandas as pd
import plotly.express as px

from core.report_builder import ReportBuilder
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

builder = ReportBuilder(branding)

# ---------------------------
# HEADER
# ---------------------------
head1, head2 = st.columns([1, 4])

with head1:
    st.image("assets/logo/coltradata_logo.png", width=110)

with head2:
    st.markdown(f"**{branding['tagline']}**")
    st.caption("Generate structured cleaned datasets, validation reports and visual data summaries.")

st.markdown("---")

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

            report_file = builder.build_report(df, cleaned_df, log_df, quality_df)

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

        # Additional detail section
        st.markdown("#### Cleaned Data Preview")
        st.dataframe(cleaned_df.head(10), use_container_width=True)

        # Download
        st.subheader("Step 6: Download")
        with open(report_file, "rb") as f:
            st.download_button(
                "Download Structured Excel Report",
                data=f,
                file_name=report_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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

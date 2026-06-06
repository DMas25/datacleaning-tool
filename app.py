import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from core.report_builder import ReportBuilder
from config.branding_config import branding

# --------------------------
# PAGE CONFIG
# --------------------------
st.set_page_config(
    page_title=branding["app_name"],
    layout="wide"
)

# --------------------------
# CSS STYLING
# --------------------------
st.markdown("""
<style>
    .stButton>button {
        border-radius: 8px;
        height: 45px;
        font-size: 16px;
    }

    .stDownloadButton>button {
        border-radius: 8px;
        height: 45px;
        font-size: 16px;
        background-color: #1F4E79;
        color: white;
    }

    .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------
# HEADER
# --------------------------
col1, col2 = st.columns([1, 4])

with col1:
    logo_path = Path("assets/logo/coltradata_logo.png")
    if not logo_path.exists():
        logo_path = Path("assets/New_logo.png")
    if logo_path.exists():
        st.image(str(logo_path), width=110)

with col2:
    st.title(branding["app_name"])
    st.markdown(f"**{branding['tagline']}**")

st.markdown("### Structured Data Cleaning & Reporting")
st.markdown("---")

builder = ReportBuilder(branding)

# --------------------------
# STEP 1 — UPLOAD
# --------------------------
st.markdown("## Step 1: Upload Dataset")
st.caption("Supported formats: CSV, Excel (Max 25MB)")

uploaded_file = st.file_uploader("", type=["csv", "xlsx"])

# --------------------------
# STEP 2 — CONFIGURE
# --------------------------
if uploaded_file:

    st.markdown("## Step 2: Configure Cleaning")

    col1, col2, col3 = st.columns(3)

    with col1:
        remove_duplicates = st.checkbox("Remove duplicates", value=True)

    with col2:
        trim_whitespace = st.checkbox("Trim whitespace", value=True)

    with col3:
        standardise_headers = st.checkbox("Standardise headers", value=True)

    null_handling = st.selectbox(
        "Missing values handling",
        ["No Change", "Fill with blank", "Fill with placeholder"]
    )

# --------------------------
# STEP 3 — PREVIEW
# --------------------------
if uploaded_file:

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.markdown("## Step 3: Data Preview")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.dataframe(df.head(), use_container_width=True)

    with col2:
        st.markdown("### File Summary")
        st.metric("Rows", len(df))
        st.metric("Columns", len(df.columns))
        st.metric("Missing Values", int(df.isnull().sum().sum()))

# --------------------------
# STEP 4 — PROCESS
# --------------------------
if uploaded_file:

    st.markdown("## Step 4: Process Data")
    process = st.button("Generate Clean Report", use_container_width=True)

# --------------------------
# PROCESSING LOGIC
# --------------------------
if uploaded_file and process:

    with st.spinner("Processing dataset..."):

        cleaned_df = df.copy()

        if remove_duplicates:
            cleaned_df = cleaned_df.drop_duplicates()

        if trim_whitespace:
            cleaned_df = cleaned_df.map(
                lambda x: x.strip() if isinstance(x, str) else x
            )

        if standardise_headers:
            cleaned_df.columns = [
                col.strip().lower().replace(" ", "_")
                for col in cleaned_df.columns
            ]

        if null_handling == "Fill with blank":
            cleaned_df = cleaned_df.fillna("")
        elif null_handling == "Fill with placeholder":
            cleaned_df = cleaned_df.fillna("N/A")

        log_df = pd.DataFrame({
            "Step":   [1, 2, 3, 4],
            "Action": [
                "File loaded",
                "Duplicates removed" if remove_duplicates else "Duplicates kept",
                "Whitespace trimmed" if trim_whitespace else "Whitespace unchanged",
                "Headers standardised" if standardise_headers else "Headers unchanged",
            ],
            "Result": ["Success", "Completed", "Completed", "Completed"],
        })

        quality_df = pd.DataFrame({
            "Metric": ["Rows", "Columns", "Missing Values", "Duplicates Removed"],
            "Value": [
                len(cleaned_df),
                len(cleaned_df.columns),
                int(cleaned_df.isnull().sum().sum()),
                len(df) - len(df.drop_duplicates()),
            ],
        })

        report_file = builder.build_report(df, cleaned_df, log_df, quality_df)

    st.success("Report generated successfully")

    # --------------------------
    # STEP 5 — DOWNLOAD
    # --------------------------
    st.markdown("## Step 5: Download Report")

    with open(report_file, "rb") as f:
        st.download_button(
            "Download Structured Report",
            f,
            file_name=Path(report_file).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

# --------------------------
# FOOTER
# --------------------------
st.markdown("---")
st.markdown(
    f"""
    **{branding['app_name']}**
    Data cleaning and structured reporting only (non‑advisory output)
    Contact: {branding['contact_email']}
    """
)

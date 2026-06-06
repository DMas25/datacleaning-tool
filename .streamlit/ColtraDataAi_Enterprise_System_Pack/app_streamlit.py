import io
from pathlib import Path
import streamlit as st
from coltradata.engine import run_pipeline_from_uploaded_file

st.set_page_config(page_title="ColtraDataAi", layout="wide")
st.title("ColtraDataAi — Data Cleaning Report Generator")
st.caption("Upload CSV or Excel data to generate a refined Excel cleaning report with visuals.")

with st.sidebar:
    st.header("Options")
    include_dashboard = st.checkbox("Include dashboard visuals", value=True)
    z_thresh = st.slider("Outlier sensitivity (z-score)", min_value=2.0, max_value=5.0, value=3.0, step=0.1)

uploaded = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded:
    with st.spinner("Processing file..."):
        report_path, preview = run_pipeline_from_uploaded_file(
            uploaded,
            output_dir="output",
            z_threshold=z_thresh,
            include_dashboard=include_dashboard,
        )

    st.success(f"Report generated: {report_path}")

    st.subheader("Preview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", preview.get("rows", 0))
    c2.metric("Columns", preview.get("columns", 0))
    c3.metric("Duplicates removed", preview.get("duplicates_removed", 0))
    c4.metric("Issue count", preview.get("issue_count", 0))

    st.write("**Detected sheets**")
    st.json(preview.get("detected_sheets", {}))

    with open(report_path, "rb") as f:
        st.download_button(
            label="Download refined Excel report",
            data=f.read(),
            file_name=Path(report_path).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.info("Upload a file to begin.")

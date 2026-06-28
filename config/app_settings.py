"""Application-level settings for ColtraDataAi.

Non-branding, non-tier configuration that controls runtime behaviour.
Import ``settings`` from this module anywhere you need these values.
"""

settings = {
    # File upload
    "max_upload_mb":        200,
    "supported_extensions": ["csv", "xlsx", "xls"],

    # Preview
    "preview_rows":         10,    # rows shown in raw/cleaned data previews
    "profile_sample_rows":  5_000, # rows used for profiling (full if smaller)

    # Chart gallery
    "max_numeric_charts":   3,     # max auto-generated numeric distribution charts
    "max_category_charts":  3,     # max auto-generated categorical frequency charts

    # Report filenames
    "excel_prefix":  "ColtraDataAi_Cleaned_Report",
    "pdf_prefix":    "ColtraDataAi_Executive_Summary",

    # Streamlit page
    "page_layout":   "wide",
    "sidebar_state": "expanded",

    # Logging
    "log_level":     "INFO",
    "log_to_file":   True,
    "log_file_path": "logs/coltradata.log",
}

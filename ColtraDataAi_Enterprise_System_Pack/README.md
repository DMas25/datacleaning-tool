# ColtraDataAi Enterprise System Pack

This project contains **both** a local desktop GUI and a local web interface for ColtraDataAi.

## Included interfaces
- **Desktop GUI**: `app_desktop.py` (Tkinter)
- **Web App**: `app_streamlit.py` (Streamlit)

## What the system does
- Accepts CSV and Excel files
- Reads **raw data** and/or **cleaned data** sheets automatically
- Cleans and standardises data
- Produces a refined Excel report with:
  - Raw Data
  - Cleaned Data
  - Executive Summary
  - Data Quality Summary
  - Missing Values by Column
  - Key Metrics Summary
  - Segmentation (top values for categorical fields)
  - Outlier Log
  - Outlier Summary
  - Dashboard Data
  - Dashboard sheet with embedded visuals
  - Data Dictionary
  - Disclaimer
- Creates PNG dashboard charts and embeds them into the Excel workbook

## Quick start
### 1) Create a virtual environment (recommended)
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Run the desktop GUI
```bash
python app_desktop.py
```

### 4) Run the web app
```bash
streamlit run app_streamlit.py
```

## Naming convention expected by the report builder
If your input workbook contains multiple sheets, the engine tries to detect:
- a **raw** sheet if its name contains `raw`
- a **cleaned** sheet if its name contains `clean`

If only one dataset is found, it is used as both source and cleaned baseline for processing.

## Output path
Generated reports are saved into the `output/` folder.

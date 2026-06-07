# ColtraDataAi - Structured Data Cleaning & Dashboard Reporting

**Version:** 2.0  
**By:** Coltrane Ltd  
**Last Updated:** May 2026

## 🎯 Overview

ColtraDataAi is a professional-grade data cleaning, validation, and analytics platform designed for enterprises, accountancy firms, trade compliance teams, and data-driven organizations. It provides automated data quality assessment, advanced anomaly detection, and comprehensive reporting capabilities.

## ✨ Key Features

### 1. **Automated Data Cleaning**
- Intelligent text normalization (trimming, standardization)
- Automatic date format detection and conversion
- Numeric value detection and type conversion
- Support for multiple encodings (UTF-8, CP1252, Latin1)
- Duplicate detection and handling

### 2. **Advanced Analytics Dashboard**
- Real-time data quality scoring (0-100%)
- Missing data pattern visualization
- Data type distribution analysis
- Issue type and risk level breakdown
- Numeric data distribution charts
- Statistical summaries

### 3. **Anomaly Detection Engine**
- Statistical outlier detection (IQR method)
- Sparse data identification
- Email format validation
- Duplicate detection
- Data type consistency checks
- Integrity violation alerts

### 4. **Trade Compliance Mode**
- SITC code validation (1-5 digits)
- HS code validation (6 digits)
- UK HMRC commodity code validation (8-10 digits)
- Compliance reporting

### 5. **Risk-Based Reporting**
- **Critical/High-Risk Flagging:** Immediate client notification alerts
- **Error Classification:** Categorized by issue type and severity
- **Quarantine System:** High-risk rows isolated for manual review
- **Audit Trail:** Complete processing history

### 6. **Multiple Export Formats**
- Excel workbooks (cleaned data + error report + quarantine sheets)
- CSV data exports
- Error logs for compliance documentation

### 7. **Enterprise-Ready Features**
- Logging and audit capability
- GDPR-compliant data handling (no retention)
- Production deployment ready
- Scalable architecture

## 📋 Processing Modes

### Mode 1: General Cleaning
- Standard data cleaning and validation
- General-purpose data quality assessment
- Best for: Spreadsheet cleanup, data consolidation

### Mode 2: Accounting / HMRC Mode
- Financial data validation
- VAT calculation verification
- Tax compliance checks
- Best for: Accountants, bookkeepers, tax firms

### Mode 3: Trade Compliance Mode
- International trade classification validation
- SITC, HS, and UK commodity code checks
- Import/export compliance
- Best for: Customs brokers, logistics, import/export businesses

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip or conda

### Installation

1. **Clone/Download the repository**
```bash
cd DataCleaningApp
```

2. **Create a virtual environment (recommended)**
```bash
# Using venv
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Or using conda
conda create -n coltradata python=3.9
conda activate coltradata
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Running Locally

```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

## 📊 Data Quality Metrics Explained

### Quality Score (%)
- **80-100%:** Excellent - minimal data quality issues
- **60-79%:** Good - some issues require attention
- **40-59%:** Fair - significant data quality concerns
- **<40%:** Poor - extensive cleaning required

### Risk Levels
- **Critical:** Immediate action required, blocks processing
- **High:** Requires manual review before use
- **Medium:** Should be reviewed, may not block use
- **Low:** Informational, minimal business impact

## 🔍 Anomaly Detection Methods

### Statistical Outliers
- **Method:** Interquartile Range (IQR)
- **Formula:** Values outside [Q1 - 1.5×IQR, Q3 + 1.5×IQR]
- **Use Case:** Identifying unusual numeric values

### Sparse Data
- **Detection:** Columns with >50% null values
- **Action:** Flag for review or removal

### Data Type Mismatches
- **Detection:** Invalid email formats, type inconsistencies
- **Action:** Quarantine for manual correction

### Integrity Issues
- **Detection:** Logical errors in related fields
- **Action:** Document for stakeholder review

## 💾 Export Outputs

### Excel Report (.xlsx)
Three sheets:
1. **Cleaned_Data** - Processed and validated data
2. **Error_Report** - All identified issues with details
3. **Quarantined_High_Risk** - Rows requiring manual review

### CSV Exports
- **Cleaned_Data.csv** - Ready-to-use clean data
- **Error_Log.csv** - Issues for compliance documentation

## 🔐 Data Privacy & Security

- **No Data Retention:** Files deleted after session ends
- **Local Processing:** All data processed locally
- **GDPR Compliant:** Supports data minimization principles
- **Secure:** No external data transmission
- **Audit Ready:** Processing logs available

## 📈 Processing Examples

### Example 1: Messy Spreadsheet
```
Input: 500 rows, 20 columns, 15% missing data
Output: 480 clean rows, 18 issues flagged, 2 high-risk quarantined
Quality Score: 85%
```

### Example 2: Trade Data
```
Input: 1000 trade records, mixed HS codes
Output: 950 validated records, 50 classification issues
Compliance: 95% codes valid
```

### Example 3: Financial Data
```
Input: 5000 invoice records
Output: 4900 clean records, VAT mismatches flagged
High-Risk Issues: 3 duplicate invoices identified
```

## 🛠️ Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'streamlit'"
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: File encoding errors
**Solution:** The app automatically tries multiple encodings (UTF-8, CP1252, Latin1). If still failing, try converting to UTF-8 in your spreadsheet application first.

### Issue: Large files running slowly
**Solution:** For files >50MB, consider:
- Splitting into smaller batches
- Filtering unnecessary columns
- Using CSV format instead of Excel

## 📞 Support & Maintenance

### For Technical Issues:
- Check requirements are installed: `pip list`
- Verify Python version: `python --version`
- Review logs for detailed error messages

### For Feature Requests:
- Contact: Coltrane Ltd
- Include use case and expected output

## 📦 Deployment Options

### Local Desktop Use
```bash
streamlit run app.py
```

### Server Deployment
```bash
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

### Docker Deployment
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

## 📋 System Requirements

| Requirement | Minimum | Recommended |
|------------|---------|------------|
| Python | 3.8 | 3.10+ |
| RAM | 2GB | 8GB+ |
| Storage | 500MB | 2GB |
| Network | None | Broadband (for deployment) |

## 📚 Version History

### v2.0 (Current)
- ✅ Added comprehensive dashboard with KPIs
- ✅ Advanced anomaly detection engine
- ✅ Statistical outlier detection
- ✅ Risk-based critical alerts
- ✅ Multiple export formats
- ✅ Trade compliance validation
- ✅ Data integrity checks
- ✅ Production-ready architecture
- ✅ Enterprise logging

### v1.0
- Basic data cleaning
- CSV and Excel support
- Simple error reporting

## 📄 Legal & Compliance

### Privacy
- GDPR Compliant
- CCPA Ready
- No data storage
- Session-based processing

### Liability
This tool identifies and highlights data quality issues but does not make binding business decisions. Users remain responsible for reviewing outputs and obtaining professional advice where needed.

### Disclaimer
- Not legal/tax/compliance advice
- Professional review recommended
- Suitable for data preparation only

## 📞 Contact

**Coltrane Ltd**
- Email: [support@coltrane.co.uk]
- Website: [www.coltrane.co.uk]
- Support Hours: Monday-Friday, 9AM-5PM GMT

## 📄 License

© 2026 Coltrane Ltd. All rights reserved.

---

**Ready to transform your data quality?** Start with ColtraDataAi today!

# ColtraDataAi - Quick Start Guide

**Version:** 2.0  
**Setup Time:** ~5 minutes

---

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies (2 minutes)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Launch the App (30 seconds)

```bash
streamlit run app.py
```

The app will open automatically in your browser at `http://localhost:8501`

### Step 3: Process Your First Data File (1 minute)

1. **Upload a file** - CSV or Excel
2. **Select a mode** - General Cleaning, Accounting, or Trade Compliance
3. **Click "Clean, Validate & Analyze"**
4. **Review dashboard** - See your data quality metrics
5. **Download reports** - Excel, CSV, or error logs

---

## 📊 Try with Sample Data

**We've included sample data!**

```bash
# Find this file in the repository:
sample_data/Sample_Invoice_Data.csv

# This sample includes:
✓ Missing values
✓ Invalid emails  
✓ Duplicate records
✓ Formatting issues
✓ Statistical outliers
✓ VAT mismatches
```

**Perfect for testing all features!**

---

## 🎯 Common Tasks

### Task 1: Clean a CSV File
1. Run `streamlit run app.py`
2. Select **General Cleaning** mode
3. Upload your `.csv` file
4. Click process button
5. Download cleaned data

### Task 2: Validate Financial Data
1. Run `streamlit run app.py`
2. Select **Accounting / HMRC Mode**
3. Upload invoice/financial data
4. System checks VAT calculations
5. Review highlighted discrepancies

### Task 3: Check Trade Compliance
1. Run `streamlit run app.py`
2. Select **Trade Compliance Mode**
3. Upload trade records
4. Validates SITC/HS codes
5. Flags classification issues

---

## 📈 Understanding the Dashboard

### KPI Metrics (Top Section)
- **Quality Score**: 0-100% (80+ = Good)
- **Completeness**: % of non-null data
- **Issues Found**: Total anomalies detected
- **High-Risk Issues**: Require immediate attention
- **Duplicates**: Records flagged as duplicates

### Visual Charts
- **Missing Data Pattern** - Which columns need attention
- **Data Type Distribution** - What types of data you have
- **Issue Distribution** - Types of problems found
- **Risk Breakdown** - Severity of issues

### Risk Levels
🔴 **Critical/High** → Immediate action needed  
🟠 **Medium** → Should be reviewed  
🟡 **Low** → Informational only

---

## 💾 Export Options

After processing, download:

1. **Excel Report** (Complete package)
   - Cleaned_Data sheet
   - Error_Report sheet
   - Quarantined_High_Risk sheet

2. **Cleaned CSV** (Ready to use)
   - Your cleaned data file

3. **Error Log** (Documentation)
   - All issues for client reporting

---

## ⚡ Pro Tips

### Tip 1: Sample First
Always test with sample data first before processing large files.

### Tip 2: Review Alerts
Watch for 🚨 **CRITICAL** alerts - these need immediate action.

### Tip 3: Export Everything
Keep copies of all reports for audit trail and compliance.

### Tip 4: Multiple Modes
Different modes catch different issues - use appropriate mode for your data.

### Tip 5: Large Files
For files >50MB, split into smaller batches for faster processing.

---

## 🔍 What Gets Checked

### Automatically Detected Issues:
✅ Missing values  
✅ Duplicates  
✅ Invalid formats  
✅ Statistical outliers  
✅ Type mismatches  
✅ Sparse columns  

### Mode-Specific Checks:
- **Accounting**: VAT calculations, financial amounts
- **Trade**: SITC codes, HS codes, commodity codes

---

## 🆘 Troubleshooting

| Problem | Solution |
|---------|----------|
| "No module streamlit" | Run: `pip install -r requirements.txt` |
| App won't start | Check Python version 3.8+ |
| File won't upload | Ensure file is CSV or Excel format |
| Charts not showing | Try smaller dataset first |
| Slow processing | File too large - split into parts |

---

## 📞 Need Help?

1. **Check README.md** - Full feature documentation
2. **See DEPLOYMENT_GUIDE.md** - Production setup
3. **Review ANALYST_REVIEW_REPORT.md** - Technical details
4. **Contact Coltrane Ltd** - Professional support

---

## 🎓 Learning Resources

### Feature Deep-Dives:
- **README.md** - Complete feature guide (10 min read)
- **ANALYST_REVIEW_REPORT.md** - Technical architecture (15 min read)
- **DEPLOYMENT_GUIDE.md** - Production deployment (20 min read)

### Sample Data:
- **sample_data/Sample_Invoice_Data.csv** - Pre-built test data

---

## ✅ Checklist: First Run

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] App launches successfully (`streamlit run app.py`)
- [ ] Browser opens to localhost:8501
- [ ] Can upload sample CSV file
- [ ] Processing completes without errors
- [ ] Dashboard displays with charts
- [ ] Can download Excel report
- [ ] All visualizations render correctly
- [ ] Ready for production data!

---

## 🎉 You're Ready!

ColtraDataAi is now ready to transform your data quality.

**Next Steps:**
1. Try the sample data
2. Test with your own files
3. Review generated reports
4. Deploy to production (see DEPLOYMENT_GUIDE.md)

**Happy data cleaning!** 🧹

---

**Questions?** See the full documentation in README.md or contact support@coltrane.co.uk

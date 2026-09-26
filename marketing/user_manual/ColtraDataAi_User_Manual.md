# ColtraDataAi
## User Manual

**Clean Data. Clear Decisions.**

coltradata.com | app.coltradata.com
support@coltradata.com

Version 1.0 | September 2026
Produced by Coltrane Ltd

---

*This manual is intended for all ColtraDataAi users, from first-time sign-ups to enterprise integration teams. Each chapter is written to be read standalone - jump to the section most relevant to your role.*

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Getting Started](#2-getting-started)
3. [Domain Cleaners](#3-domain-cleaners)
   - 3.1 Finance and Accounting
   - 3.2 Import/Export and Trade
   - 3.3 Logistics and Supply Chain
   - 3.4 Healthcare - Operational
   - 3.5 Clinical Research
   - 3.6 Retail and Inventory
   - 3.7 Consultants and Professional Services
   - 3.8 SME and Small Business
   - 3.9 Hospitality and Accommodation
4. [Understanding Your Results](#4-understanding-your-results)
5. [Exporting Reports](#5-exporting-reports)
6. [Connecting Your Data Sources](#6-connecting-your-data-sources)
7. [Enterprise API](#7-enterprise-api)
8. [Plans, Billing, and Upgrading](#8-plans-billing-and-upgrading)
9. [Security and Data Privacy](#9-security-and-data-privacy)
10. [Getting Help](#10-getting-help)

**Appendices**
- A. Pricing Quick Reference
- B. Domain Cleaner Compatibility Matrix
- C. API Endpoint Reference
- D. S3 Scheduled Export Setup Checklist
- E. Glossary

---

## 1. Introduction

### 1.1 What ColtraDataAi Does

ColtraDataAi is a specialist data cleaning and reporting platform built for business professionals. It validates, standardises, and reports on your business data - catching errors, inconsistencies, and compliance gaps before they cause problems downstream.

The platform covers nine distinct business domains, each with its own set of rules, standards, and checks appropriate to that sector. Whether you are preparing accounts for year-end, auditing a supplier import file, or reviewing clinical trial records, ColtraDataAi applies the right checks for your data type automatically.

Key capabilities:
- **Data validation** - flags rows and fields that do not meet expected formats or standards
- **Standardisation** - normalises inconsistent values to a single canonical form (carrier names, currency codes, account codes, etc.)
- **Compliance checking** - verifies data against recognised standards (HMRC MTD VAT, NHS RTT, WCO HS codes, Incoterms 2020, and others)
- **Structured reporting** - produces clean, professional Excel and PDF outputs ready to share with colleagues, auditors, or clients
- **AI-powered observations** - on Starter plans and above, a descriptive summary of patterns and anomalies found in your dataset (Starter plans and above)
- **Enterprise API** - for development teams who want to embed ColtraDataAi cleaning logic into their own pipelines and applications

### 1.2 What ColtraDataAi Does Not Do

ColtraDataAi is a data cleaning and reporting tool. It does not provide:
- Business advice, financial recommendations, or consulting opinions
- Tax calculations or legal guidance
- Predictions or forecasts
- Automated decisions about your business

All outputs from the platform are descriptive and observational. They tell you what the data contains and where issues exist. Decisions about what to do with that information remain with you and your professional advisers.

### 1.3 Who It Is For

ColtraDataAi is built for professionals who work with business data regularly and need it to be accurate, consistent, and audit-ready:

- **Bookkeepers and accountants** - preparing client records, VAT returns, or year-end files
- **Operations and logistics managers** - validating shipment data, carrier records, and supply chain reports
- **Import/export coordinators** - checking trade documentation against customs standards
- **Data analysts** - pre-processing raw datasets before loading into dashboards or reporting tools
- **SME owners** - cleaning mixed records before sharing with an accountant or investor
- **Developers and IT teams** - integrating structured data cleaning into automated pipelines via the Enterprise API

You do not need technical skills to use the web application. A working knowledge of spreadsheets and business software is sufficient for all features except the Enterprise API, which is aimed at developers.

### 1.4 How to Access the Platform

The ColtraDataAi application is available at **app.coltradata.com**.

You do not need to install any software. The platform runs in your web browser on desktop, tablet, or mobile.

**Login method:** ColtraDataAi uses one-time passcode (OTP) authentication. There are no passwords to remember or manage.

To sign in:
1. Go to app.coltradata.com
2. Enter your email address
3. Check your inbox for a six-digit code (arrives within 60 seconds)
4. Enter the code to access your account

### 1.5 Try It First - The Live Demo

Before uploading your own data, you can explore the platform using the Live Demo at **app.coltradata.com/Live_Demo**.

The demo includes two pre-built sample datasets that run through the cleaning engine and return real results. You will see the quality score card, the findings table, and a results preview - exactly as you would with your own file. No account is required to access the demo.

The Live Demo is a useful starting point for:
- Understanding what the platform produces before committing to a plan
- Showing a colleague or client what the output looks like
- Exploring a domain you are less familiar with

> **Key Takeaways - Chapter 1**
> - ColtraDataAi cleans, validates, and reports on business data. It does not give advice.
> - Nine domain cleaners cover finance, trade, logistics, healthcare, clinical research, retail, professional services, SME, and hospitality.
> - Login uses one-time passcode - no password required.
> - Try the Live Demo at app.coltradata.com/Live_Demo before uploading your first file.

---

## 2. Getting Started

### 2.1 Creating an Account

Go to **app.coltradata.com** and enter your email address. A six-digit code will be sent to your inbox. Enter the code to complete sign-in. Your account is created automatically on your first successful login - there is no separate registration form.

If the code does not arrive within two minutes, check your spam folder. If the problem persists, contact support@coltradata.com.

### 2.2 Choosing a Plan

ColtraDataAi offers a Free plan so you can try the full cleaning workflow before committing to a paid subscription.

| Plan | Monthly Price | Runs | Max Rows per Run | Key Features |
|---|---|---|---|---|
| Free | £0 | 3 | 5,000 | All 9 cleaners, basic results |
| Starter | £29 | 50 | 50,000 | AI insights, Excel export |
| Professional | £99 | 200 | 250,000 | PDF reports, API access |
| Business | £299 | 1,000 | 1,000,000 | Branded reports, unlimited API calls |
| Enterprise | £999 | Unlimited | Unlimited | Custom onboarding, contact sales |
| Enterprise API | £499 | - | Unlimited | API-only product, standalone key |

See Chapter 8 for full plan details and how to upgrade.

### 2.3 Uploading Your First File

ColtraDataAi accepts data in **CSV format** (comma-separated values). Most accounting, ERP, WMS, and logistics platforms can export CSV files directly. Chapter 3 lists the specific export paths for the most common applications in each domain.

**To upload a file:**
1. Sign in at app.coltradata.com
2. Select a domain cleaner from the dropdown menu
3. Click "Upload File" and choose your CSV from your computer
4. Click "Run Cleaning"

The platform will process your file and display the results within seconds for most file sizes. Larger files (100,000+ rows) may take up to 60 seconds.

**File preparation tips:**
- Your file does not need to be formatted in any special way. ColtraDataAi auto-detects column names using common naming patterns from major business applications.
- Remove any summary or total rows at the bottom of your export before uploading (accountancy software exports sometimes include these).
- Ensure your file is saved as CSV, not as an Excel .xlsx file. Most software gives you a "Save as CSV" or "Export as CSV" option.
- There is no requirement to rename columns before uploading.

### 2.4 Selecting a Domain Cleaner

The domain cleaner tells ColtraDataAi which set of rules and standards to apply to your data. Select the one that best matches the data you are uploading:

| Your Data Type | Use This Cleaner |
|---|---|
| Nominal ledger, journal entries, VAT transactions | Finance and Accounting |
| Import/export declarations, trade invoices | Import/Export and Trade |
| Shipment records, carrier data, tracking logs | Logistics and Supply Chain |
| Patient appointments, wait times, NHS records | Healthcare - Operational |
| Clinical trial records, adverse events | Clinical Research |
| Product catalogue, stock levels, sales orders | Retail and Inventory |
| Time entries, project codes, billing records | Consultants and Professional Services |
| Mixed small business records | SME and Small Business |
| Reservations, room data, guest records | Hospitality and Accommodation |

If your data spans more than one domain, run it through the cleaner that covers its primary content. For example, a file with both sales order lines and shipment tracking should go through Logistics if the shipment data is the primary concern.

> **Key Takeaways - Chapter 2**
> - Login with your email and a one-time code - no password.
> - Files must be in CSV format. Column naming is detected automatically.
> - Select the domain cleaner that matches your data type.
> - Free plan allows 3 runs of up to 5,000 rows each - enough to evaluate the platform with your own data.

---

## 3. Domain Cleaners

Each cleaner applies a distinct set of validation rules relevant to its sector. This chapter describes what each cleaner checks, what it expects in your file, and which applications export compatible data.

---

### 3.1 Finance and Accounting

**Best for:** nominal ledger exports, journal entry files, transaction lists, VAT transaction records.

#### What It Checks

**Nominal account codes**
The cleaner validates account codes against the standard UK nominal range (0-9999) and classifies each code by type: assets, liabilities, equity, income, or expenditure. Codes that fall outside this range or that cannot be parsed are flagged for review.

**VAT code validation**
The cleaner recognises and validates three VAT code formats commonly used in UK accounting software:
- Sage 50 codes: T0, T1, T2, T5, T9, T15, T16, T17, T18, T19, T20, T21
- Xero and QuickBooks style: EXEMPT, ZERORATER, STANDARD, REDUCEDRATE
- HMRC rate labels: 0%, 5%, 20%, Exempt, Outside the Scope

Codes that do not match any recognised format are flagged. Mixed formats within a single file are normalised and reported.

**Journal reference normalisation**
Journal references are standardised to a consistent format. Duplicates within a period and missing references are flagged.

**Period distribution**
The cleaner analyses how transactions are distributed across accounting periods. Periods with unusually high or low transaction counts are noted in the findings table.

**Cost centre coverage**
Where cost centre codes are present, the cleaner checks coverage (percentage of transactions assigned to a cost centre) and flags transactions with missing assignments.

**Trial balance check**
If your file contains debit and credit columns, the cleaner performs a double-entry check: total debits must equal total credits within a 1p tolerance. Any imbalance is reported as a high-severity finding.

**Narrative quality**
Transaction narratives are checked for quality. Blank narratives and generic entries (such as "Payment", "Receipt", or "Transfer") are flagged as low-quality. High volumes of generic narratives reduce the overall quality score.

**MTD VAT Digital Records Readiness**
The cleaner checks whether your transaction data meets the digital records requirements set out in HMRC VAT Notice 700/22 for Making Tax Digital (MTD). Four fields are required per transaction under MTD:
1. Tax point date (the time of supply)
2. Supply description (nature of the supply)
3. Net value of the supply
4. VAT rate applied

Each transaction receives a readiness score from 0 to 4. The results panel shows a per-field breakdown, so you can see exactly which fields need attention before your next VAT return.

#### Compatible Export Sources

| Application | How to Export |
|---|---|
| **Xero** | Reports > Account Transactions > select date range > Export to CSV |
| **Sage 50** | File > Export > Transactions or Nominal Ledger > CSV format |
| **QuickBooks Online** | Reports > Transaction List by Date > Export (select CSV) |
| **FreeAgent** | Reports > Account Details > Export CSV |
| **Microsoft Dynamics 365 Business Central** | General Ledger Entries > Export to Excel, save as CSV |
| **SAP Business One** | Journal Entry reports via Crystal Reports > Export to CSV |

No column renaming is required for exports from these applications. ColtraDataAi recognises the standard column names each system uses.

---

### 3.2 Import/Export and Trade

**Best for:** import declarations, export invoices, customs entries, trade manifests, commodity reports.

#### What It Checks

**HS code validation**
Harmonised System (HS) commodity codes are validated against the World Customs Organization (WCO) standard. The cleaner accepts 6-digit, 8-digit, and 10-digit codes and zero-pads shorter codes to the correct length. Invalid codes are flagged.

**HS chapter-level commodity breakdown**
Each validated HS code is mapped to its WCO chapter heading, giving you a commodity composition summary of the dataset.

**Country normalisation**
Country values are normalised to ISO 3166-1 alpha-2 two-letter codes (e.g. "United Kingdom" becomes "GB", "Nigeria" becomes "NG"). The cleaner covers approximately 55 countries, including all major African markets.

**Currency standardisation**
Currency codes are validated and standardised to ISO 4217. The cleaner covers all major global currencies and includes the following African currencies specifically: KES, NGN, GHS, EGP, TZS, UGX, ETB, MAD, ZMW, MWK, MZN, BWP, RWF, XOF, XAF.

**Incoterms 2020 validation**
All 11 International Chamber of Commerce (ICC) Incoterms 2020 terms are supported: EXW, FCA, FAS, FOB, CFR, CIF, CPT, CIP, DAP, DPU, DDP. Invalid Incoterm values are flagged. Missing values are flagged at row level. If no Incoterms column is detected in the file at all, the cleaner raises a dataset-level advisory - Incoterms are a legal requirement on many trade documents.

**Unit of measure standardisation**
Units of measure are standardised to WCO/UN nomenclature (kg, m, L, units, etc.).

**Trade direction detection and declared value checks**
The cleaner detects trade direction (import or export) from available fields and performs basic sanity checks on declared values (e.g. zero-value commercial entries, negative declared values).

#### Compatible Export Sources

| Application / Source | Notes |
|---|---|
| **SAP Global Trade Services (GTS)** | Export customs entry reports as CSV |
| **Oracle Trade Management** | Export transaction detail reports |
| **HMRC import declaration exports** | C88/E2 reports available from the CHIEF / CDS portal |
| **CargoWise** | Export Shipment or Customs Entry reports as CSV |
| **Freight forwarder manifests** | Most freight forwarders provide CSV or Excel manifests - save as CSV |

---

### 3.3 Logistics and Supply Chain

**Best for:** shipment tracking files, carrier logs, warehouse movement records, delivery confirmations.

#### What It Checks

**Shipment status standardisation**
Inconsistent status labels (e.g. "In Transit", "in-transit", "INTRANSIT") are mapped to a canonical set of status labels. This is particularly useful when combining data from multiple carriers or warehouse systems that use different terminology.

**Carrier name normalisation**
Carrier names are normalised to their correct trading name. The cleaner recognises:
- International freight: DHL, FedEx, UPS, TNT, DB Schenker, Kuehne+Nagel, DSV, CEVA Logistics, Geodis, GLS
- UK domestic carriers: Royal Mail, Evri (Hermes), DPD, Yodel, APC Overnight, Parcelforce, CitySprint, and others

**Weight unit normalisation**
Weight values are standardised to a single unit. Supported input units: kg, lbs, g, metric_ton, oz.

**Transit time calculation**
Where dispatch and delivery dates are present, actual transit time is calculated for each shipment. Shipments with implausible transit times (delivery before dispatch, or transit times outside expected ranges for the carrier/route) are flagged.

**Duplicate tracking number detection**
Duplicate tracking numbers within the file are identified and listed in the findings table.

#### Compatible Export Sources

| Application | Notes |
|---|---|
| **Mintsoft WMS** | Reports > Shipments > Export CSV |
| **Peoplevox WMS** | Shipment Despatch reports, CSV export |
| **Linnworks** | Reports > Processed Orders > Export |
| **DHL / FedEx / UPS portals** | Shipment history downloads available as CSV from each carrier portal |
| **3PL data extracts** | Any flat-file export from a third-party logistics provider |

---

### 3.4 Healthcare - Operational

**Best for:** patient appointment records, referral logs, waiting list data, staff rotas.

#### What It Checks

**NHS number validation**
Each NHS number is validated using the Modulus 11 check digit algorithm. Invalid numbers are flagged at row level.

**ICD-10 code validation**
Diagnosis codes are checked for correct ICD-10 format (letter followed by two or more digits, with optional decimal point). Codes that do not match the expected pattern are flagged.

**Appointment type and staff category normalisation**
Appointment type labels (e.g. "FU", "Follow Up", "follow-up") and staff category labels are normalised to standard NHS terminology.

**Wait time analysis - NHS 18-week RTT standard**
Where referral and treatment dates are present, waiting times are calculated and each pathway is assessed against the NHS 18-week Referral to Treatment (RTT) standard. The findings table shows the number and percentage of pathways that breach the standard.

**DNA rate benchmarking**
Did Not Attend (DNA) rates are calculated and compared against the 10% NHS benchmark threshold. Rates above this threshold are flagged.

**UK postcode validation**
Postcodes are validated against the standard UK postcode format. Incorrectly formatted postcodes are flagged and listed.

#### Compatible Export Sources

| System | Notes |
|---|---|
| **SystmOne** | Export patient lists and appointment reports as CSV |
| **EMIS Health** | Export via Reports module |
| **Cerner Millennium** | Export patient scheduling reports |
| **NHS Digital extract files** | Standard extract formats supported |

*Note: Always ensure patient data is handled in accordance with your organisation's data protection policy and Caldicott principles before uploading to any external system. See Chapter 9 for details of how ColtraDataAi handles data.*

---

### 3.5 Clinical Research

**Best for:** clinical trial datasets, adverse event logs, study endpoint records, CRF data exports.

#### What It Checks

**Patient ID format validation**
Patient identifiers are checked for consistency and correct format within the file. Non-standard or malformed IDs are flagged.

**NCT ID normalisation**
ClinicalTrials.gov identifiers (NCT IDs) are validated and normalised to the standard format (NCT followed by 8 digits). Importantly, non-NCT registry identifiers - including ISRCTN, EudraCT, and others - are left unchanged. The cleaner does not attempt to reformat identifiers it does not recognise, preventing silent data corruption.

**Adverse event severity classification**
Adverse event severity labels are checked against standard classifications (Mild, Moderate, Severe, Life-threatening, Fatal) and non-standard values are flagged.

**Endpoint type detection**
Endpoint type values (Primary, Secondary, Exploratory) are normalised and non-standard values flagged.

**Full audit trail**
Every cleaning run on a clinical dataset receives a unique run_id and a cleaned_at timestamp. These are included in the export, supporting audit and inspection readiness.

#### Compatible Export Sources

| System | Notes |
|---|---|
| **Medidata Rave** | Export subject-level and adverse event datasets as CSV |
| **Oracle Clinical** | Data extract reports, CSV format |
| **REDCap** | Data Exports > CSV/Microsoft Excel (raw data) |
| **CRO data packages** | Most CROs provide study data as CSV or pipe-delimited flat files - save as CSV |

---

### 3.6 Retail and Inventory

**Best for:** product catalogues, stock level reports, sales order lines, purchase order records.

#### What It Checks

- **SKU validation** - checks for blank, duplicate, or non-standard SKU formats
- **Price anomaly detection** - flags zero-price lines, negative prices, and values that deviate significantly from the product group median
- **Stock level checks** - flags negative stock quantities and implausible reorder point values
- **Supplier name normalisation** - inconsistent supplier name entries are grouped and reported
- **Category and product type standardisation** - freetext category entries are normalised where possible

#### Compatible Export Sources

| Application | Notes |
|---|---|
| **Shopify** | Admin > Products or Orders > Export CSV |
| **WooCommerce** | WooCommerce > Products > Export |
| **Linnworks** | Reports > Stock or Orders > Export CSV |
| **DEAR Inventory** | Reports > Inventory Summary > Export |
| **Brightpearl** | Reports > Product or Order reports > Export |

---

### 3.7 Consultants and Professional Services

**Best for:** timesheet exports, project billing records, resource allocation files, invoice line data.

#### What It Checks

- **Project code standardisation** - normalises project code formats and flags unrecognised codes
- **Time entry validation** - checks for negative durations, entries that exceed a working day, and missing project assignments
- **Billing reference checks** - validates billing reference formats and flags duplicates
- **Staff category normalisation** - freetext role or grade descriptions are normalised to standard category labels
- **Period coverage** - checks for gaps in time entry coverage across the reporting period

#### Compatible Export Sources

| Application | Notes |
|---|---|
| **Harvest** | Reports > Time > Export CSV |
| **Toggl Track** | Reports > Detailed > Export CSV |
| **Mavenlink / Kantata** | Project and time reports, CSV format |
| **Kimble PSA** | Standard timesheet exports |
| **Salesforce Service Cloud** | Case and activity reports, CSV export |

---

### 3.8 SME and Small Business

**Best for:** mixed small business records that do not fit neatly into a single specialist domain - combined ledger/customer/supplier data, Excel-based management accounts, or exported records from entry-level accounting tools.

#### What It Checks

This cleaner applies a broad set of general-purpose checks suitable for mixed business data:
- **Duplicate record detection** across key identifier fields
- **Date format standardisation** to ISO 8601 (YYYY-MM-DD)
- **Numeric field validation** - checks for values that cannot be parsed as numbers in fields expected to contain them
- **Missing value analysis** - calculates completeness per column and flags columns below an acceptable threshold
- **Contact data validation** - basic format checks on email addresses and phone numbers where present
- **Currency and amount checks** - flags negative amounts and zero-value entries in revenue or payment fields

#### Compatible Export Sources

Any CSV export from the following is suitable:
- Xero (any report)
- QuickBooks Online or Desktop
- FreeAgent
- KashFlow
- Wave Accounting
- Excel or Google Sheets files saved as CSV

---

### 3.9 Hospitality and Accommodation

**Best for:** hotel reservation data, room revenue reports, guest records, food and beverage transaction files.

#### What It Checks

- **Reservation data validation** - checks for missing booking references, invalid stay dates, and check-out before check-in anomalies
- **Room type standardisation** - normalises room type labels (e.g. "DBL", "Double", "double room" all map to a canonical label)
- **Revenue per available room (RevPAR) checks** - where room count and revenue data are present, RevPAR is calculated and outlier periods flagged
- **Guest record deduplication** - identifies probable duplicate guest records based on name and contact field similarity
- **Rate code validation** - checks rate code formats and flags missing or unrecognised codes

#### Compatible Export Sources

| System | Notes |
|---|---|
| **Opera PMS (Oracle Hospitality)** | Export Reservation and Revenue reports as CSV |
| **Mews** | Reports > Export (CSV format available throughout) |
| **Cloudbeds** | Reports > Reservations > Export |
| **SiteMinder** | Booking and revenue reports, CSV export |

> **Key Takeaways - Chapter 3**
> - Nine cleaners cover every major business data type. Select the one that matches your file's primary content.
> - Column names are detected automatically - no reformatting needed before upload.
> - Each cleaner applies sector-specific standards (HMRC, NHS, WCO, ICC, etc.).
> - Compatible export paths are listed for the most common applications in each domain.

---

## 4. Understanding Your Results

After a cleaning run completes, the results panel displays four main components.

### 4.1 The Quality Score Card

The quality score is a single percentage from 0-100 that summarises the overall data quality of your file. It is calculated from the proportion of records that pass all applicable checks weighted by finding severity.

| Score Range | Interpretation |
|---|---|
| 90-100% | High quality - minor issues only |
| 70-89% | Acceptable - some areas need attention |
| 50-69% | Below standard - review findings before using this data |
| Below 50% | Poor quality - significant issues detected |

The score is a guide, not a compliance certificate. A file with a high score that contains one critical error (e.g. a failed trial balance) may still require action.

### 4.2 The KPI Banner

Directly below the score card, a row of key metrics gives you an at-a-glance view of the dataset:

| Metric | What It Means |
|---|---|
| Total Rows | Number of data rows in your file |
| Rows with Issues | Number of rows with at least one finding |
| Critical Findings | High-severity issues requiring immediate attention |
| Warnings | Medium-severity issues that should be reviewed |
| Passed Checks | Total number of individual checks that returned clean |

### 4.3 The Findings Table

The findings table lists every issue detected, with the following columns:

- **Severity** - Critical, Warning, or Info
- **Finding Type** - the category of issue (e.g. "Invalid VAT Code", "Duplicate Tracking Number")
- **Affected Rows** - the count and percentage of rows affected
- **Description** - a plain-language explanation of the issue
- **Recommended Action** - what you can do to resolve the finding

Findings are sorted by severity (Critical first) by default. You can click any column header to re-sort.

### 4.4 Charts and Visualisations

Below the findings table, a set of charts provides a visual breakdown of your data quality. Chart types vary by domain cleaner but typically include:
- A breakdown of issue types by volume
- A distribution of findings across the dataset (e.g. by period, carrier, or account code group)
- A completeness chart showing data fill rates per column

Charts are interactive - hover to see values, click the legend to isolate a series.

### 4.5 AI Insights (Starter Plan and Above)

On Starter, Professional, Business, and Enterprise plans, an AI Insights section appears below the charts. This provides a descriptive summary of the most significant patterns found in your data - unusual concentrations, recurring error types, and consistency patterns across the file.

AI Insights are observational only. They describe what the data shows. They do not recommend business decisions, give accounting opinions, or interpret findings in a regulatory context.

### 4.6 MTD VAT Readiness Score (Finance Cleaner)

When running the Finance and Accounting cleaner, an additional panel shows your MTD VAT digital records readiness. Four fields are required under HMRC VAT Notice 700/22:

1. Tax point date
2. Supply description
3. Net value
4. VAT rate

Each transaction receives a score from 0 to 4 (one point per field present and correctly formatted). The panel displays the overall dataset readiness percentage and a per-field breakdown table, so you can identify which specific fields are incomplete before your next VAT return submission.

> **Key Takeaways - Chapter 4**
> - The quality score gives a single headline figure; the findings table shows the detail.
> - Severity levels (Critical, Warning, Info) help you prioritise what to fix first.
> - AI Insights are descriptive - they do not provide business or compliance advice.
> - The MTD VAT Readiness panel (Finance cleaner) shows your HMRC 700/22 compliance position at field level.

---

## 5. Exporting Reports

### 5.1 Excel Report

Available on: Starter, Professional, Business, Enterprise plans.

The Excel report is a multi-sheet workbook generated from your cleaning run. It contains:

| Sheet | Contents |
|---|---|
| Summary | Quality score, KPI banner, and run metadata |
| Cleaned Data | Your data with issue flags appended as additional columns |
| Findings | The full findings table, sortable and filterable |
| Charts | Key visualisations embedded as chart objects |
| Audit Trail | Run ID, timestamp, domain, row count, and plan tier |

To download the Excel report, click "Download Excel Report" in the results panel. The file downloads immediately to your browser's default download folder.

**Using your Excel report downstream:**
- Attach it to an email to your accountant or auditor as supporting documentation
- Import the Cleaned Data sheet into Power BI, Tableau, or other BI tools
- File it alongside the original source export for audit trail purposes
- Share the Findings sheet with the team responsible for correcting the data

### 5.2 PDF Executive Summary

Available on: Professional, Business, Enterprise plans.

The PDF report provides a concise executive summary of your cleaning run, designed to be shared with a manager, client, or senior stakeholder who needs the headline picture without the raw data.

The PDF includes:
- Cover page with your organisation name and run date
- Quality score and KPI summary
- Top findings in plain language
- Charts and visualisations
- Branded footer (Coltrane Ltd / ColtraDataAi)

On Business and Enterprise plans, the report can be branded with your own logo and organisation name. Contact support@coltradata.com to configure branded reporting.

To download the PDF, click "Download PDF Summary" in the results panel.

### 5.3 Accessing Previous Run Reports

All reports from previous runs are available in your account history. Sign in, navigate to "Run History" in the left menu, and click any previous run to view or re-download its reports.

> **Key Takeaways - Chapter 5**
> - Excel reports contain cleaned data, findings, charts, and an audit trail in separate sheets.
> - PDF summaries are designed for sharing with stakeholders - clean, professional, no raw data.
> - Previous run reports are accessible from your account history at any time.

---

## 6. Connecting Your Data Sources

### 6.1 How ColtraDataAi Connects to Your Data

ColtraDataAi uses a **scheduled file export and upload model**. You export a CSV from your source system and upload it to ColtraDataAi - manually, or by placing it in a connected storage location that ColtraDataAi can read from.

ColtraDataAi does not connect directly to your databases, accounting software, or ERP systems. It does not store credentials, connection strings, or API keys for your source systems. This is a deliberate design decision that keeps the integration simple and protects your data.

Benefits of this approach:
- No IT involvement required to set up. Anyone who can export a CSV can use ColtraDataAi.
- No credentials shared with a third party
- Compatible with any software that can export CSV, regardless of age or platform
- No GDPR complexity from live database connections
- Works even where direct integrations are blocked by firewalls or IT policy

### 6.2 Manual Upload

The simplest connection method. Export a CSV from your source system, then upload it directly at app.coltradata.com.

This works for all plans and requires no configuration. It is suitable for:
- Monthly or periodic cleaning runs
- One-off data quality checks
- Ad hoc audit preparation

### 6.3 Scheduled Export to AWS S3 (Business and Enterprise Plans)

For teams that need to run ColtraDataAi on a regular schedule without manual intervention, the recommended automation pattern uses AWS S3 as an intermediary storage layer.

**How it works:**
1. Your source system (accounting software, ERP, WMS, etc.) exports a CSV to a designated S3 bucket on a schedule you define (daily, weekly, end of period).
2. ColtraDataAi reads the file from the bucket using a pre-signed URL or bucket access policy.
3. The cleaning run executes and the report is available in your account.

This pattern requires no live connection between your source system and ColtraDataAi. The S3 bucket acts as a secure handoff point.

**Setup overview:**

Step 1 - Create an S3 bucket (or use an existing one)
- Log in to your AWS console
- Create a bucket in the region closest to your users (eu-west-2 for UK users)
- Enable versioning if you want to retain previous exports

Step 2 - Configure your source system to export to S3
- Most enterprise ERP and accounting platforms support scheduled exports to S3 via their native reporting scheduler or a lightweight ETL tool (AWS Data Pipeline, Azure Data Factory, Zapier, or a simple Lambda function)
- Configure the export to land as a dated CSV file (e.g. finance_export_2026-09-04.csv)

Step 3 - Connect the bucket to ColtraDataAi
- On Business and Enterprise plans, navigate to Settings > Data Sources in your ColtraDataAi account
- Enter your S3 bucket name and the pre-signed URL or IAM access credentials for read-only bucket access
- Select the target domain cleaner and the run schedule

Step 4 - Review reports in your account
- Scheduled runs appear in your Run History with the source filename and timestamp

See Appendix D for the full S3 setup checklist.

### 6.4 SharePoint and OneDrive (Alternative for Microsoft 365 Users)

If your organisation uses Microsoft 365, you can use SharePoint or OneDrive as the file drop location instead of S3.

Configure your source system to export a CSV to a designated SharePoint document library or OneDrive folder on a schedule. ColtraDataAi can read from a shared link to that location on Business and Enterprise plans.

Contact support@coltradata.com to configure SharePoint or OneDrive integration.

### 6.5 Why There Are No Direct Database Connections

ColtraDataAi does not offer ODBC, JDBC, SQL connection string, or REST API credential input for live database access. This is not a technical limitation - it is a deliberate product decision based on:

- **Simplicity** - the target user (bookkeeper, accountant, operations manager) typically does not have access to database credentials and should not need them
- **GDPR** - live database connections require formal Data Processing Agreements covering data minimisation, international transfer, and multi-tenant isolation. File upload is far simpler to govern.
- **Security** - storing database credentials in a cloud application introduces credential exposure risk. File export avoids this entirely.
- **Compatibility** - any system that can export CSV works, regardless of the underlying database technology

> **Key Takeaways - Chapter 6**
> - ColtraDataAi uses a file export + upload model. No database credentials are needed or stored.
> - Manual upload works for all plans and requires no setup.
> - AWS S3 scheduled export is the recommended automation pattern for Business and Enterprise plans.
> - SharePoint/OneDrive is an alternative for Microsoft 365 users.

---

## 7. Enterprise API

### 7.1 Who This Is For

The Enterprise API is designed for developers, data engineers, and IT teams who want to embed ColtraDataAi's data cleaning logic into their own applications, pipelines, or scheduled jobs.

With the API, you can:
- Call any of the nine domain cleaners programmatically with a CSV file or JSON body
- Receive structured cleaning results in JSON format for use in your own reporting, dashboards, or databases
- Integrate data quality checking into existing ETL pipelines, data warehouses, or business intelligence workflows
- Automate data cleaning as part of a nightly batch job, a CI/CD pipeline, or a real-time processing workflow

The Enterprise API is available as a standalone product at £499 per month (Enterprise API plan) or as part of the Professional (£99), Business (£299), and Enterprise (£999) application plans with the row and call limits for each plan.

### 7.2 API Access and Authentication

**Base URL:** `https://coltradata-api.onrender.com`

**Interactive documentation (Swagger):** `https://coltradata-api.onrender.com/docs`

**Health check:** `GET https://coltradata-api.onrender.com/health`

Authentication uses a **Bearer token** in the Authorization header of every request:

```
Authorization: Bearer cdai_your_api_key_here
```

Your API key is automatically provisioned and emailed to you when you purchase the Enterprise API plan. For application plan subscribers (Professional, Business, Enterprise), your key is available in your account under Settings > API Access.

API keys are SHA-256 hashed and stored securely. If your key is compromised, contact support@coltradata.com to revoke and re-issue it.

### 7.3 The Core Endpoint

```
POST /v1/clean/{domain}
```

Replace `{domain}` with one of the following values:

| Domain Value | Cleaner |
|---|---|
| `finance` | Finance and Accounting |
| `logistics` | Logistics and Supply Chain |
| `retail` | Retail and Inventory |
| `trade` | Import/Export and Trade |
| `healthcare` | Healthcare - Operational |
| `consultant` | Consultants and Professional Services |
| `sme` | SME and Small Business |
| `hospitality` | Hospitality and Accommodation |
| `clinical` | Clinical Research |

**Input formats accepted:**
- CSV file via multipart/form-data (field name: `file`)
- JSON body with an array of row objects

**Response format:**
JSON object containing:
- `quality_score` - overall score (0-100)
- `rows_processed` - total row count
- `findings` - array of finding objects (severity, type, affected rows, description)
- `cleaned_data` - array of cleaned row objects with issue flags appended
- `kpi` - key metrics object
- `run_id` - unique identifier for this run
- `cleaned_at` - ISO 8601 timestamp

### 7.4 Example Requests

**CSV file upload (Python):**
```python
import requests

api_key = "cdai_your_api_key_here"
url = "https://coltradata-api.onrender.com/v1/clean/finance"

with open("ledger_export.csv", "rb") as f:
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("ledger_export.csv", f, "text/csv")}
    )

result = response.json()
print(f"Quality score: {result['quality_score']}")
print(f"Critical findings: {len([f for f in result['findings'] if f['severity'] == 'critical'])}")
```

**JSON body (curl):**
```bash
curl -X POST https://coltradata-api.onrender.com/v1/clean/logistics \
  -H "Authorization: Bearer cdai_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"rows": [{"tracking_number": "1Z999AA10123456784", "carrier": "UPS", "status": "in transit", "weight_kg": 2.5}]}'
```

Full request and response schemas are available in the interactive Swagger documentation at `https://coltradata-api.onrender.com/docs`.

### 7.5 API Use Cases by Industry

**Accountancy firms**
A developer at an accountancy firm configures a Python script to run every night. The script pulls the latest Xero transaction export from S3, posts it to the Finance cleaner endpoint, and loads the findings JSON into a Power BI dataset. The firm's dashboard shows each client's data quality score updated daily, without any manual intervention.

**Logistics operations**
A logistics team adds an API call to their morning batch job. The WMS export drops to S3 at 06:00. At 06:15, the batch job reads the file and posts it to the Logistics cleaner endpoint. Any Critical findings trigger an alert to the operations supervisor before the warehouse opens.

**Enterprise data teams**
A data engineering team at a large organisation runs a Cisco network infrastructure monitoring platform that generates asset and vendor CSV feeds daily. These feeds are posted to the SME cleaner endpoint as part of the data ingestion pipeline to validate vendor name consistency, duplicate asset records, and missing field values before the data lands in the CMDB. The cleaning run's `run_id` is stored alongside each ingested record for audit purposes.

**Import/export compliance**
A trade compliance team at a freight forwarder builds the Trade cleaner into their pre-submission validation workflow. Every shipment file is posted to the API before the customs declaration is submitted. Any invalid HS code or Incoterms finding blocks the submission and triggers a review task.

**Clinical data management**
A CRO data manager integrates the Clinical cleaner into their REDCap export pipeline. Every time a study dataset is exported for sponsor review, it is automatically posted to the API. The findings JSON is attached to the data transfer package as a data quality certificate with the `run_id` and `cleaned_at` timestamp.

### 7.6 Rate Limits and Row Limits by Plan

| Plan | Rows per Call | Calls per Month |
|---|---|---|
| Professional | 1,000 | 100 |
| Business | 10,000 | Unlimited |
| Enterprise | Unlimited | Unlimited |
| Enterprise API | Unlimited | Unlimited |

Requests that exceed the row limit for your plan will return a `429` status with a descriptive error message.

### 7.7 Usage Logging

Every API call is logged to your account. Usage data includes the domain cleaner used, rows processed, input format, and timestamp. This is accessible in your account dashboard under Settings > API Usage, and is used to generate your monthly usage summary.

> **Key Takeaways - Chapter 7**
> - The API endpoint is `POST /v1/clean/{domain}` at `https://coltradata-api.onrender.com`.
> - Authentication uses a Bearer token. Your key is provisioned automatically on purchase.
> - Accepts CSV (multipart) or JSON body. Returns structured JSON.
> - Full interactive documentation is available at `https://coltradata-api.onrender.com/docs`.
> - Suitable for nightly batch jobs, ETL pipelines, pre-submission validation, and embedded data quality checks.

---

## 8. Plans, Billing, and Upgrading

### 8.1 Full Plan Comparison

| Feature | Free | Starter | Professional | Business | Enterprise | Enterprise API |
|---|---|---|---|---|---|---|
| Monthly price | £0 | £29 | £99 | £299 | £999 | £499 |
| Cleaning runs | 3 | 50 | 200 | 1,000 | Unlimited | - |
| Max rows per run | 5,000 | 50,000 | 250,000 | 1,000,000 | Unlimited | Unlimited |
| All 9 domain cleaners | Yes | Yes | Yes | Yes | Yes | Yes |
| AI insights | No | Yes | Yes | Yes | Yes | Yes |
| Excel report | No | Yes | Yes | Yes | Yes | Yes |
| PDF report | No | No | Yes | Yes | Yes | Yes |
| Branded reports | No | No | No | Yes | Yes | No |
| API access | No | No | Yes (1k rows, 100 calls) | Yes (10k rows, unlimited) | Yes (unlimited) | Yes (unlimited) |
| S3/SharePoint automation | No | No | No | Yes | Yes | No |
| Custom onboarding | No | No | No | No | Yes | No |

### 8.2 How to Upgrade

Visit **coltradata.com/pricing** and click the upgrade button for your chosen plan. Payment is handled securely through LemonSqueezy. You will receive a licence key by email immediately after purchase. Enter the key in your ColtraDataAi account under Settings > Licence Key to activate your new plan.

### 8.3 Enterprise Plan

The Enterprise plan at £999/month is not available via a self-serve checkout. To discuss Enterprise, contact **support@coltradata.com**. Enterprise includes custom onboarding, a dedicated account contact, and configuration support for S3 or SharePoint automation.

### 8.4 Enterprise API Plan

The Enterprise API plan at £499/month is self-serve. Purchase at coltradata.com/pricing and your API key will be provisioned and emailed to you automatically within a few minutes of payment. No manual setup is required.

### 8.5 Legacy Premium Plan

If you hold a Premium licence key (issued before July 2026), your key continues to work and provides access at the Starter feature level. If you would like to upgrade to a current plan, visit coltradata.com/pricing or contact support@coltradata.com.

### 8.6 Cancellation and Refunds

To cancel a subscription or request a refund, contact support@coltradata.com. Subscription cancellations take effect at the end of the current billing period.

> **Key Takeaways - Chapter 8**
> - Free plan gives 3 runs of up to 5,000 rows - no credit card required.
> - Starter (£29) unlocks AI insights and Excel export. Professional (£99) adds PDF and API access.
> - Enterprise is contact-only. Enterprise API at £499 is self-serve with automatic key delivery.
> - Legacy Premium keys continue to work at the Starter feature level.

---

## 9. Security and Data Privacy

### 9.1 Authentication

ColtraDataAi uses one-time passcode (OTP) email authentication. No passwords are stored by the platform. Each login session uses a fresh code sent to your registered email address.

### 9.2 Data Handling During Cleaning Runs

Your uploaded data is processed in-session. It is not retained, stored, or indexed after your cleaning run completes and you close or navigate away from the results.

ColtraDataAi does not:
- Store copies of your uploaded files after processing
- Use your data for model training or any purpose other than the cleaning run you initiated
- Share your data with third parties

### 9.3 No Live Database Connections or Stored Credentials

ColtraDataAi does not ask for and does not store database credentials, API keys from your source systems, or connection strings. See Chapter 6 for the data connectivity model.

### 9.4 API Key Security

Enterprise API keys are stored as SHA-256 hashes. The plain-text key is displayed only at provisioning time. ColtraDataAi staff cannot retrieve a plain-text key after it has been issued. If you lose your key, contact support@coltradata.com to revoke the existing key and issue a replacement.

### 9.5 GDPR and Data Processing

Under UK GDPR, you remain the data controller for any data you upload to ColtraDataAi. Coltrane Ltd acts as a data processor for the duration of the processing session only.

For clinical and healthcare data specifically, ensure you have a lawful basis for the processing and that your organisation's data protection policy permits upload to a cloud processing service before uploading patient-identifiable data. Consider uploading anonymised or pseudonymised exports where possible.

A Data Processing Agreement (DPA) is available on request for organisations that require one. Contact support@coltradata.com.

### 9.6 Infrastructure

The application runs on Render (EU region). Authentication and storage are handled by Supabase. Both providers are GDPR-compliant with standard contractual clauses in place for EU data transfers.

> **Key Takeaways - Chapter 9**
> - OTP login - no passwords stored.
> - Uploaded data is not retained after your session ends.
> - API keys are SHA-256 hashed. Plain-text keys are shown once at provisioning.
> - You are the data controller. A DPA is available on request.
> - For healthcare and clinical data, consider using pseudonymised exports.

---

## 10. Getting Help

### 10.1 Live Demo

Explore the platform with sample data before uploading your own files:
**app.coltradata.com/Live_Demo**

Two pre-built datasets are available. The demo shows the full results flow including quality score card, findings table, and charts.

### 10.2 Email Support

For questions about the platform, billing, or your account:
**support@coltradata.com**

For Enterprise plan enquiries and custom onboarding:
**support@coltradata.com** (mark your subject line "Enterprise")

Response times: 1 business day for Starter and above; 2 business days for Free plan.

### 10.3 API Documentation

Full interactive API documentation (Swagger/OpenAPI):
**https://coltradata-api.onrender.com/docs**

### 10.4 Marketing and Pricing Information

**coltradata.com** - platform overview, use cases, and pricing comparison
**coltradata.com/pricing** - full pricing page with plan comparison and checkout

---

## Appendix A: Pricing Quick Reference

| Plan | Price | Runs | Max Rows | API | Reports |
|---|---|---|---|---|---|
| Free | £0/month | 3 | 5,000 | No | Basic results only |
| Starter | £29/month | 50 | 50,000 | No | Excel |
| Professional | £99/month | 200 | 250,000 | Yes (1k rows, 100 calls) | Excel + PDF |
| Business | £299/month | 1,000 | 1,000,000 | Yes (10k rows, unlimited) | Branded Excel + PDF |
| Enterprise | £999/month | Unlimited | Unlimited | Yes (unlimited) | Branded + custom |
| Enterprise API | £499/month | - | Unlimited | Yes (unlimited, standalone) | - |

---

## Appendix B: Domain Cleaner Compatibility Matrix

| Source Application | Finance | Logistics | Trade | Healthcare | Clinical | Retail | Consultant | SME | Hospitality |
|---|---|---|---|---|---|---|---|---|---|
| Xero | Yes | - | - | - | - | - | - | Yes | - |
| Sage 50 | Yes | - | - | - | - | - | - | Yes | - |
| QuickBooks Online | Yes | - | - | - | - | - | - | Yes | - |
| FreeAgent | Yes | - | - | - | - | - | - | Yes | - |
| SAP Business One | Yes | - | Yes | - | - | - | - | - | - |
| SAP GTS | - | - | Yes | - | - | - | - | - | - |
| Oracle Trade Management | - | - | Yes | - | - | - | - | - | - |
| CargoWise | - | Yes | Yes | - | - | - | - | - | - |
| Mintsoft WMS | - | Yes | - | - | - | - | - | - | - |
| Linnworks | - | Yes | - | - | - | Yes | - | - | - |
| Shopify | - | - | - | - | - | Yes | - | - | - |
| SystmOne | - | - | - | Yes | - | - | - | - | - |
| EMIS Health | - | - | - | Yes | - | - | - | - | - |
| REDCap | - | - | - | - | Yes | - | - | - | - |
| Medidata Rave | - | - | - | - | Yes | - | - | - | - |
| Harvest | - | - | - | - | - | - | Yes | - | - |
| Toggl Track | - | - | - | - | - | - | Yes | - | - |
| Opera PMS | - | - | - | - | - | - | - | - | Yes |
| Mews | - | - | - | - | - | - | - | - | Yes |
| Cloudbeds | - | - | - | - | - | - | - | - | Yes |

*Any application not listed that can export CSV is compatible. Column names are auto-detected.*

---

## Appendix C: API Endpoint Reference

**Base URL:** `https://coltradata-api.onrender.com`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Returns API health status |
| POST | `/v1/clean/finance` | Finance and Accounting cleaner |
| POST | `/v1/clean/logistics` | Logistics and Supply Chain cleaner |
| POST | `/v1/clean/retail` | Retail and Inventory cleaner |
| POST | `/v1/clean/trade` | Import/Export and Trade cleaner |
| POST | `/v1/clean/healthcare` | Healthcare - Operational cleaner |
| POST | `/v1/clean/consultant` | Consultants and Professional Services cleaner |
| POST | `/v1/clean/sme` | SME and Small Business cleaner |
| POST | `/v1/clean/hospitality` | Hospitality and Accommodation cleaner |
| POST | `/v1/clean/clinical` | Clinical Research cleaner |

**Authentication:** `Authorization: Bearer <api_key>`

**Accepted input:** `multipart/form-data` with CSV file (field: `file`) or `application/json` with row array (field: `rows`)

**Response:** JSON - see Section 7.3 for response structure.

**Interactive docs:** `https://coltradata-api.onrender.com/docs`

---

## Appendix D: S3 Scheduled Export Setup Checklist

Use this checklist when setting up an automated scheduled export to AWS S3 for use with ColtraDataAi (Business and Enterprise plans).

**AWS setup**
- [ ] Create an S3 bucket in eu-west-2 (London) or your nearest region
- [ ] Enable versioning on the bucket (recommended for audit trail)
- [ ] Create an IAM user with read-only access to the bucket (for ColtraDataAi)
- [ ] Generate an access key pair for the IAM user
- [ ] Apply a bucket policy restricting write access to your source system only

**Source system setup**
- [ ] Configure your source system's scheduled report to export as CSV
- [ ] Set the export schedule (daily, weekly, or period-end)
- [ ] Configure the export destination as the S3 bucket path
- [ ] Test one manual export to confirm the file lands in the correct location
- [ ] Verify the CSV column names match ColtraDataAi's expected format for your chosen domain cleaner

**ColtraDataAi setup**
- [ ] Log in to app.coltradata.com
- [ ] Navigate to Settings > Data Sources
- [ ] Enter your S3 bucket name and IAM read-only credentials
- [ ] Select the target domain cleaner
- [ ] Set the run schedule to match your export schedule (allow 15 minutes after export)
- [ ] Run a manual test using the "Run Now" option
- [ ] Verify the report appears in Run History with the correct row count

**Ongoing**
- [ ] Review Run History regularly to confirm scheduled runs are completing
- [ ] Rotate IAM access keys every 90 days as per AWS best practice
- [ ] Contact support@coltradata.com if a scheduled run fails to appear

---

## Appendix E: Glossary

**CSV** - Comma-Separated Values. A plain text file format used to store tabular data. Supported by all major accounting, ERP, and business applications.

**Domain Cleaner** - One of ColtraDataAi's nine sector-specific data validation modules. Each applies standards and checks relevant to its domain.

**HS Code** - Harmonised System code. A globally standardised commodity code issued by the World Customs Organization. Used to classify goods for import and export.

**Incoterms** - International Commercial Terms. A set of 11 standard trade terms published by the International Chamber of Commerce (ICC) defining the responsibilities of buyers and sellers in international transactions.

**ISO 3166-1 alpha-2** - The international standard for two-letter country codes (e.g. GB, US, NG).

**ISO 4217** - The international standard for three-letter currency codes (e.g. GBP, USD, NGN).

**MTD** - Making Tax Digital. HMRC's programme requiring businesses to keep digital tax records and submit returns using compatible software.

**NCT ID** - ClinicalTrials.gov identifier. A unique identifier assigned to each registered clinical trial (format: NCT followed by 8 digits).

**NHS RTT** - NHS Referral to Treatment. The 18-week standard that sets the maximum time from referral to start of treatment.

**OTP** - One-Time Passcode. A single-use authentication code sent by email, used by ColtraDataAi in place of a password.

**Pre-signed URL** - A time-limited URL generated by AWS that grants temporary access to a specific S3 object without requiring AWS credentials.

**Quality Score** - ColtraDataAi's single-figure summary of overall data quality for a cleaning run, expressed as a percentage from 0 to 100.

**RevPAR** - Revenue per Available Room. A standard hospitality industry metric calculated as total room revenue divided by available rooms.

**Run** - One execution of the ColtraDataAi cleaning engine on a single uploaded file.

**S3** - Amazon Simple Storage Service. An AWS cloud object storage service used as an intermediary file drop in the ColtraDataAi scheduled export automation pattern.

**Trial Balance** - An accounting report that lists all nominal ledger accounts and confirms that total debits equal total credits, verifying the integrity of the double-entry bookkeeping records.

**VAT Notice 700/22** - HMRC guidance specifying the digital records that must be kept per transaction for Making Tax Digital for VAT.

**WCO** - World Customs Organization. The international body that maintains the Harmonised System for commodity classification.

---

*ColtraDataAi is a product of Coltrane Ltd.*
*For support: support@coltradata.com*
*Platform: app.coltradata.com | Marketing: coltradata.com | API docs: coltradata-api.onrender.com/docs*

*Version 1.0 | September 2026*

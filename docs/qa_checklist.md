# ColtraDataAi — QA & Deployment Checklist

Use this checklist before every production push and after every significant change.

---

## Pre-Push: Code Quality

- [ ] `python -m pytest tests/` — all tests pass
- [ ] No syntax errors: `python -m py_compile app.py core/*.py ui/*.py config/*.py utils/*.py`
- [ ] No hardcoded colours, names or disclaimer text outside `config/branding_config.py`
- [ ] No advisory language in any insight/output copy
- [ ] New modules have corresponding tests in `tests/`
- [ ] `requirements.txt` updated if new packages were added

---

## Pre-Push: Branding Consistency

- [ ] `config/branding_config.py` is the single source for all brand values
- [ ] Any brand change is also updated in `assets/branding/style_guide.md`
- [ ] Any brand change is also updated in `assets/templates/report_styles.json`
- [ ] Logo file is at `assets/logo/coltradata_logo.png`
- [ ] Favicon is at `assets/favicon.png`
- [ ] `docs/branding_update_log.md` updated with the change date and description

---

## Pre-Push: GitHub

- [ ] Branch is `master` (production deploys from master)
- [ ] `git status` is clean — no unintended uncommitted changes
- [ ] `.streamlit/secrets.toml` is **not** staged (it's in `.gitignore`)
- [ ] No `.env` files or API keys visible in the diff
- [ ] Commit message is descriptive and follows project convention

---

## Post-Deploy: Streamlit Cloud

- [ ] Streamlit Cloud dashboard shows the deploy succeeded (green)
- [ ] App loads at the live URL without errors
- [ ] Login screen renders correctly with logo and tagline
- [ ] Correct password accepted; incorrect password shows error (not a crash)
- [ ] File upload accepts CSV, XLSX and XLS files
- [ ] Tier shown in sidebar matches expected (Free for new sessions)

---

## Functional Smoke Test — Run After Every Deploy

Upload the sample test file and verify:

### Step 1: Upload
- [ ] CSV upload loads without error
- [ ] XLSX upload loads without error
- [ ] Row count shown in preview matches file

### Step 2: Configure
- [ ] All three checkboxes render correctly
- [ ] Null handling selectbox shows 3 options

### Step 3: Preview
- [ ] Raw data preview shows first 10 rows
- [ ] File summary shows correct row count, column count, missing values

### Step 4: Process
- [ ] "Generate Clean Report" button triggers spinner
- [ ] Processing completes without error
- [ ] KPI banner appears: 5 cards with correct values
- [ ] Overall Risk card shows correct colour (Low/Medium/High)

### Step 5: Dashboard
- [ ] Missing Values by Column chart renders (or "No missing values" info)
- [ ] Original vs Cleaned Rows chart renders
- [ ] For Pro tier: Premium Chart Gallery renders all auto-generated charts
- [ ] For Pro tier: Distribution Analysis dropdowns work without losing results
- [ ] Cleaned Data Preview shows post-cleaning data

### Step 6: Insights (Pro+)
- [ ] Data Insights section renders with categories and bullet points
- [ ] No advisory language present in any insight line

### Step 7: Download
- [ ] Excel download produces a valid `.xlsx` file
- [ ] Excel file opens correctly in Excel/LibreOffice
- [ ] All 9 sheet tabs are present with correct names and tab colours
- [ ] Cover sheet shows logo, title, ToC with working hyperlinks
- [ ] Executive Summary sheet shows KPIs and embedded charts
- [ ] PDF download produces a valid `.pdf` file
- [ ] PDF opens and displays: logo, title, KPI table, Risk Mix, charts
- [ ] PDF page footer shows branding line + page number on every page

---

## Excel Report QA Detail

Open the downloaded Excel file and verify:

| Check                              | Pass |
|------------------------------------|------|
| All 9 tabs present                 | [ ]  |
| Tab colours applied                | [ ]  |
| Cover sheet has logo               | [ ]  |
| Cover sheet ToC links work         | [ ]  |
| Raw Data tab: auto-filter active   | [ ]  |
| Raw Data tab: blank cells highlighted `#FFF2CC` | [ ] |
| Cleaned Data tab: blank cells highlighted | [ ] |
| Quality Checks tab: risk colours correct | [ ] |
| Executive Summary: KPI grid aligned | [ ] |
| Executive Summary: charts embedded  | [ ] |
| Dashboard tab: charts render        | [ ] |
| No hardcoded placeholder text       | [ ] |

---

## PDF Report QA Detail

Open the downloaded PDF file and verify:

| Check                                    | Pass |
|------------------------------------------|------|
| Logo visible on page 1                   | [ ]  |
| Tagline visible below logo               | [ ]  |
| Generation date correct                  | [ ]  |
| KPI table: 4 rows × 4 columns           | [ ]  |
| Risk cell colour-coded correctly         | [ ]  |
| Risk Mix table: correct counts           | [ ]  |
| Charts embedded and readable             | [ ]  |
| Non-advisory disclaimer present          | [ ]  |
| Page footer on every page                | [ ]  |
| Page number increments correctly         | [ ]  |
| Contact email in footer                  | [ ]  |

---

## GitHub Branding Update Checklist

When a branding element (logo, tagline, email, colour) changes:

1. [ ] Edit `config/branding_config.py`
2. [ ] Edit `assets/templates/report_styles.json` (matching tokens)
3. [ ] Replace file in `assets/logo/` or `assets/` as needed
4. [ ] Edit `.streamlit/config.toml` if primary colour changed
5. [ ] Update `assets/branding/style_guide.md`
6. [ ] Add entry to `docs/branding_update_log.md`
7. [ ] Run full smoke test (checklist above)
8. [ ] Commit with message: `Branding: update [element] — [brief description]`
9. [ ] Push to `master`
10. [ ] Verify deployment on Render (`app.coltradata.com`)
11. [ ] Confirm live app reflects change

---

## Enterprise API QA

Run these checks after any change to `api/` or after a Render API service deploy.

### Health & Authentication

- [ ] `GET https://coltradata-api.onrender.com/health` returns `{"status": "ok"}`
- [ ] `GET https://coltradata-api.onrender.com/docs` — Swagger UI loads without errors
- [ ] Request with no Authorization header returns `401 Unauthorized`
- [ ] Request with malformed bearer token returns `401 Unauthorized`
- [ ] Request with a deactivated key returns `401 Unauthorized`
- [ ] Request with valid test key returns successful response

### Domain Cleaner Endpoints

For each domain, send a representative CSV and confirm the response:

| Domain | Endpoint | Key columns to check |
|---|---|---|
| Finance | `POST /v1/clean/finance` | Transaction dates, DR/CR amounts, missing values flagged |
| Logistics | `POST /v1/clean/logistics` | Shipment dates, tracking numbers, duplicate refs |
| Retail | `POST /v1/clean/retail` | SKU normalisation, price validation, stock levels |
| Trade | `POST /v1/clean/trade` | Import/export codes, currency, incoterms |
| Healthcare | `POST /v1/clean/healthcare` | Patient ref format, date validity, status codes |
| Consultant | `POST /v1/clean/consultant` | Project codes, timesheet entries, billing rates |
| SME | `POST /v1/clean/sme` | Mixed column detection, date/amount parsing |
| Hospitality | `POST /v1/clean/hospitality` | Booking refs, check-in/out dates, channel normalisation |

- [ ] All 8 domain endpoints return `200 OK` with cleaned data
- [ ] CSV input (multipart/form-data) accepted on all domains
- [ ] JSON body input accepted on all domains
- [ ] Unknown domain (`POST /v1/clean/invalid`) returns `404` or `422`
- [ ] Empty file returns appropriate error, not a 500
- [ ] File with 0 data rows (headers only) handled gracefully

### Usage Logging

- [ ] After a successful API call, a new row appears in Supabase `api_usage_log` with correct domain and row count
- [ ] `api_usage_monthly` view reflects the new call
- [ ] Failed auth attempts do NOT generate usage log entries

---

## AI Advisor / Chatbot Capabilities QA

The AI Advisor (`core/ai_advisor.py`) generates descriptive data quality observations after a clean run. It is available to Business and Enterprise tiers only.

### Tier Access

- [ ] Free tier: AI Advisor section does NOT appear
- [ ] Starter tier: AI Advisor section does NOT appear
- [ ] Professional tier: AI Advisor section appears (confirm model used)
- [ ] Business tier: AI Advisor uses Claude Sonnet model — confirm in Anthropic API usage logs
- [ ] Enterprise tier: AI Advisor uses Claude Opus model — confirm in Anthropic API usage logs

### Output Quality

- [ ] AI Advisor output describes data quality findings (e.g. "23 date fields contain entries outside the expected range")
- [ ] NO advisory language present: phrases like "you should", "we recommend", "action required" must NOT appear
- [ ] Each observation is factual and tied to a specific data column or metric
- [ ] Output renders correctly in the app — no raw JSON or error messages visible
- [ ] If Anthropic API key is missing or rate-limited, a graceful error message appears (not a crash)

### Chatbot Capabilities — What the AI Advisor Can Do

| Capability | Available |
|---|---|
| Describe data quality issues in natural language | Yes |
| Summarise column-level findings | Yes |
| Identify patterns in missing/invalid data | Yes |
| Flag outliers or anomalies in the dataset | Yes |
| Explain what each domain-specific flag means | Yes |
| Provide business recommendations or advice | No — out of scope |
| Answer user questions interactively (chatbot) | No — single-pass output only |
| Predict future trends from cleaned data | No — out of scope |
| Access the internet or external data | No |

> **Note:** The AI Advisor is a single-pass insights generator, not an interactive chatbot. It runs once after the cleaning step and produces a structured set of observations. If an interactive chatbot capability is added in future, this checklist will be updated.

---

## Domain-Specific Cleaner QA

Upload a sample dataset for each domain and verify the following after running a clean:

### Finance & Accounting

- [ ] Duplicate transaction references flagged
- [ ] Invalid or unparseable date entries flagged
- [ ] DR/CR type column detected correctly (word-boundary matching — "dr" must NOT match "description")
- [ ] Missing amount values flagged
- [ ] Currency inconsistencies flagged (if multi-currency dataset)
- [ ] KPI banner shows: Total Transactions, Missing Values, Issues Detected, Clean Rate

### Logistics & Supply Chain

- [ ] Duplicate shipment/order references detected
- [ ] Invalid shipment dates (future dates, impossible ranges) flagged
- [ ] Carrier name normalisation applied
- [ ] Missing destination or origin fields flagged
- [ ] KPI banner shows: Total Shipments, On-Time Rate, Issues, Clean Rate

### Retail & Inventory

- [ ] SKU formatting normalised
- [ ] Negative stock values flagged
- [ ] Price anomalies (zero price, outlier prices) flagged
- [ ] Product name duplicates detected

### Import/Export & Trade

- [ ] HS/commodity codes validated
- [ ] Missing country of origin flagged
- [ ] Date of dispatch vs. date of arrival logic checked

### Healthcare (Operational)

- [ ] Patient reference format validated
- [ ] Invalid appointment/admission dates flagged
- [ ] Status field normalised (Admitted/Discharged/No-Show etc.)
- [ ] No clinical or diagnostic data expected — operational data only

### Consultants & Professional Services

- [ ] Project code format standardised
- [ ] Timesheet entries with zero or negative hours flagged
- [ ] Billing rate outliers flagged

### SME & Small Business

- [ ] Mixed-format date columns detected and normalised
- [ ] General missing value scan across all columns
- [ ] Duplicate row detection

### Hospitality & Accommodation

- [ ] Booking reference standardisation and duplicate detection
- [ ] Check-in/check-out date validation (impossible dates, zero-night stays, stays >30 nights)
- [ ] Room type normalisation (Double/Suite/King/Twin etc.)
- [ ] Booking status normalisation (Confirmed/Cancelled/No-Show/Checked-In/Checked-Out)
- [ ] Channel normalisation (OTA/Direct/Corporate/Travel Agent etc.)
- [ ] KPI banner: Total Bookings, Cancellation Rate, Avg Daily Rate, Avg Length of Stay, No-Show Rate

---

## Accounting Software Data Format QA

Test that common accounting software exports clean correctly:

### Xero Export (CSV)

- [ ] Upload a Xero transaction export → Finance cleaner produces meaningful output
- [ ] Date column (Xero format: DD/MM/YYYY) correctly parsed
- [ ] "Account Code", "Reference", "Net Amount" columns handled without errors
- [ ] Tax amount columns do not cause type errors

### QuickBooks Export (CSV)

- [ ] Upload a QuickBooks transaction list export → Finance cleaner runs without error
- [ ] MM/DD/YYYY date format detected and normalised
- [ ] Multi-currency columns handled gracefully

### Sage Export (CSV / XLS)

- [ ] Upload a Sage 50 / Sage 200 export → Finance cleaner processes correctly
- [ ] Account reference column normalised
- [ ] Debit/Credit columns recognised

> **Note:** ColtraDataAi does not connect directly to these platforms. These tests cover exported file formats only.

---

## Website & Pricing Page QA

Run after any website update or pricing change:

- [ ] `coltradata.com` loads correctly (GitHub Pages live)
- [ ] All 5 pricing tier cards visible on `pricing.html`
- [ ] Enterprise £999 card shows "Book a Demo" CTA — not a checkout link
- [ ] Enterprise API £499 card shows checkout link
- [ ] Free, Starter, Professional, Business cards link to correct LemonSqueezy checkout URLs
- [ ] `privacy.html` — "Last updated" date matches the date of last policy change
- [ ] All industry landing pages load without broken links: `bookkeepers.html`, `finance-teams.html`, `logistics.html`, `consultants.html`, `retail.html`, `researchers.html`, `smes.html`, `healthcare.html`, `importers-exporters.html`
- [ ] Nav links on all pages point to live app: `app.coltradata.com`
- [ ] Footer contact email is `support@coltradata.com` on all pages
- [ ] Mobile view (375px viewport) — no horizontal scroll, nav readable

---

## Authentication & Billing QA

- [ ] Sign-in at `app.coltradata.com` — OTP email received via Resend within 60 seconds
- [ ] Correct 6-digit OTP accepted; incorrect code rejected
- [ ] After sign-in, plan tier shown in sidebar matches subscription in Supabase `subscriptions` table
- [ ] Free user sees Free tier limits; Starter user sees Starter limits; etc.
- [ ] Test checkout (Starter) in LemonSqueezy test mode — licence key delivered by email
- [ ] After licence delivery, sign in and confirm plan upgrades to Starter
- [ ] Cancelled subscription → plan reverts to Free after billing period

---

## Legal & Compliance QA

Run when privacy.html or terms are updated:

- [ ] `docs/privacy.html` reflects all current third-party processors (LemonSqueezy, Supabase, Render, Resend, Anthropic, YouTube)
- [ ] Section 5b present: Xero/QuickBooks/Sage export handling
- [ ] Section 5c present: Enterprise database connection handling
- [ ] Section 5d present: Enterprise API data handling
- [ ] Data retention periods are correctly stated and match actual system behaviour
- [ ] "Last updated" date is current
- [ ] ICO complaint link is present and correct (`ico.org.uk`)

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
10. [ ] Verify deployment on Streamlit Cloud
11. [ ] Confirm live app reflects change

# ColtraDataAi — Branding Update Log

Record every brand change here so the team can trace when and why each
element changed without needing to dig through git history.

---

## v2.0 — June 2026

### Logo
- Updated to new ColtraDataAi logo (`assets/logo/coltradata_logo.png`)
- Old logo archived (backup copies in `assets/`)
- Favicon updated to match (`assets/favicon.png`)

### Tagline
- Changed to: **DATA. INSIGHTS. INTELLIGENCE.**
- Applied across: Streamlit header, login screen, Excel cover sheet, PDF header

### Contact Email
- Updated to: `support@coltradata.com`
- Applied across: Streamlit footer, Excel cover sheet, PDF footer

### Colour Palette — no changes in v2.0
- Primary: `#1F4E79` (unchanged)
- All other tokens: unchanged

### Pushed to GitHub
- All branding changes committed and pushed via VS Code on the `master` branch
- Streamlit Cloud redeployed automatically

---

## Enhancement Pack — June 2026

### New branding tokens added to `config/branding_config.py`
- `accent_colour`: `#2E86AB` — used for download buttons and PDF highlights
- `light_fill`: `#F8FAFC` — very light background for PDF KPI cells
- `logo_path`: `"assets/logo/coltradata_logo.png"` — centralised path reference
- `report_disclaimer`: full non-advisory disclaimer string
- `footer_line`: standardised footer branding line for PDF pages
- `chart_palette`: 6-colour sequence for consistent chart coloring

### New UI components (`core/ui_components.py`, `ui/branding_components.py`)
- `render_step_header` — numbered circular badge headers
- `render_kpi_row` — branded KPI metric cards
- `render_risk_kpi` — colour-coded risk badge
- `render_section_divider` — labelled section dividers
- `inject_app_css` — centralised CSS injection

### Excel report improvements
- Sheet tab colours applied (each sheet gets a distinct brand colour)
- Cover sheet now includes a clickable Table of Contents
- Header row heights increased for readability
- Executive Summary sheet uses a 2-column KPI layout

### PDF report improvements
- Branded page footer on every page (footer line + page number)
- Improved cover block: logo → title → tagline → date → HR divider
- KPI table: risk level cell coloured red/amber/green
- Risk Mix table: per-row coloured label cells

### Chart gallery improvements
- Updated `_premium_theme`: cleaner axis formatting, consistent tick fonts
- Chart palette draws from `branding["chart_palette"]`

---

## How to Update Branding in Future

1. Edit `config/branding_config.py` — change the relevant key(s)
2. If adding a new token, also update `assets/templates/report_styles.json` and `assets/branding/style_guide.md`
3. If changing the logo, replace `assets/logo/coltradata_logo.png` and `assets/favicon.png`
4. If changing the Streamlit theme colour, update `.streamlit/config.toml` → `[theme].primaryColor`
5. Run `pytest tests/` to verify nothing is broken
6. Commit and push to `master`
7. Record the change in this file with date and description

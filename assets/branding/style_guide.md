# ColtraDataAi Brand Style Guide

## Identity

| Element         | Value                                   |
|-----------------|-----------------------------------------|
| Product name    | **ColtraDataAi**                        |
| Company         | Coltrane Ltd                            |
| Tagline         | DATA. INSIGHTS. INTELLIGENCE.           |
| Contact email   | support@coltradata.com                  |
| Version         | 2.0                                     |

---

## Colour Palette

| Role              | Hex       | Usage                                                      |
|-------------------|-----------|------------------------------------------------------------|
| Primary           | `#1F4E79` | Headers, primary buttons, chart titles, section dividers   |
| Accent            | `#2E86AB` | Download buttons, highlighted values, mid-tier accents     |
| Secondary         | `#D9E1F2` | Table header fills, chart fill areas                       |
| Neutral fill      | `#F2F2F2` | Metric label backgrounds, alternating row fills            |
| Light fill        | `#F8FAFC` | Section card backgrounds, PDF label cells                  |
| Success           | `#46D324` | Pass / Low Risk / Cleaned Data tab                         |
| Warning           | `#F59E0B` | Review / Medium Risk / Quality Checks tab                  |
| Danger            | `#DC2626` | Warning / High Risk / error states                         |
| Body text         | `#33414E` | Main body copy, chart axis labels                          |
| Muted text        | `#657286` | Captions, subtitles, metadata                              |
| Border / rule     | `#E6ECF0` | Card borders, divider lines, table grid lines              |

---

## Typography

### Streamlit UI
- Font stack: Streamlit default (Inter / system sans-serif)
- Step headers: **700 weight, 1.05 rem**, primary colour
- Captions / subtitles: 0.83 rem, muted (`#657286`)
- KPI values: **800 weight, 1.5 rem**, primary colour
- KPI labels: 0.72 rem, uppercase, letter-spacing 0.07 em

### Excel Reports
- Title rows: Calibri (or default), 20 pt, bold, primary colour
- Section headers: 12 pt, bold, white text on primary background
- Table headers: 10 pt, bold, primary colour on secondary fill
- Body: 10 pt, standard weight
- Disclaimers: 9 pt, italic, muted grey (`#666666`)

### PDF Reports
- Title: Helvetica-Bold, 22 pt, primary colour
- Tagline: Helvetica, 9.5 pt, muted grey, letter-spacing
- Section headers: Helvetica-Bold, 11 pt, white on primary background
- Body copy: Helvetica, 9.5 pt, body text colour
- Captions: Helvetica-Oblique, 8.5 pt, muted grey
- Footer: Helvetica, 7.5 pt, muted grey

---

## Logo Usage

- **File:** `assets/logo/coltradata_logo.png`
- **Favicon:** `assets/favicon.png`
- Minimum clear space: equal to the height of the "C" letterform on all sides
- Do not stretch, recolour, rotate, or apply drop shadows to the logo
- On dark backgrounds, use the white/reversed version if available
- Minimum display width: 80 px (digital); 25 mm (print)

---

## Non-Advisory Positioning

ColtraDataAi is positioned as a **data cleaning and structured reporting engine**, not an advisory or consulting platform.

### Permitted language
- "This column contains X% missing values."
- "Y duplicate rows were identified and removed."
- "The dataset completeness rate is Z%."
- "High-risk fields: [list]."

### Prohibited language
- "You should…" / "We recommend…"
- "This data suggests your business is…"
- "Based on this data, consider…"
- Any language implying financial, legal, tax or strategic advice

All insight and observation copy must be **descriptive and observational only**.
The non-advisory disclaimer must appear on every PDF page, every Excel cover sheet, and in the Streamlit app footer.

---

## Report Output Standards

| Output surface     | Logo | Brand colours | Disclaimer | Footer |
|--------------------|------|---------------|------------|--------|
| Streamlit UI       | ✓    | ✓             | ✓ (footer) | ✓      |
| Excel Report       | ✓    | ✓             | ✓ (cover)  | –      |
| Excel sheets       | –    | ✓ (tab colour)| –          | –      |
| PDF Executive Sum. | ✓    | ✓             | ✓          | ✓ (pg) |

---

## Branding Update Checklist

When updating the brand (logo, tagline, contact, colours), change values in:

1. `config/branding_config.py` — primary source of truth
2. `assets/branding/style_guide.md` — this document
3. `assets/templates/report_styles.json` — report token overrides
4. `.streamlit/config.toml` — Streamlit theme colours

Do **not** hardcode brand values anywhere else in the codebase.

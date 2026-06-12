# ColtraDataAi — Deployment Notes

## Live Deployment

| Item            | Detail                                              |
|-----------------|-----------------------------------------------------|
| Platform        | Streamlit Community Cloud                           |
| Entry point     | `app.py`                                            |
| Python version  | 3.11 (pinned in `runtime.txt` if required)         |
| GitHub repo     | Connected via VS Code / GitHub integration          |
| Deploy trigger  | Push to `master` branch → auto-deploys             |

---

## Secrets Configuration

The app requires `.streamlit/secrets.toml` on Streamlit Cloud (set via the Secrets panel in the dashboard — never commit this file).

```toml
[credentials]
password = "your-app-password"

[dev]
local_dev    = false   # set true locally to bypass tier enforcement
testing_mode = false   # set true to show the tier-override dropdown
```

---

## Required Environment / Dependencies

All runtime dependencies are listed in `requirements.txt`.  Key packages:

| Package         | Purpose                                  | Version constraint |
|-----------------|------------------------------------------|--------------------|
| streamlit       | Web UI framework                         | latest compatible  |
| pandas          | Data manipulation                        | ≥ 2.0              |
| plotly          | Interactive charts                       | latest             |
| kaleido         | PNG chart export for Excel/PDF embedding | < 1.0              |
| xlsxwriter      | Excel workbook generation                | latest             |
| reportlab       | PDF generation                           | latest             |
| openpyxl        | .xlsx reading                            | latest             |
| xlrd            | .xls reading                             | ≥ 2.0              |
| Pillow          | Logo/image handling                      | latest             |

---

## Folder Structure (Reference)

```
coltradataai/
├── app.py                    ← Streamlit entry point (slim orchestrator)
├── requirements.txt
├── .streamlit/
│   ├── config.toml           ← Theme and layout settings
│   └── secrets.toml          ← NOT committed (set via Cloud Secrets panel)
├── assets/
│   ├── logo/coltradata_logo.png
│   ├── favicon.png
│   ├── branding/style_guide.md
│   └── templates/report_styles.json
├── core/                     ← Business logic (no Streamlit imports)
├── ui/                       ← Streamlit panel renderers
├── config/                   ← All configuration (branding, tiers, rules)
├── utils/                    ← Shared helpers
├── tests/                    ← pytest test suite
└── docs/                     ← This folder
```

---

## Local Development

```bash
# 1. Clone and create virtual environment
git clone <repo-url>
cd DataCleaningApp
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create local secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml — set credentials.password

# 4. Run
streamlit run app.py
```

---

## Deployment Steps (Streamlit Cloud)

1. Push changes to `master` on GitHub
2. Streamlit Cloud detects the push and redeploys automatically
3. Monitor deployment progress in the Streamlit Cloud dashboard
4. If the deploy fails, check the **Manage app → Logs** panel

### Rolling back

1. Open the Streamlit Cloud dashboard
2. Select the app → **Manage app**
3. Use **Reboot app** or revert the GitHub commit and push

---

## Common Issues

| Symptom                    | Likely cause                          | Fix                                          |
|----------------------------|---------------------------------------|----------------------------------------------|
| App won't start            | Missing package in requirements.txt   | Add package, push                            |
| Login screen loop          | Secrets not configured                | Add `[credentials].password` in Cloud Secrets|
| Charts blank in PDF        | Kaleido version ≥ 1.0                | Pin `kaleido<1.0` in requirements.txt        |
| Excel download fails       | xlsxwriter write error                | Check logs; usually a data type issue        |
| Tier shows "Free" always   | LemonSqueezy not configured           | Set keys in secrets.toml (optional)          |

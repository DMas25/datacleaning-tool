# ColtraDataAi

**Turn messy spreadsheets into clean data and board-ready quality reports — in minutes, not afternoons.**

Automated data cleaning, exact value recovery, validation, and dashboard reporting.
Built by **Coltrane Ltd** · [support@coltradata.com](mailto:support@coltradata.com) · [coltradata.com](https://coltradata.com)

<!-- TODO: add 15–30s demo GIF here (Streamlit screencast → GIF). One image sells this better than every word below. -->
<!-- ![ColtraDataAi demo](assets/demo.gif) -->
<!-- Brand spelling is ColtraDataAi (capital A, lowercase i) — matches the logo. Keep consistent in branding_config.py, landing page, and Lemon Squeezy product names. -->

---

## What it does

Upload a CSV, XLSX, or XLS file. ColtraDataAi cleans it, repairs what can be repaired with certainty, flags what can't, and hands back a professional multi-sheet report — with a transparent log of every operation applied.

**Intelligent cleaning pipeline:**

- **Sentinel normalisation** — converts disguised missing values (`ERROR`, `UNKNOWN`, `N/A`, `-`, …) into true nulls before any analysis, so missingness counts are honest and numeric columns keep their types
- **Exact arithmetic recovery** — repairs missing values mathematically where relationships allow (e.g. `total = quantity × price`); recovered, not imputed, with zero guesswork
- **Reference-based field recovery** — fills missing categorical values only where the mapping is unambiguous (≥99% confidence); ambiguous cases are never guessed
- **Intelligent outlier classification** — separates true anomalies from *valid extreme values* (large-but-legitimate records), so your best transactions aren't flagged as errors
- **Standard hygiene** — deduplication, whitespace trimming, header standardisation

**Reporting:**

- Per-column quality breakdown with weighted risk scoring
- Step-by-step cleaning log — every operation recorded, nothing silent
- Conditional recommended actions (distinguishes "fixable by cleaning" from "fix at source")
- Distribution, correlation, and trend dashboards
- AI-generated structured data insights
- Multi-sheet Excel workbook with embedded chart gallery
- One-page PDF executive summary

**Scope:** data cleaning and structuring only. No SQL, no advisory output, no business recommendations. Outputs are observational; users remain responsible for decisions made with them.

---

## Plans

| Feature | Free | Pro (£29/mo) | Enterprise (£99/mo) |
|---|:---:|:---:|:---:|
| Cleaning pipeline + quality checks | ✅ | ✅ | ✅ |
| Cleaning log + risk summary | ✅ | ✅ | ✅ |
| Distribution / correlation / trend dashboards | — | ✅ | ✅ |
| AI-generated data insights | — | ✅ | ✅ |
| Multi-sheet Excel report with chart gallery | — | ✅ | ✅ |
| One-page PDF executive summary | — | ✅ | ✅ |

<!-- TODO: confirm the Free vs Pro split above matches tier_config.py before publishing -->

---

## Repository layout

```
DataCleaningApp/
├── app.py                        # Streamlit entrypoint
├── config/
│   ├── branding_config.py        # Colours, app name, contact
│   ├── tier_config.py            # Free / Pro / Enterprise definitions
│   └── lemonsqueezy_config.py    # Payment config (fill in when LS approved)
├── core/
│   ├── feature_gate.py           # Sidebar: licence key UI + tier logic
│   ├── licence_verifier.py       # Lemon Squeezy validate API call
│   ├── report_builder.py         # Excel report assembly
│   ├── pdf_report.py             # PDF executive summary
│   ├── chart_gallery.py          # Auto-generated chart assets
│   ├── insights_engine.py        # AI data insights
│   ├── dashboard_analytics.py    # Numeric/categorical analysis helpers
│   └── data_validator.py         # Outlier + inconsistent-value detection
├── docs/
│   ├── index.html                # Landing page (GitHub Pages)
│   └── CNAME                     # coltradata.com custom domain
├── assets/
│   ├── logo/coltradata_logo.png
│   └── favicon.png
├── .streamlit/
│   ├── config.toml               # Theme + server settings (committed)
│   ├── secrets.toml              # Credentials (gitignored — never commit)
│   └── secrets.toml.example      # Template for secrets.toml
└── requirements.txt
```

---

## Local setup

**Prerequisites:** Python 3.10+

```bash
# 1. Clone and enter the repo
git clone https://github.com/<your-org>/DataCleaningApp.git
cd DataCleaningApp

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your local secrets file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml — set [credentials] password and [dev] testing_mode

# 5. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`.

To test Pro/Enterprise features without a licence key, set `testing_mode = true` in
`.streamlit/secrets.toml` — this reveals a **Dev: override tier** dropdown in the sidebar.

> ⚠️ **If this repository ever becomes public**, move this dev-override note to an
> internal doc. Documenting the tier bypass alongside the code that implements it
> is fine in a private repo, unwise in a public one.

---

## Required secrets (`secrets.toml`)

See `.streamlit/secrets.toml.example` for the full template.

| Secret | Purpose |
|--------|---------|
| `[credentials] password` | Password that gates the entire app |
| `[dev] testing_mode` | `true` to enable tier override dropdown locally |

No other secrets are required at runtime until Lemon Squeezy is configured.

---

## Streamlit Community Cloud deployment

1. Push the repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Select your repo, branch (`main`), and set the main file path to `app.py`.
4. Under **Advanced settings → Secrets**, paste the contents of your local
   `secrets.toml` (the actual values, not the example).
5. Click **Deploy**.

The live URL will be something like `https://coltradata.streamlit.app`.
**Update this URL in `docs/index.html`** wherever `https://coltradata.streamlit.app` appears
(search for that string — it appears in navigation, hero, pricing, and footer links).

### Streamlit Cloud notes

- `output/` is excluded from the repo (generated at runtime, session-scoped).
- `kaleido<1.0` is pinned in `requirements.txt` to avoid a known crash on Streamlit Cloud.
- Max upload size is set to 200 MB in `.streamlit/config.toml`.

---

## Payment setup (Lemon Squeezy)

ColtraDataAi uses **Lemon Squeezy** for hosted checkout and licence key delivery.
No card details are handled in the app — customers are redirected to a LS-hosted page.

### Why Lemon Squeezy?

- Hosted checkout (no PCI scope)
- Built-in subscription and licence key management
- VAT / tax handling included (important for UK/EU)
- Low operational burden — no self-hosted webhook infra needed for licence validation
- The licence validate endpoint requires no API key, so validation works without secrets

### Setup steps (once your LS account is approved)

1. **Create products** in the LS dashboard:
   - Product: **ColtraDataAi Pro** — create a Monthly variant (£29/mo) and optionally an Annual variant
   - Product: **ColtraDataAi Enterprise** — create a Monthly variant (£99/mo)
   - Enable **Licence Keys** for each product variant (Products → variant → Licence keys tab)

2. **Copy variant IDs** — three-dot menu next to each variant → **Copy ID**

3. **Copy checkout URLs** — three-dot menu → **Share** → **Buy link** (the `checkout/buy/...` URL)

4. **Fill in `config/lemonsqueezy_config.py`:**

```python
PRO_MONTHLY_VARIANT_ID   = "123456"      # replace with real ID
PRO_ANNUAL_VARIANT_ID    = "789012"      # replace with real ID
ENTERPRISE_VARIANT_ID    = "345678"      # replace with real ID

PRO_MONTHLY_CHECKOUT_URL = "https://coltradata.lemonsqueezy.com/checkout/buy/..."
ENTERPRISE_CHECKOUT_URL  = "https://coltradata.lemonsqueezy.com/checkout/buy/..."

VARIANT_TIER_MAP = {
    "123456": "Pro",
    "789012": "Pro",
    "345678": "Enterprise",
}
```

5. **Update `docs/index.html`** pricing section — replace the `onclick="alert(...)"` on the Pro
   button with `href="<your PRO_MONTHLY_CHECKOUT_URL>"`.

6. **Test end-to-end:** use LS test mode → buy a test licence → enter the key in the app sidebar
   → confirm the tier changes to Pro.

### Licence key flow (user perspective)

1. User buys a plan on the LS checkout page.
2. LS emails them a licence key (e.g. `XXXX-XXXX-XXXX-XXXX`).
3. User opens the app → enters the key in the **Licence Key** field in the sidebar → clicks **Activate Licence**.
4. The app calls the LS validate API (no API key required) and unlocks the corresponding tier for the session.

**Note:** Tier activation is session-scoped — users re-enter their key each session. A persistent
entitlement store (e.g. webhook-provisioned user table) can be added in a future upgrade without
changing the existing gate logic.

### Webhook setup (optional but recommended)

If you want to automate licence revocation, renewals, or future entitlement storage, configure
a LS webhook:

1. LS dashboard → **Webhooks** → **Add webhook**
2. Set the endpoint URL to your webhook handler
3. Select events: `subscription_created`, `subscription_cancelled`, `licence_key_created`
4. Copy the signing secret

A minimal FastAPI webhook handler (`core/webhook_handler_skeleton.py`) is **planned for a
future sprint and does not yet exist in this repo**. Until then, licence key validation
alone is sufficient.

---

## GitHub Pages setup (landing page)

The `docs/` folder contains a self-contained landing page served via GitHub Pages.

### Enable GitHub Pages

1. Go to your GitHub repo → **Settings** → **Pages**
2. Under **Source**, select **Deploy from a branch**
3. Branch: `main` · Folder: `/docs`
4. Click **Save**

GitHub will deploy `docs/index.html` at `https://<your-username>.github.io/<repo-name>/`
(or at `https://coltradata.com` once DNS is configured — see below).

### Update the Streamlit app URL in the landing page

In `docs/index.html`, search for `https://coltradata.streamlit.app` and replace all
occurrences with your actual Streamlit Cloud deployment URL.

---

## GoDaddy DNS setup for coltradata.com

Once GitHub Pages is live, connect your GoDaddy domain.

### Step 1 — Add the custom domain in GitHub Pages

1. Repo → **Settings** → **Pages** → **Custom domain**
2. Enter `coltradata.com` and click **Save**
3. GitHub will verify the `docs/CNAME` file (already present in the repo)

### Step 2 — Configure DNS records in GoDaddy

Log in to GoDaddy → **My Products** → **DNS** for `coltradata.com`.

**For the apex domain (`coltradata.com`) — add four A records:**

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | 185.199.108.153 | 600 |
| A | @ | 185.199.109.153 | 600 |
| A | @ | 185.199.110.153 | 600 |
| A | @ | 185.199.111.153 | 600 |

**For `www.coltradata.com` — add a CNAME record:**

| Type | Name | Value | TTL |
|------|------|-------|-----|
| CNAME | www | `<your-github-username>.github.io` | 600 |

Replace `<your-github-username>` with your actual GitHub username.

### Step 3 — Enable HTTPS

1. Wait 10–30 minutes for DNS to propagate.
2. Return to repo **Settings → Pages** — GitHub will show a green tick once DNS resolves.
3. Check **Enforce HTTPS**.

### Result

| URL | Destination |
|-----|-------------|
| `https://coltradata.com` | Landing page (`docs/index.html`) via GitHub Pages |
| `https://www.coltradata.com` | Same — CNAME redirects to apex |
| **Launch App** button on landing page | Streamlit Cloud deployment URL |

---

## Security notes

- `secrets.toml` is gitignored — never commit it.
- Licence key validation calls the LS public API (no bearer token needed).
- All file processing is in-session; no data is written to disk beyond the generated
  report file, which is also session-scoped and cleaned up by Streamlit.
- Webhook signature verification (HMAC-SHA256) must be implemented before processing
  any LS webhook payloads in production.

---

## Contact

**Coltrane Ltd** · [support@coltradata.com](mailto:support@coltradata.com) · [coltradata.com](https://coltradata.com)

"""Enterprise API documentation page content for ColtraDataAi."""

from __future__ import annotations

import streamlit as st

_API_BASE = "https://coltradata-api.onrender.com"
_SWAGGER_URL = f"{_API_BASE}/docs"
_CHECKOUT_URL = "https://app.coltradata.com/Pricing"

_DOMAINS = [
    ("finance",      "Invoice, ledger and transaction data",   "UK MTD VAT (HMRC 700/22), IFRS/GAAP alignment"),
    ("logistics",    "Shipment and delivery records",          "GS1 identifiers, ISO 3166 country codes"),
    ("retail",       "Product catalogue and sales data",       "UPC/EAN validation, currency normalisation"),
    ("trade",        "Import/export and customs data",         "Incoterms 2020, HS codes, 15 African currencies"),
    ("healthcare",   "Clinical and patient records",           "NCT ID normalisation, ICD-10 code validation"),
    ("consultant",   "Project and time-billing data",          "Date/time standardisation, category normalisation"),
    ("sme",          "General SME operational data",           "Companies House format, UK address standardisation"),
    ("hospitality",  "Reservations, F&B and asset records",    "Date normalisation, currency and property code validation"),
]

_CURL_CSV = """\
curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \\
  -H "Authorization: Bearer cdai_YOUR_API_KEY" \\
  -F "file=@invoices.csv"\
"""

_CURL_JSON = """\
curl -X POST https://coltradata-api.onrender.com/v1/clean/finance \\
  -H "Authorization: Bearer cdai_YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '[{"Invoice_ID":"INV001","Amount":"1,250.00","Date":"01-Jan-2026","VAT_Code":"20%"}]'\
"""

_PYTHON = """\
import requests

API_KEY = "cdai_YOUR_API_KEY"
BASE_URL = "https://coltradata-api.onrender.com"

headers = {"Authorization": f"Bearer {API_KEY}"}

# Option 1 - CSV upload
with open("invoices.csv", "rb") as f:
    resp = requests.post(
        f"{BASE_URL}/v1/clean/finance",
        headers=headers,
        files={"file": f},
    )

# Option 2 - JSON body
records = [
    {"Invoice_ID": "INV001", "Amount": "1,250.00", "Date": "01-Jan-2026"},
    {"Invoice_ID": "INV002", "Amount": "875.50",   "Date": "2026/01/03"},
]
resp = requests.post(
    f"{BASE_URL}/v1/clean/finance",
    headers=headers,
    json=records,
)

result = resp.json()
print(f"Cleaned {result['rows_processed']} rows")
print(result["metrics"])
print(result["issues"])
\
"""

_RESPONSE_EXAMPLE = """\
{
  "domain": "finance",
  "rows_processed": 120,
  "cleaned_data": [
    {
      "Invoice_ID": "INV001",
      "Amount": 1250.00,
      "Date": "2026-01-01",
      "VAT_Code": "20"
    }
  ],
  "metrics": {
    "dates_standardised": 120,
    "amounts_normalised": 118,
    "vat_codes_cleaned": 112
  },
  "issues": [
    "2 rows had unparseable amounts and were left unchanged"
  ]
}\
"""


def render_api_docs_page(branding: dict) -> None:
    """Render the Enterprise API documentation page."""
    primary = branding["primary_colour"]
    accent  = branding.get("accent_colour", "#2E86AB")
    contact = branding.get("contact_email", "support@coltradata.com")

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="text-align:center;padding:48px 0 28px 0;">
            <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.14em;
                        text-transform:uppercase;color:{accent};margin-bottom:10px;">
                Enterprise REST API
            </div>
            <div style="font-size:2.2rem;font-weight:800;color:{primary};line-height:1.25;
                        max-width:660px;margin:0 auto;">
                Clean data without leaving your infrastructure
            </div>
            <div style="font-size:0.92rem;color:#657286;margin-top:14px;line-height:1.8;
                        max-width:560px;margin-left:auto;margin-right:auto;">
                The ColtraDataAi REST API slots directly into your existing data pipeline.
                Your source data flows from your system to our cleaner and straight back -
                it never touches a web interface, and nothing is stored on our side.
            </div>
            <div style="margin-top:22px;display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
                <a href="{_SWAGGER_URL}" target="_blank"
                   style="display:inline-block;padding:10px 24px;background:{primary};color:#fff;
                          border-radius:8px;font-size:0.84rem;font-weight:600;text-decoration:none;
                          letter-spacing:0.01em;">
                    Explore in Swagger →
                </a>
                <a href="{_CHECKOUT_URL}" target="_blank"
                   style="display:inline-block;padding:10px 24px;
                          border:2px solid {primary};color:{primary};background:#fff;
                          border-radius:8px;font-size:0.84rem;font-weight:600;text-decoration:none;
                          letter-spacing:0.01em;">
                    Get an API Key - £499/month →
                </a>
            </div>
        </div>
        <hr style="border:none;border-top:1px solid #E6ECF0;margin:0 0 2.5rem 0;" />
        """,
        unsafe_allow_html=True,
    )

    # ── Privacy & Data Residency ───────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#EAF4FB 0%,#EEF8EE 100%);
                    border:1.5px solid {accent};border-radius:14px;
                    padding:1.8rem 2rem 1.6rem 2rem;margin-bottom:2.5rem;">
            <div style="font-size:1.05rem;font-weight:800;color:{primary};margin-bottom:6px;">
                Built for enterprise data governance requirements
            </div>
            <div style="font-size:0.82rem;color:#4B5563;margin-bottom:1.2rem;line-height:1.7;">
                Hospitality property data, corporate financial records and clinical datasets are
                subject to strict internal governance policies. The API is designed so that
                sensitive data never has to leave your own environment.
            </div>
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1.2rem;">
                <div style="background:#fff;border-radius:10px;padding:1rem 1.1rem;
                            border:1px solid #D1E8D8;">
                    <div style="font-size:0.82rem;font-weight:700;color:{primary};margin-bottom:4px;">
                        Zero data retention
                    </div>
                    <div style="font-size:0.77rem;color:#4B5563;line-height:1.6;">
                        Source rows are processed in-transit and immediately discarded.
                        No field values are written to any database on our side.
                    </div>
                </div>
                <div style="background:#fff;border-radius:10px;padding:1rem 1.1rem;
                            border:1px solid #D1E8D8;">
                    <div style="font-size:0.82rem;font-weight:700;color:{primary};margin-bottom:4px;">
                        Your pipeline, your control
                    </div>
                    <div style="font-size:0.77rem;color:#4B5563;line-height:1.6;">
                        Call from your ERP, ETL job, or internal tooling. Data travels
                        database to cleaner to database - the web UI is never involved.
                    </div>
                </div>
                <div style="background:#fff;border-radius:10px;padding:1rem 1.1rem;
                            border:1px solid #D1E8D8;">
                    <div style="font-size:0.82rem;font-weight:700;color:{primary};margin-bottom:4px;">
                        Encrypted in transit
                    </div>
                    <div style="font-size:0.77rem;color:#4B5563;line-height:1.6;">
                        All requests use HTTPS/TLS. API keys are stored as SHA-256
                        hashes - never in plaintext, never visible to anyone.
                    </div>
                </div>
                <div style="background:#fff;border-radius:10px;padding:1rem 1.1rem;
                            border:1px solid #D1E8D8;">
                    <div style="font-size:0.82rem;font-weight:700;color:{primary};margin-bottom:4px;">
                        GDPR Article 28 aligned
                    </div>
                    <div style="font-size:0.77rem;color:#4B5563;line-height:1.6;">
                        Coltrane Ltd acts as data processor. Only anonymised usage
                        metadata (domain, row count, timestamp) is logged - never the data itself.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Quick start ────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{primary};'
        f'margin-bottom:0.8rem;">Quick start</div>',
        unsafe_allow_html=True,
    )

    col_base, col_auth = st.columns(2)
    with col_base:
        st.markdown(
            f"""
            <div style="background:#F8FAFC;border:1px solid #DCE6EE;border-radius:10px;
                        padding:1rem 1.2rem;">
                <div style="font-size:0.78rem;font-weight:700;color:{primary};
                            text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
                    Base URL
                </div>
                <code style="font-size:0.82rem;color:{accent};background:#EEF4F9;
                             padding:5px 9px;border-radius:5px;display:block;word-break:break-all;">
                    https://coltradata-api.onrender.com
                </code>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_auth:
        st.markdown(
            f"""
            <div style="background:#F8FAFC;border:1px solid #DCE6EE;border-radius:10px;
                        padding:1rem 1.2rem;">
                <div style="font-size:0.78rem;font-weight:700;color:{primary};
                            text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
                    Authentication header
                </div>
                <code style="font-size:0.82rem;color:{accent};background:#EEF4F9;
                             padding:5px 9px;border-radius:5px;display:block;word-break:break-all;">
                    Authorization: Bearer cdai_YOUR_API_KEY
                </code>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Endpoints table ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{primary};'
        f'margin-top:1.8rem;margin-bottom:0.8rem;">Endpoints</div>',
        unsafe_allow_html=True,
    )

    endpoints = [
        ("POST", "/v1/clean/{domain}", "Clean a dataset for the specified domain. See Domain Reference below."),
        ("GET",  "/v1/domains",        "Return the list of all supported domain names."),
        ("GET",  "/health",            "Liveness check. No authentication required."),
        ("GET",  "/health/detail",     "Full dependency check - Supabase circuit state, domain availability, env vars."),
    ]

    rows_html = ""
    for method, path, desc in endpoints:
        badge_bg = "#2E7D32" if method == "GET" else primary
        rows_html += f"""
        <tr>
            <td style="padding:9px 10px;vertical-align:middle;">
                <span style="background:{badge_bg};color:#fff;font-size:0.71rem;font-weight:700;
                             padding:2px 8px;border-radius:4px;font-family:monospace;
                             letter-spacing:0.03em;">{method}</span>
            </td>
            <td style="padding:9px 10px;vertical-align:middle;">
                <code style="font-size:0.8rem;color:{accent};">{path}</code>
            </td>
            <td style="padding:9px 10px;vertical-align:middle;font-size:0.8rem;color:#374151;">
                {desc}
            </td>
        </tr>
        """

    st.markdown(
        f"""
        <div style="overflow-x:auto;margin-bottom:2rem;">
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#F0F4F8;border-bottom:2px solid #DCE6EE;">
                        <th style="padding:9px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;width:72px;">
                            Method
                        </th>
                        <th style="padding:9px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;width:280px;">
                            Path
                        </th>
                        <th style="padding:9px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;">
                            Description
                        </th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Code examples ──────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{primary};'
        f'margin-bottom:0.8rem;">Code examples</div>',
        unsafe_allow_html=True,
    )

    tab_csv, tab_json, tab_py = st.tabs(["curl - CSV upload", "curl - JSON body", "Python (requests)"])
    with tab_csv:
        st.code(_CURL_CSV, language="bash")
        st.caption(
            "Send a CSV file as multipart/form-data using the `file` field. "
            "Replace `cdai_YOUR_API_KEY` with your actual key and choose the domain that matches your data."
        )
    with tab_json:
        st.code(_CURL_JSON, language="bash")
        st.caption(
            "Send records as a JSON array (or `{\"rows\": [...]}` wrapper). "
            "Useful for streaming rows directly out of a database query without writing a temp file."
        )
    with tab_py:
        st.code(_PYTHON, language="python")
        st.caption(
            "Both input formats work with the same endpoint. "
            "The `requests` library is the only dependency."
        )

    # ── Response format ────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{primary};'
        f'margin-top:1.8rem;margin-bottom:0.6rem;">Response format</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.82rem;color:#657286;margin-bottom:0.7rem;">'
        "All successful requests return HTTP 200 with the structure below.</div>",
        unsafe_allow_html=True,
    )

    st.code(_RESPONSE_EXAMPLE, language="json")

    field_rows = [
        ("domain",         "string",  "The cleaning domain that was applied."),
        ("rows_processed", "integer", "Number of rows returned after cleaning."),
        ("cleaned_data",   "array",   "Cleaned records as an array of JSON objects."),
        ("metrics",        "object",  "Per-operation counts - dates standardised, amounts normalised, etc."),
        ("issues",         "array",   "Human-readable list of data quality warnings or skipped rows."),
    ]
    field_rows_html = "".join(
        f'<tr style="background:{"#F8FAFC" if i % 2 else "#fff"};">'
        f'<td style="padding:8px 10px;"><code style="font-size:0.79rem;color:{accent};">{f}</code></td>'
        f'<td style="padding:8px 10px;font-size:0.78rem;color:#657286;">{t}</td>'
        f'<td style="padding:8px 10px;font-size:0.79rem;color:#374151;">{d}</td></tr>'
        for i, (f, t, d) in enumerate(field_rows)
    )
    st.markdown(
        f"""
        <div style="overflow-x:auto;margin:0.8rem 0 2rem 0;">
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#F0F4F8;border-bottom:2px solid #DCE6EE;">
                        <th style="padding:8px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;width:160px;">Field</th>
                        <th style="padding:8px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;width:80px;">Type</th>
                        <th style="padding:8px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;">Description</th>
                    </tr>
                </thead>
                <tbody>{field_rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Domain reference ───────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{primary};'
        f'margin-bottom:0.6rem;">Domain reference</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div style="font-size:0.82rem;color:#657286;margin-bottom:0.8rem;">'
        f'Use the domain name as the path parameter: '
        f'<code style="color:{accent};">POST /v1/clean/{{domain}}</code></div>',
        unsafe_allow_html=True,
    )

    domain_rows_html = "".join(
        f'<tr style="background:{"#F8FAFC" if i % 2 else "#fff"};">'
        f'<td style="padding:9px 10px;"><code style="font-size:0.8rem;color:{accent};font-weight:600;">'
        f'{dom}</code></td>'
        f'<td style="padding:9px 10px;font-size:0.8rem;color:#374151;">{data}</td>'
        f'<td style="padding:9px 10px;font-size:0.78rem;color:#657286;">{stds}</td></tr>'
        for i, (dom, data, stds) in enumerate(_DOMAINS)
    )
    st.markdown(
        f"""
        <div style="overflow-x:auto;margin-bottom:2rem;">
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#F0F4F8;border-bottom:2px solid #DCE6EE;">
                        <th style="padding:9px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;width:120px;">Domain</th>
                        <th style="padding:9px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;">Cleans</th>
                        <th style="padding:9px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;">Standards applied</th>
                    </tr>
                </thead>
                <tbody>{domain_rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Error codes ────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:1.15rem;font-weight:800;color:{primary};'
        f'margin-bottom:0.8rem;">Error codes</div>',
        unsafe_allow_html=True,
    )

    errors = [
        ("401", "Unauthorised",          "Missing or invalid API key in the Authorization header."),
        ("404", "Domain not found",      "The domain name in the path is not one of the supported values."),
        ("422", "Unprocessable entity",  "Malformed CSV, invalid JSON, empty body, or missing file field."),
        ("429", "Rate limited",          "Too many requests - back off and retry after the indicated delay."),
        ("500", "Internal server error", "An unexpected error occurred inside the cleaner. Contact support."),
    ]
    error_rows_html = "".join(
        f'<tr style="background:{"#F8FAFC" if i % 2 else "#fff"};">'
        f'<td style="padding:8px 10px;"><code style="font-size:0.8rem;color:#DC2626;font-weight:700;">'
        f'{code}</code></td>'
        f'<td style="padding:8px 10px;font-size:0.8rem;font-weight:600;color:#374151;">{label}</td>'
        f'<td style="padding:8px 10px;font-size:0.79rem;color:#657286;">{desc}</td></tr>'
        for i, (code, label, desc) in enumerate(errors)
    )
    st.markdown(
        f"""
        <div style="overflow-x:auto;margin-bottom:2.5rem;">
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#F0F4F8;border-bottom:2px solid #DCE6EE;">
                        <th style="padding:8px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;width:56px;">Code</th>
                        <th style="padding:8px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;width:200px;">Label</th>
                        <th style="padding:8px 10px;text-align:left;color:{primary};font-size:0.72rem;
                                   letter-spacing:0.07em;text-transform:uppercase;">Meaning</th>
                    </tr>
                </thead>
                <tbody>{error_rows_html}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── CTA ────────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,{primary} 0%,{accent} 100%);
                    border-radius:16px;padding:2.2rem 2.4rem;text-align:center;
                    margin-bottom:2rem;">
            <div style="font-size:1.3rem;font-weight:800;color:#fff;margin-bottom:8px;">
                Ready to integrate?
            </div>
            <div style="font-size:0.88rem;color:#D9E1F2;margin-bottom:1.4rem;line-height:1.75;">
                Enterprise API access is <strong style="color:#fff;">£499/month</strong>.
                Includes all 8 domain cleaners, unlimited calls,<br>
                a dedicated API key, Swagger access, and priority support.
            </div>
            <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
                <a href="{_CHECKOUT_URL}" target="_blank"
                   style="display:inline-block;padding:12px 30px;background:#fff;color:{primary};
                          border-radius:8px;font-size:0.9rem;font-weight:700;text-decoration:none;">
                    Get API Key - £499/month →
                </a>
                <a href="{_SWAGGER_URL}" target="_blank"
                   style="display:inline-block;padding:12px 30px;
                          border:2px solid rgba(255,255,255,0.65);color:#fff;
                          border-radius:8px;font-size:0.9rem;font-weight:600;text-decoration:none;">
                    Explore in Swagger →
                </a>
            </div>
            <div style="margin-top:1.1rem;font-size:0.76rem;color:rgba(217,225,242,0.8);">
                Questions about enterprise contracts or volume pricing - contact us at
                <a href="mailto:{contact}"
                   style="color:#fff;text-decoration:none;font-weight:600;">{contact}</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

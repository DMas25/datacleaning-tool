"""Zero-login interactive data-cleaning preview widget.

Conversion-focused: shows two pre-built messy datasets side-by-side with
their cleaned counterparts, a quality-score improvement card, and a CTA to
start a free account. No pipeline calls - pre-computed DataFrames only.

Usage:
    from ui.demo_widget import render_demo_widget
    render_demo_widget()
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config.branding_config import branding as BRAND

PRIMARY = BRAND["primary_colour"]
ACCENT  = BRAND.get("accent_colour", "#2E86AB")

# ── Session-state key ──────────────────────────────────────────────────────────
_STATE_KEY = "_demo_widget_ran"


# =============================================================================
# PRE-BUILT SAMPLE DATA
# =============================================================================

_ACCOUNTING_RAW = pd.DataFrame([
    {"invoice_date": "01/01/2024",   "vendor": "ACME SUPPLIES LTD", "account_code": "4000", "amount": "£1,250.00",  "vat_code": "T1",  "status": "Paid",    "invoice_ref": "INV-001"},
    {"invoice_date": "2024-01-15",   "vendor": "Acme Supplies Ltd",  "account_code": "4000", "amount": "1250.00",   "vat_code": "T1",  "status": "PAID",    "invoice_ref": "INV-001"},
    {"invoice_date": "Jan 20 2024",  "vendor": "beta services",      "account_code": "45",   "amount": "$850.50",   "vat_code": "T9",  "status": "paid",    "invoice_ref": "INV-002"},
    {"invoice_date": "22-01-2024",   "vendor": "Delta Corp",         "account_code": "4100", "amount": "£325.00",   "vat_code": "T1",  "status": "Unpaid",  "invoice_ref": "INV-003"},
    {"invoice_date": "01/01/2024",   "vendor": "ACME SUPPLIES LTD", "account_code": "4000", "amount": "£1,250.00",  "vat_code": "T1",  "status": "Paid",    "invoice_ref": "INV-001"},
    {"invoice_date": "2024-02-01",   "vendor": None,                  "account_code": "200",  "amount": "0.00",      "vat_code": "ZZ",  "status": "P",       "invoice_ref": "INV-004"},
    {"invoice_date": "31 Jan 2024",  "vendor": "Epsilon Ltd",        "account_code": "4200", "amount": "£2,100.00", "vat_code": "T1",  "status": "Unpaid",  "invoice_ref": "INV-005"},
    {"invoice_date": "05/02/2024",   "vendor": "GAMMA TECH",         "account_code": "3000", "amount": "£975,00",   "vat_code": "T1",  "status": "unpaid",  "invoice_ref": "INV-006"},
    {"invoice_date": "2024-02-10",   "vendor": "Zeta Corp",          "account_code": "4300", "amount": "£450.00",   "vat_code": "T1",  "status": "Paid",    "invoice_ref": "INV-007"},
    {"invoice_date": "15-02-2024",   "vendor": None,                  "account_code": "4400", "amount": "£88.50",    "vat_code": "T2",  "status": "Pending", "invoice_ref": "INV-008"},
])

_ACCOUNTING_CLEAN = pd.DataFrame([
    {"invoice_date": "2024-01-01", "vendor": "Acme Supplies Ltd",  "account_code": "4000", "amount": 1250.00, "vat_code": "T1",         "status": "Paid",    "invoice_ref": "INV-001"},
    {"invoice_date": "2024-01-20", "vendor": "Beta Services",      "account_code": "0045", "amount": 850.50,  "vat_code": "T9 [CHECK]", "status": "Paid",    "invoice_ref": "INV-002"},
    {"invoice_date": "2024-01-22", "vendor": "Delta Corp",         "account_code": "4100", "amount": 325.00,  "vat_code": "T1",         "status": "Unpaid",  "invoice_ref": "INV-003"},
    {"invoice_date": "2024-02-01", "vendor": "[MISSING]",           "account_code": "0200", "amount": 0.00,    "vat_code": "ZZ [CHECK]", "status": "Unknown", "invoice_ref": "INV-004"},
    {"invoice_date": "2024-01-31", "vendor": "Epsilon Ltd",        "account_code": "4200", "amount": 2100.00, "vat_code": "T1",         "status": "Unpaid",  "invoice_ref": "INV-005"},
    {"invoice_date": "2024-02-05", "vendor": "Gamma Tech",         "account_code": "3000", "amount": 975.00,  "vat_code": "T1",         "status": "Unpaid",  "invoice_ref": "INV-006"},
    {"invoice_date": "2024-02-10", "vendor": "Zeta Corp",          "account_code": "4300", "amount": 450.00,  "vat_code": "T1",         "status": "Paid",    "invoice_ref": "INV-007"},
    {"invoice_date": "2024-02-15", "vendor": "[MISSING]",           "account_code": "4400", "amount": 88.50,   "vat_code": "T2",         "status": "Pending", "invoice_ref": "INV-008"},
])

_LOGISTICS_RAW = pd.DataFrame([
    {"tracking_ref": "SHP-001", "origin": "United Kingdom",            "hs_code": "9401",    "declared_value_gbp": 15000.00,  "weight_kg": 125.5, "status": "In Transit"},
    {"tracking_ref": "SHP-002", "origin": "USA",                       "hs_code": "8471.30", "declared_value_gbp": 8500.00,   "weight_kg": 3.2,   "status": "delivered"},
    {"tracking_ref": "SHP-003", "origin": "Deutschland",               "hs_code": "8517",    "declared_value_gbp": 22000.00,  "weight_kg": 44.0,  "status": "in-transit"},
    {"tracking_ref": "SHP-004", "origin": "France",                    "hs_code": "090121",  "declared_value_gbp": 4500.00,   "weight_kg": 8.5,   "status": "Completed"},
    {"tracking_ref": "SHP-001", "origin": "United Kingdom",            "hs_code": "9401",    "declared_value_gbp": 15000.00,  "weight_kg": 125.5, "status": "In Transit"},
    {"tracking_ref": "SHP-005", "origin": "China",                     "hs_code": "2701",    "declared_value_gbp": -1200.00,  "weight_kg": 890.0, "status": "Pending"},
    {"tracking_ref": "SHP-006", "origin": "JPN",                       "hs_code": "030200",  "declared_value_gbp": 850000.00, "weight_kg": 12.3,  "status": "Cleared"},
    {"tracking_ref": "SHP-007", "origin": "UK",                        "hs_code": "852872",  "declared_value_gbp": 3200.00,   "weight_kg": 6.8,   "status": "IN TRANSIT"},
    {"tracking_ref": "SHP-008", "origin": "Peoples Republic of China", "hs_code": "300490",  "declared_value_gbp": 0.00,      "weight_kg": 22.1,  "status": "Cleared"},
    {"tracking_ref": "SHP-009", "origin": "United States of America",  "hs_code": "611020",  "declared_value_gbp": 3200.00,   "weight_kg": 5.5,   "status": "completed"},
    {"tracking_ref": "SHP-003", "origin": "Deutschland",               "hs_code": "8517",    "declared_value_gbp": 22000.00,  "weight_kg": 44.0,  "status": "in-transit"},
    {"tracking_ref": "SHP-010", "origin": "Brazil",                    "hs_code": "220421",  "declared_value_gbp": 25000.00,  "weight_kg": 88.0,  "status": "Pending"},
])

_LOGISTICS_CLEAN = pd.DataFrame([
    {"tracking_ref": "SHP-001", "origin": "GB", "hs_code": "940100", "declared_value_gbp": 15000.00,  "weight_kg": 125.5, "status": "In Transit"},
    {"tracking_ref": "SHP-002", "origin": "US", "hs_code": "847130", "declared_value_gbp": 8500.00,   "weight_kg": 3.2,   "status": "Delivered"},
    {"tracking_ref": "SHP-003", "origin": "DE", "hs_code": "851700", "declared_value_gbp": 22000.00,  "weight_kg": 44.0,  "status": "In Transit"},
    {"tracking_ref": "SHP-004", "origin": "FR", "hs_code": "090121", "declared_value_gbp": 4500.00,   "weight_kg": 8.5,   "status": "Completed"},
    {"tracking_ref": "SHP-005", "origin": "CN", "hs_code": "270100", "declared_value_gbp": -1200.00,  "weight_kg": 890.0, "status": "Pending [VALUE FLAGGED]"},
    {"tracking_ref": "SHP-006", "origin": "JP", "hs_code": "030200", "declared_value_gbp": 850000.00, "weight_kg": 12.3,  "status": "Cleared"},
    {"tracking_ref": "SHP-007", "origin": "GB", "hs_code": "852872", "declared_value_gbp": 3200.00,   "weight_kg": 6.8,   "status": "In Transit"},
    {"tracking_ref": "SHP-008", "origin": "CN", "hs_code": "300490", "declared_value_gbp": 0.00,      "weight_kg": 22.1,  "status": "Cleared [VALUE FLAGGED]"},
    {"tracking_ref": "SHP-009", "origin": "US", "hs_code": "611020", "declared_value_gbp": 3200.00,   "weight_kg": 5.5,   "status": "Completed"},
    {"tracking_ref": "SHP-010", "origin": "BR", "hs_code": "220421", "declared_value_gbp": 25000.00,  "weight_kg": 88.0,  "status": "Pending"},
])


# =============================================================================
# DATASET REGISTRY
# =============================================================================

_DATASETS: dict[str, dict] = {
    "Bookkeeping / Accounting Export (Mixed dates, currency symbols, broken rows)": {
        "key":          "accounting",
        "raw":          _ACCOUNTING_RAW,
        "clean":        _ACCOUNTING_CLEAN,
        "before_score": 43,
        "after_score":  91,
        "rows_removed": 2,
        "errors_fixed": [
            ("2 duplicate invoice entries removed",                    "#EF4444"),
            ("7 date formats standardised to ISO 8601 (YYYY-MM-DD)",  "#F59E0B"),
            ("6 currency symbols stripped (£, $, comma separators)",   "#F59E0B"),
            ("2 blank vendor names flagged for review",                "#F59E0B"),
            ("1 short account code zero-padded (45 → 0045)",          "#F59E0B"),
            ("2 invalid VAT codes flagged (T9, ZZ)",                   "#F59E0B"),
            ("1 ambiguous status normalised (P → Unknown)",            "#6B7280"),
        ],
    },
    "Customs / Logistics Export (Missing country codes, invalid HS codes, duplicate lines)": {
        "key":          "logistics",
        "raw":          _LOGISTICS_RAW,
        "clean":        _LOGISTICS_CLEAN,
        "before_score": 51,
        "after_score":  94,
        "rows_removed": 2,
        "errors_fixed": [
            ("2 duplicate shipment lines removed",                              "#EF4444"),
            ("6 country names mapped to ISO 3166-1 alpha-2 codes",             "#F59E0B"),
            ("4 short HS codes padded/corrected to 6-digit minimum",           "#F59E0B"),
            ("4 inconsistent status labels normalised (delivered, IN TRANSIT)", "#F59E0B"),
            ("2 invalid declared values flagged (negative and zero)",           "#F59E0B"),
        ],
    },
}


# =============================================================================
# CSS
# =============================================================================

def _inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .dw-header {{
            padding: 0.8rem 0 0.4rem 0;
        }}
        .dw-title {{
            font-size: 1.35rem;
            font-weight: 800;
            color: {PRIMARY};
            margin: 0 0 0.2rem 0;
            line-height: 1.2;
        }}
        .dw-sub {{
            font-size: 0.88rem;
            color: #4B5563;
            margin: 0 0 0.6rem 0;
        }}
        .dw-col-label {{
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 5px 12px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 0.5rem;
        }}
        .dw-col-label-raw {{
            background: #FEF3C7;
            color: #92400E;
        }}
        .dw-col-label-clean {{
            background: #D1FAE5;
            color: #065F46;
        }}
        .dw-score-bar-wrap {{
            background: #F3F4F6;
            border-radius: 999px;
            height: 10px;
            width: 100%;
            margin: 6px 0 2px 0;
            overflow: hidden;
        }}
        .dw-score-bar {{
            height: 10px;
            border-radius: 999px;
            transition: width 0.6s ease;
        }}
        .dw-score-card {{
            background: linear-gradient(135deg, {PRIMARY}0A 0%, {ACCENT}14 100%);
            border: 1.5px solid {PRIMARY}30;
            border-radius: 14px;
            padding: 1.2rem 1.4rem;
            margin-top: 1rem;
        }}
        .dw-score-title {{
            font-size: 0.85rem;
            font-weight: 700;
            color: {PRIMARY};
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-bottom: 0.6rem;
        }}
        .dw-score-numbers {{
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 0.4rem;
        }}
        .dw-score-val {{
            font-size: 2rem;
            font-weight: 900;
            line-height: 1;
        }}
        .dw-score-before {{ color: #EF4444; }}
        .dw-score-after  {{ color: #10B981; }}
        .dw-score-arrow  {{ font-size: 1.1rem; color: #9CA3AF; }}
        .dw-score-label  {{ font-size: 0.72rem; color: #6B7280; margin-top: 2px; }}
        .dw-error-line {{
            display: flex;
            align-items: flex-start;
            gap: 0.5rem;
            padding: 3px 0;
            font-size: 0.82rem;
            color: #374151;
        }}
        .dw-error-dot {{
            width: 7px;
            height: 7px;
            border-radius: 50%;
            flex-shrink: 0;
            margin-top: 5px;
        }}
        .dw-cta-box {{
            background: linear-gradient(135deg, {PRIMARY}0D 0%, {ACCENT}18 100%);
            border: 2px solid {PRIMARY}40;
            border-radius: 16px;
            padding: 1.4rem 1.6rem;
            text-align: center;
            margin-top: 1.4rem;
        }}
        .dw-cta-title {{
            font-size: 1.1rem;
            font-weight: 800;
            color: {PRIMARY};
            margin-bottom: 0.2rem;
        }}
        .dw-cta-sub {{
            font-size: 0.88rem;
            color: #4B5563;
            margin-bottom: 0.9rem;
        }}
        .dw-trust-strip {{
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 0.6rem;
        }}
        .dw-trust-item {{
            font-size: 0.72rem;
            color: #6B7280;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# HELPERS
# =============================================================================

def _score_bar(score: int, colour: str) -> str:
    return (
        f'<div class="dw-score-bar-wrap">'
        f'<div class="dw-score-bar" style="width:{score}%;background:{colour};"></div>'
        f'</div>'
    )


def _render_score_card(cfg: dict) -> None:
    before = cfg["before_score"]
    after  = cfg["after_score"]
    errors = cfg["errors_fixed"]
    removed = cfg["rows_removed"]

    # Build error lines HTML
    error_lines = "".join(
        f'<div class="dw-error-line">'
        f'<span class="dw-error-dot" style="background:{colour};"></span>'
        f'{text}'
        f'</div>'
        for text, colour in errors
    )

    st.markdown(
        f"""
        <div class="dw-score-card">
          <div class="dw-score-title">Data Quality Score</div>
          <div class="dw-score-numbers">
            <div>
              <div class="dw-score-val dw-score-before">{before}<span style="font-size:1rem;font-weight:500;">/100</span></div>
              <div class="dw-score-label">Before</div>
              {_score_bar(before, "#FCA5A5")}
            </div>
            <div class="dw-score-arrow">&#8594;</div>
            <div>
              <div class="dw-score-val dw-score-after">{after}<span style="font-size:1rem;font-weight:500;">/100</span></div>
              <div class="dw-score-label">After</div>
              {_score_bar(after, "#34D399")}
            </div>
            <div style="margin-left:auto;text-align:right;">
              <div style="font-size:1.5rem;font-weight:900;color:{PRIMARY};">+{after - before}</div>
              <div class="dw-score-label">pts improvement</div>
            </div>
          </div>
          <div style="margin-top:0.75rem;border-top:1px solid {PRIMARY}20;padding-top:0.6rem;">
            <div style="font-size:0.78rem;font-weight:700;color:#374151;margin-bottom:0.35rem;">
              Errors corrected &amp; flagged
            </div>
            {error_lines}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_checkout_url() -> str:
    """Return the Starter checkout URL with affiliate ref appended if present."""
    try:
        from services.billing import checkout_url
        return checkout_url("starter")
    except Exception:
        return "https://app.coltradata.com"


def _render_cta() -> None:
    starter_url = _get_checkout_url()
    app_url     = "https://app.coltradata.com"

    # Append affiliate ref to app URL manually (billing.checkout_url handles LS URLs;
    # the app URL needs the same treatment for any tracking pixel on the landing page).
    try:
        from services.billing import append_affiliate
        app_url = append_affiliate(app_url)
    except Exception:
        pass

    st.markdown(
        f"""
        <div class="dw-cta-box">
          <div class="dw-cta-title">Want to clean your own client files?</div>
          <div class="dw-cta-sub">
            Clean up to 5,000 rows free today - no credit card required.
            Upload your own file and get the same results in seconds.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.link_button(
            "Start Free Account",
            app_url,
            use_container_width=True,
            type="primary",
        )
    with btn_col2:
        if starter_url:
            st.link_button(
                "Get Starter - £29/month",
                starter_url,
                use_container_width=True,
            )
        else:
            st.link_button(
                "View Pricing",
                "https://coltradata.com/pricing",
                use_container_width=True,
            )

    st.markdown(
        """
        <div class="dw-trust-strip">
          <span class="dw-trust-item">No card required</span>
          <span class="dw-trust-item">&#183;</span>
          <span class="dw-trust-item">GDPR compliant</span>
          <span class="dw-trust-item">&#183;</span>
          <span class="dw-trust-item">Cancel anytime</span>
          <span class="dw-trust-item">&#183;</span>
          <span class="dw-trust-item">UK-based processing</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# PUBLIC ENTRY POINT
# =============================================================================

def render_demo_widget() -> None:
    """Render the zero-login interactive data-cleaning preview widget.

    Designed to be embedded in app.py inside an expander or tab:

        with st.expander("Interactive Demo - No Signup Required", expanded=False):
            render_demo_widget()
    """
    _inject_css()

    # ── Header -----------------------------------------------------------------
    st.markdown(
        f"""
        <div class="dw-header">
          <div class="dw-title">Interactive Data Health &amp; Cleaning Preview</div>
          <div class="dw-sub">
            Select a sample dataset, run the instant auto-clean, and see exactly
            what ColtraDataAi catches - no account needed.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Dataset selector -------------------------------------------------------
    dataset_label = st.selectbox(
        "Choose a sample dataset:",
        list(_DATASETS.keys()),
        key="_demo_widget_dataset",
        label_visibility="visible",
    )
    cfg = _DATASETS[dataset_label]

    # Reset run state when the user switches datasets
    run_key = f"{_STATE_KEY}_{cfg['key']}"
    if st.session_state.get("_demo_widget_last_key") != cfg["key"]:
        st.session_state["_demo_widget_last_key"] = cfg["key"]

    # ── Run button -------------------------------------------------------------
    col_run, col_reset = st.columns([3, 1])
    with col_run:
        run_clicked = st.button(
            "Run Instant Auto-Clean",
            key=f"_demo_widget_run_{cfg['key']}",
            type="primary",
            use_container_width=True,
        )
    with col_reset:
        if st.button(
            "Reset",
            key=f"_demo_widget_reset_{cfg['key']}",
            use_container_width=True,
        ):
            st.session_state.pop(run_key, None)
            st.rerun()

    if run_clicked:
        st.session_state[run_key] = True

    already_ran = st.session_state.get(run_key, False)

    # Show the raw data preview before the button is pressed
    if not already_ran:
        st.markdown(
            '<span class="dw-col-label dw-col-label-raw">Raw Input Data</span>',
            unsafe_allow_html=True,
        )
        st.dataframe(cfg["raw"], use_container_width=True, height=280)
        return

    # ── Side-by-side comparison ------------------------------------------------
    left, right = st.columns(2)

    with left:
        st.markdown(
            '<span class="dw-col-label dw-col-label-raw">Raw Input Data</span>',
            unsafe_allow_html=True,
        )
        st.dataframe(cfg["raw"], use_container_width=True, height=320)
        st.caption(
            f"{len(cfg['raw'])} rows | "
            f"{int(cfg['raw'].isnull().sum().sum())} empty cells | "
            f"{int(cfg['raw'].duplicated().sum())} duplicate rows"
        )

    with right:
        st.markdown(
            '<span class="dw-col-label dw-col-label-clean">Cleaned Output Data</span>',
            unsafe_allow_html=True,
        )
        st.dataframe(cfg["clean"], use_container_width=True, height=320)
        st.caption(
            f"{len(cfg['clean'])} rows | "
            f"{cfg['rows_removed']} duplicate(s) removed | "
            f"formats standardised"
        )

    # ── Quality score card -----------------------------------------------------
    _render_score_card(cfg)

    # ── Conversion CTA ---------------------------------------------------------
    _render_cta()

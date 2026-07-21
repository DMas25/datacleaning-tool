"""Free Data Health Check — UI panel.

Self-contained Streamlit panel that walks a first-time visitor through:
  1. Email collection (gate, one free check per address)
  2. File upload (CSV / XLSX, ≤5 000 rows, ≤10 MB)
  3. Automated analysis
  4. Limited report display
  5. Paywall / conversion section (upgrade CTAs)

No subscription or password required. The panel manages its own session
state under keys prefixed with 'hc_'.
"""
from __future__ import annotations

import io
import re
from typing import Optional

import pandas as pd
import streamlit as st

from config.branding_config import branding as BRAND
from config.lemonsqueezy_config import CHECKOUT_URLS
from core.file_loader import load_file
from core.health_check_engine import (
    _MAX_FREE_MB,
    _MAX_FREE_ROWS,
    run_health_check,
    validate_row_count,
    validate_upload,
)
from services.health_check_store import (
    has_used_free_check,
    is_rate_limited,
    log_event,
    record_cta_click,
    record_health_check,
)

PRIMARY   = BRAND["primary_colour"]
ACCENT    = BRAND.get("accent_colour", "#2E86AB")
SUCCESS   = BRAND.get("success_colour", "#46D324")
WARNING   = BRAND.get("warning_colour", "#F59E0B")
DANGER    = BRAND.get("danger_colour", "#DC2626")


# ── CSS ───────────────────────────────────────────────────────────────────────

def _inject_css() -> None:
    st.markdown(
        f"""
        <style>
        /* ── Page & layout ───────────────────────────── */
        .block-container {{ padding-top: 1.2rem; padding-bottom: 2rem; }}

        /* ── Card containers ─────────────────────────── */
        .hc-card {{
            background: #FFFFFF;
            border-radius: 14px;
            border: 1px solid #E6ECF0;
            border-left: 4px solid {PRIMARY};
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            padding: 1.3rem 1.5rem;
            margin-bottom: 1rem;
        }}
        .hc-card-plain {{
            background: #FFFFFF;
            border-radius: 14px;
            border: 1px solid #E6ECF0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            padding: 1.3rem 1.5rem;
            margin-bottom: 1rem;
        }}

        /* ── Score ring ──────────────────────────────── */
        .score-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            width: 130px;
            height: 130px;
            border-radius: 50%;
            font-weight: 800;
            box-shadow: 0 4px 16px rgba(0,0,0,0.12);
            margin: 0 auto;
        }}
        .score-number {{
            font-size: 2.6rem;
            line-height: 1;
        }}
        .score-label {{
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 3px;
            opacity: 0.85;
        }}

        /* ── KPI metric card ─────────────────────────── */
        .hc-kpi {{
            background: white;
            border-radius: 12px;
            border: 1px solid #E6ECF0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            padding: 0.9rem 1rem;
            text-align: center;
        }}
        .hc-kpi-value {{
            font-size: 1.55rem;
            font-weight: 800;
            color: {PRIMARY};
            line-height: 1.15;
            display: block;
        }}
        .hc-kpi-label {{
            font-size: 0.7rem;
            color: #657286;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            margin-top: 4px;
            display: block;
        }}

        /* ── Section divider ─────────────────────────── */
        .hc-divider {{
            display: flex; align-items: center; gap: 12px;
            margin: 1.4rem 0 0.8rem 0;
        }}
        .hc-divider-line {{
            height: 1px; flex: 1;
            background: #E6ECF0; display: inline-block;
        }}
        .hc-divider-label {{
            font-size: 0.72rem; font-weight: 700;
            color: {PRIMARY}; text-transform: uppercase;
            letter-spacing: 0.11em;
        }}

        /* ── Observation pill ────────────────────────── */
        .obs-pill {{
            background: #F0F7FF;
            border-left: 3px solid {ACCENT};
            border-radius: 0 8px 8px 0;
            padding: 0.65rem 1rem;
            margin-bottom: 0.5rem;
            font-size: 0.9rem;
            color: #1A2F45;
            line-height: 1.5;
        }}

        /* ── Issue table row ─────────────────────────── */
        .issue-row {{
            display: flex; align-items: flex-start; gap: 0.7rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid #F3F4F6;
            font-size: 0.875rem;
        }}
        .issue-tag {{
            display: inline-block;
            background: #FEF3C7;
            color: #92400E;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.75rem;
            font-weight: 600;
            white-space: nowrap;
            flex-shrink: 0;
        }}

        /* ── Score breakdown bar ─────────────────────── */
        .sb-row {{
            display: flex; align-items: center; gap: 0.75rem;
            margin-bottom: 0.45rem;
        }}
        .sb-label {{
            font-size: 0.8rem; color: #374151;
            width: 110px; flex-shrink: 0;
        }}
        .sb-bar-wrap {{
            flex: 1; background: #F3F4F6;
            border-radius: 4px; height: 8px; overflow: hidden;
        }}
        .sb-bar-fill {{
            height: 8px; border-radius: 4px;
            transition: width 0.6s ease;
        }}
        .sb-pts {{
            font-size: 0.78rem; font-weight: 700;
            color: {PRIMARY}; width: 50px; text-align: right;
            flex-shrink: 0;
        }}

        /* ── Paywall / upgrade section ───────────────── */
        .paywall-box {{
            background: linear-gradient(135deg, {PRIMARY}08 0%, {ACCENT}10 100%);
            border: 2px solid {PRIMARY}30;
            border-radius: 16px;
            padding: 1.8rem 2rem;
            text-align: center;
            margin-top: 1.5rem;
        }}
        .paywall-title {{
            font-size: 1.4rem; font-weight: 800;
            color: {PRIMARY}; margin-bottom: 0.3rem;
        }}
        .paywall-sub {{
            color: #4B5563; font-size: 0.95rem;
            margin-bottom: 1.2rem;
        }}
        .feature-pill {{
            display: inline-flex; align-items: center; gap: 6px;
            background: white;
            border: 1px solid #E6ECF0;
            border-radius: 20px;
            padding: 6px 14px;
            margin: 4px;
            font-size: 0.82rem;
            color: #374151;
            font-weight: 500;
        }}
        .feature-pill-check {{
            color: {SUCCESS}; font-weight: 700;
        }}

        /* ── Primary CTA button override ─────────────── */
        .stButton > button {{
            border-radius: 10px !important;
            height: 46px !important;
            font-weight: 700 !important;
            border: none !important;
            transition: opacity 0.15s ease !important;
        }}
        .stButton > button:hover {{ opacity: 0.88 !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _divider(label: str = "") -> None:
    if label:
        st.markdown(
            f'<div class="hc-divider">'
            f'<span class="hc-divider-line"></span>'
            f'<span class="hc-divider-label">{label}</span>'
            f'<span class="hc-divider-line"></span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<hr style="border:none;border-top:1px solid #E6ECF0;margin:1rem 0;" />', unsafe_allow_html=True)


def _kpi(label: str, value: str) -> None:
    st.markdown(
        f'<div class="hc-kpi">'
        f'<span class="hc-kpi-value">{value}</span>'
        f'<span class="hc-kpi-label">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _score_colour(score: int) -> tuple[str, str]:
    """Return (bg_colour, text_colour) for the score badge."""
    if score >= 80:
        return "#ECFDF5", "#065F46"
    if score >= 60:
        return "#FFFBEB", "#92400E"
    return "#FEF2F2", "#991B1B"


def _score_label(score: int) -> str:
    if score >= 80:
        return "Good"
    if score >= 60:
        return "Fair"
    if score >= 40:
        return "Poor"
    return "Critical"


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email.strip()))


def _checkout_url(plan: str) -> str:
    return CHECKOUT_URLS.get(plan, "")


# ── Step 1: Email gate ────────────────────────────────────────────────────────

def _render_email_gate() -> None:
    st.markdown(
        f"""
        <div style="text-align:center;padding:1.5rem 0 1rem 0;">
            <div style="font-size:2rem;font-weight:900;color:{PRIMARY};letter-spacing:-0.5px;
                        line-height:1.2;margin-bottom:0.4rem;">
                Free Data Health Check
            </div>
            <div style="font-size:1.05rem;color:#4B5563;max-width:540px;margin:0 auto;">
                Upload a sample file and get an instant quality report —
                no subscription needed.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Feature highlight row
    cols = st.columns(4)
    highlights = [
        ("Quality Score", "0–100 rating"),
        ("Missing Values", "per column"),
        ("Duplicates", "detected"),
        ("AI Observations", "top 3 insights"),
    ]
    for col, (title, sub) in zip(cols, highlights):
        with col:
            st.markdown(
                f'<div style="text-align:center;padding:0.7rem 0.5rem;background:#F8FAFC;'
                f'border-radius:12px;border:1px solid #E6ECF0;">'
                f'<div style="font-weight:700;color:{PRIMARY};font-size:0.85rem;">{title}</div>'
                f'<div style="color:#6B7280;font-size:0.75rem;margin-top:2px;">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

    with st.form("hc_email_form", clear_on_submit=False):
        email = st.text_input(
            "Your work email address",
            placeholder="you@company.com",
            help="We'll send you a copy of your report. One free analysis per address.",
        )
        consent = st.checkbox(
            "I agree to ColtraDataAi's Privacy Policy and Terms of Use. "
            "Coltrane Ltd may contact me about related services.",
        )
        submitted = st.form_submit_button("Get My Free Health Check", use_container_width=True)

        if submitted:
            email = email.strip()
            if not email or not _validate_email(email):
                st.error("Please enter a valid email address.")
                return
            if not consent:
                st.error("Please accept the terms to continue.")
                return

            # Check rate limiting (session-based fallback when no DB)
            ip = st.context.headers.get("X-Forwarded-For", "").split(",")[0].strip() if hasattr(st, "context") else ""
            if is_rate_limited(ip):
                st.warning(
                    "Too many uploads from this connection. Please try again in an hour.",
                    icon="⚠️",
                )
                log_event("", "rate_limited", {"ip_address": ip})
                return

            # Warn but still allow if they've checked before (they may want to refresh)
            if has_used_free_check(email):
                st.info(
                    "We've already run a free health check for this address. "
                    "Your previous results have been replaced with the new analysis.",
                    icon="ℹ️",
                )

            st.session_state["hc_email"]  = email
            st.session_state["hc_state"]  = "upload"
            st.session_state["hc_ip"]     = ip
            log_event(email, "email_captured")
            st.rerun()

    st.markdown(
        f'<div style="text-align:center;margin-top:0.8rem;font-size:0.78rem;color:#9CA3AF;">'
        f'Coltrane Ltd · {BRAND["legal_line"]}</div>',
        unsafe_allow_html=True,
    )


# ── Step 2: File upload ───────────────────────────────────────────────────────

def _render_upload() -> None:
    email = st.session_state.get("hc_email", "")

    st.markdown(
        f'<div style="color:#6B7280;font-size:0.88rem;margin-bottom:0.5rem;">'
        f'Running health check for <strong>{email}</strong></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="hc-card">'
        f'<div style="font-size:1.05rem;font-weight:700;color:{PRIMARY};margin-bottom:0.4rem;">'
        f'Upload your data file</div>'
        f'<div style="color:#6B7280;font-size:0.88rem;">'
        f'Supported: CSV, XLSX · Max {_MAX_FREE_ROWS:,} rows · Max {_MAX_FREE_MB:.0f} MB · '
        f'File is deleted immediately after analysis.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx"],
        label_visibility="collapsed",
        key="hc_file_uploader",
    )

    if uploaded is not None:
        file_bytes   = uploaded.getvalue()
        file_size_mb = len(file_bytes) / 1_048_576

        # Basic security: validate extension and size before parsing
        ok, err_msg = validate_upload(file_bytes, uploaded.name, file_size_mb)
        if not ok:
            st.error(err_msg)
            log_event(email, "upload_error", {"error": err_msg, "file": uploaded.name})
            return

        log_event(email, "upload_started", {
            "ip_address": st.session_state.get("hc_ip", ""),
            "file_name": uploaded.name,
            "size_mb": round(file_size_mb, 2),
        })

        with st.spinner("Analysing your data..."):
            try:
                df = load_file(uploaded)
            except Exception as exc:
                st.error(f"Could not read the file: {exc}")
                log_event(email, "upload_error", {"error": str(exc)})
                return

        _, truncation_msg, df = validate_row_count(df)

        if truncation_msg:
            st.info(truncation_msg, icon="ℹ️")

        with st.spinner("Running health check..."):
            report = run_health_check(df, uploaded.name, file_size_mb, BRAND)

        # Persist metadata (strip non-serialisable chart objects)
        check_id = record_health_check(
            email=email,
            file_name=uploaded.name,
            file_size_bytes=len(file_bytes),
            row_count=report["rows"],
            column_count=report["columns"],
            quality_score=report["quality_score"],
            result_summary={k: v for k, v in report.items() if not k.startswith("_")},
            ip_address=st.session_state.get("hc_ip", ""),
        )
        log_event(email, "upload_completed", {
            "rows": report["rows"],
            "columns": report["columns"],
            "quality_score": report["quality_score"],
        })

        # Store in session — charts are Plotly objects, safe for session state
        st.session_state["hc_report"]   = report
        st.session_state["hc_check_id"] = check_id
        st.session_state["hc_state"]    = "report"

        # Immediately clear the raw bytes from memory (file never touches disk)
        del file_bytes
        del df
        st.rerun()


# ── Step 3: Report ────────────────────────────────────────────────────────────

def _render_score_banner(report: dict) -> None:
    score  = report["quality_score"]
    bg, fg = _score_colour(score)
    label  = _score_label(score)

    col_badge, col_breakdown = st.columns([1, 2])

    with col_badge:
        st.markdown(
            f'<div style="display:flex;justify-content:center;padding:1rem 0;">'
            f'<div class="score-badge" style="background:{bg};color:{fg};">'
            f'<span class="score-number">{score}</span>'
            f'<span class="score-label">{label}</span>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        charts = report.get("_charts", {})
        if charts.get("gauge"):
            st.plotly_chart(charts["gauge"], use_container_width=True, config={"displayModeBar": False})

    with col_breakdown:
        st.markdown(
            f'<div style="font-size:0.9rem;font-weight:700;color:{PRIMARY};margin-bottom:0.7rem;">'
            f'Score breakdown</div>',
            unsafe_allow_html=True,
        )
        bd = report["score_breakdown"]
        bar_colours = {
            "completeness": "#2E86AB",
            "uniqueness":   "#48C9B0",
            "consistency":  "#46D324",
            "structure":    "#F59E0B",
        }
        for key, cfg in bd.items():
            pct       = int((cfg["score"] / max(cfg["max"], 1)) * 100)
            bar_color = bar_colours.get(key, PRIMARY)
            st.markdown(
                f'<div class="sb-row">'
                f'  <span class="sb-label">{key.capitalize()}</span>'
                f'  <div class="sb-bar-wrap">'
                f'    <div class="sb-bar-fill" style="width:{pct}%;background:{bar_color};"></div>'
                f'  </div>'
                f'  <span class="sb-pts">{cfg["score"]}/{cfg["max"]}</span>'
                f'</div>'
                f'<div style="font-size:0.72rem;color:#6B7280;margin:-0.3rem 0 0.5rem 0;'
                f'padding-left:115px;">{cfg["label"]}</div>',
                unsafe_allow_html=True,
            )


def _render_kpi_row(report: dict) -> None:
    dup_pct = round((report["duplicate_total"] / max(report["rows"], 1)) * 100, 1)
    cols = st.columns(4)
    metrics = [
        ("Rows", f"{report['rows']:,}"),
        ("Columns", str(report["columns"])),
        ("Completeness", f"{report['completeness_pct']:.1f}%"),
        ("Duplicates", f"{report['duplicate_total']:,} ({dup_pct}%)"),
    ]
    for col, (lbl, val) in zip(cols, metrics):
        with col:
            _kpi(lbl, val)


def _render_missing_values(report: dict) -> None:
    missing = {k: v for k, v in report["missing_by_col"].items() if v > 0}
    if not missing:
        st.success("No missing values detected across any column.", icon="✅")
        return

    charts = report.get("_charts", {})
    total_rows = max(report["rows"], 1)

    col_chart, col_table = st.columns([1, 1])
    with col_chart:
        if charts.get("missing_values"):
            st.plotly_chart(
                charts["missing_values"],
                use_container_width=True,
                config={"displayModeBar": False},
            )
    with col_table:
        rows_sorted = sorted(missing.items(), key=lambda x: x[1], reverse=True)[:12]
        table_rows = "".join(
            f'<tr style="border-bottom:1px solid #F3F4F6;">'
            f'<td style="padding:5px 8px;font-size:0.82rem;color:#374151;max-width:160px;'
            f'overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{col}</td>'
            f'<td style="padding:5px 8px;font-size:0.82rem;text-align:right;">{cnt:,}</td>'
            f'<td style="padding:5px 8px;font-size:0.82rem;text-align:right;color:#DC2626;">'
            f'{round(cnt/total_rows*100,1)}%</td>'
            f'</tr>'
            for col, cnt in rows_sorted
        )
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;">'
            f'<thead><tr style="background:#F9FAFB;">'
            f'<th style="padding:5px 8px;text-align:left;font-size:0.75rem;color:#6B7280;'
            f'text-transform:uppercase;letter-spacing:0.06em;">Column</th>'
            f'<th style="padding:5px 8px;text-align:right;font-size:0.75rem;color:#6B7280;'
            f'text-transform:uppercase;letter-spacing:0.06em;">Missing</th>'
            f'<th style="padding:5px 8px;text-align:right;font-size:0.75rem;color:#6B7280;'
            f'text-transform:uppercase;letter-spacing:0.06em;">Rate</th>'
            f'</tr></thead><tbody>{table_rows}</tbody></table>',
            unsafe_allow_html=True,
        )


def _render_duplicates(report: dict) -> None:
    dup   = report["duplicate_total"]
    rows  = max(report["rows"], 1)
    pct   = round((dup / rows) * 100, 1)

    if dup == 0:
        st.success("No duplicate records detected.", icon="✅")
    else:
        colour = DANGER if pct >= 10 else WARNING
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:1rem;padding:0.9rem 1rem;'
            f'background:#FFFBEB;border-radius:10px;border:1px solid #FDE68A;">'
            f'<span style="font-size:1.6rem;font-weight:900;color:{colour};">{dup:,}</span>'
            f'<div>'
            f'<div style="font-weight:700;color:#92400E;font-size:0.95rem;">'
            f'duplicate row(s) — {pct}% of records</div>'
            f'<div style="color:#78350F;font-size:0.82rem;margin-top:2px;">'
            f'Removing duplicates improves the accuracy of totals, averages, and reports.'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )


def _render_formatting_issues(report: dict) -> None:
    issues = report.get("formatting_issues", [])
    if not issues:
        st.success("No formatting inconsistencies found.", icon="✅")
        return

    for issue in issues[:8]:
        st.markdown(
            f'<div class="issue-row">'
            f'<span class="issue-tag">{issue["issue"]}</span>'
            f'<span style="color:#374151;font-size:0.875rem;">'
            f'<strong>{issue["column"]}</strong> — {issue["detail"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    if len(issues) > 8:
        st.caption(f"+{len(issues) - 8} more issues found. Upgrade to see the full list.")


def _render_column_types(report: dict) -> None:
    charts = report.get("_charts", {})
    col_chart, col_legend = st.columns([1, 1])
    with col_chart:
        if charts.get("column_types"):
            st.plotly_chart(
                charts["column_types"],
                use_container_width=True,
                config={"displayModeBar": False},
            )
    with col_legend:
        st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
        dtypes = report.get("dtypes", {})
        for col, dtype in list(dtypes.items())[:8]:
            st.markdown(
                f'<div style="font-size:0.8rem;padding:3px 0;border-bottom:1px solid #F3F4F6;">'
                f'<span style="color:#374151;font-weight:500;">{col}</span> '
                f'<span style="color:#9CA3AF;">({dtype})</span></div>',
                unsafe_allow_html=True,
            )
        if len(dtypes) > 8:
            st.caption(f"+{len(dtypes) - 8} more columns…")


def _render_observations(report: dict) -> None:
    for i, obs in enumerate(report.get("observations", []), 1):
        st.markdown(
            f'<div class="obs-pill">'
            f'<strong style="color:{PRIMARY};">#{i}</strong>&nbsp; {obs}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_paywall(report: dict, email: str, check_id: Optional[int]) -> None:
    st.markdown(
        f'<div class="paywall-box">'
        f'<div class="paywall-title">Unlock the full report</div>'
        f'<div class="paywall-sub">'
        f'Your free health check reveals the surface-level issues. '
        f'Upgrade to get the complete picture and one-click fixes.'
        f'</div>'
        f'<div style="margin-bottom:1.3rem;">'
        + "".join(
            f'<span class="feature-pill">'
            f'<span class="feature-pill-check">✓</span>{feat}'
            f'</span>'
            for feat in [
                "Complete cleaned dataset",
                "Executive PDF report",
                "AI recommendations",
                "Interactive dashboard",
                "Excel exports",
                "Full column-level fixes",
                "Branded outputs",
                "2,000 runs/month",
            ]
        )
        + f'</div></div>',
        unsafe_allow_html=True,
    )

    col_trial, col_pro, col_spacer = st.columns([1, 1, 0.5])

    starter_url = _checkout_url("Starter")
    pro_url     = _checkout_url("Professional")

    with col_trial:
        if starter_url:
            if st.button(
                "Start Free Trial — £9/month",
                use_container_width=True,
                type="primary",
                key="hc_cta_trial",
            ):
                record_cta_click(check_id, "starter_trial", email)
                log_event(email, "cta_clicked", {"cta": "starter_trial"})
                st.markdown(
                    f'<meta http-equiv="refresh" content="0;url={starter_url}">',
                    unsafe_allow_html=True,
                )
        else:
            st.info("Starter plan checkout coming soon.", icon="ℹ️")

    with col_pro:
        if pro_url:
            if st.button(
                "Upgrade to Professional — £29/month",
                use_container_width=True,
                key="hc_cta_pro",
            ):
                record_cta_click(check_id, "professional", email)
                log_event(email, "cta_clicked", {"cta": "professional"})
                st.markdown(
                    f'<meta http-equiv="refresh" content="0;url={pro_url}">',
                    unsafe_allow_html=True,
                )
        else:
            st.info("Professional plan checkout coming soon.", icon="ℹ️")

    # What's included comparison table
    _divider("What's included")

    comparison = [
        ("Data Quality Score",         True,  True),
        ("Missing Values Summary",     True,  True),
        ("Duplicate Detection",        True,  True),
        ("Formatting Issues",          True,  True),
        ("3 AI Observations",          True,  True),
        ("Full AI Advisory Report",    False, True),
        ("Cleaned Dataset Download",   False, True),
        ("Excel Export",               False, True),
        ("Executive PDF Report",       False, True),
        ("Interactive Dashboard",      False, True),
        ("Branded Outputs",            False, True),
        ("2,000 Runs/Month",           False, True),
    ]

    tick = f'<span style="color:{SUCCESS};font-weight:700;">✓</span>'
    cross = '<span style="color:#D1D5DB;">—</span>'

    header = (
        f'<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
        f'<thead><tr style="background:#F9FAFB;">'
        f'<th style="padding:8px 12px;text-align:left;color:#6B7280;font-size:0.75rem;'
        f'text-transform:uppercase;letter-spacing:0.06em;">Feature</th>'
        f'<th style="padding:8px 12px;text-align:center;color:#6B7280;font-size:0.75rem;'
        f'text-transform:uppercase;letter-spacing:0.06em;">Free</th>'
        f'<th style="padding:8px 12px;text-align:center;color:{PRIMARY};font-size:0.75rem;'
        f'text-transform:uppercase;letter-spacing:0.06em;">Paid Plans</th>'
        f'</tr></thead><tbody>'
    )
    rows_html = "".join(
        f'<tr style="border-bottom:1px solid #F3F4F6;">'
        f'<td style="padding:7px 12px;color:#374151;">{feat}</td>'
        f'<td style="padding:7px 12px;text-align:center;">{tick if free else cross}</td>'
        f'<td style="padding:7px 12px;text-align:center;">{tick if paid else cross}</td>'
        f'</tr>'
        for feat, free, paid in comparison
    )
    st.markdown(header + rows_html + "</tbody></table>", unsafe_allow_html=True)


def _render_report(report: dict) -> None:
    email    = st.session_state.get("hc_email", "")
    check_id = st.session_state.get("hc_check_id")

    log_event(email, "report_viewed", {"quality_score": report["quality_score"]})

    # ── Header ───────────────────────────────────────────────────────────────
    score = report["quality_score"]
    bg, _ = _score_colour(score)
    st.markdown(
        f'<div style="padding:0.5rem 0 0.2rem 0;">'
        f'<div style="font-size:1.3rem;font-weight:800;color:{PRIMARY};">'
        f'Data Health Report</div>'
        f'<div style="font-size:0.85rem;color:#6B7280;margin-top:2px;">'
        f'{report["file_name"]} · {report["rows"]:,} rows · {report["file_size_mb"]:.2f} MB</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Quality score + breakdown ─────────────────────────────────────────────
    _divider("Quality Score")
    with st.container(border=True):
        _render_score_banner(report)

    # ── KPI row ───────────────────────────────────────────────────────────────
    _divider("Overview")
    _render_kpi_row(report)

    # ── Missing values ────────────────────────────────────────────────────────
    _divider("Missing Values")
    with st.container(border=True):
        _render_missing_values(report)

    # ── Duplicates ────────────────────────────────────────────────────────────
    _divider("Duplicate Records")
    with st.container(border=True):
        _render_duplicates(report)

    # ── Formatting issues ─────────────────────────────────────────────────────
    _divider("Formatting Inconsistencies")
    with st.container(border=True):
        _render_formatting_issues(report)

    # ── Column types chart ────────────────────────────────────────────────────
    _divider("Column Type Distribution")
    with st.container(border=True):
        _render_column_types(report)

    # ── AI Observations ───────────────────────────────────────────────────────
    _divider("Top 3 AI-Powered Observations")
    with st.container(border=True):
        _render_observations(report)

    # ── Paywall ───────────────────────────────────────────────────────────────
    _render_paywall(report, email, check_id)

    # ── Start over ────────────────────────────────────────────────────────────
    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
    if st.button("Analyse a different file", key="hc_restart", use_container_width=False):
        for key in ["hc_state", "hc_report", "hc_check_id", "hc_email", "hc_ip"]:
            st.session_state.pop(key, None)
        st.rerun()


# ── Public entry point ────────────────────────────────────────────────────────

def render_health_check_panel() -> None:
    """Render the complete free health check panel (call from a Streamlit page)."""
    _inject_css()

    # Initialise session state
    if "hc_state" not in st.session_state:
        st.session_state["hc_state"] = "email_gate"

    state = st.session_state["hc_state"]

    if state == "email_gate":
        _render_email_gate()

    elif state == "upload":
        _render_upload()

    elif state == "report":
        report = st.session_state.get("hc_report")
        if report is None:
            st.session_state["hc_state"] = "email_gate"
            st.rerun()
        else:
            _render_report(report)

    else:
        st.session_state["hc_state"] = "email_gate"
        st.rerun()

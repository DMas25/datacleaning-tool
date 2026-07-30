"""Steps 4–7: Process, Dashboard, Insights and Download panel for ColtraDataAi.

Processing results are cached in st.session_state so interactive widgets
(chart selectors, distribution dropdowns) do not wipe the results on rerun.
"""
from __future__ import annotations

import os
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

from core.cleaner import CleaningOptions, apply_cleaning
from core.clinical_cleaner import apply_clinical_cleaning
from core.logistics_cleaner import apply_logistics_cleaning
from core.trade_cleaner import apply_trade_cleaning
from core.finance_cleaner import apply_finance_cleaning
from core.retail_cleaner import apply_retail_cleaning
from core.consultant_cleaner import apply_consultant_cleaning
from core.healthcare_cleaner import apply_healthcare_cleaning
from core.sme_cleaner import apply_sme_cleaning
from core.hospitality_cleaner import apply_hospitality_cleaning
from core.profiler import build_quality_summary_df
from core.insights_engine import generate_insights, detect_date_columns
from core.ai_advisor import generate_ai_advisory
from core.export_manager import generate_reports, build_chart_and_risk
from core.feature_gate import feature_unlocked
from services.entitlements import has_feature
from services.subscription import get_user_plan_from_subscription
from services.usage_tracker import can_run, increment_run
from services.ledger_analyser import analyse_ledger
from services.licence_manager_pg import (
    log_usage_event,
    get_runs_this_calendar_month,
    milestone_already_shown,
    log_milestone_shown,
)
from services.milestone_messaging import detect_milestone, build_milestone_message
from services.audit_service import log_cleaning_run
from utils.session_helpers import get_user_email
from ui.paywall import paywall_card, render_upgrade_cta_button
from ui.upgrade_prompts import render_run_limit_trigger
from ui.ledger_panel import render_ledger_panel
from core.dashboard_builder import (
    get_numeric_columns,
    get_categorical_columns,
    get_frequency_table,
    get_top_bottom,
    get_correlation_matrix,
    get_time_series,
)
from ui.branding_components import (
    render_step_header,
    render_kpi_row,
    render_risk_kpi,
    render_section_divider,
)

_RESULT_KEY = "coltradata_result"
_INPUT_SHAPE_KEY = "coltradata_input_shape"


def render_results_panel(
    df: pd.DataFrame,
    options: CleaningOptions,
    account_tier: str,
    branding: dict,
) -> None:
    """Render Steps 4–7: process button → dashboard → insights → downloads."""
    user_plan = get_user_plan_from_subscription()

    # ── Step 4: Process ───────────────────────────────────────────────────
    render_step_header(4, "Process Dataset", branding=branding)

    # Invalidate stale cached result if the uploaded file changed
    if st.session_state.get(_INPUT_SHAPE_KEY) != df.shape:
        st.session_state.pop(_RESULT_KEY, None)

    if st.button("Generate Clean Report"):
        if not can_run(user_plan):
            render_run_limit_trigger(user_plan)
            st.stop()
        st.session_state.pop(_RESULT_KEY, None)
        with st.spinner("Processing dataset…"):
            result = _run_processing(df, options, branding, user_plan)
        increment_run()
        st.session_state["runs_this_session"] = st.session_state.get("runs_this_session", 0) + 1
        if get_user_email():
            email = get_user_email()
            log_usage_event(email, "run", user_plan)
            milestone = detect_milestone(get_runs_this_calendar_month(email))
            if milestone and not milestone_already_shown(email, milestone):
                msg = build_milestone_message(milestone)
                st.toast(f"{msg.headline} {msg.supporting_message} ({msg.cta})", icon="🎉")
                log_milestone_shown(email, milestone)

            # Audit trail — one row per completed cleaning run
            _adf = result["cleaned_df"]
            _tcells = _adf.shape[0] * _adf.shape[1]
            _missing = int(_adf.isnull().sum().sum())
            _ad = result.get("audit_data", {})
            log_cleaning_run(
                email=email,
                plan=user_plan,
                dataset_type=options.dataset_type,
                rows_in=_ad.get("rows_in", len(df)),
                rows_out=len(_adf),
                cols_in=df.shape[1],
                cols_out=_adf.shape[1],
                completeness_pct=round((1 - _missing / max(_tcells, 1)) * 100, 1),
                issues_found=_ad.get("issues_found", 0),
                steps_log=_ad.get("steps_log", []),
            )

        st.session_state[_RESULT_KEY] = result
        st.session_state[_INPUT_SHAPE_KEY] = df.shape
        # Sidebar run counter is rendered earlier in the script (before this
        # button handler runs), so it would otherwise show the stale count
        # until some unrelated future rerun. Force one now to refresh it.
        st.rerun()

    result = st.session_state.get(_RESULT_KEY)
    if result is None:
        return

    # ── Post-processing KPI banner ────────────────────────────────────────
    cleaned_df       = result["cleaned_df"]
    risk_summary     = result["risk_summary"]
    total_cells      = cleaned_df.shape[0] * cleaned_df.shape[1]
    missing_post     = int(cleaned_df.isnull().sum().sum())
    completeness_pct = round((1 - missing_post / max(total_cells, 1)) * 100, 1)

    st.success("Report generated successfully.")

    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        render_kpi_row([("Original Rows", f"{len(df):,}")], branding)
    with kpi_cols[1]:
        render_kpi_row([("Cleaned Rows", f"{len(cleaned_df):,}")], branding)
    with kpi_cols[2]:
        render_kpi_row([("Rows Removed", f"{len(df) - len(cleaned_df):,}")], branding)
    with kpi_cols[3]:
        render_kpi_row([("Completeness", f"{completeness_pct}%")], branding)
    with kpi_cols[4]:
        render_risk_kpi(risk_summary["overall_risk"])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Step 5: Dashboard Results ─────────────────────────────────────────
    render_step_header(5, "Dashboard Results", branding=branding)
    _render_base_charts(df, cleaned_df, branding)

    # ── Premium chart gallery (Premium+) ─────────────────────────────────
    st.subheader("Premium Chart Gallery")

    if has_feature(user_plan, "can_view_premium_charts"):
        _render_premium_gallery(result, branding)
    else:
        paywall_card(
            "Premium visual analytics are locked",
            "Upgrade to Premium or above to unlock enhanced visual storytelling and premium charts.",
        )
        render_upgrade_cta_button("premium", key_suffix="charts_lock")

    # ── Distribution & trend analysis (Professional+) ─────────────────────
    if has_feature(user_plan, "can_view_advanced_insights"):
        _render_distribution_analysis(cleaned_df, result["date_cols"], branding)
    else:
        paywall_card(
            "Advanced Dashboard Analysis",
            "Distribution, trend, correlation and top/bottom analysis are part of the full reporting suite.",
        )
        render_upgrade_cta_button("professional", key_suffix="dashboard_lock")

    st.markdown("#### Cleaned Data Preview")
    st.dataframe(cleaned_df.head(10), use_container_width=True)

    # ── Clinical Trial Register (Clinical Research mode only) ─────────────
    if "Clinical Research" in options.dataset_type:
        _render_clinical_trial_view(result, branding)

    # ── Domain-specific results views ─────────────────────────────────────
    if "Logistics" in options.dataset_type and result.get("logistics_result"):
        _render_logistics_view(result, branding)

    if "Import/Export" in options.dataset_type and result.get("trade_result"):
        _render_trade_view(result, branding)

    if "Finance" in options.dataset_type and result.get("finance_result"):
        _render_finance_view(result, branding)

    if "Retail" in options.dataset_type and result.get("retail_result"):
        _render_retail_view(result, branding)

    if "Consultant" in options.dataset_type and result.get("consultant_result"):
        _render_consultant_view(result, branding)

    if "Healthcare" in options.dataset_type and result.get("healthcare_result"):
        _render_healthcare_view(result, branding)

    if "SME" in options.dataset_type and result.get("sme_result"):
        _render_sme_view(result, branding)

    if "Hospitality" in options.dataset_type and result.get("hospitality_result"):
        _render_hospitality_view(result, branding)

    # ── Audit Intelligence (Professional+) ───────────────────────────────
    if has_feature(user_plan, "can_view_advanced_insights"):
        render_ledger_panel(result["ledger_analysis"], branding)
    else:
        render_section_divider(branding=branding)
        render_step_header(6, "Audit Intelligence", branding=branding)
        paywall_card(
            "Audit Intelligence is locked",
            "Upgrade to Professional or above to unlock Benford's Law analysis, "
            "duplicate transaction detection, round-number testing, and more.",
            key="audit_intelligence_lock",
        )
        render_upgrade_cta_button("professional", key_suffix="audit_lock")

    # ── Step 6: Data Insights ─────────────────────────────────────────────
    render_section_divider(branding=branding)
    render_step_header(
        6, "Data Insights",
        "Structured, descriptive observations generated directly from the data. Observational only — not advice.",
        branding,
    )

    st.subheader("Advanced Data Insights")

    if has_feature(user_plan, "can_view_advanced_insights"):
        insights = generate_insights(cleaned_df)
        with st.container(border=True):
            for category, lines in insights.items():
                st.markdown(f"**{category}**")
                for line in lines:
                    st.markdown(f"- {line}")
    else:
        paywall_card(
            "Advanced insights are locked",
            "Upgrade to Professional or above to unlock deeper diagnostics and richer analysis.",
            key="data_insights_lock",
        )
        render_upgrade_cta_button("professional", key_suffix="insights_lock")

    # ── AI Advisory ───────────────────────────────────────────────────────
    # Only render this section if the Anthropic key is actually configured.
    # When the key is absent/placeholder, skip silently — no error shown.
    _ai_key_live = _anthropic_key_configured()
    if _ai_key_live or not has_feature(user_plan, "can_view_advanced_insights"):
        render_section_divider(branding=branding)
        render_step_header(
            6, "AI Advisory",
            "Claude-powered interpretation of your cleaned data — patterns, anomalies, quality risks, and concrete next steps.",
            branding,
        )

        st.subheader("AI Advisory")

        if has_feature(user_plan, "can_view_advanced_insights"):
            _model_labels = {
                "professional": "Haiku · fast analysis",
                "premium":      "Sonnet · enhanced analysis",
                "enterprise":   "Opus · comprehensive analysis",
            }
            st.caption(f"Model: {_model_labels.get(user_plan, 'AI analysis')}")

            advisory = result.get("ai_advisory")
            if advisory:
                with st.container(border=True):
                    st.markdown(advisory)
        else:
            if get_user_email():
                log_usage_event(get_user_email(), "advisory_blocked", user_plan)
                st.session_state["blocked_attempts_this_session"] = (
                    st.session_state.get("blocked_attempts_this_session", 0) + 1
                )
            paywall_card(
                "Advanced insights are locked",
                "Upgrade to Professional or above to unlock deeper diagnostics and richer analysis.",
                key="ai_advisory_lock",
            )
            render_upgrade_cta_button("professional", key_suffix="advisory_lock")

    # ── Step 7: Download Reports ──────────────────────────────────────────
    render_section_divider(branding=branding)
    render_step_header(7, "Download Reports", branding=branding)

    can_export     = has_feature(user_plan, "can_download_excel")
    can_export_pdf = has_feature(user_plan, "can_download_pdf")
    can_branding   = has_feature(user_plan, "can_brand_reports")

    # ── Excel export ──────────────────────────────────────────────────────
    st.subheader("Excel Report Export")

    if can_export:
        with open(result["excel_path"], "rb") as excel_file_bytes:
            excel_clicked = st.download_button(
                label="Download cleaned Excel report",
                data=excel_file_bytes,
                file_name=result["excel_path"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        if excel_clicked and get_user_email():
            log_usage_event(get_user_email(), "export_excel", user_plan)
            st.session_state["follow_through_this_session"] = True
        if result.get("excel_url"):
            st.link_button("Permanent download link (1 hr) →", result["excel_url"])
        st.caption(
            "Full multi-sheet workbook: cleaned data, quality log, summary statistics, "
            "and an embedded premium chart gallery."
        )
    else:
        if get_user_email():
            log_usage_event(get_user_email(), "export_blocked", user_plan)
            st.session_state["blocked_attempts_this_session"] = (
                st.session_state.get("blocked_attempts_this_session", 0) + 1
            )
        paywall_card(
            "Excel report download is locked",
            "Upgrade to Starter or above to download the full cleaned dataset and structured Excel report.",
        )
        render_upgrade_cta_button("starter", key_suffix="excel_lock")

    # ── PDF export ────────────────────────────────────────────────────────
    st.subheader("PDF Report Export")

    if can_export_pdf:
        branding_note = " Produced with your custom branding." if can_branding else ""
        pdf_clicked = st.download_button(
            label="Download PDF summary report",
            data=result["pdf_bytes"],
            file_name=result["pdf_filename"],
            mime="application/pdf",
            use_container_width=True,
        )
        if pdf_clicked and get_user_email():
            log_usage_event(get_user_email(), "export_pdf", user_plan)
            st.session_state["follow_through_this_session"] = True
        if result.get("pdf_url"):
            st.link_button("Permanent download link (1 hr) →", result["pdf_url"])
        st.caption(
            f"Portable executive summary with the same premium charts as the Excel report.{branding_note}"
        )
    else:
        if get_user_email():
            log_usage_event(get_user_email(), "export_blocked", user_plan)
            st.session_state["blocked_attempts_this_session"] = (
                st.session_state.get("blocked_attempts_this_session", 0) + 1
            )
        paywall_card(
            "PDF reporting is locked",
            "Upgrade to Professional or above to unlock downloadable PDF reporting.",
        )
        render_upgrade_cta_button("professional", key_suffix="pdf_lock")

    # ── Branded report outputs ────────────────────────────────────────────
    st.subheader("Branded Report Outputs")

    if can_branding:
        if st.session_state.pop("_branding_just_applied", False):
            st.success("Branded reports regenerated — the downloads above now use your custom logo.")
        st.success("Branding is enabled on this plan. Upload a logo below to test client-ready branded outputs.")
        _render_branding_test_form(result, df, branding)
    else:
        paywall_card(
            "Branded report outputs are locked",
            "Upgrade to Premium or Enterprise to unlock branded reports and client-facing presentation outputs.",
        )
        render_upgrade_cta_button("premium", key_suffix="branding_lock")

    # ── Step 8: Email Report Delivery ─────────────────────────────────────
    render_section_divider(branding=branding)
    render_step_header(
        8, "Email Report",
        "Send your PDF report directly to an inbox — useful when you're on the move.",
        branding=branding,
    )

    if can_export_pdf:
        _render_email_delivery_section(result, user_plan)
    else:
        paywall_card(
            "Email delivery is locked",
            "Upgrade to Professional or above to send reports directly to your inbox.",
        )
        render_upgrade_cta_button("professional", key_suffix="email_lock")


# ── Private helpers ───────────────────────────────────────────────────────────

def _render_email_delivery_section(result: dict, user_plan: str) -> None:
    from services.transactional_email import send_email_with_attachment, transactional_email_config_complete
    from services.lifecycle_emails import render_report_delivery_email

    try:
        email_cfg = dict(st.secrets.get("transactional_email", {}))
    except Exception:
        email_cfg = {}

    if not transactional_email_config_complete(email_cfg):
        st.info(
            "Email delivery is not configured on this deployment. "
            "Use the download buttons above to save your report."
        )
        return

    default_email = get_user_email() or ""
    recipient = st.text_input(
        "Recipient email address",
        value=default_email,
        placeholder="you@example.com",
        key="email_delivery_recipient",
    )

    if st.button("Send PDF report to inbox", use_container_width=True, key="send_report_email_btn"):
        if not recipient or "@" not in recipient:
            st.error("Please enter a valid email address.")
        else:
            subject, body = render_report_delivery_email(app_url=email_cfg.get("app_url", ""))
            with st.spinner("Sending report…"):
                ok = send_email_with_attachment(
                    cfg=email_cfg,
                    to_email=recipient,
                    subject=subject,
                    body=body,
                    attachment_data=result["pdf_bytes"],
                    attachment_filename=result["pdf_filename"],
                )
            if ok:
                st.success(f"Report sent to {recipient}")
                if get_user_email():
                    log_usage_event(get_user_email(), "export_email", user_plan)
                    st.session_state["follow_through_this_session"] = True
            else:
                st.error("Failed to send the email. Please download the report using the button above.")

    st.caption("The PDF executive summary is attached. Delivery may take a few minutes.")


def _render_branding_test_form(result: dict, raw_df: pd.DataFrame, branding: dict) -> None:
    """Lets an Enterprise/Premium tester swap in a custom logo and regenerate
    the Excel/PDF downloads with it, to verify the branded-output capability.

    This is co-branding, not white-labelling: the logo image is the only
    field that changes. The ColtraDataAi / Coltrane Ltd brand name, contact
    details, liability disclaimer and statutory trading-disclosure line are
    re-asserted from the canonical config by export_manager regardless of
    what's supplied here — see _enforce_protected_branding().
    """
    with st.form("branding_test_form"):
        custom_logo = st.file_uploader(
            "Custom logo (PNG/JPG)", type=["png", "jpg", "jpeg"],
            help="Upload a client or parent-company logo to test branded report generation.",
        )
        st.caption(
            "Co-branding swaps the logo only. The ColtraDataAi / Coltrane Ltd name, contact "
            "details and legal disclosures are fixed on every report regardless of plan."
        )
        apply_branding = st.form_submit_button("Apply branding & regenerate downloads")

    if not apply_branding:
        return

    branded = dict(branding)
    if custom_logo is not None:
        branded["logo_bytes"] = custom_logo.getvalue()
        branded["logo_ext"] = os.path.splitext(custom_logo.name)[1] or ".png"

    with st.spinner("Regenerating branded reports…"):
        export = generate_reports(
            branding=branded,
            raw_df=raw_df,
            cleaned_df=result["cleaned_df"],
            log_df=result["log_df"],
            quality_df=result["quality_df"],
            quality_breakdown_df=result["quality_breakdown_df"],
            chart_assets=result["chart_assets"],
            risk_summary=result["risk_summary"],
            ai_advisory=result.get("ai_advisory"),
            ledger_analysis=result.get("ledger_analysis"),
        )

    result["excel_path"]   = export.excel_path
    result["pdf_bytes"]    = export.pdf_bytes
    result["pdf_filename"] = export.pdf_filename
    st.session_state[_RESULT_KEY] = result
    st.session_state["_branding_just_applied"] = True
    # The Excel/PDF download buttons render earlier in this script than this
    # form, so without a rerun they'd keep showing the stale pre-branding
    # files for the rest of this pass. Rerun so the top of the script picks
    # up the freshly branded result before those buttons render again.
    st.rerun()


def _anthropic_key_configured() -> bool:
    """Return True only when a real (non-placeholder) Anthropic API key is present."""
    try:
        key = st.secrets["anthropic"]["api_key"]
        return bool(key) and not key.startswith("sk-ant-REPLACE")
    except Exception:
        return False


def _detect_col(df: pd.DataFrame, *keywords: str) -> Optional[str]:
    """Return the first column whose lowercased name contains any keyword."""
    for col in df.columns:
        col_l = col.lower()
        if any(kw in col_l for kw in keywords):
            return col
    return None


def _run_processing(
    df: pd.DataFrame, options: CleaningOptions, branding: dict, user_plan: str,
) -> dict:
    """Apply cleaning, build quality metrics, generate reports, return result dict."""
    cleaning_result      = apply_cleaning(df, options)
    cleaned_df           = cleaning_result.cleaned_df
    log_df               = cleaning_result.log_df

    # ── Domain-specific cleaning passes ──────────────────────────────────
    clinical_profiles    = None
    clinical_metrics     = None
    logistics_result     = None
    trade_result         = None
    finance_result       = None
    retail_result        = None
    consultant_result    = None
    healthcare_result    = None
    sme_result           = None
    hospitality_result   = None

    if "Clinical Research" in options.dataset_type:
        nct_col = _detect_col(cleaned_df, "nct")
        inv_col = _detect_col(cleaned_df, "investigator", "principal_inv", "pi_name")
        raw_unique_count  = int(df[inv_col].nunique()) if inv_col and inv_col in df.columns else 0
        clinical_result   = apply_clinical_cleaning(
            cleaned_df,
            nct_col=nct_col,
            researcher_name_col=inv_col,
        )
        cleaned_df         = clinical_result.cleaned_df
        clinical_profiles  = clinical_result.profiles
        clean_unique_count = len(clinical_profiles)
        clinical_metrics   = {
            "raw_unique_count":   raw_unique_count,
            "clean_unique_count": clean_unique_count,
            "duplicates_merged":  max(0, raw_unique_count - clean_unique_count),
        }

    if "Logistics" in options.dataset_type:
        logistics_result = apply_logistics_cleaning(cleaned_df)
        cleaned_df = logistics_result.cleaned_df

    if "Import/Export" in options.dataset_type:
        trade_result = apply_trade_cleaning(cleaned_df)
        cleaned_df = trade_result.cleaned_df

    if "Finance" in options.dataset_type:
        finance_result = apply_finance_cleaning(cleaned_df)
        cleaned_df = finance_result.cleaned_df

    if "Retail" in options.dataset_type:
        retail_result = apply_retail_cleaning(cleaned_df)
        cleaned_df = retail_result.cleaned_df

    if "Consultant" in options.dataset_type:
        consultant_result = apply_consultant_cleaning(cleaned_df)
        cleaned_df = consultant_result.cleaned_df

    if "Healthcare" in options.dataset_type:
        healthcare_result = apply_healthcare_cleaning(cleaned_df)
        cleaned_df = healthcare_result.cleaned_df

    if "SME" in options.dataset_type:
        sme_result = apply_sme_cleaning(cleaned_df)
        cleaned_df = sme_result.cleaned_df

    if "Hospitality" in options.dataset_type:
        hospitality_result = apply_hospitality_cleaning(cleaned_df)
        cleaned_df = hospitality_result.cleaned_df

    quality_df           = build_quality_summary_df(df, cleaned_df, options.null_handling)
    date_cols            = detect_date_columns(cleaned_df)

    quality_breakdown_df, risk_summary, chart_assets = build_chart_and_risk(
        branding, df, cleaned_df, date_cols=date_cols
    )

    ledger_analysis = analyse_ledger(cleaned_df)

    ai_advisory = None
    if has_feature(user_plan, "can_view_advanced_insights") and _anthropic_key_configured():
        with st.spinner("Generating AI advisory…"):
            ai_advisory = generate_ai_advisory(
                cleaned_df,
                plan_key=user_plan,
                risk_summary=risk_summary,
                ledger_analysis=ledger_analysis,
            )
        if ai_advisory and get_user_email():
            log_usage_event(get_user_email(), "ai_advisory", user_plan)
            st.session_state["follow_through_this_session"] = True

    from services.storage_service import make_run_id, storage_configured
    storage_run_id = make_run_id(get_user_email() or "") if storage_configured() else None

    # Aggregate issues across all active domain cleaners for the audit log.
    _domain_results = [
        logistics_result, trade_result, finance_result, retail_result,
        consultant_result, healthcare_result, sme_result, hospitality_result,
    ]
    _audit_issues = sum(
        r.metrics.get("issues_found", 0) for r in _domain_results if r is not None
    )
    _audit_data = {
        "rows_in":      len(df),
        "steps_log":    cleaning_result.steps_taken,
        "issues_found": _audit_issues,
    }

    export = generate_reports(
        branding=branding,
        raw_df=df,
        cleaned_df=cleaned_df,
        log_df=log_df,
        quality_df=quality_df,
        quality_breakdown_df=quality_breakdown_df,
        chart_assets=chart_assets,
        risk_summary=risk_summary,
        ai_advisory=ai_advisory,
        ledger_analysis=ledger_analysis,
        storage_run_id=storage_run_id,
    )

    return {
        "cleaned_df":           cleaned_df,
        "log_df":               log_df,
        "quality_df":           quality_df,
        "quality_breakdown_df": quality_breakdown_df,
        "date_cols":            date_cols,
        "chart_assets":         chart_assets,
        "risk_summary":         risk_summary,
        "ai_advisory":          ai_advisory,
        "ledger_analysis":      ledger_analysis,
        "excel_path":           export.excel_path,
        "pdf_bytes":            export.pdf_bytes,
        "pdf_filename":         export.pdf_filename,
        "excel_url":            export.excel_url,
        "pdf_url":              export.pdf_url,
        "clinical_profiles":    clinical_profiles,
        "clinical_metrics":     clinical_metrics,
        "logistics_result":     logistics_result,
        "trade_result":         trade_result,
        "finance_result":       finance_result,
        "retail_result":        retail_result,
        "consultant_result":    consultant_result,
        "healthcare_result":    healthcare_result,
        "sme_result":           sme_result,
        "hospitality_result":   hospitality_result,
        "audit_data":           _audit_data,
    }


def _render_base_charts(df: pd.DataFrame, cleaned_df: pd.DataFrame, branding: dict) -> None:
    """Always-visible baseline charts: missing values + original vs cleaned."""
    d1, d2 = st.columns(2)

    missing_by_col = cleaned_df.isnull().sum().sort_values(ascending=False)
    missing_by_col = missing_by_col[missing_by_col > 0]

    with d1:
        with st.container(border=True):
            st.markdown("#### Missing Values by Column")
            if not missing_by_col.empty:
                fig = px.bar(
                    x=missing_by_col.index,
                    y=missing_by_col.values,
                    labels={"x": "Column", "y": "Missing Values"},
                    color=missing_by_col.values,
                    color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]],
                )
                fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=80), coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No missing values detected.")

    with d2:
        with st.container(border=True):
            st.markdown("#### Original vs Cleaned Rows")
            rows_compare = pd.DataFrame({"Stage": ["Original", "Cleaned"], "Rows": [len(df), len(cleaned_df)]})
            fig = px.bar(
                rows_compare, x="Stage", y="Rows", color="Stage",
                color_discrete_map={"Original": branding["secondary_colour"], "Cleaned": branding["primary_colour"]},
            )
            fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def _render_premium_gallery(result: dict, branding: dict) -> None:
    render_section_divider("Premium Chart Gallery", branding)
    st.markdown("#### Premium Chart Gallery")
    st.caption(
        "High-quality charts generated automatically from your cleaned dataset — the same "
        "visuals are embedded in the Excel Executive Summary and the downloadable PDF report."
    )
    gallery_cols = st.columns(2)
    for idx, (card, _) in enumerate(result["chart_assets"]):
        with gallery_cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"##### {card.title}")
                st.caption(card.description)
                st.plotly_chart(card.figure, use_container_width=True, key=f"gallery_{card.key}")


def _render_distribution_analysis(cleaned_df: pd.DataFrame, date_cols: list, branding: dict) -> None:
    num_cols = get_numeric_columns(cleaned_df)
    cat_cols = get_categorical_columns(cleaned_df, exclude=date_cols)

    st.markdown("#### Distribution Analysis")
    dist1, dist2 = st.columns(2)

    with dist1:
        with st.container(border=True):
            st.markdown("##### Numerical Distribution")
            if num_cols:
                sel_num = st.selectbox("Select a numeric column", num_cols, key="dist_numeric")
                fig = px.histogram(cleaned_df, x=sel_num, nbins=30, color_discrete_sequence=[branding["primary_colour"]])
                fig.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No numeric columns available.")

    with dist2:
        with st.container(border=True):
            st.markdown("##### Categorical Frequency")
            if cat_cols:
                sel_cat = st.selectbox("Select a categorical column", cat_cols, key="dist_categorical")
                freq_df = get_frequency_table(cleaned_df, sel_cat, top_n=8)
                fig = px.bar(freq_df, x=str(sel_cat), y="Count", color_discrete_sequence=[branding["secondary_colour"]])
                fig.update_layout(height=360, margin=dict(l=20, r=20, t=30, b=80))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No categorical columns available.")

    # Trend analysis
    if date_cols:
        st.markdown("#### Trend Analysis")
        with st.container(border=True):
            sel_date = st.selectbox("Select a date column", date_cols, key="trend_date")
            trend_df = get_time_series(cleaned_df, sel_date)
            if trend_df is not None and not trend_df.empty:
                fig = px.line(trend_df, x="Date", y="Records", color_discrete_sequence=[branding["primary_colour"]])
                fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Selected column does not contain enough valid date values for a trend chart.")

    # Correlation heatmap
    corr = get_correlation_matrix(cleaned_df)
    if corr is not None:
        st.markdown("#### Correlation Analysis")
        with st.container(border=True):
            fig = px.imshow(
                corr, text_auto=".2f",
                color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]],
                aspect="auto",
            )
            fig.update_layout(height=420, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig, use_container_width=True)

    # Top / Bottom analysis
    st.markdown("#### Top / Bottom Analysis")
    tb1, tb2 = st.columns(2)

    with tb1:
        with st.container(border=True):
            st.markdown("##### Top Categories")
            if cat_cols:
                sel_top_cat = st.selectbox("Select a categorical column", cat_cols, key="top_categorical")
                st.dataframe(get_frequency_table(cleaned_df, sel_top_cat, top_n=5), use_container_width=True, hide_index=True)
            else:
                st.info("No categorical columns available.")

    with tb2:
        with st.container(border=True):
            st.markdown("##### Highest / Lowest Values")
            if num_cols:
                sel_top_num = st.selectbox("Select a numeric column", num_cols, key="top_numeric")
                top_vals, bottom_vals = get_top_bottom(cleaned_df, sel_top_num, n=5)
                hl1, hl2 = st.columns(2)
                with hl1:
                    st.caption("Highest")
                    st.dataframe(top_vals.reset_index(drop=True).to_frame(name=str(sel_top_num)), use_container_width=True)
                with hl2:
                    st.caption("Lowest")
                    st.dataframe(bottom_vals.reset_index(drop=True).to_frame(name=str(sel_top_num)), use_container_width=True)
            else:
                st.info("No numeric columns available.")


def _render_clinical_trial_view(result: dict, branding: dict) -> None:
    """Render the researcher → trial expander register for Clinical Research datasets.

    Each verified researcher profile is one collapsible expander. Trial records
    are listed inside, one per row, with status badge, NCT/trial ID, and phase.
    Unverified researcher IDs (failed regex) are flagged with a warning icon.
    """
    profiles = result.get("clinical_profiles")
    if not profiles:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Clinical Trial Register", branding=branding)

    st.markdown("### 2. Cleaned Relational Registry Output")

    metrics            = result.get("clinical_metrics") or {}
    raw_unique_count   = metrics.get("raw_unique_count",   0)
    clean_unique_count = metrics.get("clean_unique_count", len(profiles))
    duplicates_merged  = metrics.get("duplicates_merged",  0)

    st.toast(
        f"Data mapping complete! Merged {duplicates_merged} duplicate profiles.",
        icon="🎉",
    )
    st.success(
        f"**Cleanup Summary:** We analyzed **{raw_unique_count}** variations of "
        f"investigator names and safely resolved them down to **{clean_unique_count}** "
        f"unique master profiles. **{duplicates_merged} alignment conflicts** were "
        f"automatically corrected."
    )

    verified_count   = sum(1 for p in profiles if p.verified)
    unverified_count = len(profiles) - verified_count
    st.caption(
        f"{len(profiles)} researcher profile(s) — "
        f"{verified_count} verified"
        + (f", {unverified_count} flagged" if unverified_count else "")
    )

    for profile in profiles:
        header_icon = "✓" if profile.verified else "⚠"
        id_note     = "" if profile.verified else "  · ID format issue"
        expander_label = (
            f"{header_icon}  {profile.researcher_id} "
            f"— {profile.trial_count} trial(s){id_note}"
        )

        with st.expander(expander_label, expanded=False):
            if not profile.trials:
                st.write("No trial records found for this researcher.")
                continue

            for trial in profile.trials:
                trial_id = trial.get("trial_id", "—")
                phase    = trial.get("phase",    "—")
                status   = trial.get("status",   "—")
                verified = trial.get("researcher_valid", True)

                status_lower = str(status).lower()
                if status_lower in ("completed",):
                    badge = "🟢"
                elif status_lower in ("active", "ongoing", "recruiting", "enrolling"):
                    badge = "🔵"
                elif status_lower in ("terminated", "withdrawn", "suspended"):
                    badge = "🔴"
                else:
                    badge = "⚪"

                id_flag = "  ⚠ researcher ID unverified" if not verified else ""
                st.write(
                    f"{badge} &nbsp;**{trial_id}**"
                    f"&nbsp;&nbsp;|&nbsp;&nbsp;Phase: {phase}"
                    f"&nbsp;&nbsp;|&nbsp;&nbsp;Status: {status}{id_flag}"
                )


# ── Logistics & Supply Chain results view ─────────────────────────────────────

def _render_logistics_view(result: dict, branding: dict) -> None:
    lr = result.get("logistics_result")
    if not lr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Logistics & Supply Chain Analysis", branding=branding)

    m = lr.metrics
    cols = st.columns(3)
    with cols[0]:
        render_kpi_row([("Total Shipments", f"{m.get('total_shipments', 0):,}")], branding)
    with cols[1]:
        transit = m.get("transit_stats") or {}
        avg_transit = transit.get("avg_days")
        render_kpi_row([("Avg Transit Days", f"{avg_transit:.1f}" if avg_transit is not None else "—")], branding)
    with cols[2]:
        render_kpi_row([("Issues Detected", f"{m.get('issues_found', 0)}")], branding)

    if m.get("status_counts"):
        st.markdown("#### Shipment Status Breakdown")
        status_df = pd.DataFrame(
            list(m["status_counts"].items()), columns=["Status", "Count"]
        ).sort_values("Count", ascending=False)
        fig = px.bar(
            status_df, x="Status", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=60), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if lr.issues:
        st.markdown("#### Findings")
        for issue in lr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")


# ── Import/Export & Trade results view ────────────────────────────────────────

def _render_trade_view(result: dict, branding: dict) -> None:
    tr = result.get("trade_result")
    if not tr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Import/Export & Trade Analysis", branding=branding)

    m = tr.metrics
    cols = st.columns(3)
    with cols[0]:
        render_kpi_row([("Total Records", f"{m.get('total_records', 0):,}")], branding)
    with cols[1]:
        hs_issues = sum(i["count"] for i in tr.issues if "HS" in i["type"] and i["count"] > 0)
        render_kpi_row([("HS Code Issues", f"{hs_issues:,}")], branding)
    with cols[2]:
        render_kpi_row([("Issues Detected", f"{m.get('issues_found', 0)}")], branding)

    if m.get("origin_counts"):
        st.markdown("#### Top Origin Countries")
        co_df = pd.DataFrame(
            list(m["origin_counts"].items()), columns=["Country", "Count"]
        ).sort_values("Count", ascending=False).head(10)
        fig = px.bar(
            co_df, x="Country", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=60), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if tr.issues:
        st.markdown("#### Findings")
        for issue in tr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")


# ── Finance & Accounting results view ─────────────────────────────────────────

def _render_finance_view(result: dict, branding: dict) -> None:
    fr = result.get("finance_result")
    if not fr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Finance & Accounting Analysis", branding=branding)

    m = fr.metrics
    cols = st.columns(3)
    with cols[0]:
        render_kpi_row([("Total Entries", f"{m.get('total_entries', 0):,}")], branding)
    with cols[1]:
        render_kpi_row([("Unique Accounts", f"{m.get('unique_accounts', '—')}")], branding)
    with cols[2]:
        render_kpi_row([("Issues Detected", f"{m.get('issues_found', 0)}")], branding)

    tb = m.get("trial_balance")
    if tb:
        balance_colour = "normal" if tb["in_balance"] else "inverse"
        bal_cols = st.columns(3)
        with bal_cols[0]:
            st.metric("Total Debits", f"{tb['total_debits']:,.2f}")
        with bal_cols[1]:
            st.metric("Total Credits", f"{tb['total_credits']:,.2f}")
        with bal_cols[2]:
            st.metric(
                "Balance Difference",
                f"{tb['difference']:,.2f}",
                delta="In Balance" if tb["in_balance"] else f"{tb['pct_diff']}% off",
                delta_color="normal" if tb["in_balance"] else "inverse",
            )

    if m.get("account_type_counts"):
        st.markdown("#### Account Type Distribution")
        ac_df = pd.DataFrame(
            list(m["account_type_counts"].items()), columns=["Type", "Count"]
        ).sort_values("Count", ascending=False)
        fig = px.bar(
            ac_df, x="Type", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=100), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if fr.issues:
        st.markdown("#### Findings")
        for issue in fr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")


# ── Retail & Inventory results view ──────────────────────────────────────────

def _render_retail_view(result: dict, branding: dict) -> None:
    rr = result.get("retail_result")
    if not rr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Retail & Inventory Analysis", branding=branding)

    m = rr.metrics
    cols = st.columns(4)
    with cols[0]:
        render_kpi_row([("Total Products", f"{m.get('total_products', 0):,}")], branding)
    with cols[1]:
        render_kpi_row([("Unique SKUs", f"{m.get('unique_skus', '—')}")], branding)
    with cols[2]:
        margin = m.get("avg_gross_margin_pct")
        render_kpi_row([("Avg Gross Margin", f"{margin:.1f}%" if margin is not None else "—")], branding)
    with cols[3]:
        render_kpi_row([("Issues Detected", f"{m.get('issues_found', 0)}")], branding)

    if m.get("avg_price") is not None or m.get("avg_cost") is not None:
        price_cols = st.columns(2)
        with price_cols[0]:
            avg_p = m.get("avg_price")
            st.metric("Avg Selling Price", f"£{avg_p:,.2f}" if avg_p is not None else "—")
        with price_cols[1]:
            avg_c = m.get("avg_cost")
            st.metric("Avg Cost Price", f"£{avg_c:,.2f}" if avg_c is not None else "—")

    if m.get("category_counts"):
        st.markdown("#### Category Breakdown")
        cat_df = pd.DataFrame(
            list(m["category_counts"].items()), columns=["Category", "Count"]
        ).sort_values("Count", ascending=False).head(12)
        fig = px.bar(
            cat_df, x="Category", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=30, b=100), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if rr.issues:
        st.markdown("#### Findings")
        for issue in rr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")


# ── Consultants & Professional Services results view ──────────────────────────

def _render_consultant_view(result: dict, branding: dict) -> None:
    cr = result.get("consultant_result")
    if not cr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Consultants & Professional Services Analysis", branding=branding)

    m = cr.metrics
    cols = st.columns(4)
    with cols[0]:
        render_kpi_row([("Total Rows", f"{m.get('total_rows', 0):,}")], branding)
    with cols[1]:
        render_kpi_row([("Unique Projects", f"{m.get('unique_projects', '—')}")], branding)
    with cols[2]:
        render_kpi_row([("Unique Clients", f"{m.get('unique_clients', '—')}")], branding)
    with cols[3]:
        util = m.get("utilisation_pct")
        render_kpi_row([("Utilisation", f"{util:.1f}%" if util is not None else "—")], branding)

    hour_cols = st.columns(3)
    with hour_cols[0]:
        total_b = m.get("total_billable_hours")
        st.metric("Billable Hours", f"{total_b:,.1f}" if total_b is not None else "—")
    with hour_cols[1]:
        total_l = m.get("total_hours_logged")
        st.metric("Total Hours Logged", f"{total_l:,.1f}" if total_l is not None else "—")
    with hour_cols[2]:
        overruns = m.get("overrun_count")
        avg_over = m.get("avg_overrun_pct")
        st.metric(
            "Budget Overruns",
            f"{overruns}" if overruns is not None else "—",
            delta=f"avg +{avg_over:.1f}%" if avg_over else None,
            delta_color="inverse" if overruns else "normal",
        )

    if m.get("status_counts"):
        st.markdown("#### Engagement Status Breakdown")
        s_df = pd.DataFrame(
            list(m["status_counts"].items()), columns=["Status", "Count"]
        ).sort_values("Count", ascending=False)
        fig = px.bar(
            s_df, x="Status", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=60), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if cr.issues:
        st.markdown("#### Findings")
        for issue in cr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")


# ── Healthcare (Operational) results view ─────────────────────────────────────

def _render_healthcare_view(result: dict, branding: dict) -> None:
    hr = result.get("healthcare_result")
    if not hr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Healthcare (Operational) Analysis", branding=branding)

    m = hr.metrics
    cols = st.columns(4)
    with cols[0]:
        render_kpi_row([("Total Records", f"{m.get('total_records', 0):,}")], branding)
    with cols[1]:
        dna = m.get("dna_rate_pct")
        render_kpi_row([("DNA Rate", f"{dna:.1f}%" if dna is not None else "—")], branding)
    with cols[2]:
        wt = (m.get("waiting_time_stats") or {}).get("avg_days")
        render_kpi_row([("Avg Wait (days)", f"{wt:.1f}" if wt is not None else "—")], branding)
    with cols[3]:
        render_kpi_row([("Issues Detected", f"{m.get('issues_found', 0)}")], branding)

    wt_stats = m.get("waiting_time_stats")
    if wt_stats:
        over_18 = wt_stats.get("over_18wk", 0)
        wt_cols = st.columns(4)
        with wt_cols[0]:
            st.metric("Min Wait (days)", wt_stats.get("min_days", "—"))
        with wt_cols[1]:
            st.metric("Avg Wait (days)", wt_stats.get("avg_days", "—"))
        with wt_cols[2]:
            st.metric("Max Wait (days)", wt_stats.get("max_days", "—"))
        with wt_cols[3]:
            st.metric("18-Week Breaches", over_18, delta_color="inverse" if over_18 else "normal")

    if m.get("status_counts"):
        st.markdown("#### Appointment Status Breakdown")
        apt_df = pd.DataFrame(
            list(m["status_counts"].items()), columns=["Status", "Count"]
        ).sort_values("Count", ascending=False)
        fig = px.bar(
            apt_df, x="Status", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=80), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if hr.issues:
        st.markdown("#### Findings")
        for issue in hr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")


# ── SME & Small Business results view ────────────────────────────────────────

def _render_sme_view(result: dict, branding: dict) -> None:
    sr = result.get("sme_result")
    if not sr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "SME & Small Business Analysis", branding=branding)

    m = sr.metrics
    cols = st.columns(4)
    with cols[0]:
        render_kpi_row([("Total Records", f"{m.get('total_records', 0):,}")], branding)
    with cols[1]:
        render_kpi_row([("Unique Customers", f"{m.get('unique_customers', '—')}")], branding)
    with cols[2]:
        overdue = m.get("overdue_invoices")
        render_kpi_row([("Overdue Invoices", f"{overdue:,}" if overdue is not None else "—")], branding)
    with cols[3]:
        render_kpi_row([("Issues Detected", f"{m.get('issues_found', 0)}")], branding)

    if m.get("total_invoice_value") is not None or m.get("avg_invoice_value") is not None:
        inv_cols = st.columns(3)
        with inv_cols[0]:
            total_v = m.get("total_invoice_value")
            st.metric("Total Invoice Value", f"£{total_v:,.2f}" if total_v is not None else "—")
        with inv_cols[1]:
            avg_v = m.get("avg_invoice_value")
            st.metric("Avg Invoice Value", f"£{avg_v:,.2f}" if avg_v is not None else "—")
        with inv_cols[2]:
            avg_od = m.get("avg_days_overdue")
            st.metric(
                "Avg Days Overdue",
                f"{avg_od:.0f}" if avg_od else "0",
                delta_color="inverse" if avg_od and avg_od > 0 else "normal",
            )

    if m.get("terms_counts"):
        st.markdown("#### Payment Terms Breakdown")
        t_df = pd.DataFrame(
            list(m["terms_counts"].items()), columns=["Terms", "Count"]
        ).sort_values("Count", ascending=False)
        fig = px.bar(
            t_df, x="Terms", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=100), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if sr.issues:
        st.markdown("#### Findings")
        for issue in sr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")


# ── Hospitality & Accommodation results view ──────────────────────────────────

def _render_hospitality_view(result: dict, branding: dict) -> None:
    hr = result.get("hospitality_result")
    if not hr:
        return

    render_section_divider(branding=branding)
    render_step_header(5, "Hospitality & Accommodation Analysis", branding=branding)

    m = hr.metrics
    cols = st.columns(4)
    with cols[0]:
        render_kpi_row([("Total Bookings", f"{m.get('total_bookings', 0):,}")], branding)
    with cols[1]:
        cancel = m.get("cancellation_rate_pct")
        render_kpi_row([("Cancellation Rate", f"{cancel:.1f}%" if cancel is not None else "—")], branding)
    with cols[2]:
        adr = m.get("avg_daily_rate")
        render_kpi_row([("Avg Daily Rate", f"£{adr:,.2f}" if adr is not None else "—")], branding)
    with cols[3]:
        render_kpi_row([("Issues Detected", f"{m.get('issues_found', 0)}")], branding)

    stay_stats = m.get("stay_stats")
    if stay_stats:
        stay_cols = st.columns(4)
        with stay_cols[0]:
            st.metric("Avg Length of Stay", f"{stay_stats.get('avg_nights', '—')} nights")
        with stay_cols[1]:
            st.metric("Min Nights", stay_stats.get("min_nights", "—"))
        with stay_cols[2]:
            st.metric("Max Nights", stay_stats.get("max_nights", "—"))
        with stay_cols[3]:
            no_show_rate = m.get("no_show_rate_pct")
            st.metric("No-Show Rate", f"{no_show_rate:.1f}%" if no_show_rate is not None else "—")

    if m.get("total_revenue") is not None or m.get("avg_revenue") is not None:
        rev_cols = st.columns(2)
        with rev_cols[0]:
            total_r = m.get("total_revenue")
            st.metric("Total Revenue", f"£{total_r:,.2f}" if total_r is not None else "—")
        with rev_cols[1]:
            avg_r = m.get("avg_revenue")
            st.metric("Avg Revenue / Booking", f"£{avg_r:,.2f}" if avg_r is not None else "—")

    chart_cols = st.columns(2)

    if m.get("status_counts"):
        with chart_cols[0]:
            st.markdown("#### Booking Status Breakdown")
            s_df = pd.DataFrame(
                list(m["status_counts"].items()), columns=["Status", "Count"]
            ).sort_values("Count", ascending=False)
            fig = px.bar(
                s_df, x="Status", y="Count",
                color_discrete_sequence=[branding["primary_colour"]],
                text="Count",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=60), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    if m.get("channel_counts"):
        with chart_cols[1]:
            st.markdown("#### Booking Channel Breakdown")
            ch_df = pd.DataFrame(
                list(m["channel_counts"].items()), columns=["Channel", "Count"]
            ).sort_values("Count", ascending=False)
            fig = px.bar(
                ch_df, x="Channel", y="Count",
                color_discrete_sequence=[branding["secondary_colour"]],
                text="Count",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=80), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    if m.get("room_type_counts"):
        st.markdown("#### Room Type Breakdown")
        rt_df = pd.DataFrame(
            list(m["room_type_counts"].items()), columns=["Room Type", "Count"]
        ).sort_values("Count", ascending=False).head(12)
        fig = px.bar(
            rt_df, x="Room Type", y="Count",
            color_discrete_sequence=[branding["primary_colour"]],
            text="Count",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=100), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    if hr.issues:
        st.markdown("#### Findings")
        for issue in hr.issues:
            if issue["count"] > 0:
                st.warning(f"**{issue['type']}** — {issue['description']}")
            else:
                st.success(f"**{issue['type']}** — {issue['description']}")

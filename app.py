"""ColtraDataAi — main Streamlit entry point.

This file is intentionally thin: it wires together the panel modules in
ui/ and delegates all rendering and business logic to them.  Do not add
data-processing or report-building code here.
"""
import time

import streamlit as st
from PIL import Image

from config.branding_config import branding
from config.legal_config import legal
from config.tier_config import row_limit_for
from core.feature_gate import render_tier_selector, render_sidebar_subscription_panel
from ui.upgrade_prompts import render_targeted_upgrade_banner
from ui.pricing_cards import render_pricing_page
from ui.branding_components import inject_app_css, inject_og_meta_tags
from ui.homepage import check_password, render_header, render_footer, render_legal_notices, render_sign_out_button
from ui.onboarding_modal import show_onboarding_modal, needs_onboarding
from ui.feedback_modal import show_feedback_modal
from services.feedback_service import should_show_feedback
from ui.upload_panel import render_upload_panel
from ui.cleaning_options import render_cleaning_options
from ui.preview_panel import render_preview_panel
from ui.results_panel import render_results_panel
from utils.session_helpers import init_session, get_plan_key, set_plan_key
from services.subscription import load_customer_plan_from_store
from core.fault_monitor import capture_exception, log_recovery_outcome, reset_volatile_session_state
from core.recovery_rules import get_recovery_action, RecoveryAction, MAX_AUTO_RETRIES, RETRY_DELAY_SECONDS
from core.safe_mode import get_safe_mode_status
from core.circuit_breaker import is_component_disabled
from core.lifecycle import log_app_start_once
from ui.error_page import render_down_page, render_safe_mode_page
from ui.fault_dashboard import render_fault_dashboard
from ui.internal_insights_dashboard import render_internal_insights_dashboard

# Logged once per process (see core/lifecycle.py for why this can't just
# be a module-level call inside _run_app — Streamlit re-execs this file
# on every rerun, but the guard backing this lives in an imported module).
log_app_start_once()

# =============================================================================
# SUBSCRIPTION SYSTEM — OVERVIEW
# =============================================================================
# What was done
# Your app already had excellent subscription infrastructure in place — the
# issue was that several pieces weren't wired together correctly.  No logic
# was duplicated or rewritten; only the gaps were fixed.
#
# Files changed
# app.py
#   - Added # SUBSCRIPTION LOGIC START / END comment blocks at all three
#     subscription points (session init, sidebar plan selector, results gating)
#   - Introduced user_plan = get_plan_key() as the single canonical variable
#     for all feature gate decisions
#   - Documents the full plan matrix and feature flag names inline
#
# core/feature_gate.py  —  CRITICAL BUG FIX
#   - On licence activation, now calls set_plan_key() to sync
#     st.session_state["plan_key"] alongside account_tier — previously,
#     activating a Pro/Enterprise licence had no effect on feature gates
#     because plan_key stayed at "free"
#   - Dev tier override dropdown also syncs plan_key
#   - Removed "Row limit: X,XXX rows per upload" from the sidebar badge —
#     users no longer see raw capacity numbers
#
# services/access_control.py
#   - validate_capacity() now returns commercial SaaS language instead of
#     technical messages ("Upgrade your plan to process this dataset in full"
#     vs "This file exceeds the processing capacity for…")
#
# ui/upload_panel.py
#   - Replaced st.error(reason) with paywall_card("Unlock Full Dataset
#     Processing", reason) — users hit a branded upgrade prompt instead of
#     a red error box
#
# Plan matrix  (config/plans.py)
# ┌──────────────┬───────┬─────┬──────────┬──────────┬───────────┐
# │ Plan         │ Excel │ PDF │ Insights │ Branding │ Max rows  │
# ├──────────────┼───────┼─────┼──────────┼──────────┼───────────┤
# │ free         │  —    │  —  │    —     │    —     │     5,000 │
# │ starter      │  ✓    │  —  │    —     │    —     │    25,000 │
# │ professional │  ✓    │  ✓  │    ✓     │    —     │   100,000 │
# │ premium      │  ✓    │  ✓  │    ✓     │    ✓     │   250,000 │
# │ enterprise   │  ✓    │  ✓  │    ✓     │    ✓     │ 1,000,000 │
# └──────────────┴───────┴─────┴──────────┴──────────┴───────────┘
# =============================================================================

# ── Page configuration ────────────────────────────────────────────────────────

try:
    _page_icon = Image.open("assets/favicon.png")
except Exception:
    _page_icon = "🗂️"

st.set_page_config(
    page_title=branding["app_name"],
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_app_css(branding)
inject_og_meta_tags(branding)

# ── PWA bootstrap ──────────────────────────────────────────────────────────────
# Injects the web-app manifest link and registers the service worker so the app
# can be installed to a home screen on mobile (iOS Safari / Android Chrome).
# Icons must be placed in static/icon-192.png and static/icon-512.png.
st.markdown(
    """
    <script>
    (function () {
        if (!document.querySelector('link[rel="manifest"]')) {
            var link = document.createElement('link');
            link.rel = 'manifest';
            link.href = '/app/static/manifest.json';
            document.head.appendChild(link);
        }
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function () {
                navigator.serviceWorker
                    .register('/app/static/sw.js')
                    .catch(function () {});
            });
        }
    })();
    </script>
    """,
    unsafe_allow_html=True,
)


# Pre-built CSV payload for the sidebar sample download.
# Uses the full 10-row entity-resolution dataset so the Clinical Research
# template pipeline (NCT normalise → name standardise → entity resolve →
# expander view) is fully exercised on first try.
_DEMO_CSV_BYTES: bytes = (
    "Trial_ID,Principal_Investigator,Facility_Site,Phase,Status\n"
    "nct 49211,Dr. John Smith,Mayo Clinic,Phase II,Recruiting\n"
    "NCT-051122,J. Smith,Mayo Clinic,Phase II,Recruiting\n"
    "nct0049211,Smith John,Mayo Clinic,Phase II,Completed\n"
    "NCT:88231,John A. Smith MD,Mayo Clinic,Phase I,Active\n"
    "NCT 00511220,Dr. Sarah Jones,Stanford Med,Phase III,Completed\n"
    "NCT 39100,Sarah Jones MD,Stanford Med,Phase III,Completed\n"
    "NCT 10044,S. Jones,Stanford Med,Phase I,Active\n"
    "NCT 88823,Sarah E. Jones,Johns Hopkins,Phase II,Recruiting\n"
    "NCT 22201,Dr. Emily Carter,Cleveland Clinic,Phase II,Active\n"
    "NCT 33902,James Okafor PhD,Johns Hopkins,Phase III,Recruiting\n"
).encode("utf-8")


def _run_app() -> None:
    # SUBSCRIPTION LOGIC START
    # ── Session + subscription init ──────────────────────────────────────────
    # Bootstraps st.session_state["plan_key"] on first load.
    # Resolution order: licence-key activation → dev override → "free" default.
    # Plan keys: "free" | "starter" | "professional" | "premium" | "enterprise"
    # All feature gates, capacity checks, and paywall cards read from plan_key.
    # See config/plans.py for the full tier matrix and feature flags:
    #   can_download_excel, can_download_pdf, can_view_advanced_insights,
    #   can_brand_reports, max_rows_backend, max_file_mb_backend
    init_session()
    # SUBSCRIPTION LOGIC END

    # ── App mode ───────────────────────────────────────────────────────────────
    # Resolution order:
    #   1. secrets.toml [dev] app_mode   — explicit override (highest priority)
    #   2. secrets.toml [dev] local_dev  — True → "desktop" (bat file / local run)
    #   3. "dev" fallback                — no secrets available
    # To deploy to production: set app_mode = "live" in Streamlit Cloud secrets.
    try:
        _dev_cfg = st.secrets.get("dev", {})
        if "app_mode" in _dev_cfg:
            app_mode = _dev_cfg["app_mode"]
        elif _dev_cfg.get("local_dev", False):
            app_mode = "desktop"
        else:
            app_mode = "dev"
    except Exception:
        app_mode = "dev"

    # ── Authentication gate ─────────────────────────────────────────────────────

    if not check_password(branding):
        st.stop()

    render_sign_out_button()

    st.sidebar.image("assets/New_logo.png", use_container_width=True)
    st.sidebar.markdown("---")

    # ── Admin · fault dashboard ─────────────────────────────────────────────────
    # Password-gated (separate from the client login above). Never linked from
    # client-facing UI — operators navigate here manually when investigating
    # an incident. Rendering it short-circuits the rest of the app for this run.
    with st.sidebar.expander("🛠 Admin", expanded=False):
        if st.session_state.get("is_admin"):
            # Admin bypass users get toggle checkboxes — no secondary password needed
            st.session_state["_show_fault_dashboard"] = st.checkbox(
                "Fault dashboard",
                value=st.session_state.get("_show_fault_dashboard", False),
            )
            st.session_state["_show_internal_insights"] = st.checkbox(
                "Insights dashboard",
                value=st.session_state.get("_show_internal_insights", False),
            )
        else:
            admin_password = st.secrets.get("admin", {}).get("dashboard_password", "")
            entered = st.text_input("Admin password", type="password", key="_admin_pwd")
            if st.button("Unlock", key="_admin_unlock", use_container_width=True):
                if admin_password and entered == admin_password:
                    st.session_state["_admin_unlocked"] = True
                else:
                    st.error("Incorrect password")
            if st.session_state.get("_admin_unlocked"):
                st.session_state["_show_fault_dashboard"] = st.checkbox(
                    "Fault dashboard",
                    value=st.session_state.get("_show_fault_dashboard", False),
                )
                st.session_state["_show_internal_insights"] = st.checkbox(
                    "Insights dashboard",
                    value=st.session_state.get("_show_internal_insights", False),
                )

    if st.session_state.get("_show_fault_dashboard"):
        render_fault_dashboard()
        return

    if st.session_state.get("_show_internal_insights"):
        render_internal_insights_dashboard()
        return

    # ── Safe mode gate ───────────────────────────────────────────────────────────
    # core/safe_mode.py trips this after a sustained fault rate (see
    # core/fault_monitor.py) or a watchdog-detected crash loop. While active,
    # skip straight to a minimal status page instead of the full pipeline below.
    # get_safe_mode_status() is the same payload ui/fault_dashboard.py reads,
    # so the reason/timestamp shown here always matches the admin view.
    safe_mode_status = get_safe_mode_status()
    if safe_mode_status["active"]:
        render_safe_mode_page(branding, safe_mode_status)
        return

    # SUBSCRIPTION LOGIC START
    # ── Live-mode plan resolution ───────────────────────────────────────────────
    # When app_mode is "live", the customer's plan is loaded from the backend store
    # and written into session_state so all downstream feature gates see the correct
    # entitlements.  In "dev" mode this block is skipped and the plan falls back to
    # the licence-key / dev-override / "free" default set by init_session().
    if app_mode == "live":
        customer_email = st.session_state.get("customer_email", "")
        if customer_email:
            set_plan_key(load_customer_plan_from_store(customer_email))

    # ── Onboarding gate ────────────────────────────────────────────────────────
    # Intercepts a paying subscriber on their first activation to capture
    # profile and compliance-consent data.  Runs after plan resolution so that
    # plan_key is already correct.  st.stop() blocks the rest of the app from
    # rendering until the modal is dismissed (i.e. onboarding_complete is set).
    _onboarding_email = st.session_state.get("user_email") or st.session_state.get("customer_email", "")
    if needs_onboarding(_onboarding_email):
        show_onboarding_modal(_onboarding_email)
        st.stop()

    # ── Subscription panels ─────────────────────────────────────────────────────
    # ---------------------------------------------
    # SUBSCRIPTION UI ENTRY POINTS
    # ---------------------------------------------
    render_sidebar_subscription_panel()         # licence form · plan badge · run counter · upgrade CTAs

    # ── Sidebar: sample file download ───────────────────────────────────────
    # Gives first-time visitors a one-click way to try the Clinical Research
    # template without needing their own dataset.  The CSV is intentionally
    # messy so the full pipeline (NCT normalisation → name standardisation →
    # entity resolution → expander view) is exercised end-to-end.
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🧪 Test the Platform")
        st.caption(
            "Don't have a dataset ready? Download our intentionally messy "
            "sample file and upload it with the "
            "**🧬 Clinical Research & Trial Registers** template selected."
        )
        st.download_button(
            label="📥 Download Messy Clinical CSV",
            data=_DEMO_CSV_BYTES,
            file_name="messy_clinical_trials_sample.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # main-area nudge, grounded in actual usage history — evaluated once per
    # session (page-load moment only). Restricted to banner-tier signals
    # inside the function itself; the session gate lives here at the call
    # site so the function stays a pure "evaluate and render" with no
    # session-state side effects.
    if not st.session_state.get("session_prompt_evaluated"):
        render_targeted_upgrade_banner()
        st.session_state["session_prompt_evaluated"] = True

    # Derive routing keys used by upload capacity checks and legacy helpers.
    account_tier   = st.session_state.get("account_tier", "Free")
    user_plan      = get_plan_key()             # canonical plan key for all feature gates
    tier_row_limit = row_limit_for(account_tier)
    # SUBSCRIPTION LOGIC END

    # ── App header ──────────────────────────────────────────────────────────────

    render_header(branding)

    with st.expander("View pricing plans", expanded=False):
        render_pricing_page()                   # full 5-tier interactive pricing table

    # ── Step 1: Upload ──────────────────────────────────────────────────────────
    # Capacity limits (rows + file size) are enforced here against user_plan.
    # Users see upgrade prompts, not raw technical limits.
    #
    # Each step is gated by its own circuit breaker (core/circuit_breaker.py):
    # if this exact component has failed FAILURE_THRESHOLD times in the last
    # WINDOW_SECONDS, it's temporarily disabled instead of failing again for
    # every new session — it auto-recovers after COOLDOWN_SECONDS.

    if is_component_disabled("ui.upload_panel"):
        st.warning("File upload is temporarily unavailable while we resolve an issue. Please check back shortly.")
        return

    df = render_upload_panel(branding, tier_row_limit, tier_name=account_tier)

    if df is not None:

        # ── Step 2: Configure ───────────────────────────────────────────────────

        options = render_cleaning_options(branding)

        # ── Step 3: Preview ─────────────────────────────────────────────────────

        if is_component_disabled("ui.preview_panel"):
            st.warning("Data preview is temporarily unavailable while we resolve an issue.")
        else:
            render_preview_panel(df, branding)

        # SUBSCRIPTION LOGIC START
        # ── Steps 4–7: Process → Dashboard → Insights → Download ───────────────
        # Feature gates applied inside render_results_panel by user_plan:
        #   • Advanced dashboard & insights → can_view_advanced_insights
        #   • Excel download               → can_download_excel
        #   • PDF download                 → can_download_pdf
        #   • Custom branding              → can_brand_reports
        # Paywalls render only at the point of action, never during upload/preview.
        if is_component_disabled("ui.results_panel"):
            st.warning("Report generation is temporarily unavailable while we resolve an issue.")
        else:
            render_results_panel(df, options, user_plan, branding)
        # SUBSCRIPTION LOGIC END

        # ── Post-run feedback survey ────────────────────────────────────────────
        # Show once per session, after the user's 3rd lifetime run.
        # Suppression (snooze / never-ask-again) is persisted in signal_log.
        _fb_email = st.session_state.get("user_email") or st.session_state.get("customer_email", "")
        if (
            _fb_email
            and st.session_state.get("runs_this_session", 0) >= 1
            and should_show_feedback(_fb_email)
        ):
            show_feedback_modal(_fb_email)

    # ── Page footer ─────────────────────────────────────────────────────────────

    render_legal_notices(legal)
    render_footer(branding)


# ── Fault boundary ──────────────────────────────────────────────────────────────
# Any unhandled exception from the rendering pipeline above is caught here so
# clients see a branded "we're on it" page instead of a raw stack trace. Every
# fault is logged and classified (core/fault_monitor.py, core/fault_types.py);
# core/recovery_rules.py then decides whether it's worth silently retrying
# (transient network errors, likely-corrupted session state) before giving up
# and showing the client the down page.
#
# Retries are done via st.rerun() rather than looping in-process: re-calling
# _run_app() directly within the same script execution would re-render every
# widget that already succeeded before the failure point, and Streamlit
# raises DuplicateWidgetID for the second copy of each one. A rerun starts a
# clean script execution instead, so the retry count is tracked in
# session_state (capped at MAX_AUTO_RETRIES) rather than a local variable.
try:
    _run_app()
    # A prior attempt this session failed and is only succeeding now because
    # of a retry/reset — close the loop so the dashboard can show whether
    # auto-recovery actually worked, not just that it was attempted.
    if st.session_state.get("_fault_retry_count", 0) > 0 and st.session_state.get("_last_incident_id"):
        log_recovery_outcome(
            st.session_state["_last_incident_id"],
            st.session_state.get("_last_recovery_action", "unknown"),
            recovery_success=True,
        )
    st.session_state["_fault_retry_count"] = 0
except Exception as exc:
    action = get_recovery_action(exc)
    if action is RecoveryAction.RESET_STATE:
        reset_volatile_session_state()

    _retry_count = st.session_state.get("_fault_retry_count", 0)
    _incident_id = capture_exception(
        exc, context="app._run_app",
        recovery_action=action.value,
        recovery_success=None,  # unknown until the retry (or giving up) below resolves it
        metadata={"attempt": _retry_count},
    )
    st.session_state["_last_incident_id"] = _incident_id
    st.session_state["_last_recovery_action"] = action.value

    can_retry = action is not RecoveryAction.NONE and _retry_count < MAX_AUTO_RETRIES
    if can_retry:
        st.session_state["_fault_retry_count"] = _retry_count + 1
        if action is RecoveryAction.RETRY_WITH_DELAY:
            time.sleep(RETRY_DELAY_SECONDS)
        st.rerun()
    else:
        if _retry_count > 0:
            # Retries were attempted (action wasn't NONE) and still ran out — recovery failed.
            log_recovery_outcome(_incident_id, action.value, recovery_success=False)
        st.session_state["_fault_retry_count"] = 0
        render_down_page(branding, _incident_id)

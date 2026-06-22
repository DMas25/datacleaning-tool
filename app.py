"""ColtraDataAi — main Streamlit entry point.

This file is intentionally thin: it wires together the panel modules in
ui/ and delegates all rendering and business logic to them.  Do not add
data-processing or report-building code here.
"""
import streamlit as st
from PIL import Image

from config.branding_config import branding
from config.legal_config import legal
from config.tier_config import row_limit_for
from core.feature_gate import render_tier_selector, render_sidebar_subscription_panel
from ui.upgrade_prompts import render_live_upgrade_banner
from ui.pricing_cards import render_pricing_page
from ui.branding_components import inject_app_css
from ui.homepage import check_password, render_header, render_footer, render_legal_notices, render_sign_out_button
from ui.upload_panel import render_upload_panel
from ui.cleaning_options import render_cleaning_options
from ui.preview_panel import render_preview_panel
from ui.results_panel import render_results_panel
from utils.session_helpers import init_session, get_plan_key, set_plan_key
from services.subscription import load_customer_plan_from_store

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

# SUBSCRIPTION LOGIC START
# ── Session + subscription init ──────────────────────────────────────────────
# Bootstraps st.session_state["plan_key"] on first load.
# Resolution order: licence-key activation → dev override → "free" default.
# Plan keys: "free" | "starter" | "professional" | "premium" | "enterprise"
# All feature gates, capacity checks, and paywall cards read from plan_key.
# See config/plans.py for the full tier matrix and feature flags:
#   can_download_excel, can_download_pdf, can_view_advanced_insights,
#   can_brand_reports, max_rows_backend, max_file_mb_backend
init_session()
# SUBSCRIPTION LOGIC END

# ── App mode ─────────────────────────────────────────────────────────────────
# Resolution order:
#   1. secrets.toml [dev] app_mode   — explicit override (highest priority)
#   2. secrets.toml [dev] local_dev  — True → "desktop" (bat file / local run)
#   3. "dev" fallback                — no secrets available
# To deploy to production: set app_mode = "live" in Streamlit Cloud secrets.
try:
    _dev_cfg = st.secrets.get("dev", {})
    if "app_mode" in _dev_cfg:
        APP_MODE = _dev_cfg["app_mode"]
    elif _dev_cfg.get("local_dev", False):
        APP_MODE = "desktop"
    else:
        APP_MODE = "dev"
except Exception:
    APP_MODE = "dev"

# ── Authentication gate ───────────────────────────────────────────────────────

if not check_password(branding):
    st.stop()

render_sign_out_button()

# SUBSCRIPTION LOGIC START
# ── Live-mode plan resolution ─────────────────────────────────────────────────
# When APP_MODE is "live", the customer's plan is loaded from the backend store
# and written into session_state so all downstream feature gates see the correct
# entitlements.  In "dev" mode this block is skipped and the plan falls back to
# the licence-key / dev-override / "free" default set by init_session().
if APP_MODE == "live":
    customer_email = st.session_state.get("customer_email", "")
    if customer_email:
        set_plan_key(load_customer_plan_from_store(customer_email))

# ── Subscription panels ───────────────────────────────────────────────────────
# ---------------------------------------------
# SUBSCRIPTION UI ENTRY POINTS
# ---------------------------------------------
render_sidebar_subscription_panel()         # licence form · plan badge · run counter · upgrade CTAs
render_live_upgrade_banner()                # main-area nudge for free / starter users

# Derive routing keys used by upload capacity checks and legacy helpers.
account_tier   = st.session_state.get("account_tier", "Free")
user_plan      = get_plan_key()             # canonical plan key for all feature gates
tier_row_limit = row_limit_for(account_tier)
# SUBSCRIPTION LOGIC END

# ── App header ────────────────────────────────────────────────────────────────

render_header(branding)

with st.expander("View pricing plans", expanded=False):
    render_pricing_page()                   # full 5-tier interactive pricing table

# ── Step 1: Upload ────────────────────────────────────────────────────────────
# Capacity limits (rows + file size) are enforced here against user_plan.
# Users see upgrade prompts, not raw technical limits.

df = render_upload_panel(branding, tier_row_limit, tier_name=account_tier)

if df is not None:

    # ── Step 2: Configure ─────────────────────────────────────────────────────

    options = render_cleaning_options(branding)

    # ── Step 3: Preview ───────────────────────────────────────────────────────

    render_preview_panel(df, branding)

    # SUBSCRIPTION LOGIC START
    # ── Steps 4–7: Process → Dashboard → Insights → Download ─────────────────
    # Feature gates applied inside render_results_panel by user_plan:
    #   • Advanced dashboard & insights → can_view_advanced_insights
    #   • Excel download               → can_download_excel
    #   • PDF download                 → can_download_pdf
    #   • Custom branding              → can_brand_reports
    # Paywalls render only at the point of action, never during upload/preview.
    render_results_panel(df, options, user_plan, branding)
    # SUBSCRIPTION LOGIC END

# ── Page footer ───────────────────────────────────────────────────────────────

render_legal_notices(legal)
render_footer(branding)

"""ColtraDataAi — main Streamlit entry point.

This file is intentionally thin: it wires together the panel modules in
ui/ and delegates all rendering and business logic to them.  Do not add
data-processing or report-building code here.
"""
import streamlit as st
from PIL import Image

from config.branding_config import branding
from config.tier_config import row_limit_for
from core.feature_gate import render_tier_selector
from ui.branding_components import inject_app_css
from ui.homepage import check_password, render_header, render_footer
from ui.upload_panel import render_upload_panel
from ui.cleaning_options import render_cleaning_options
from ui.preview_panel import render_preview_panel
from ui.results_panel import render_results_panel
from utils.session_helpers import init_session

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

# ── Session + subscription init ──────────────────────────────────────────────
# SUBSCRIPTION LOGIC START
init_session()
# SUBSCRIPTION LOGIC END

# ── Authentication gate ───────────────────────────────────────────────────────

if not check_password(branding):
    st.stop()

# ── Sidebar: plan selector ────────────────────────────────────────────────────

account_tier   = render_tier_selector(branding)
tier_row_limit = row_limit_for(account_tier)

# ── App header ────────────────────────────────────────────────────────────────

render_header(branding)

# ── Step 1: Upload ────────────────────────────────────────────────────────────

df = render_upload_panel(branding, tier_row_limit, tier_name=account_tier)

if df is not None:

    # ── Step 2: Configure ─────────────────────────────────────────────────────

    options = render_cleaning_options(branding)

    # ── Step 3: Preview ───────────────────────────────────────────────────────

    render_preview_panel(df, branding)

    # ── Steps 4–7: Process → Dashboard → Insights → Download ─────────────────

    render_results_panel(df, options, account_tier, branding)

# ── Page footer ───────────────────────────────────────────────────────────────

render_footer(branding)

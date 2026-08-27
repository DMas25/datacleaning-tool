"""Live Demo — Streamlit page.

Accessible at /Live_Demo without requiring a password or subscription.
Delegates all rendering to ui/demo_panel.py.
"""
import streamlit as st

from config.branding_config import branding as BRAND

st.set_page_config(
    page_title="Live Demo · ColtraDataAi",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none; }
    [data-testid="stSidebar"]    { display: none; }
    #MainMenu                    { visibility: hidden; }
    footer                       { visibility: hidden; }
    header                       { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

from ui.demo_panel import render_demo_panel  # noqa: E402

# Capture affiliate ref on this public page so it carries into session state
# when the visitor navigates to the main app and clicks an upgrade button.
# Must run before render_demo_panel() so it is set before any CTA is rendered.
if not st.session_state.get("affiliate_ref"):
    _params = st.query_params
    st.session_state["affiliate_ref"] = (
        _params.get("aff")
        or _params.get("ref")
        or _params.get("affiliate")
        or ""
    )

render_demo_panel()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="text-align:center;padding:2rem 0 1rem 0;color:#9CA3AF;font-size:0.75rem;">
        <a href="/" style="color:{BRAND['primary_colour']};text-decoration:none;font-weight:600;">
            ← Back to ColtraDataAi
        </a>
        &nbsp;·&nbsp;
        <a href="/Free_Health_Check" style="color:{BRAND['primary_colour']};text-decoration:none;">
            Free Health Check
        </a>
        &nbsp;·&nbsp;
        <a href="/docs/privacy.html" style="color:#9CA3AF;text-decoration:none;">Privacy Policy</a>
        &nbsp;·&nbsp; {BRAND['legal_line']}
    </div>
    """,
    unsafe_allow_html=True,
)

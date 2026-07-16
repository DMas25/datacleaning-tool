"""Free Data Health Check — Streamlit page.

Accessible at /Free_Health_Check without requiring a password or subscription.
Delegates all rendering to ui/health_check_panel.py.
"""
import streamlit as st

from config.branding_config import branding as BRAND

st.set_page_config(
    page_title="Free Data Health Check · ColtraDataAi",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide the default Streamlit sidebar multipage navigation (cleaner standalone UX)
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

from ui.health_check_panel import render_health_check_panel  # noqa: E402

render_health_check_panel()

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="text-align:center;padding:2rem 0 1rem 0;color:#9CA3AF;font-size:0.75rem;">
        <a href="/" style="color:{BRAND['primary_colour']};text-decoration:none;font-weight:600;">
            ← Back to ColtraDataAi
        </a>
        &nbsp;·&nbsp;
        <a href="/docs/privacy.html" style="color:#9CA3AF;text-decoration:none;">Privacy Policy</a>
        &nbsp;·&nbsp; {BRAND['legal_line']}
    </div>
    """,
    unsafe_allow_html=True,
)

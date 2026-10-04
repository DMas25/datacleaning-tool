"""Enterprise API Docs - public Streamlit page.

Accessible at /API_Docs without requiring a password or subscription.
Delegates all rendering to ui/api_docs_page.py.
"""
import streamlit as st

from config.branding_config import branding as BRAND
from ui.api_docs_page import render_api_docs_page
from ui.branding_components import inject_app_css

st.set_page_config(
    page_title="Enterprise API Docs · ColtraDataAi",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_app_css(BRAND)

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

render_api_docs_page(BRAND)

primary = BRAND["primary_colour"]
contact = BRAND.get("contact_email", "support@coltradata.com")

st.markdown(
    f"""
    <div style="text-align:center;padding:1rem 0 2.5rem 0;font-size:0.73rem;color:#9CA3AF;">
        <a href="/" style="color:{primary};text-decoration:none;font-weight:600;">
            Back to ColtraDataAi
        </a>
        &nbsp;·&nbsp;
        <a href="/Pricing" style="color:{primary};text-decoration:none;">
            Plans and Pricing
        </a>
        &nbsp;·&nbsp;
        <a href="/Live_Demo" style="color:{primary};text-decoration:none;">
            Live Demo
        </a>
        &nbsp;·&nbsp;
        <a href="/Free_Health_Check" style="color:{primary};text-decoration:none;">
            Free Health Check
        </a>
        &nbsp;·&nbsp;
        <a href="mailto:{contact}" style="color:{primary};text-decoration:none;">
            {contact}
        </a>
        <br><br>
        {BRAND['legal_line']}
    </div>
    """,
    unsafe_allow_html=True,
)

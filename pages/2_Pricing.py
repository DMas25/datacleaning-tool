"""Pricing — public Streamlit page.

Accessible at /Pricing without requiring a password or subscription.
Shows the full pricing table with live LemonSqueezy checkout links.
"""
import streamlit as st

from config.branding_config import branding as BRAND
from ui.pricing_cards import render_pricing_cards
from ui.branding_components import inject_app_css

st.set_page_config(
    page_title="Plans & Pricing · ColtraDataAi",
    page_icon="💳",
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

primary = BRAND["primary_colour"]
contact = BRAND.get("contact_email", "support@coltradata.com")
app_url = "https://app.coltradata.com"

st.markdown(
    f"""
    <div style="text-align:center;padding:40px 0 8px 0;">
        <div style="font-size:2rem;font-weight:800;color:{primary};line-height:1.2;">
            Plans &amp; Pricing
        </div>
        <div style="font-size:1rem;color:#657286;margin-top:8px;max-width:500px;
                    margin-left:auto;margin-right:auto;line-height:1.6;">
            Choose the plan that fits your team. All plans include a free tier to get started.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_pricing_cards(current_plan_key="free")

st.markdown("<br>", unsafe_allow_html=True)

_, mid, _ = st.columns([1.5, 1, 1.5])
with mid:
    if st.button("Sign in / Get started →", use_container_width=True, type="primary", key="_pricing_signin"):
        st.switch_page("app.py")

st.markdown(
    f"""
    <div style="text-align:center;margin-top:1.5rem;padding-bottom:2rem;
                font-size:0.73rem;color:#9CA3AF;">
        &copy; 2026 {BRAND.get('company', 'Coltrane Ltd')} &nbsp;-&nbsp;
        <a href="mailto:{contact}" style="color:{primary};text-decoration:none;">{contact}</a>
        &nbsp;-&nbsp;
        <a href="{app_url}" style="color:{primary};text-decoration:none;">Back to app</a>
    </div>
    """,
    unsafe_allow_html=True,
)

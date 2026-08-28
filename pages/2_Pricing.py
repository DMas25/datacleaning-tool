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
        <div style="font-size:0.72rem;font-weight:700;letter-spacing:0.14em;
                    text-transform:uppercase;color:{primary};margin-bottom:10px;">
            Simple Pricing
        </div>
        <div style="font-size:2.2rem;font-weight:800;color:#1F4E79;line-height:1.2;">
            Start Free. Scale as You Grow.
        </div>
        <div style="font-size:0.88rem;color:#657286;margin-top:8px;">
            No hidden fees. Cancel anytime. Upgrade or downgrade whenever you need.
        </div>
        <div style="font-size:0.95rem;color:#374151;margin-top:18px;max-width:620px;
                    margin-left:auto;margin-right:auto;line-height:1.65;">
            From free data quality checks to enterprise-grade validation automation,
            ColtraDataAi helps organisations clean, standardise and trust their data
            before it drives business decisions.
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

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div style="
        background:linear-gradient(135deg,#EBF8F5 0%,#E0F4F8 100%);
        border:1.5px solid {primary};
        border-radius:14px;
        padding:1.4rem 1.8rem;
        max-width:560px;
        margin:0 auto 1.5rem auto;
        text-align:center;
    ">
        <div style="font-size:1rem;font-weight:700;color:#1F4E79;margin-bottom:4px;">
            Not ready to subscribe?
        </div>
        <div style="font-size:0.82rem;color:#4B5563;margin-bottom:0.8rem;">
            Start with a free data health check - no card required.
        </div>
        <div style="display:flex;flex-direction:column;align-items:center;
                    gap:4px;margin-bottom:0.9rem;">
            <span style="font-size:0.79rem;color:#374151;">&#10003; Upload a sample dataset</span>
            <span style="font-size:0.79rem;color:#374151;">&#10003; Receive a detailed quality report</span>
            <span style="font-size:0.79rem;color:#374151;">&#10003; Identify hidden errors and inconsistencies</span>
            <span style="font-size:0.79rem;color:#374151;">&#10003; No obligation, no card required</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

_, hc_col, _ = st.columns([2, 1, 2])
with hc_col:
    if st.button("Start Free Health Check", use_container_width=True, key="_pricing_hc_cta"):
        st.switch_page("pages/1_Free_Health_Check.py")

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

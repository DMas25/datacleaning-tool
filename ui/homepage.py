"""Login gate, app header and page footer rendering for ColtraDataAi."""
from __future__ import annotations

import base64
import os

import streamlit as st


def check_password(branding: dict) -> bool:
    """Return True if the user is authenticated, False otherwise.

    Renders the login form when not authenticated.  Does not call st.stop()
    — the caller is responsible for halting the app when False is returned.
    """
    if st.session_state.get("authenticated"):
        return True

    _inject_login_css(branding)
    _render_login_header(branding)

    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #DCE6EE;border-radius:16px;
                        box-shadow:0 4px 28px rgba(31,78,121,0.10);padding:2rem 2rem 1.6rem 2rem;
                        margin-top:0.5rem;">
                <div style="font-size:1.05rem;font-weight:700;color:{branding['primary_colour']};
                            margin-bottom:1.1rem;letter-spacing:0.01em;">
                    Sign in to continue
                </div>
            """,
            unsafe_allow_html=True,
        )
        pwd = st.text_input(
            "Password",
            type="password",
            label_visibility="collapsed",
            placeholder="Enter your password",
        )
        if st.button("Sign in", use_container_width=True, type="primary"):
            configured = _get_configured_password()
            if configured is None:
                st.error(
                    "No login password is configured. Add a [credentials] password "
                    "to .streamlit/secrets.toml (see .streamlit/secrets.toml.example)."
                )
            elif pwd == configured:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
        st.markdown(
            f"""
            <div style="margin-top:1rem;text-align:center;font-size:0.75rem;color:#9CA3AF;">
                Access restricted to authorised users only.
            </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    _render_login_features(branding)
    return False


def render_header(branding: dict) -> None:
    """Render the branded app header: logo | divider | tagline block."""
    logo_path = branding.get("logo_path", "assets/logo/coltradata_logo.png")
    logo_b64 = _encode_logo(logo_path)

    if logo_b64:
        img_tag = f'<img src="data:image/png;base64,{logo_b64}" style="width:234px;height:auto;display:block;flex-shrink:0;border:none;outline:none;" />'
    else:
        img_tag = f'<div style="font-size:1.4rem;font-weight:800;color:{branding["primary_colour"]};">{branding["app_name"]}</div>'

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:0;padding:32px 0 12px 0;">
            {img_tag}
            <div style="width:1.5px;height:68px;background:#C8D6DF;margin:0 22px;flex-shrink:0;align-self:center;"></div>
            <div style="display:flex;flex-direction:column;align-items:center;max-width:340px;">
                <h3 style="margin:0;color:{branding['primary_colour']};letter-spacing:1.5px;font-size:1.05em;text-align:center;white-space:nowrap;">
                    DATA &nbsp;&bull;&nbsp; INSIGHTS &nbsp;&bull;&nbsp; INTELLIGENCE
                </h3>
                <p style="margin:6px 0 0 0;color:#657286;font-size:0.82em;line-height:1.5;text-align:center;">
                    Generate Structured Cleaned Datasets,<br/>Validation Reports And Visual Data Summaries.
                </p>
            </div>
        </div>
        <hr style="margin:0 0 16px 0;border:none;border-top:1px solid #E6ECF0;" />
        """,
        unsafe_allow_html=True,
    )


def render_footer(branding: dict) -> None:
    """Render the branded page footer with contact link and disclaimer."""
    st.markdown(
        f"""
        <div style="margin-top:3rem;padding:20px 0 8px 0;border-top:1px solid #E6ECF0;text-align:center;">
            <div style="font-size:0.875rem;color:#657286;margin-bottom:10px;">
                <strong style="color:{branding['primary_colour']};">{branding['app_name']}</strong>
                &nbsp;&nbsp;|&nbsp;&nbsp;
                Structured Data Cleaning, Validation &amp; Reporting
                &nbsp;&nbsp;|&nbsp;&nbsp;
                <a href="mailto:{branding['contact_email']}"
                   style="color:{branding['primary_colour']};text-decoration:none;">
                   {branding['contact_email']}
                </a>
            </div>
            <div style="font-size:0.75rem;color:#9CA3AF;max-width:740px;margin:0 auto;line-height:1.65;">
                This tool performs automated data cleaning and structuring only. It does not provide
                legal, financial, tax, or compliance advice. Users remain responsible for reviewing
                all outputs and obtaining professional guidance where required.
                &copy; 2026 {branding.get('company', 'Coltrane Ltd')}. All rights reserved.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _inject_login_css(branding: dict) -> None:
    primary = branding["primary_colour"]
    st.markdown(
        f"""
        <style>
            /* Hide sidebar on the login page */
            [data-testid="stSidebar"] {{ display: none !important; }}
            [data-testid="collapsedControl"] {{ display: none !important; }}

            /* Remove the app-wide left border from column containers on login */
            [data-testid="stVerticalBlockBorderWrapper"] {{
                border-left: none !important;
                border: none !important;
                box-shadow: none !important;
                background: transparent !important;
                border-radius: 0 !important;
                margin-bottom: 0 !important;
            }}

            /* Tighten the top padding on the login page */
            .block-container {{
                padding-top: 0 !important;
                max-width: 860px !important;
                margin: 0 auto !important;
            }}

            /* Style the sign-in button */
            .stButton > button {{
                border-radius: 10px;
                height: 46px;
                background-color: {primary};
                color: white;
                font-weight: 600;
                border: none;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_login_header(branding: dict) -> None:
    primary = branding["primary_colour"]
    logo_path = branding.get("logo_path", "assets/logo/coltradata_logo.png")
    logo_b64 = _encode_logo(logo_path)

    if logo_b64:
        brand_html = (
            f'<img src="data:image/png;base64,{logo_b64}" '
            f'style="height:52px;width:auto;display:block;margin:0 auto 8px auto;" />'
        )
    else:
        brand_html = (
            f'<div style="font-size:2.4rem;font-weight:800;color:{primary};'
            f'letter-spacing:-0.5px;line-height:1;">{branding["app_name"]}</div>'
        )

    st.markdown(
        f"""
        <div style="text-align:center;padding:56px 0 32px 0;">
            {brand_html}
            <div style="font-size:11.5px;letter-spacing:.28em;color:#657286;
                        text-transform:uppercase;margin-top:10px;">
                {branding['tagline']}
            </div>
            <div style="font-size:0.87rem;color:#657286;margin-top:10px;line-height:1.6;">
                Structured data cleaning, validation reports &amp; visual summaries —<br/>
                built for teams who need clean data, fast.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_login_features(branding: dict) -> None:
    primary = branding["primary_colour"]
    features = [
        ("📂", "Upload any CSV or Excel", "Handles messy real-world files with missing values, duplicates, and mixed types."),
        ("✅", "Instant cleaning & validation", "Automated rules detect and fix common data quality issues in seconds."),
        ("📊", "Reports & visual summaries", "Export cleaned datasets with PDF validation reports and chart galleries."),
    ]
    cols = st.columns(3)
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(
                f"""
                <div style="background:#FFFFFF;border:1px solid #E6ECF0;border-radius:14px;
                            padding:1.4rem 1.2rem;text-align:center;margin-top:1.6rem;
                            box-shadow:0 2px 10px rgba(0,0,0,0.04);">
                    <div style="font-size:1.7rem;margin-bottom:0.55rem;">{icon}</div>
                    <div style="font-size:0.9rem;font-weight:700;color:{primary};
                                margin-bottom:0.4rem;">{title}</div>
                    <div style="font-size:0.78rem;color:#657286;line-height:1.55;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown(
        f"""
        <div style="text-align:center;margin-top:2.8rem;font-size:0.73rem;color:#9CA3AF;">
            &copy; 2026 {branding.get('company', 'Coltrane Ltd')} &nbsp;&mdash;&nbsp;
            <a href="mailto:{branding['contact_email']}"
               style="color:{primary};text-decoration:none;">{branding['contact_email']}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _get_configured_password() -> str | None:
    try:
        return st.secrets["credentials"]["password"]
    except (KeyError, st.errors.StreamlitSecretNotFoundError):
        return None


def _encode_logo(logo_path: str) -> str:
    """Return base64-encoded logo string, or empty string if file not found."""
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

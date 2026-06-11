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

    _render_login_header(branding)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("##### Sign in to continue")
        pwd = st.text_input(
            "Password",
            type="password",
            label_visibility="collapsed",
            placeholder="Enter password",
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

def _render_login_header(branding: dict) -> None:
    st.markdown(
        f"""
        <div style="max-width:420px;margin:80px auto 0 auto;text-align:center;">
            <div style="font-size:38px;font-weight:800;color:{branding['primary_colour']};margin-bottom:4px;">
                {branding['app_name']}
            </div>
            <div style="font-size:12px;letter-spacing:.26em;color:#657286;text-transform:uppercase;margin-bottom:36px;">
                {branding['tagline']}
            </div>
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

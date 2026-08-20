"""Branded Streamlit HTML/CSS components for ColtraDataAi.

This is the canonical location for all reusable UI primitives.
``core/ui_components.py`` re-exports from here for backward compatibility.
"""
from __future__ import annotations

from typing import List, Tuple

import streamlit as st


def inject_og_meta_tags(branding: dict) -> None:
    """Best-effort override of Streamlit's default social meta tags.

    Crawlers that execute JavaScript (Google, Bing) will pick these up.
    LinkedIn's OGP scraper is server-side only — the reliable fix for
    LinkedIn previews is a proxy page at coltradata.com with proper
    og:tags that redirects to app.coltradata.com.
    """
    app_name = branding.get("app_name", "ColtraDataAi")
    description = (
        "Turn spreadsheets into boardroom-ready insights - "
        "spend less time preparing data and more time making decisions."
    )
    st.markdown(
        f"""
        <script>
        (function() {{
            var tags = [
                ['property', 'og:title',       '{app_name}'],
                ['property', 'og:description', '{description}'],
                ['property', 'og:site_name',   '{app_name}'],
                ['property', 'og:type',        'website'],
                ['property', 'og:url',         'https://app.coltradata.com'],
                ['name',     'twitter:card',   'summary'],
                ['name',     'twitter:title',  '{app_name}'],
                ['name',     'twitter:description', '{description}'],
                ['name',     'description',    '{description}'],
            ];
            tags.forEach(function(t) {{
                var sel = 'meta[' + t[0] + '="' + t[1] + '"]';
                var el = document.querySelector(sel);
                if (el) {{
                    el.setAttribute('content', t[2]);
                }} else {{
                    var m = document.createElement('meta');
                    m.setAttribute(t[0], t[1]);
                    m.setAttribute('content', t[2]);
                    document.head.appendChild(m);
                }}
            }});
        }})();
        </script>
        """,
        unsafe_allow_html=True,
    )


def inject_app_css(branding: dict) -> None:
    """Inject the full application CSS into the Streamlit page."""
    primary = branding["primary_colour"]
    accent  = branding.get("accent_colour", primary)
    st.markdown(
        f"""
        <style>
            /* ── Hide Streamlit chrome ───────────────────────────────── */
            #MainMenu {{visibility: hidden;}}
            header {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            [data-testid="stHeader"] {{display: none !important;}}
            [data-testid="stToolbar"] {{visibility: hidden;}}
            [data-testid="stDecoration"] {{display: none;}}
            [data-testid="stStatusWidget"] {{visibility: hidden;}}
            [data-testid="stSidebarNav"] {{display: none !important;}}
            .stDeployButton {{display: none;}}

            /* ── Layout ─────────────────────────────────────────────── */
            .block-container {{
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }}

            /* ── Section card — primary content container ────────────── */
            .section-card {{
                background: #FFFFFF;
                padding: 1.3rem 1.4rem;
                border-radius: 14px;
                border: 1px solid #E6ECF0;
                border-left: 4px solid {primary};
                box-shadow: 0 2px 10px rgba(0,0,0,0.04);
                margin-bottom: 1rem;
            }}

            /* ── Metric card ─────────────────────────────────────────── */
            .metric-card {{
                background: white;
                padding: 0.9rem 1rem;
                border-radius: 12px;
                border: 1px solid #E6ECF0;
                box-shadow: 0 2px 6px rgba(0,0,0,0.04);
                text-align: center;
            }}

            /* ── KPI typography ──────────────────────────────────────── */
            .kpi-value {{
                font-size: 1.5rem;
                font-weight: 800;
                color: {primary};
                line-height: 1.2;
            }}
            .kpi-label {{
                font-size: 0.72rem;
                color: #657286;
                text-transform: uppercase;
                letter-spacing: 0.07em;
                margin-top: 5px;
            }}

            /* ── Primary action button ───────────────────────────────── */
            .stButton > button {{
                width: 100%;
                border-radius: 10px;
                height: 46px;
                background-color: {primary};
                color: white;
                font-weight: 600;
                border: none;
                transition: opacity 0.15s ease;
            }}
            .stButton > button:hover {{
                opacity: 0.88;
            }}

            /* ── Download button ─────────────────────────────────────── */
            .stDownloadButton > button {{
                width: 100%;
                border-radius: 10px;
                height: 46px;
                background-color: {accent};
                color: white;
                font-weight: 600;
                border: none;
                transition: opacity 0.15s ease;
            }}
            .stDownloadButton > button:hover {{
                opacity: 0.88;
            }}

            /* ── Expander — must not inherit primary button style ──────── */
            [data-testid="stExpander"] summary,
            [data-testid="stExpander"] summary:hover,
            [data-testid="stExpander"] summary button,
            [data-testid="stExpander"] summary button:hover {{
                background-color: transparent !important;
                color: inherit !important;
                height: auto !important;
                border-radius: 0 !important;
                font-weight: 600 !important;
                border: none !important;
                box-shadow: none !important;
                opacity: 1 !important;
            }}

            /* ── Streamlit bordered container — section-card styling ───── */
            [data-testid="stVerticalBlockBorderWrapper"] {{
                border-radius: 14px !important;
                border: 1px solid #E6ECF0 !important;
                border-left: 4px solid {primary} !important;
                box-shadow: 0 2px 10px rgba(0,0,0,0.04) !important;
                margin-bottom: 1rem !important;
                background: #FFFFFF !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_step_header(step: int, title: str, subtitle: str = "", branding: dict = None) -> None:
    """Numbered circular-badge step header with optional subtitle caption."""
    primary = branding["primary_colour"] if branding else "#1F4E79"
    sub_html = (
        f'<span style="display:block;font-size:0.83rem;color:#657286;margin-top:3px;line-height:1.4;">{subtitle}</span>'
        if subtitle else ""
    )
    # Use <span> for all inner elements — Streamlit 1.57's markdown parser treats
    # nested <div> closing tags as block boundaries and emits extras as literal text.
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:13px;margin:1.1rem 0 0.35rem 0;">'
        f'<span style="min-width:30px;height:30px;border-radius:50%;background:{primary};color:white;'
        f'font-weight:700;font-size:13px;display:inline-flex;align-items:center;justify-content:center;'
        f'flex-shrink:0;box-shadow:0 2px 6px rgba(31,78,121,0.25);">{step}</span>'
        f'<span style="padding-top:3px;display:inline-block;">'
        f'<span style="font-size:1.05rem;font-weight:700;color:{primary};line-height:1.3;display:block;">{title}</span>'
        f'{sub_html}</span></div>',
        unsafe_allow_html=True,
    )


def render_kpi_row(metrics: List[Tuple[str, str]], branding: dict = None) -> None:
    """Horizontal row of branded KPI metric cards."""
    primary = branding["primary_colour"] if branding else "#1F4E79"
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<span class="kpi-value" style="color:{primary};display:block;">{value}</span>'
                f'<span class="kpi-label" style="display:block;">{label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_risk_kpi(risk_level: str) -> None:
    """Single KPI card coloured by risk level — High / Medium / Low."""
    colour_map = {"High": "#DC2626", "Medium": "#D97706", "Low": "#16A34A"}
    bg_map     = {"High": "#FEF2F2", "Medium": "#FFFBEB", "Low": "#F0FDF4"}
    border_map = {"High": "#FECACA", "Medium": "#FDE68A", "Low": "#BBF7D0"}
    c = colour_map.get(risk_level, "#657286")
    b = bg_map.get(risk_level, "#F9FAFB")
    e = border_map.get(risk_level, "#E6ECF0")
    st.markdown(
        f'<div style="background:{b};border:1px solid {e};border-radius:12px;padding:0.9rem 1rem;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
        f'<span style="font-size:1.4rem;font-weight:800;color:{c};line-height:1.2;display:block;">{risk_level}</span>'
        f'<span style="font-size:0.72rem;color:{c};text-transform:uppercase;letter-spacing:0.07em;margin-top:5px;opacity:0.75;display:block;">Overall Risk</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_section_divider(label: str = "", branding: dict = None) -> None:
    """Decorative labelled divider separating major dashboard sections."""
    primary = branding["primary_colour"] if branding else "#1F4E79"
    if label:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin:1.4rem 0 0.7rem 0;">'
            f'<span style="height:1px;flex:1;background:#E6ECF0;display:inline-block;"></span>'
            f'<span style="font-size:0.73rem;font-weight:700;color:{primary};text-transform:uppercase;letter-spacing:0.11em;">{label}</span>'
            f'<span style="height:1px;flex:1;background:#E6ECF0;display:inline-block;"></span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<hr style="margin:1rem 0;border:none;border-top:1px solid #E6ECF0;" />',
            unsafe_allow_html=True,
        )


def render_chart_section_header(title: str, caption: str = "", branding: dict = None) -> None:
    """Compact section label above individual chart cards."""
    primary = branding["primary_colour"] if branding else "#1F4E79"
    cap_html = (
        f'<span style="display:block;margin:2px 0 0 0;color:#657286;font-size:0.8rem;">{caption}</span>'
        if caption else ""
    )
    st.markdown(
        f'<div style="margin-bottom:0.4rem;">'
        f'<span style="font-size:0.95rem;font-weight:700;color:{primary};">{title}</span>'
        f'{cap_html}</div>',
        unsafe_allow_html=True,
    )

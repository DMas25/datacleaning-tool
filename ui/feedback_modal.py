"""Post-run feedback modal — Likert satisfaction survey + NPS recommendation score.

Triggered from app.py after a user has completed 3 or more lifetime cleaning runs.
Suppression: snooze (7 days) or permanent opt-out, both stored in signal_log.
"""
from __future__ import annotations

import streamlit as st

from config.branding_config import branding as _branding

_EASE_OPTIONS = [
    "1 — Very difficult",
    "2 — Difficult",
    "3 — OK",
    "4 — Easy",
    "5 — Very easy",
]
_QUALITY_OPTIONS = [
    "1 — Poor",
    "2 — Below average",
    "3 — Average",
    "4 — Good",
    "5 — Excellent",
]
_OVERALL_OPTIONS = [
    "1 — Very dissatisfied",
    "2 — Dissatisfied",
    "3 — Neutral",
    "4 — Satisfied",
    "5 — Very satisfied",
]


def _score(option: str) -> int:
    return int(option[0])


@st.dialog("How are we doing?", width="large")
def show_feedback_modal(email: str) -> None:
    from services.feedback_service import save_feedback, snooze_feedback, suppress_feedback

    primary = _branding.get("primary_colour", "#1F4E79")
    store_url = "https://coltradataai.lemonsqueezy.com/"

    st.markdown(
        "<p style='color:#657286;font-size:0.85rem;margin-bottom:0.25rem;'>"
        "Takes 30 seconds — your answers help us make ColtraDataAi better for everyone."
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown("**1. How easy was it to use ColtraDataAi?**")
    ease_raw = st.select_slider(
        "Ease of use",
        options=_EASE_OPTIONS,
        value="3 — OK",
        label_visibility="collapsed",
        key="_fb_ease",
    )

    st.markdown("**2. How would you rate the quality of the cleaned data?**")
    quality_raw = st.select_slider(
        "Data quality",
        options=_QUALITY_OPTIONS,
        value="3 — Average",
        label_visibility="collapsed",
        key="_fb_quality",
    )

    st.markdown("**3. Overall, how satisfied are you with ColtraDataAi?**")
    overall_raw = st.select_slider(
        "Overall satisfaction",
        options=_OVERALL_OPTIONS,
        value="3 — Neutral",
        label_visibility="collapsed",
        key="_fb_overall",
    )

    st.markdown("---")
    st.markdown("**4. How likely are you to recommend ColtraDataAi to a colleague?**")
    st.caption("0 = Not at all likely &nbsp;·&nbsp; 10 = Extremely likely")
    nps = st.select_slider(
        "NPS",
        options=list(range(11)),
        value=7,
        label_visibility="collapsed",
        key="_fb_nps",
    )

    st.markdown("---")
    comment = st.text_area(
        "Anything we can improve? *(optional)*",
        placeholder="Tell us what worked well or what could be better…",
        max_chars=500,
        key="_fb_comment",
    )

    col_submit, col_later, col_never = st.columns([2, 1.2, 1.2])
    with col_submit:
        if st.button("Submit feedback", type="primary", use_container_width=True):
            save_feedback(
                email,
                ease_score=_score(ease_raw),
                quality_score=_score(quality_raw),
                overall_score=_score(overall_raw),
                nps_score=nps,
                comment=comment,
            )
            st.success(
                "Thank you — we really appreciate it! "
                "If you know a colleague who struggles with messy data, "
                "feel free to share ColtraDataAi with them."
            )
            st.markdown(
                f"<div style='text-align:center;margin-top:0.5rem;'>"
                f"<a href='{store_url}' target='_blank' "
                f"style='font-size:0.82rem;color:{primary};text-decoration:none;font-weight:600;'>"
                f"Share ColtraDataAi →</a></div>",
                unsafe_allow_html=True,
            )
    with col_later:
        if st.button("Remind me later", use_container_width=True):
            snooze_feedback(email)
            st.rerun()
    with col_never:
        if st.button("Don't ask again", use_container_width=True):
            suppress_feedback(email)
            st.rerun()

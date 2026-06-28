"""Client-facing "app is down" page shown when an unhandled fault is caught.

Replaces the default Streamlit stack trace with a branded, reassuring
message, an incident id support can look up in logs/faults.jsonl, and
three recovery actions: retry in place, a full session reset, or
filing a short report tied to the incident.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

from core.fault_monitor import reset_volatile_session_state

_REPORTS_PATH = Path("logs/user_reports.jsonl")


def render_down_page(branding: dict, incident_id: str) -> None:
    primary = branding.get("primary_colour", "#2563EB")
    app_name = branding.get("app_name", "ColtraDataAi")
    trace_id = st.session_state.get("trace_id", "unknown")

    st.markdown(
        f"""
        <div class="section-card" style="border-left-color:{primary}; text-align:center; padding:2.5rem 1.5rem;">
            <h2 style="margin-bottom:0.5rem;">We hit a snag</h2>
            <p style="color:#5B6B79; font-size:1.05rem; max-width:520px; margin:0 auto 1rem auto;">
                {app_name} ran into an unexpected problem. Our team has already
                been notified and is on it — please try again in a few minutes.
            </p>
            <p style="color:#9AA7B1; font-size:0.85rem;">
                Reference code: <code>{incident_id}</code>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Try again", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("Reset session", use_container_width=True):
            reset_volatile_session_state()
            st.rerun()

    with col3:
        report_open = st.toggle("Report issue", key="_show_report_form")

    if report_open:
        with st.form("incident_report_form", clear_on_submit=True):
            st.caption(f"Incident `{incident_id}` · trace `{trace_id}`")
            description = st.text_area(
                "What were you doing when this happened?",
                placeholder="e.g. uploading a 50k-row CSV and clicking Generate Report",
            )
            submitted = st.form_submit_button("Send report")
            if submitted:
                _save_report(incident_id, trace_id, description)
                st.success("Thanks — your report has been logged against this incident.")


def render_safe_mode_page(branding: dict, status: dict) -> None:
    """
    Minimal fallback UI shown instead of the full app while safe mode
    is active (see core/safe_mode.py). Deliberately renders nothing
    that touches uploads, processing, or report generation — just a
    status message — since safe mode exists precisely because one of
    those heavier code paths is the thing that's been failing.

    *status* is core.safe_mode.get_safe_mode_status() — the same dict
    ui/fault_dashboard.py reads, so the reason and timestamp shown here
    always match what an admin sees on the dashboard.
    """
    app_name = branding.get("app_name", "ColtraDataAi")
    st.warning(
        f"**{app_name} is running in safe mode** due to repeated errors. "
        "Core processing features are temporarily disabled while we look into it.",
        icon="🛟",
    )
    st.caption(f"Reason: {status.get('reason') or 'unknown'} · since {status.get('activated_at') or 'unknown'}")
    if st.button("Check again"):
        st.rerun()


def _save_report(incident_id: str, trace_id: str, description: str) -> None:
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "incident_id": incident_id,
        "trace_id": trace_id,
        "description": description,
    }
    try:
        _REPORTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _REPORTS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass

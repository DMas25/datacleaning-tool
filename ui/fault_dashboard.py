"""Admin fault/observability dashboard for ColtraDataAi.

Reads logs/faults.jsonl directly (no database) and renders the
operational summary an on-call person actually wants: how much is
breaking, what kind, where, and is it getting worse. Gated behind an
admin password in app.py — never linked from anywhere a client could find it.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from core.health_check import get_health_status
from core.safe_mode import get_safe_mode_status

_FAULT_LOG_PATH = Path("logs/faults.jsonl")

_DISPLAY_COLUMNS = [
    "timestamp", "incident_id", "trace_id", "fingerprint", "severity",
    "component", "error_type", "message", "recovery_action", "recovery_success",
]


def _load_faults() -> pd.DataFrame:
    """Loads the live fault log into a DataFrame. Archived/rotated days
    under logs/archive/ are intentionally excluded — this dashboard is
    about recent operational health, not long-term log search."""
    if not _FAULT_LOG_PATH.exists():
        return pd.DataFrame(columns=_DISPLAY_COLUMNS)

    rows = []
    with _FAULT_LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        return pd.DataFrame(columns=_DISPLAY_COLUMNS)

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp"])
    return df


def render_fault_dashboard() -> None:
    st.title("Fault dashboard")

    # ── Safe mode banner ─────────────────────────────────────────────────────────
    # Reads the exact same status dict app.py's client-facing safe-mode page
    # reads, so the reason/timestamp here can never drift from what a client
    # currently sees.
    safe_mode = get_safe_mode_status()
    if safe_mode["active"]:
        st.error(f"🛟 SAFE MODE ACTIVE — {safe_mode['reason']} (since {safe_mode['activated_at']})")

    health = get_health_status()
    status_emoji = {"ok": "🟢", "degraded": "🟠", "down": "🔴"}.get(health["status"], "⚪")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", f"{status_emoji} {health['status']}")
    c2.metric("Error rate (per min, last 15m)", health["error_rate"])
    c3.metric("Uptime", _format_duration(health["uptime_seconds"]))
    c4.metric("Last critical error", health["last_critical_error_time"] or "—")

    df = _load_faults()
    if df.empty:
        st.info("No faults recorded yet.")
        return

    now = datetime.now(timezone.utc)
    last_10m = df[df["timestamp"] >= now - timedelta(minutes=10)]
    last_24h = df[df["timestamp"] >= now - timedelta(hours=24)]
    last_7d = df[df["timestamp"] >= now - timedelta(days=7)]

    c1, c2 = st.columns(2)
    c1.metric("Total faults (24h)", len(last_24h))
    c2.metric("Total faults (7d)", len(last_7d))

    st.subheader("Faults by severity")
    st.bar_chart(last_7d["severity"].value_counts())

    st.subheader("Top error types")
    st.bar_chart(last_7d["error_type"].value_counts().head(10))

    st.subheader("Top failing components")
    st.bar_chart(last_7d["component"].value_counts().head(10))

    st.subheader("Active incidents (last 10 minutes)")
    if last_10m.empty:
        st.success("No faults in the last 10 minutes.")
    else:
        active = (
            last_10m.groupby("fingerprint")
            .agg(
                component=("component", "first"),
                error_type=("error_type", "first"),
                severity=("severity", "first"),
                occurrences=("incident_id", "count"),
                first_seen=("timestamp", "min"),
                last_seen=("timestamp", "max"),
            )
            .reset_index()
            .sort_values("occurrences", ascending=False)
        )
        st.dataframe(active, use_container_width=True, hide_index=True)

    st.subheader("Error frequency per fingerprint (last 7 days)")
    if "fingerprint" in last_7d.columns:
        fp_freq = last_7d["fingerprint"].value_counts().head(15)
        st.bar_chart(fp_freq)

        st.caption("Time between first and last occurrence per fingerprint (last 7 days)")
        span = (
            last_7d.groupby("fingerprint")["timestamp"]
            .agg(first_seen="min", last_seen="max")
            .reset_index()
        )
        span["span_minutes"] = (span["last_seen"] - span["first_seen"]).dt.total_seconds() / 60
        span = span.merge(
            last_7d.groupby("fingerprint")
            .agg(component=("component", "first"), error_type=("error_type", "first"), occurrences=("incident_id", "count"))
            .reset_index(),
            on="fingerprint",
        )
        span = span.sort_values("occurrences", ascending=False).head(15)
        st.dataframe(
            span[["fingerprint", "component", "error_type", "occurrences", "first_seen", "last_seen", "span_minutes"]],
            use_container_width=True, hide_index=True,
        )

    st.subheader("Error trend (hourly, last 7 days)")
    trend = last_7d.set_index("timestamp").resample("1h").size().rename("faults")
    st.line_chart(trend)

    st.subheader("Recovery outcomes")
    recovery_df = df[df["recovery_success"].notna()] if "recovery_success" in df.columns else pd.DataFrame()
    if recovery_df.empty:
        st.caption("No recovery attempts logged yet.")
    else:
        rc1, rc2 = st.columns(2)
        rc1.metric("Recovered automatically", int(recovery_df["recovery_success"].sum()))
        rc2.metric("Recovery failed", int((~recovery_df["recovery_success"].astype(bool)).sum()))

    st.subheader("Recent incidents")
    display_cols = [c for c in _DISPLAY_COLUMNS if c in df.columns]
    recent = df.sort_values("timestamp", ascending=False).head(50)[display_cols]
    st.dataframe(recent, use_container_width=True, hide_index=True)


def _format_duration(seconds: float) -> str:
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

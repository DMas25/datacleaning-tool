"""Admin internal-analytics dashboard for ColtraDataAi.

Aggregated, anonymised subscriber telemetry (industry/profession/position
mix, conversion timing, tenure, feature usage) plus an AI-generated
strategic narrative — for Coltrane Ltd's own decision-making, never shown
to customers. Gated behind an admin password in app.py.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.ai_advisor import generate_internal_insights
from services.licence_manager import get_usage_analytics


def render_internal_insights_dashboard() -> None:
    st.title("Internal Insights & Usage Analytics")
    st.caption("Aggregated, anonymised subscriber data — no names, internal use only.")

    stats = get_usage_analytics()

    col1, col2, col3 = st.columns(3)
    col1.metric("Active subscribers", f"{stats['active_subscribers']:,}")
    col2.metric(
        "Median conversion time",
        f"{stats['median_conversion_days']:.1f} days" if stats["median_conversion_days"] is not None else "—",
    )
    col3.metric(
        "Median tenure",
        f"{stats['median_tenure_days']:.1f} days" if stats["median_tenure_days"] is not None else "—",
    )

    st.divider()

    chart_cols = st.columns(2)
    _render_breakdown_chart(chart_cols[0], "Industry mix", stats["industry_breakdown"])
    _render_breakdown_chart(chart_cols[1], "Profession mix", stats["profession_breakdown"])

    chart_cols2 = st.columns(2)
    _render_breakdown_chart(chart_cols2[0], "Position in organisation", stats["position_breakdown"])
    _render_breakdown_chart(chart_cols2[1], "Plan distribution", stats["plan_breakdown"])

    st.divider()
    _render_breakdown_chart(st, "Feature usage (event counts)", stats["feature_usage_breakdown"])

    if stats["runs_last_30_days"]:
        st.subheader("Report runs — last 30 days")
        trend_df = pd.DataFrame(
            {"day": list(stats["runs_last_30_days"].keys()), "runs": list(stats["runs_last_30_days"].values())}
        )
        st.plotly_chart(px.bar(trend_df, x="day", y="runs"), use_container_width=True)

    st.divider()
    st.subheader("AI Strategic Narrative")

    if stats["active_subscribers"] == 0:
        st.info("No subscriber data yet — narrative will populate once licences are activated and used.")
        return

    with st.spinner("Generating strategic insights…"):
        narrative = generate_internal_insights(stats)

    if narrative:
        st.markdown(narrative)
    else:
        st.warning("AI insights unavailable — check the Anthropic API key configuration.")


def _render_breakdown_chart(container, title: str, breakdown: dict) -> None:
    container.markdown(f"**{title}**")
    if not breakdown:
        container.caption("No data yet.")
        return
    df = pd.DataFrame({"category": list(breakdown.keys()), "count": list(breakdown.values())})
    container.plotly_chart(px.pie(df, names="category", values="count", hole=0.4), use_container_width=True)

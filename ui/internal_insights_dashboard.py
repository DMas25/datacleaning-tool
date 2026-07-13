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
from services.licence_manager_pg import (
    get_usage_analytics,
    get_prompt_effectiveness,
    classify_signal_effectiveness,
    get_conversion_funnel,
    PROMPT_ATTRIBUTION_WINDOW_DAYS,
    WVRS_WINDOW_MINUTES,
)


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
    st.subheader("Prompt Effectiveness Score")
    st.caption(
        "Per signal: conversions / impressions, where a conversion is a paid-plan webhook "
        f"event for the same email within {PROMPT_ATTRIBUTION_WINDOW_DAYS} days of that signal "
        "being shown. Email + time-window attribution, not a guaranteed causal link."
    )
    effectiveness = get_prompt_effectiveness()
    recommendations = classify_signal_effectiveness(effectiveness)
    if recommendations:
        rec_df = pd.DataFrame(
            [
                {
                    "signal": r["signal"],
                    "impressions": r["impressions"],
                    "conversions": r["conversions"],
                    "score (%)": round(r["score"] * 100, 2) if r["score"] is not None else None,
                    "class": r["class"],
                    "action": r["action"],
                    "reason": r["reason"],
                }
                for r in recommendations
            ]
        )
        st.dataframe(rec_df, use_container_width=True, hide_index=True)
        st.caption(
            "Ranked by score, then volume. `class`/`action`/`reason` come from "
            "classify_signal_effectiveness() — thresholds, not a guess; signals below "
            "the impression confidence floor are always 'Maintain' regardless of score."
        )
    else:
        st.caption("No signal impressions logged yet.")

    st.subheader("A/B Variant Performance")
    st.caption(
        "Per-variant breakdown within each signal — same attribution rules as above, just "
        "split by which copy variant was actually shown (services.upgrade_messaging "
        "assigns variants per-user, stable per signal, via a hash of email+signal)."
    )
    variant_rows = [
        {
            "signal": signal,
            "variant": variant,
            "impressions": v["impressions"],
            "conversions": v["conversions"],
            "score (%)": round(v["score"] * 100, 2) if v["score"] is not None else None,
        }
        for signal, s in effectiveness.items()
        for variant, v in s["variants"].items()
    ]
    if variant_rows:
        variant_df = pd.DataFrame(variant_rows).sort_values(
            ["signal", "score (%)"], ascending=[True, False]
        )
        st.dataframe(variant_df, use_container_width=True, hide_index=True)
    else:
        st.caption("No variant impressions logged yet.")

    st.divider()
    st.subheader("Conversion Funnel — WVRS → Revenue")
    funnel = get_conversion_funnel()
    st.caption(
        f"WVRS = a run followed by export/AI-advisory for the same user within "
        f"{WVRS_WINDOW_MINUTES} minutes (same-session proxy, computed retrospectively). "
        f"Conversion attribution uses the same {PROMPT_ATTRIBUTION_WINDOW_DAYS}-day "
        "email+time-window rule as Prompt Effectiveness above — directional, not exact."
    )
    funnel_df = pd.DataFrame(
        [
            {"stage": "Activated (ran ≥1 dataset)", "count": funnel["activated_users"]},
            {"stage": "Engaged (total runs)", "count": funnel["total_runs"]},
            {"stage": "WVRS (value-realised runs)", "count": funnel["wvrs_count"]},
            {"stage": "Prompted (users shown a signal)", "count": funnel["prompted_users"]},
            {"stage": "Converted (any plan upgrade)", "count": funnel["converted_users"]},
            {"stage": "— attributed to a prompt", "count": funnel["attributed_converted_users"]},
            {"stage": "— unattributed (no matching prompt)", "count": funnel["unattributed_converted_users"]},
        ]
    )
    st.dataframe(funnel_df, use_container_width=True, hide_index=True)

    rev1, rev2, rev3 = st.columns(3)
    rev1.metric("WVRS rate (WVRS / runs)", f"{funnel['wvrs_rate']:.1%}" if funnel["wvrs_rate"] is not None else "—")
    rev2.metric("Attributed monthly revenue", f"£{funnel['attributed_monthly_revenue']:,.2f}")
    rev3.metric("Total monthly revenue (converted users)", f"£{funnel['total_monthly_revenue']:,.2f}")

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

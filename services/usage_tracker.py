"""
Session-scoped run counter. Counts resets each calendar month.
Replace st.session_state storage with a database call once auth is wired up.
"""
from datetime import date

import streamlit as st

from config.plans import get_plan


def _month_key() -> str:
    return f"runs_{date.today().strftime('%Y-%m')}"


def get_runs_this_month() -> int:
    return st.session_state.get(_month_key(), 0)


def increment_run() -> None:
    key = _month_key()
    st.session_state[key] = st.session_state.get(key, 0) + 1


def runs_remaining(plan_key: str) -> int | None:
    """None means unlimited (enterprise). Otherwise returns remaining runs >= 0."""
    limit = get_plan(plan_key)["monthly_runs"]
    if limit is None:
        return None
    return max(0, limit - get_runs_this_month())


def can_run(plan_key: str) -> bool:
    remaining = runs_remaining(plan_key)
    return remaining is None or remaining > 0


def usage_summary(plan_key: str) -> str:
    plan = get_plan(plan_key)
    limit = plan["monthly_runs"]
    used = get_runs_this_month()
    if limit is None:
        return f"{used} runs this month (unlimited)"
    return f"{used} / {limit} runs used this month"

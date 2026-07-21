"""
Run counter — persistent per-subscriber via Supabase run_counts table.
Falls back to session state for unauthenticated (email-less) sessions.
"""
from datetime import date

import streamlit as st

from config.plans import get_plan
from utils.session_helpers import get_user_email


def _month_key() -> str:
    return date.today().strftime("%Y-%m")


def _db_get_runs(email: str) -> int:
    try:
        from services.licence_manager_pg import get_runs
        return get_runs(email)
    except Exception:
        return st.session_state.get(f"runs_{_month_key()}", 0)


def _db_increment(email: str) -> None:
    try:
        from services.licence_manager_pg import increment_runs
        increment_runs(email)
    except Exception:
        key = f"runs_{_month_key()}"
        st.session_state[key] = st.session_state.get(key, 0) + 1


def get_runs_this_month() -> int:
    email = get_user_email()
    if email:
        return _db_get_runs(email)
    return st.session_state.get(f"runs_{_month_key()}", 0)


def increment_run() -> None:
    email = get_user_email()
    if email:
        _db_increment(email)
    else:
        key = f"runs_{_month_key()}"
        st.session_state[key] = st.session_state.get(key, 0) + 1


def runs_remaining(plan_key: str) -> int | None:
    """None means unlimited. Otherwise returns remaining runs >= 0."""
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

import uuid

import streamlit as st

from config.plans import PLAN_CONFIG, PLAN_ORDER, get_plan

_DEFAULT_PLAN = "free"


def init_session() -> None:
    """Call once at the top of app.py to ensure all session keys exist."""
    if "plan_key" not in st.session_state:
        try:
            is_local = st.secrets.get("dev", {}).get("local_dev", False)
        except Exception:
            is_local = False
        st.session_state.plan_key = "enterprise" if is_local else _DEFAULT_PLAN

    if "licence_activated" not in st.session_state:
        st.session_state.licence_activated = False

    if "user_email" not in st.session_state:
        st.session_state.user_email = ""

    if "trace_id" not in st.session_state:
        # Per-session correlation id, attached to every fault/alert this
        # session produces so support can follow one user's incidents
        # across multiple log entries.
        st.session_state.trace_id = uuid.uuid4().hex


def get_trace_id() -> str:
    return st.session_state.get("trace_id", "unknown")


def get_user_email() -> str:
    return st.session_state.get("user_email", "")


def set_user_email(email: str) -> None:
    st.session_state.user_email = (email or "").lower().strip()


def get_plan_key() -> str:
    return st.session_state.get("plan_key", _DEFAULT_PLAN)


def set_plan_key(plan_key: str) -> None:
    if plan_key not in PLAN_CONFIG:
        raise ValueError(f"Unknown plan key: {plan_key!r}")
    st.session_state.plan_key = plan_key
    st.session_state.licence_activated = True


def get_active_plan() -> dict:
    return get_plan(get_plan_key())


def is_free_plan() -> bool:
    return get_plan_key() == "free"


def render_dev_plan_override() -> None:
    """Sidebar override dropdown — only shown when dev.testing_mode = true in secrets.toml."""
    try:
        if not st.secrets.get("dev", {}).get("testing_mode", False):
            return
    except Exception:
        return

    with st.sidebar.expander("Dev: override plan", expanded=False):
        current = get_plan_key()
        override = st.selectbox(
            "Force plan",
            PLAN_ORDER,
            index=PLAN_ORDER.index(current) if current in PLAN_ORDER else 0,
            key="_dev_plan_override",
        )
        if override != current:
            set_plan_key(override)
            st.rerun()

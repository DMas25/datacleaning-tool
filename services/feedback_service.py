"""Feedback service — persistence and suppression logic for the post-run survey."""
from __future__ import annotations

import logging

import streamlit as st

log = logging.getLogger(__name__)

_SNOOZE_SIGNAL   = "feedback_snooze"
_SUPPRESS_SIGNAL = "feedback_never"
_SESSION_FLAG    = "_feedback_shown_this_session"
_MIN_RUNS        = 3       # lifetime run threshold before we ask
_SNOOZE_DAYS     = 7
_REPEAT_DAYS     = 90


def should_show_feedback(email: str) -> bool:
    """Return True if the feedback modal should be shown for this user/session."""
    if not email:
        return False
    if st.session_state.get(_SESSION_FLAG):
        return False
    try:
        from services.licence_manager_pg import _conn
        with _conn() as cur:
            cur.execute(
                "SELECT COUNT(*) AS n FROM usage_events WHERE email = %s AND event_type = 'run'",
                (email,),
            )
            row = cur.fetchone()
            if not row or (row["n"] < _MIN_RUNS):
                return False

            cur.execute(
                "SELECT 1 FROM signal_log WHERE email = %s AND signal = %s LIMIT 1",
                (email, _SUPPRESS_SIGNAL),
            )
            if cur.fetchone():
                return False

            cur.execute(
                """SELECT 1 FROM signal_log
                   WHERE email = %s AND signal = %s
                   AND shown_at > NOW() - INTERVAL '7 days'
                   LIMIT 1""",
                (email, _SNOOZE_SIGNAL),
            )
            if cur.fetchone():
                return False

            cur.execute(
                """SELECT 1 FROM user_feedback
                   WHERE email = %s
                   AND submitted_at > NOW() - INTERVAL '90 days'
                   LIMIT 1""",
                (email,),
            )
            if cur.fetchone():
                return False

        return True
    except Exception:
        log.debug("should_show_feedback: DB check failed — suppressing modal", exc_info=True)
        return False


def save_feedback(
    email: str,
    ease_score: int,
    quality_score: int,
    overall_score: int,
    nps_score: int,
    comment: str = "",
) -> None:
    from services.licence_manager_pg import _conn
    with _conn() as cur:
        cur.execute(
            """INSERT INTO user_feedback
               (email, ease_score, quality_score, overall_score, nps_score, comment)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (email, ease_score, quality_score, overall_score, nps_score, comment or None),
        )
    st.session_state[_SESSION_FLAG] = True


def snooze_feedback(email: str) -> None:
    from services.licence_manager_pg import _conn
    with _conn() as cur:
        cur.execute(
            "INSERT INTO signal_log (email, signal) VALUES (%s, %s)",
            (email, _SNOOZE_SIGNAL),
        )
    st.session_state[_SESSION_FLAG] = True


def suppress_feedback(email: str) -> None:
    from services.licence_manager_pg import _conn
    with _conn() as cur:
        cur.execute(
            "INSERT INTO signal_log (email, signal) VALUES (%s, %s)",
            (email, _SUPPRESS_SIGNAL),
        )
    st.session_state[_SESSION_FLAG] = True

"""Lightweight auto-recovery rule engine for ColtraDataAi.

Maps an exception to a recovery action so the fault boundary in app.py
can decide what to do *before* showing the client a down page: retry
the render, retry after a short delay, or wipe volatile session state
and retry once clean. This is intentionally simple — a dict lookup,
not a generic rules DSL — because the recovery vocabulary only has
three real outcomes.
"""
from __future__ import annotations

from enum import Enum


class RecoveryAction(str, Enum):
    RETRY = "retry"                    # safe to just re-run immediately
    RETRY_WITH_DELAY = "retry_delay"   # back off briefly first (likely transient)
    RESET_STATE = "reset_state"        # session_state is probably corrupted
    NONE = "none"                      # not recoverable — show the down page


# Exception type → action. Order doesn't matter here (unlike
# fault_types' classification list) because we look up by exact MRO
# walk via isinstance below, and the mapping is small enough that
# ambiguous overlaps aren't a real concern.
_RECOVERY_RULES: dict[type[BaseException], RecoveryAction] = {
    TimeoutError: RecoveryAction.RETRY,
    ConnectionError: RecoveryAction.RETRY_WITH_DELAY,
    KeyError: RecoveryAction.RESET_STATE,
    AttributeError: RecoveryAction.RESET_STATE,
}

RETRY_DELAY_SECONDS = 2
MAX_AUTO_RETRIES = 2


def get_recovery_action(exc: BaseException) -> RecoveryAction:
    for exc_type, action in _RECOVERY_RULES.items():
        if isinstance(exc, exc_type):
            return action
    return RecoveryAction.NONE

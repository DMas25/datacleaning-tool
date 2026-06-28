"""Fault classification for ColtraDataAi.

Defines the severity/category vocabulary used across logging, alerting,
the fault dashboard, and the recovery rule engine, plus the heuristic
that maps a raised exception onto that vocabulary. Keeping this in one
place means a severity label means the same thing everywhere it's read.
"""
from __future__ import annotations

import hashlib
from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# Ordered weakest → strongest so callers can do threshold comparisons,
# e.g. "only alert when severity >= ERROR".
_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
    Severity.CRITICAL: 3,
}


def severity_at_least(severity: Severity, threshold: Severity) -> bool:
    return _SEVERITY_RANK[severity] >= _SEVERITY_RANK[threshold]


class ErrorCategory(str, Enum):
    NETWORK = "network"
    DATA = "data"
    UI = "ui"
    SYSTEM = "system"
    UNKNOWN = "unknown"


# Exception type → (category, severity). Checked in MRO order via
# isinstance, most specific first, so subclasses inherit a sensible
# default unless explicitly listed.
_CLASSIFICATION_RULES: list[tuple[type[BaseException], ErrorCategory, Severity]] = [
    # Network / external service faults — usually transient.
    (ConnectionError, ErrorCategory.NETWORK, Severity.ERROR),
    (TimeoutError, ErrorCategory.NETWORK, Severity.WARNING),
    (OSError, ErrorCategory.NETWORK, Severity.ERROR),

    # Bad/missing data — caused by the input, not the platform.
    (KeyError, ErrorCategory.DATA, Severity.WARNING),
    (ValueError, ErrorCategory.DATA, Severity.WARNING),
    (TypeError, ErrorCategory.DATA, Severity.WARNING),
    (IndexError, ErrorCategory.DATA, Severity.WARNING),
    (LookupError, ErrorCategory.DATA, Severity.WARNING),

    # Streamlit / rendering issues.
    (RuntimeError, ErrorCategory.UI, Severity.ERROR),

    # Resource exhaustion / interpreter-level failures — always critical.
    (MemoryError, ErrorCategory.SYSTEM, Severity.CRITICAL),
    (RecursionError, ErrorCategory.SYSTEM, Severity.CRITICAL),
    (SystemError, ErrorCategory.SYSTEM, Severity.CRITICAL),
]


def classify_exception(exc: BaseException) -> tuple[Severity, ErrorCategory]:
    """
    Best-effort classification of *exc* into (severity, category).

    Falls back to (ERROR, UNKNOWN) for anything not covered above —
    being conservative here is intentional: an unrecognised failure
    mode should surface, not get silently downgraded to a warning.
    """
    for exc_type, category, severity in _CLASSIFICATION_RULES:
        if isinstance(exc, exc_type):
            return severity, category
    return Severity.ERROR, ErrorCategory.UNKNOWN


def compute_fingerprint(error_type: str, message: str, component: str) -> str:
    """
    Stable identity for "this kind of fault in this part of the app",
    independent of traceback line numbers (which shift every time the
    surrounding code is edited). Used to group occurrences for alert
    aggregation, rate limiting, and the dashboard's per-fingerprint views.

    Deliberately a hash of (error_type, message, component) rather than
    the full traceback — two requests that fail the same way should
    collapse into one fingerprint even if they took slightly different
    call paths to get there.
    """
    raw = f"{error_type}|{message}|{component}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

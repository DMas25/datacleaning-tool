"""Display formatting helpers for ColtraDataAi.

Pure functions — no side effects, no framework dependencies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Union


def fmt_number(value: Union[int, float], decimals: int = 0) -> str:
    """Format an integer or float with thousands separators."""
    if isinstance(value, float):
        return f"{value:,.{decimals}f}"
    return f"{int(value):,}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a 0–1 fraction or a 0–100 percentage as 'XX.X%'."""
    pct = value * 100 if value <= 1.0 else value
    return f"{pct:.{decimals}f}%"


def fmt_mb(bytes_value: int) -> str:
    """Format bytes as megabytes, rounded to 2 decimal places."""
    return f"{bytes_value / 1_048_576:.2f} MB"


def fmt_timestamp(dt: datetime | None = None, fmt: str = "%d %B %Y, %H:%M") -> str:
    """Return a formatted timestamp string (defaults to now)."""
    return (dt or datetime.now()).strftime(fmt)


def fmt_filename_timestamp(dt: datetime | None = None) -> str:
    """Return a compact timestamp string safe for use in filenames."""
    return (dt or datetime.now()).strftime("%Y%m%d_%H%M")


def safe_str(value, max_len: int = 60) -> str:
    """Convert *value* to string and truncate to *max_len* characters."""
    s = str(value) if value is not None else ""
    return s[:max_len] if len(s) > max_len else s


def snake_to_title(name: str) -> str:
    """Convert a snake_case column name to Title Case for display."""
    return name.replace("_", " ").title()


def risk_emoji(risk_level: str) -> str:
    """Return a traffic-light emoji for a risk level string."""
    return {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(risk_level, "⚪")

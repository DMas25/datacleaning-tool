"""Usage-milestone toast — habit reinforcement, not friction removal.

Unlike services/upgrade_messaging.py (which targets a specific friction point
to remove), this just celebrates that the user has hit a round-number run
count this calendar month, to reinforce the habit of coming back. Each
milestone fires once per email per month — see
services.licence_manager.milestone_already_shown / log_milestone_shown.
"""
from __future__ import annotations

from dataclasses import dataclass

MILESTONE_THRESHOLDS = (5, 10, 25, 50, 100)


@dataclass
class MilestoneMessage:
    headline: str
    supporting_message: str
    cta: str


def detect_milestone(runs_this_month: int) -> int | None:
    """Return the threshold just reached, or None if runs_this_month isn't one."""
    return runs_this_month if runs_this_month in MILESTONE_THRESHOLDS else None


def build_milestone_message(runs_this_month: int) -> MilestoneMessage:
    return MilestoneMessage(
        headline=f"You've cleaned {runs_this_month} datasets this month.",
        supporting_message="Keep the momentum going — export and reuse your results instantly.",
        cta="Export your data",
    )

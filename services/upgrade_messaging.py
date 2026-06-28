"""Behavioural signal -> targeted pricing prompt.

Reads a subscriber's own usage history (services.licence_manager.get_user_behavior)
and turns it into a single upgrade nudge grounded in what they've actually done —
not a generic "upgrade for more features" pitch.

Signals are grouped into five priority buckets (highest intent wins):
    1. Blocked intent      — explicit export/advisory attempts blocked by plan
    2. High frequency       — running often, with finer-grained sub-cases
    3. Repeated effort       — manual, repetitive behaviour without follow-through
    4. Premium underuse      — paid capability the user isn't getting value from
    5. Dormancy              — was active, has gone quiet

Within a bucket, the most specific matching condition wins over the generic
one (e.g. a starter user who already exports but never tries AI advisory gets
the advisory-specific nudge, not the generic high-frequency export pitch) —
buckets are still checked in strict order, so nothing in bucket 2 ever loses
to bucket 4, etc. Bucket order encodes behavioural-intent urgency and is fixed
— it is never reordered by effectiveness data (see candidate_signals'
`effectiveness` param below, which only reorders *within* a bucket).

build_message() also applies a cooldown: a signal already shown to this user
within COOLDOWN_HOURS is skipped in favour of the next-best matching signal,
so the same person doesn't see the identical prompt on every single visit.

Each signal also carries an A/B-tested copy variant (see UpgradeMessage.variant)
— a stable per-(user, signal) bucket, so the same user always sees the same
wording for a given signal (no flicker on rerun) but different users split
across variants, letting services.licence_manager.get_prompt_effectiveness()
compare variant performance once enough impressions exist.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from config.plans import get_plan, next_plan

HIGH_RUN_FREQUENCY_THRESHOLD = 3
REPEATED_USE_THRESHOLD = 3
SUSTAINED_FREE_USAGE_MONTHS = 2
DORMANCY_DAYS = 14
COOLDOWN_HOURS = 24

# Page-load is the lowest-intent moment — no fresh same-session evidence
# exists yet, so only long-horizon, low-volatility signals are allowed there.
# Everything else (blocked intent, high-frequency, follow-through, premium
# underuse) requires a same-session trigger site (post-run / blocked-click),
# not the once-per-session banner evaluation.
BANNER_TIER_SIGNALS = frozenset({"sustained_free_usage", "dormancy"})

# Mirrors services.licence_manager.MIN_IMPRESSIONS_FOR_CONFIDENCE — kept as a
# separate constant rather than importing licence_manager here, since this
# module is otherwise pure (no DB access, easy to unit test). Below this
# floor a signal's effectiveness score is mostly sample-size noise, so it
# must not be allowed to reorder anything yet.
DYNAMIC_PRIORITY_MIN_IMPRESSIONS = 20

# Bucket membership from candidate_signals(), as a lookup — used only to
# reorder *within* a bucket by effectiveness; bucket number itself (intent
# urgency) is never touched by data.
SIGNAL_TIERS: dict[str, int] = {
    "blocked_export": 1,
    "blocked_advisory": 1,
    "ai_advisory_inactivity": 2,
    "high_run_frequency": 2,
    "sustained_free_usage": 2,
    "repeated_without_action": 3,
    "active_no_value": 3,
    "ai_advisory_declining": 4,
    "premium_feature_inactivity": 4,
    "follow_through": 4,
    "dormancy": 5,
}

# Plan capability flag -> the usage event that proves the feature was actually used.
_PREMIUM_FEATURE_EVENTS = {
    "can_download_pdf": ("export_pdf", "PDF reports"),
    "can_view_advanced_insights": ("ai_advisory", "AI Advisory insights"),
}


@dataclass
class UpgradeMessage:
    headline: str
    supporting_message: str
    cta: str
    signal: str
    trigger_explanation: str
    usage_reference: str | None = None
    variant: str = "default"


def _select_variant(email: str, signal: str, variant_count: int) -> int:
    """Stable per-(user, signal) A/B bucket — same user always sees the same
    variant for a given signal (no flicker on rerun), but mixing the signal
    name into the hash means a user's variant assignment for one signal is
    independent of their assignment for another."""
    digest = hashlib.md5(f"{email.lower().strip()}::{signal}".encode()).hexdigest()
    return int(digest, 16) % variant_count


def _unused_premium_features(behavior: dict) -> list[tuple[str, str]]:
    """Premium features this plan already includes that the user has never triggered."""
    plan = get_plan(behavior["plan"])
    used = behavior["used_events"]
    return [
        (event, label)
        for flag, (event, label) in _PREMIUM_FEATURE_EVENTS.items()
        if plan.get(flag) and event not in used
    ]


def _multi_run_detected(behavior: dict, runs_this_session: int) -> bool:
    """Session-counter usage is fragile — it resets on tab close/reload, so a
    real 3rd run in one sitting can look like a 1st run if the page was
    refreshed. Blend it with a DB-backed pattern (sustained runs in the last
    24h *and* the last 30 days) so a lost session counter doesn't suppress a
    signal that the event history still backs up."""
    runs_last_24h = behavior.get("runs_last_24h", 0)
    runs_30d = behavior["runs_last_30_days"]
    return runs_this_session >= 2 or (runs_last_24h >= 3 and runs_30d >= 3)


def _reorder_by_effectiveness(candidates: list[str], effectiveness: dict) -> list[str]:
    """Reorder candidates within each behavioural-intent tier by historical
    conversion score — never across tiers, since tier order encodes intent
    urgency (a dormancy nudge must never outrank blocked intent just because
    it happens to convert better on average).

    Signals without enough impressions yet (see DYNAMIC_PRIORITY_MIN_IMPRESSIONS)
    keep their original designed sub-order instead of being reordered on noise.
    Sort is stable, so ties (including all-insufficient-data tiers) preserve
    the original bucket-coded sub-order.
    """
    def sort_key(item: tuple[int, str]) -> tuple[int, float]:
        idx, signal = item
        tier = SIGNAL_TIERS.get(signal, 99)
        stat = effectiveness.get(signal)
        has_confidence = bool(stat) and stat.get("impressions", 0) >= DYNAMIC_PRIORITY_MIN_IMPRESSIONS
        score = -(stat["score"] or 0.0) if has_confidence else 0.0
        return (tier, score)

    indexed = sorted(enumerate(candidates), key=sort_key)
    return [signal for _, signal in indexed]


def candidate_signals(
    behavior: dict,
    runs_this_session: int = 0,
    follow_through_this_session: bool = False,
    allowed_signals: frozenset[str] | None = None,
    effectiveness: dict | None = None,
) -> list[str]:
    """All signals that match, in strict priority order (bucket order, then
    most-specific-first within a bucket). The caller picks the first one not
    suppressed by cooldown.

    allowed_signals restricts the result to a context-appropriate subset
    (e.g. BANNER_TIER_SIGNALS for the page-load moment) — filtering here,
    before cooldown selection, ensures the cooldown fallback never escapes
    the allowed set either.

    effectiveness (services.licence_manager.get_prompt_effectiveness() output)
    enables the dynamic-priority engine: candidates are reordered *within*
    their bucket by historical conversion score. Pass None to keep the fixed,
    hand-authored sub-order (e.g. in tests or where no effectiveness data
    should influence the result)."""
    plan = behavior["plan"]
    runs_30d = behavior["runs_last_30_days"]
    follow_through_30d = behavior["follow_through_last_30_days"]
    total_runs = behavior["total_runs"]
    multi_run = _multi_run_detected(behavior, runs_this_session)
    candidates: list[str] = []

    # ── Bucket 1: blocked intent ────────────────────────────────────────────
    if behavior.get("export_blocked_last_30_days", 0) > 0:
        candidates.append("blocked_export")
    if behavior.get("advisory_blocked_last_30_days", 0) > 0:
        candidates.append("blocked_advisory")

    # ── Bucket 2: high frequency usage (most specific sub-case first) ───────
    if (
        multi_run
        and follow_through_30d > 0
        and plan not in ("professional", "premium", "enterprise")
        and "ai_advisory" not in behavior["used_events"]
    ):
        candidates.append("ai_advisory_inactivity")
    if multi_run and follow_through_30d == 0:
        candidates.append("high_run_frequency")
    if plan == "free" and behavior.get("active_months", 0) >= SUSTAINED_FREE_USAGE_MONTHS:
        candidates.append("sustained_free_usage")

    # ── Bucket 3: repeated effort / manual behaviour ────────────────────────
    if total_runs >= REPEATED_USE_THRESHOLD and follow_through_30d == 0:
        candidates.append("repeated_without_action")
    if runs_30d > 0 and follow_through_30d == 0:
        candidates.append("active_no_value")

    # ── Bucket 4: premium underuse ───────────────────────────────────────────
    if (
        plan == "premium"
        and behavior.get("ai_advisory_prior_30_days", 0) > 0
        and behavior.get("ai_advisory_last_30_days", 0) < behavior["ai_advisory_prior_30_days"]
    ):
        candidates.append("ai_advisory_declining")
    if plan in ("professional", "premium", "enterprise") and _unused_premium_features(behavior):
        candidates.append("premium_feature_inactivity")
    # "follow_through" asserts the user IS converting runs into action, so it
    # requires causal evidence — export/ai_advisory actually following a run
    # in this same session — not just "some export happened in the last 30
    # days" (which could be unrelated to any specific run, e.g. re-downloading
    # an old report).
    if follow_through_this_session:
        candidates.append("follow_through")

    # ── Bucket 5: dormancy ────────────────────────────────────────────────────
    days_since_last_run = behavior.get("days_since_last_run")
    if total_runs > 0 and days_since_last_run is not None and days_since_last_run >= DORMANCY_DAYS:
        candidates.append("dormancy")

    if allowed_signals is not None:
        candidates = [s for s in candidates if s in allowed_signals]

    if effectiveness:
        candidates = _reorder_by_effectiveness(candidates, effectiveness)

    return candidates


def detect_signal(
    behavior: dict,
    runs_this_session: int = 0,
    follow_through_this_session: bool = False,
    allowed_signals: frozenset[str] | None = None,
    effectiveness: dict | None = None,
) -> str | None:
    """Pick the single strongest behavioural signal (no cooldown applied)."""
    candidates = candidate_signals(
        behavior, runs_this_session, follow_through_this_session, allowed_signals, effectiveness
    )
    return candidates[0] if candidates else None


def build_message(
    behavior: dict,
    is_recent=None,
    runs_this_session: int = 0,
    follow_through_this_session: bool = False,
    force_lowest_priority: bool = False,
    blocked_attempts_this_session: int = 0,
    allowed_signals: frozenset[str] | None = None,
    effectiveness: dict | None = None,
) -> UpgradeMessage | None:
    """Build a targeted pricing prompt, skipping any signal already shown to
    this user within COOLDOWN_HOURS (via is_recent(signal) -> bool), or None
    if no signal matches / everything matching is on cooldown.

    force_lowest_priority bypasses the cooldown filter and falls back to the
    weakest matching candidate instead of None — used when the user has gone
    several sessions without seeing any monetisation message at all, so
    going dark again isn't acceptable even though every signal happens to be
    on cooldown right now.

    blocked_attempts_this_session escalates the wording of blocked_export /
    blocked_advisory (1st attempt -> standard, 2nd-3rd -> stronger, 4th+ ->
    urgency framing). Blocked intent already bypasses cooldown/suppression
    entirely, so repeated attempts would otherwise show the identical prompt
    every time — this varies tone with persistence instead of suppressing it.

    effectiveness enables the dynamic-priority engine — see candidate_signals().
    """
    candidates = candidate_signals(
        behavior, runs_this_session, follow_through_this_session, allowed_signals, effectiveness
    )
    signal = next((s for s in candidates if not (is_recent and is_recent(s))), None)
    if signal is None and force_lowest_priority and candidates:
        signal = candidates[-1]
    if signal is None:
        return None

    plan = behavior["plan"]
    email = behavior["email"]
    runs_30d = behavior["runs_last_30_days"]
    usage_reference = f"You've run {runs_30d} dataset(s) this month." if runs_30d else None

    if signal == "blocked_export":
        tier = 3 if blocked_attempts_this_session >= 4 else (2 if blocked_attempts_this_session >= 2 else 1)
        if tier == 3:
            headline = "You can't move forward without exporting."
            supporting = (
                "You've tried to export multiple times this session. Upgrade now — every "
                "additional attempt is time you're not getting your results into your workflow."
            )
            cta = "Unblock export now"
        elif tier == 2:
            headline = "Still blocked — this isn't going away on its own."
            supporting = "Upgrade to download your cleaned data and stop hitting this wall."
            cta = "Upgrade to export"
        else:
            headline = "You're ready to export your results."
            supporting = "Upgrade to download your cleaned data and use it immediately in your workflow."
            cta = "Upgrade to export"
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=(
                f"Attempted to export a result in the last 30 days but was blocked by the current "
                f"plan ({blocked_attempts_this_session} attempt(s) this session)."
            ),
            usage_reference=usage_reference,
            variant=f"attempt_tier_{tier}",
        )

    if signal == "blocked_advisory":
        tier = 3 if blocked_attempts_this_session >= 4 else (2 if blocked_attempts_this_session >= 2 else 1)
        if tier == 3:
            headline = "You keep coming back to AI Advisory — it's clearly what you need."
            supporting = (
                "You've tried to reach this section multiple times this session. Upgrade now "
                "instead of hitting the same wall again on your next dataset."
            )
            cta = "Unblock AI insights now"
        elif tier == 2:
            headline = "Still locked — this won't open on its own."
            supporting = (
                "Upgrade to unlock AI-powered analysis of your cleaned data, with patterns "
                "and next steps generated automatically."
            )
            cta = "Upgrade to unlock AI insights"
        else:
            headline = "You're ready for deeper insights."
            supporting = (
                "Upgrade to unlock AI-powered analysis of your cleaned data, with patterns "
                "and next steps generated automatically."
            )
            cta = "Upgrade to unlock AI insights"
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=(
                f"Reached the AI Advisory section in the last 30 days but was blocked by the "
                f"current plan ({blocked_attempts_this_session} attempt(s) this session)."
            ),
            usage_reference=usage_reference,
            variant=f"attempt_tier_{tier}",
        )

    if signal == "ai_advisory_inactivity":
        variants = (
            (
                "Stop analysing results manually.",
                "You're already cleaning your data regularly. Let AI generate insights "
                "instead of reviewing everything yourself.",
                "Unlock AI insights",
            ),
            (
                "You're already doing the hard part — let AI do the rest.",
                "Every clean you run could come with an automatic breakdown of what changed "
                "and why. Try it on your next dataset.",
                "Try AI Advisory",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=(
                f"{runs_30d} runs in the last 30 days with follow-through actions present, "
                "but AI Advisory has never been used."
            ),
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    if signal == "sustained_free_usage":
        active_months = behavior.get("active_months", 0)
        variants = (
            (
                "You're doing everything inside the app — now take it with you.",
                "You've been consistently cleaning data. Export your results to integrate "
                "them into your workflow.",
                "Unlock export",
            ),
            (
                "Weeks of cleaning, zero exports — that data is staying trapped.",
                f"You've used ColtraDataAi consistently for {active_months} month(s). Upgrade "
                "once and start exporting every result.",
                "Upgrade to export",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=(
                f"Free-plan user active across {active_months} separate "
                "calendar months without ever upgrading."
            ),
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    if signal == "ai_advisory_declining":
        prior = behavior.get("ai_advisory_prior_30_days", 0)
        last = behavior.get("ai_advisory_last_30_days", 0)
        variants = (
            (
                "You're not using your most powerful feature.",
                "AI advisory helps you move from cleaned data to decisions instantly. "
                "Try running one insight on your latest dataset.",
                "Generate AI insights",
            ),
            (
                "Your AI Advisory usage dropped off — here's what you're missing.",
                f"You went from {prior} run(s) with AI insights to {last}. Pick it back up "
                "on your next dataset.",
                "Re-enable AI insights",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=(
                f"Premium-plan AI Advisory usage dropped from {prior} (prior 30 days) to "
                f"{last} (last 30 days)."
            ),
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    if signal == "premium_feature_inactivity":
        event, label = _unused_premium_features(behavior)[0]
        plan_label = get_plan(plan)["label"]
        variants = (
            (
                f"You're already paying for {label} — you just haven't tried it yet.",
                f"It's included on your {plan_label} plan. Run it on your next dataset to see "
                "the full picture instead of just the cleaned table.",
                f"Try {label} on your next run",
            ),
            (
                f"{label} is sitting unused on your plan.",
                "You're paying for it either way — the only difference is whether you're "
                "getting value from it. Try it on your next run.",
                f"Activate {label}",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=f"Paid plan includes {label}, but it has never been used.",
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    if signal == "dormancy":
        days = behavior.get("days_since_last_run")
        variants = (
            (
                "Pick up where you left off.",
                "It's been a while since your last clean. Your data tools are right where "
                "you left them.",
                "Run a new clean",
            ),
            (
                f"It's been {days} day(s) — your workspace is exactly as you left it.",
                "No setup needed. Upload a file and pick up exactly where you stopped.",
                "Resume cleaning",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=(
                f"Previously active ({behavior['total_runs']} total runs) but no run in "
                f"{days} days."
            ),
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    upgrade_key = next_plan(plan)
    if upgrade_key is None:
        return None
    upgrade_plan = get_plan(upgrade_key)

    if signal == "high_run_frequency":
        variants = (
            (
                "You've already cleaned your data — now turn it into something usable.",
                f"You've run {runs_30d} cleans this month. Export your results as structured "
                "reports instead of copying them manually.",
                "Upgrade to export your results",
            ),
            (
                f"{runs_30d} cleans this month, zero exports.",
                "You're putting in the work every time — upgrade once and get a structured "
                "report out of every run automatically.",
                "Upgrade to export",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=f"{runs_30d} runs in the last 30 days with zero follow-through actions.",
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    if signal == "follow_through":
        blurb = upgrade_plan["blurb"].rstrip(".")
        variants = (
            (
                "You're exporting your cleaned data — let's remove the next bottleneck.",
                f"{upgrade_plan['label']} unlocks {blurb}, so you can go from clean data to a "
                "finished report in the same session.",
                f"Upgrade to {upgrade_plan['label']}",
            ),
            (
                "You're already getting value — here's how to get more.",
                f"{upgrade_plan['label']} adds {blurb} on top of what you're already exporting.",
                f"See what {upgrade_plan['label']} adds",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation="Follow-through actions present in the last 30 days; next plan tier unlocks more.",
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    if signal == "repeated_without_action":
        variants = (
            (
                "You're doing the work twice.",
                "You're re-running the same datasets instead of saving the output. "
                "Export once and reuse instantly.",
                "Unlock export",
            ),
            (
                "You're spending time reading what AI can summarise instantly.",
                "Turn your results into actionable insights automatically instead of "
                "reviewing them line by line.",
                "Try AI advisory",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=(
                f"{behavior['total_runs']} total runs with zero follow-through in the last 30 days "
                "— repeated manual effort without saving output."
            ),
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    if signal == "active_no_value":
        variants = (
            (
                "Turn more of your work into outcomes.",
                "You're using the platform, but not turning runs into completed outputs. "
                "Export or generate insights to get full value.",
                "Complete your workflow",
            ),
            (
                f"{runs_30d} run(s) this month, nothing exported yet.",
                "Turning a clean into an export or an AI insight takes one click — try it "
                "on your next result.",
                "Get full value from your next run",
            ),
        )
        idx = _select_variant(email, signal, len(variants))
        headline, supporting, cta = variants[idx]
        return UpgradeMessage(
            headline=headline,
            supporting_message=supporting,
            cta=cta,
            signal=signal,
            trigger_explanation=f"{runs_30d} run(s) in the last 30 days with zero follow-through actions.",
            usage_reference=usage_reference,
            variant=f"v{idx + 1}",
        )

    return None

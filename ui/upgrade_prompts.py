import streamlit as st

from config.plans import get_plan, next_plan
from services.billing import checkout_url, payments_live
from services.usage_tracker import runs_remaining, usage_summary


def render_targeted_upgrade_banner() -> None:
    """Main-area upgrade nudge grounded in the user's actual usage history.

    Page-load is the lowest-intent moment — no fresh same-session evidence
    exists yet — so this is restricted to BANNER_TIER_SIGNALS only (long
    horizon, low-volatility signals). Everything else (blocked intent,
    high-frequency, follow-through) needs a same-session trigger site, not
    this once-per-session call. The once-per-session gate itself lives at the
    call site (app.py), not here, so this function is purely "evaluate and
    render" with no session-state side effects of its own.

    Falls back to render_live_upgrade_banner() when there's no email on file
    or no behavioural signal strong enough to act on (e.g. brand-new users).
    """
    from services.licence_manager import (
        get_user_behavior,
        signal_shown_recently,
        log_signal_shown,
        sessions_without_prompt,
        log_prompt_evaluation,
        get_prompt_effectiveness,
    )
    from services.upgrade_messaging import build_message, COOLDOWN_HOURS, BANNER_TIER_SIGNALS
    from utils.session_helpers import get_user_email

    email = get_user_email()
    if not email:
        render_live_upgrade_banner()
        return

    behavior = get_user_behavior(email)

    if behavior["total_runs"] == 0:
        # Brand-new user — no behavioural history to ground a targeted nudge
        # in, so don't let a behaviourally-empty message slip through.
        render_live_upgrade_banner()
        return

    # If every matching signal has been cooldown-suppressed for the last 3
    # sessions in a row, force the weakest matching one through anyway —
    # otherwise a user can go indefinitely without ever seeing any
    # monetisation messaging just because of unlucky cooldown timing.
    force_fallback = sessions_without_prompt(email) >= 3

    # Dynamic-priority engine: reorders candidates *within* their fixed
    # behavioural-intent tier by historical conversion score (see
    # upgrade_messaging.SIGNAL_TIERS / _reorder_by_effectiveness). At this
    # call site BANNER_TIER_SIGNALS only ever contains one signal per tier
    # (sustained_free_usage, dormancy live in different tiers), so there's
    # nothing to reorder here yet — this only starts mattering once a
    # same-session trigger site exposes multiple same-tier candidates at once.
    effectiveness = get_prompt_effectiveness()

    message = build_message(
        behavior,
        is_recent=lambda signal: signal_shown_recently(email, signal, COOLDOWN_HOURS),
        runs_this_session=st.session_state.get("runs_this_session", 0),
        follow_through_this_session=st.session_state.get("follow_through_this_session", False),
        force_lowest_priority=force_fallback,
        blocked_attempts_this_session=st.session_state.get("blocked_attempts_this_session", 0),
        allowed_signals=BANNER_TIER_SIGNALS,
        effectiveness=effectiveness,
    )
    if message is None:
        log_prompt_evaluation(email, shown=False)
        render_live_upgrade_banner()
        return

    log_signal_shown(email, message.signal, message.variant)
    log_prompt_evaluation(email, shown=True)

    url = checkout_url(next_plan(behavior["plan"])) if behavior["plan"] not in (
        "professional", "premium", "enterprise"
    ) else None

    cta_html = (
        f"""<a href="{url}" target="_blank" rel="noopener noreferrer" style="
            display:inline-block;white-space:nowrap;flex-shrink:0;
            background:#1F4E79;color:white;font-weight:600;font-size:0.85rem;
            padding:0.45rem 1rem;border-radius:7px;text-decoration:none;
        ">{message.cta} →</a>"""
        if url
        else f'<span style="color:#1F4E79;font-weight:600;font-size:0.85rem;">{message.cta}</span>'
    )

    reference_html = (
        f'<div style="color:#5B7A99;font-size:0.78rem;margin-top:0.15rem;">{message.usage_reference}</div>'
        if message.usage_reference
        else ""
    )

    st.markdown(
        f"""
        <div style="
            display:flex;align-items:center;justify-content:space-between;
            background:#EFF6FF;border:1px solid #BFDBFE;border-left:4px solid #3B82F6;
            border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;gap:1rem;
        ">
            <div style="flex:1;">
                <div style="color:#1E3A5F;font-size:0.9rem;line-height:1.5;font-weight:600;">{message.headline}</div>
                <div style="color:#1E3A5F;font-size:0.85rem;line-height:1.5;margin-top:0.15rem;">{message.supporting_message}</div>
                {reference_html}
            </div>
            {cta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_upgrade_banner() -> None:
    """Main-area upgrade nudge — shown only to free and starter users.

    Reads the active plan from session_state automatically.
    Renders nothing for professional, premium, and enterprise plans.
    """
    from utils.session_helpers import get_plan_key

    plan_key = get_plan_key()
    if plan_key in ("professional", "premium", "enterprise"):
        return

    upgrade = next_plan(plan_key)
    if upgrade is None:
        return

    plan         = get_plan(plan_key)
    upgrade_plan = get_plan(upgrade)
    url          = checkout_url(upgrade)

    msg_text = (
        f"You're on the <strong>{plan['label']}</strong> plan. "
        f"Upgrade to <strong>{upgrade_plan['label']}</strong> ({upgrade_plan['price']}) "
        f"to unlock {upgrade_plan['blurb'].rstrip('.')}."
    )

    if url:
        st.markdown(
            f"""
            <div style="
                display:flex;align-items:center;justify-content:space-between;
                background:#EFF6FF;border:1px solid #BFDBFE;border-left:4px solid #3B82F6;
                border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;gap:1rem;
            ">
                <span style="color:#1E3A5F;font-size:0.9rem;line-height:1.5;flex:1;">{msg_text}</span>
                <a href="{url}" target="_blank" rel="noopener noreferrer" style="
                    display:inline-block;white-space:nowrap;flex-shrink:0;
                    background:#1F4E79;color:white;font-weight:600;font-size:0.85rem;
                    padding:0.45rem 1rem;border-radius:7px;text-decoration:none;
                ">Upgrade to {upgrade_plan['label']} →</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info(
            f"You're on the **{plan['label']}** plan. "
            f"Upgrade to **{upgrade_plan['label']}** ({upgrade_plan['price']}) "
            f"to unlock {upgrade_plan['blurb'].rstrip('.')}. Paid plans launching soon."
        )


def render_upgrade_banner(current_plan_key: str) -> None:
    """Sidebar or top-of-page nudge shown to free/starter users."""
    if current_plan_key in ("premium", "enterprise"):
        return

    upgrade = next_plan(current_plan_key)
    if upgrade is None:
        return

    upgrade_plan = get_plan(upgrade)
    url = checkout_url(upgrade)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Upgrade to {upgrade_plan['label']}**")
    st.sidebar.caption(upgrade_plan["blurb"])

    if url:
        st.sidebar.link_button(
            f"{upgrade_plan['label']} — {upgrade_plan['price']}",
            url,
            use_container_width=True,
        )
    elif not payments_live():
        st.sidebar.caption("Paid plans launching soon.")


def render_run_counter(current_plan_key: str) -> None:
    """Small usage counter shown in the sidebar."""
    summary = usage_summary(current_plan_key)
    remaining = runs_remaining(current_plan_key)

    if remaining is None:
        st.sidebar.caption(f"Runs: {summary}")
        return

    if remaining == 0:
        st.sidebar.error(f"No runs left this month. {summary}")
    elif remaining <= 3:
        st.sidebar.warning(f"{remaining} run(s) left this month.")
    else:
        st.sidebar.caption(summary)


def render_inline_upgrade(feature: str, current_plan_key: str) -> None:
    """
    Compact single-line nudge for use inside a disabled section.
    Less prominent than render_paywall — use for soft upsells, not hard gates.
    """
    from services.entitlements import first_plan_with_feature

    required = first_plan_with_feature(feature)
    if required is None:
        return

    plan = get_plan(required)
    url = checkout_url(required)
    label = f"Unlock with {plan['label']} ({plan['price']})"

    if url:
        st.link_button(label, url)
    else:
        st.caption(f"Available on {plan['label']} — launching soon.")


def render_run_limit_trigger(current_plan_key: str) -> None:
    """Inline warning banner when the user has exhausted their monthly run allowance.

    Call this at the top of any action that consumes a run, before executing it.
    Returns without rendering if the user has runs remaining or is on an unlimited plan.
    """
    remaining = runs_remaining(current_plan_key)
    if remaining is None or remaining > 0:
        return

    plan    = get_plan(current_plan_key)
    upgrade = next_plan(current_plan_key)

    st.error(
        f"**You've reached your monthly run limit** "
        f"({plan['monthly_runs']} runs on the {plan['label']} plan). "
        "Upgrade to continue processing datasets this month."
    )

    if upgrade:
        upgrade_plan = get_plan(upgrade)
        url          = checkout_url(upgrade)
        runs         = upgrade_plan["monthly_runs"]
        runs_label   = "unlimited runs" if runs is None else f"{runs} runs/month"

        st.caption(
            f"**{upgrade_plan['label']}** ({upgrade_plan['price']}) gives you {runs_label} "
            f"and {upgrade_plan['blurb'].rstrip('.')}."
        )

        if url:
            from ui.pricing_cards import _CTA_LABELS
            label = _CTA_LABELS.get(upgrade, f"Upgrade to {upgrade_plan['label']}")
            st.link_button(label, url, use_container_width=True, type="primary")
        else:
            st.caption("Paid plans launching soon.")


def render_file_size_trigger(current_plan_key: str, file_mb: float) -> bool:
    """Inline warning when the uploaded file exceeds the plan's file size limit.

    Renders the banner and returns True if the file is blocked (caller should halt).
    Returns False if the file is within limits.
    """
    plan    = get_plan(current_plan_key)
    max_mb  = plan["max_file_mb_backend"]

    if file_mb <= max_mb:
        return False

    upgrade = next_plan(current_plan_key)

    st.warning(
        f"**This dataset exceeds your plan limit.** "
        f"Your file is {file_mb:.1f} MB but the **{plan['label']}** plan supports up to {max_mb} MB. "
        "Upgrade to continue."
    )

    if upgrade:
        upgrade_plan    = get_plan(upgrade)
        upgrade_max_mb  = upgrade_plan["max_file_mb_backend"]
        url             = checkout_url(upgrade)

        st.caption(
            f"**{upgrade_plan['label']}** ({upgrade_plan['price']}) supports files up to {upgrade_max_mb} MB."
        )

        if url:
            from ui.pricing_cards import _CTA_LABELS
            label = _CTA_LABELS.get(upgrade, f"Upgrade to {upgrade_plan['label']}")
            st.link_button(label, url, use_container_width=True, type="primary")
        else:
            st.caption("Paid plans launching soon.")

    return True


def render_row_limit_trigger(current_plan_key: str, row_count: int) -> bool:
    """Inline warning when the uploaded dataset exceeds the plan's row limit.

    Returns True if the dataset is blocked (caller should halt), False if within limits.
    """
    plan     = get_plan(current_plan_key)
    max_rows = plan["max_rows_backend"]

    if row_count <= max_rows:
        return False

    upgrade = next_plan(current_plan_key)

    st.warning(
        f"**This dataset exceeds your plan limit.** "
        f"Your file has {row_count:,} rows but the **{plan['label']}** plan supports up to {max_rows:,} rows. "
        "Upgrade to continue."
    )

    if upgrade:
        upgrade_plan     = get_plan(upgrade)
        upgrade_max_rows = upgrade_plan["max_rows_backend"]
        url              = checkout_url(upgrade)

        st.caption(
            f"**{upgrade_plan['label']}** ({upgrade_plan['price']}) supports up to {upgrade_max_rows:,} rows."
        )

        if url:
            from ui.pricing_cards import _CTA_LABELS
            label = _CTA_LABELS.get(upgrade, f"Upgrade to {upgrade_plan['label']}")
            st.link_button(label, url, use_container_width=True, type="primary")
        else:
            st.caption("Paid plans launching soon.")

    return True

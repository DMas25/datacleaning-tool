import streamlit as st

from config.plans import get_plan, next_plan
from services.billing import checkout_url, payments_live
from services.usage_tracker import runs_remaining, usage_summary


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

    msg = (
        f"You're on the **{plan['label']}** plan. "
        f"Upgrade to **{upgrade_plan['label']}** ({upgrade_plan['price']}) "
        f"to unlock {upgrade_plan['blurb'].rstrip('.')}."
    )

    if url:
        col_msg, col_btn = st.columns([5, 1])
        with col_msg:
            st.info(msg)
        with col_btn:
            st.link_button(
                f"Upgrade to {upgrade_plan['label']}",
                url,
                use_container_width=True,
            )
    else:
        st.info(msg + " Paid plans launching soon.")


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

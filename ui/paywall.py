import streamlit as st

from config.plans import get_plan, next_plan
from services.billing import checkout_url, payments_live
from services.entitlements import first_plan_with_feature


def render_upgrade_cta_button(plan_key: str | None, key_suffix: str = "") -> None:
    """Prominent primary upgrade button.

    Renders a link button to the checkout page for *plan_key*.
    Silently does nothing when plan_key is None (user is already at the top tier)
    or when payments are not yet live.
    """
    if plan_key is None:
        return
    plan = get_plan(plan_key)
    url  = checkout_url(plan_key)
    label = f"Upgrade to {plan['label']} — {plan['price']}"
    if url:
        st.link_button(label, url, use_container_width=True, type="primary")
    elif not payments_live():
        st.caption(
            f"**{plan['label']}** ({plan['price']}) — paid plans launching soon. "
            "Activate your licence key in the sidebar once you have one."
        )


def paywall_card(title: str, body: str, button_text: str = "Upgrade", key: str | None = None) -> None:
    """Simple inline paywall card — use for quick guards throughout the app.

    `key` disambiguates calls that share the same title (e.g. the same
    locked-feature message shown in two different sections).
    """
    st.warning(f"**{title}**\n\n{body}")
    st.button(button_text, key=f"btn_{key or title}")


def render_paywall(
    feature: str,
    title: str,
    description: str,
    current_plan_key: str = "free",
) -> None:
    """
    Inline paywall card. Renders instead of the locked feature.
    Returns nothing — the caller should guard with `if can(plan, feature):`.
    """
    required_plan_key = first_plan_with_feature(feature)
    if required_plan_key is None:
        st.warning(f"Feature '{feature}' is not available on any plan.")
        return

    required_plan = get_plan(required_plan_key)
    url = checkout_url(required_plan_key)

    with st.container(border=True):
        st.markdown(f"#### 🔒 {title}")
        st.caption(description)
        st.info(
            f"Available from the **{required_plan['label']}** plan "
            f"({required_plan['price']})."
        )
        if url:
            st.link_button(
                f"Upgrade to {required_plan['label']}",
                url,
                use_container_width=True,
            )
        elif not payments_live():
            st.caption("Paid plans launching soon — check back shortly.")


def render_run_limit_paywall(current_plan_key: str) -> None:
    """Shown when the user has exhausted their monthly runs."""
    plan = get_plan(current_plan_key)
    upgrade = next_plan(current_plan_key)

    with st.container(border=True):
        st.warning(
            f"You've used all **{plan['monthly_runs']}** runs for this month "
            f"on the **{plan['label']}** plan."
        )
        if upgrade:
            upgrade_plan = get_plan(upgrade)
            url = checkout_url(upgrade)
            runs = upgrade_plan["monthly_runs"]
            run_text = "unlimited runs" if runs is None else f"{runs} runs/month"
            st.caption(
                f"Upgrade to **{upgrade_plan['label']}** ({upgrade_plan['price']}) "
                f"for {run_text}."
            )
            if url:
                st.link_button(
                    f"Upgrade to {upgrade_plan['label']}",
                    url,
                    use_container_width=True,
                )
            else:
                st.caption("Paid plans launching soon.")

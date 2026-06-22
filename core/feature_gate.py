import streamlit as st

from config.tier_config import TIERS, get_tier
from config.lemonsqueezy_config import get_checkout_url, is_payments_live
from services.entitlements import has_feature
from utils.session_helpers import set_plan_key

# Map old capitalised tier names → new plan keys, and old feature names → new flags.
_TIER_TO_PLAN: dict[str, str] = {
    "free": "free", "Free": "free",
    "starter": "starter", "Starter": "starter",
    "pro": "professional", "Pro": "professional",
    "professional": "professional", "Professional": "professional",
    "premium": "premium", "Premium": "premium",
    "enterprise": "enterprise", "Enterprise": "enterprise",
}
_FEATURE_MAP: dict[str, str] = {
    "advanced_dashboards": "can_view_advanced_insights",
    "ai_insights": "can_view_advanced_insights",
    "ai_advisory": "can_view_advanced_insights",
    "export": "can_download_excel",
    "export_pdf": "can_download_pdf",
    "export_branding": "can_brand_reports",
}


def render_tier_selector(branding: dict) -> str:
    """Sidebar: licence key entry, current tier badge, and upgrade CTAs.

    Returns the active tier name for the current session.
    """
    st.sidebar.markdown(f"### {branding['app_name']} Plans")

    if "account_tier" not in st.session_state:
        try:
            is_local = st.secrets.get("dev", {}).get("local_dev", False)
        except Exception:
            is_local = False
        st.session_state.account_tier = "Enterprise" if is_local else "Free"

    _render_licence_form()
    _render_tier_badge()
    _render_upgrade_ctas()
    _render_dev_tier_override()

    return st.session_state.account_tier


def _render_licence_form() -> None:
    with st.sidebar.form("licence_form", clear_on_submit=False):
        licence_key = st.text_input(
            "Licence Key",
            placeholder="XXXX-XXXX-XXXX-XXXX",
            type="password",
            help="Enter the licence key you received after purchasing a plan.",
        )
        submitted = st.form_submit_button("Activate Licence", use_container_width=True)

    if submitted:
        if not licence_key:
            st.sidebar.warning("Please enter a licence key.")
        else:
            from core.licence_verifier import validate_licence_key
            with st.sidebar.spinner("Validating…"):
                result = validate_licence_key(licence_key)
            if result["valid"]:
                plan_key = result.get("plan") or _TIER_TO_PLAN.get(result["tier"], "free")
                tier_display = result["tier"]
                st.session_state.account_tier = tier_display
                set_plan_key(plan_key)
                st.sidebar.success(f"Activated — {tier_display} plan.")
            else:
                st.session_state.account_tier = "Free"
                set_plan_key("free")
                st.sidebar.error(result["error"] or "Invalid or expired licence key.")


def _render_tier_badge() -> None:
    tier_name = st.session_state.get("account_tier", "Free")
    tier = get_tier(tier_name)
    if tier_name == "Free":
        st.sidebar.info(f"Plan: **{tier['label']}** · {tier['price']}")
    else:
        st.sidebar.success(f"Plan: **{tier['label']}** · {tier['price']}")
    st.sidebar.caption(tier["blurb"])


def _render_upgrade_ctas() -> None:
    from config.plans import PLAN_ORDER, get_plan, get_next_paid_plan

    st.sidebar.markdown("---")
    tier_name = st.session_state.get("account_tier", "Free")
    plan_key = _TIER_TO_PLAN.get(tier_name, "free")

    if plan_key == "enterprise":
        return

    if not is_payments_live():
        st.sidebar.caption("Paid plans launching soon — activate your licence key above once you have one.")
        return

    current_idx = PLAN_ORDER.index(plan_key) if plan_key in PLAN_ORDER else 0
    upgrade_options = [p for p in PLAN_ORDER[current_idx + 1:] if p != "free"]
    if not upgrade_options:
        return

    recommended = get_next_paid_plan(plan_key) or upgrade_options[0]

    from config.branding_config import branding as _branding

    with st.sidebar.container(border=True):
        st.markdown(
            f"<span style='font-size:0.7rem;font-weight:700;letter-spacing:0.06em;"
            f"text-transform:uppercase;color:{_branding['primary_colour']};opacity:0.75;'>"
            f"Upgrade your plan</span>",
            unsafe_allow_html=True,
        )
        selected = st.selectbox(
            "Choose a plan",
            upgrade_options,
            index=upgrade_options.index(recommended),
            format_func=lambda key: get_plan(key)["label"],
            label_visibility="collapsed",
            key="_upgrade_plan_select",
        )
        plan = get_plan(selected)
        st.markdown(
            f"<div style='font-size:1.35rem;font-weight:700;color:{_branding['primary_colour']};"
            f"margin:0.1rem 0 0.25rem 0;'>{plan['price']}</div>",
            unsafe_allow_html=True,
        )
        st.caption(plan["blurb"])

        url = get_checkout_url(plan["label"])
        if url:
            st.link_button(f"Upgrade to {plan['label']} →", url, use_container_width=True, type="primary")


def _render_dev_tier_override() -> None:
    """Tier override dropdown — visible in desktop/local mode or when testing_mode = true."""
    try:
        dev_cfg = st.secrets.get("dev", {})
        is_desktop = (
            dev_cfg.get("testing_mode", False)
            or dev_cfg.get("local_dev", False)
            or dev_cfg.get("app_mode", "") == "desktop"
        )
        if not is_desktop:
            return
    except Exception:
        return

    with st.sidebar.expander("Select Plan (Internal)", expanded=False):
        current = st.session_state.get("account_tier", "Free")
        tier_override = st.selectbox(
            "Force tier",
            list(TIERS.keys()),
            index=list(TIERS.keys()).index(current),
            key="_dev_tier_override",
        )
        if tier_override != current:
            st.session_state.account_tier = tier_override
            set_plan_key(_TIER_TO_PLAN.get(tier_override, "free"))
            st.rerun()


def render_sidebar_subscription_panel() -> None:
    """Single call that renders the complete sidebar subscription UI.

    Combines licence activation, plan badge, run counter, and upgrade CTAs.
    Reads branding from config internally — no arguments required.
    Call this once per page load in place of render_tier_selector().
    """
    from config.branding_config import branding as _branding
    from ui.upgrade_prompts import render_run_counter

    render_tier_selector(_branding)
    plan_key = _TIER_TO_PLAN.get(st.session_state.get("account_tier", "Free"), "free")
    render_run_counter(plan_key)


def render_locked_feature(title: str, description: str, required_tier: str = "Pro") -> None:
    """Renders a locked-feature card with an upgrade prompt and checkout link."""
    tier = get_tier(required_tier)
    checkout_url = get_checkout_url(required_tier)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f"#### {title}")
    st.caption(description)

    if checkout_url:
        st.info(f"Available on the **{tier['label']}** plan ({tier['price']}).")
        st.link_button(f"Upgrade to {tier['label']}", checkout_url)
    else:
        st.info(
            f"Available on the **{tier['label']}** plan ({tier['price']}). "
            "Paid plans are launching soon — activate your licence key in the sidebar once you have one."
        )

    st.markdown('</div>', unsafe_allow_html=True)


def feature_unlocked(tier_name: str, feature: str) -> bool:
    plan_key = _TIER_TO_PLAN.get(tier_name, tier_name.lower())
    mapped = _FEATURE_MAP.get(feature, feature)
    return has_feature(plan_key, mapped)

import streamlit as st

from config.tier_config import TIERS, get_tier
from config.lemonsqueezy_config import get_checkout_url, is_payments_live
from services.entitlements import has_feature

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
                st.session_state.account_tier = result["tier"]
                st.sidebar.success(f"Activated — {result['tier']} plan.")
            else:
                st.session_state.account_tier = "Free"
                st.sidebar.error(result["error"] or "Invalid or expired licence key.")


def _render_tier_badge() -> None:
    tier_name = st.session_state.get("account_tier", "Free")
    tier = get_tier(tier_name)
    if tier_name == "Free":
        st.sidebar.info(f"Plan: **{tier['label']}** · {tier['price']}")
    else:
        st.sidebar.success(f"Plan: **{tier['label']}** · {tier['price']}")
    st.sidebar.caption(tier["blurb"])
    row_limit = tier["row_limit"]
    if row_limit is not None:
        st.sidebar.caption(f"Row limit: {row_limit:,} rows per upload")
    else:
        st.sidebar.caption("Row limit: Unlimited")


def _render_upgrade_ctas() -> None:
    st.sidebar.markdown("---")
    tier_name = st.session_state.get("account_tier", "Free")

    if tier_name == "Enterprise":
        return

    if not is_payments_live():
        st.sidebar.caption("Paid plans launching soon — activate your licence key above once you have one.")
        return

    st.sidebar.markdown("**Upgrade your plan**")

    if tier_name != "Pro":
        pro_url = get_checkout_url("Pro")
        if pro_url:
            st.sidebar.link_button("Pro", pro_url, use_container_width=True)

    ent_url = get_checkout_url("Enterprise")
    if ent_url:
        st.sidebar.link_button("Enterprise", ent_url, use_container_width=True)


def _render_dev_tier_override() -> None:
    """Tier override dropdown — visible only when dev.testing_mode = true in secrets.toml."""
    try:
        if not st.secrets.get("dev", {}).get("testing_mode", False):
            return
    except Exception:
        return

    with st.sidebar.expander("Dev: override tier", expanded=False):
        current = st.session_state.get("account_tier", "Free")
        tier_override = st.selectbox(
            "Force tier",
            list(TIERS.keys()),
            index=list(TIERS.keys()).index(current),
            key="_dev_tier_override",
        )
        if tier_override != current:
            st.session_state.account_tier = tier_override
            st.rerun()


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

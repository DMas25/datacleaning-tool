import streamlit as st

from config.tier_config import TIERS, get_tier, has_feature


def render_tier_selector(branding):
    """Sidebar control for the active (simulated) account tier.

    This is scaffolding for the SaaS pricing model — there is no live
    payment processor wired up, so the tier is just a session-state value
    the user can switch for demo/testing purposes.
    """
    st.sidebar.markdown(f"### {branding['app_name']} Plans")

    if "account_tier" not in st.session_state:
        st.session_state.account_tier = "Free"

    tier_name = st.sidebar.selectbox(
        "Account tier (demo)",
        list(TIERS.keys()),
        index=list(TIERS.keys()).index(st.session_state.account_tier),
        key="account_tier",
    )

    tier = get_tier(tier_name)
    st.sidebar.caption(f"**{tier['label']}** · {tier['price']}")
    st.sidebar.caption(tier["blurb"])

    row_limit = tier["row_limit"]
    if row_limit is not None:
        st.sidebar.caption(f"Row limit: {row_limit:,} rows per upload")
    else:
        st.sidebar.caption("Row limit: Unlimited")

    return tier_name


def render_locked_feature(title: str, description: str, required_tier: str = "Pro"):
    """Renders a consistent 'locked feature' placeholder card with an upgrade prompt."""
    tier = get_tier(required_tier)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f"#### 🔒 {title}")
    st.caption(description)
    st.info(
        f"This feature is available on the **{tier['label']}** plan ({tier['price']}). "
        f"Upgrade to unlock full report access."
    )
    st.button(f"Unlock with {tier['label']}", key=f"unlock_{title}", disabled=True,
              help="Upgrade flow is not yet connected to a payment provider.")
    st.markdown('</div>', unsafe_allow_html=True)


def feature_unlocked(tier_name: str, feature: str) -> bool:
    return has_feature(tier_name, feature)

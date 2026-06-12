import streamlit as st

from config.plans import PLAN_CONFIG, PLAN_ORDER
from services.billing import checkout_url, payments_live


_FEATURE_LABELS = {
    "can_download_excel": "Excel export",
    "can_download_pdf": "PDF reports",
    "can_view_advanced_insights": "Advanced AI insights",
    "can_brand_reports": "Custom branding",
}


def render_pricing_page() -> None:
    """Convenience wrapper — reads the active plan from session and renders the full pricing table.

    Designed to be dropped inside an st.expander() or a modal.
    """
    from utils.session_helpers import get_plan_key
    render_pricing_cards(current_plan_key=get_plan_key())


def render_pricing_cards(current_plan_key: str = "free") -> None:
    """Full pricing table — call from a modal or dedicated pricing page."""
    # Prevent price text from wrapping and allow the card grid to scroll
    # horizontally on narrow viewports rather than crushing each column.
    st.markdown(
        """
        <style>
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 160px;
        }
        div[data-testid="stHorizontalBlock"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## ColtraDataAi Plans")
    st.caption("Choose the plan that fits your data volume and workflow.")

    cols = st.columns(len(PLAN_ORDER), gap="small")
    for col, plan_key in zip(cols, PLAN_ORDER):
        plan = PLAN_CONFIG[plan_key]
        is_current = plan_key == current_plan_key

        with col:
            if is_current:
                st.success(f"**{plan['label']}** ✓ Current")
            else:
                st.markdown(f"**{plan['label']}**")

            # Use HTML so the price never wraps mid-string
            st.markdown(
                f"<p style='font-size:1.5rem;font-weight:700;margin:4px 0;white-space:nowrap'>"
                f"{plan['price']}</p>",
                unsafe_allow_html=True,
            )
            st.caption(plan["blurb"])
            st.markdown("---")

            runs = plan["monthly_runs"]
            st.caption(f"Runs/month: {'Unlimited' if runs is None else runs}")
            st.caption(f"Rows: {plan['max_rows_backend']:,}")
            st.caption(f"File size: {plan['max_file_mb_backend']} MB")

            st.markdown("")
            for feature_key, label in _FEATURE_LABELS.items():
                icon = "✅" if plan.get(feature_key) else "—"
                st.caption(f"{icon} {label}")

            if not is_current:
                url = checkout_url(plan_key)
                if url:
                    st.link_button(f"Get {plan['label']}", url, use_container_width=True)
                elif plan_key != "free":
                    if payments_live():
                        st.button(
                            f"Get {plan['label']}",
                            disabled=True,
                            use_container_width=True,
                            key=f"_pricing_btn_{plan_key}",
                        )
                    else:
                        st.caption("Coming soon")

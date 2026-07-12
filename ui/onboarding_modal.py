"""Onboarding modal — shown once per paying subscriber on first activation.

Captures:
  - Profile: full name, company, country (required), phone and VAT (optional)
  - Compliance consent: T&C, Privacy Policy (required), marketing opt-in (optional)

Uses st.dialog (Streamlit >= 1.30).  After a successful submission the session
flag "onboarding_complete" is set and st.rerun() is called so the main app
renders immediately without re-showing the dialog.
"""
from __future__ import annotations

import streamlit as st

from services.licence_manager import (
    get_by_email,
    save_compliance_consent,
    update_customer_profile,
)

_COUNTRIES = [
    "United Kingdom",
    "United States",
    "South Africa",
    "Zimbabwe",
    "Nigeria",
    "Kenya",
    "Ghana",
    "Canada",
    "Australia",
    "Ireland",
    "India",
    "Germany",
    "France",
    "Netherlands",
    "Spain",
    "Portugal",
    "UAE",
    "Singapore",
    "New Zealand",
    "Other",
]


def needs_onboarding(email: str) -> bool:
    """Return True if this subscriber still needs to complete the onboarding form.

    Returns False when:
      - The session flag "onboarding_complete" is already set (avoids a DB
        round-trip on every rerun after onboarding is done)
      - The plan is "free" (free users are not put through onboarding)
      - The subscription row already has a non-empty customer_name (onboarding
        was completed in a previous session)
    """
    if st.session_state.get("onboarding_complete"):
        return False

    plan = st.session_state.get("plan_key", "free")
    if plan == "free":
        return False

    if not email:
        return False

    row = get_by_email(email)
    if row is None:
        return False

    # customer_name column may not exist yet in the current SQLite schema
    customer_name = row.get("customer_name", "") or ""
    if customer_name and customer_name != "Not provided":
        # Already completed in a previous session — mark the flag so we don't
        # hit the DB again this session.
        st.session_state["onboarding_complete"] = True
        return False

    return True


@st.dialog("Complete your account setup", width="large")
def show_onboarding_modal(email: str) -> None:
    """Render the onboarding form inside a Streamlit modal dialog."""

    st.markdown("### Your details")

    customer_name = st.text_input(
        "Full name *",
        key="_ob_customer_name",
        placeholder="e.g. Jane Smith",
    )
    company_name = st.text_input(
        "Company / Organisation *",
        key="_ob_company_name",
        placeholder="e.g. Acme Ltd",
    )
    country = st.selectbox(
        "Country *",
        options=[""] + _COUNTRIES,
        key="_ob_country",
        format_func=lambda x: "Select your country" if x == "" else x,
    )
    phone = st.text_input(
        "Phone number (optional)",
        key="_ob_phone",
        placeholder="e.g. +44 7700 900000",
    )
    vat_number = st.text_input(
        "VAT number (optional)",
        key="_ob_vat_number",
        placeholder="e.g. GB123456789",
        help="If VAT-registered, include country prefix e.g. GB123456789",
    )

    st.markdown("### Legal & communications")

    t_and_c = st.checkbox(
        "I have read and agree to the [Terms & Conditions](https://coltradata.com/terms)",
        key="_ob_t_and_c",
    )
    privacy = st.checkbox(
        "I have read and agree to the [Privacy Policy](https://coltradata.com/privacy)",
        key="_ob_privacy",
    )
    marketing = st.checkbox(
        "I'm happy to receive product updates and tips by email",
        key="_ob_marketing",
        value=False,
    )

    st.caption("\\* Required. Your information is processed in accordance with our Privacy Policy and never sold.")

    if st.button("Complete setup", type="primary", use_container_width=True):
        errors = []
        if not customer_name.strip():
            errors.append("full name")
        if not company_name.strip():
            errors.append("company / organisation")
        if not country:
            errors.append("country")
        if not t_and_c:
            errors.append("Terms & Conditions acceptance")
        if not privacy:
            errors.append("Privacy Policy acceptance")

        if errors:
            st.error(
                "Please complete all required fields and accept the Terms & Conditions and Privacy Policy."
            )
            return

        update_customer_profile(
            email,
            customer_name=customer_name.strip(),
            company_name=company_name.strip(),
            phone=phone.strip(),
            country=country,
            vat_number=vat_number.strip(),
        )
        save_compliance_consent(
            email,
            t_and_c=t_and_c,
            privacy=privacy,
            marketing=marketing,
        )

        st.session_state["onboarding_complete"] = True
        st.rerun()

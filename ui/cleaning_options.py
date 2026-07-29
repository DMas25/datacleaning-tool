"""Step 2: Cleaning configuration panel for ColtraDataAi."""
from __future__ import annotations

from typing import List

import streamlit as st

from core.cleaner import CleaningOptions
from core.clinical_cleaner import ResearcherProfile
from ui.branding_components import render_step_header

_DATASET_TYPES = [
    "General",
    "🧬 Clinical Research & Trial Registers",
    "📦 Logistics & Supply Chain",
    "🌐 Import/Export & Trade",
    "💰 Finance & Accounting",
    "🛍️ Retail & Inventory",
    "💼 Consultants & Professional Services",
    "🏥 Healthcare (Operational)",
    "🏢 SME & Small Business",
    "🏨 Hospitality & Accommodation",
]

_CLINICAL_LABEL     = "🧬 Clinical Research & Trial Registers"
_LOGISTICS_LABEL    = "📦 Logistics & Supply Chain"
_TRADE_LABEL        = "🌐 Import/Export & Trade"
_FINANCE_LABEL      = "💰 Finance & Accounting"
_RETAIL_LABEL       = "🛍️ Retail & Inventory"
_CONSULTANT_LABEL   = "💼 Consultants & Professional Services"
_HEALTHCARE_LABEL   = "🏥 Healthcare (Operational)"
_SME_LABEL          = "🏢 SME & Small Business"
_HOSPITALITY_LABEL  = "🏨 Hospitality & Accommodation"

_CLINICAL_INFO = (
    "Clinical Research mode applies additional validation on top of the "
    "standard cleaning pipeline: NCT ID normalisation, researcher name "
    "standardisation, trial ID zero-padding, registry code normalisation, "
    "and a nested researcher → trial sequence register in your results."
)

_LOGISTICS_INFO = (
    "Logistics & Supply Chain mode standardises shipment status labels, "
    "carrier names, and weight units. It calculates transit times, flags "
    "impossible date orders (delivery before dispatch), and identifies "
    "duplicate tracking numbers."
)

_TRADE_INFO = (
    "Import/Export & Trade mode validates HS codes (6-10 digits), maps country "
    "names to ISO 3166-1 alpha-2 codes, standardises currency symbols (GBP/USD/EUR), "
    "and checks declared values for negatives or zeros that would fail customs "
    "declaration."
)

_FINANCE_INFO = (
    "Finance & Accounting mode normalises UK nominal account codes (0000–9999), "
    "validates VAT/tax codes against recognised UK schemes (Sage, Xero), checks "
    "trial balance (debit = credit), and flags blank or generic narrative descriptions "
    "that would weaken an audit trail."
)

_RETAIL_INFO = (
    "Retail & Inventory mode standardises SKU codes, checks price/cost margins "
    "(flags items where cost exceeds selling price), detects negative stock levels, "
    "flags items below reorder point, validates EAN-13 and UPC-A barcodes (including "
    "check digit), and identifies duplicate SKUs."
)

_CONSULTANT_INFO = (
    "Consultants & Professional Services mode validates timesheet hours (flags entries "
    "exceeding 24 hours), checks day rates and hourly rates for zeros or negatives, "
    "formats project codes, calculates utilisation rate (billable vs total hours), "
    "and detects budget overruns where actual hours exceed budgeted."
)

_HEALTHCARE_INFO = (
    "Healthcare (Operational) mode validates NHS numbers using the Modulus 11 check "
    "digit algorithm, checks ICD-10 diagnosis code format, standardises appointment "
    "status labels, calculates waiting times (referral → appointment), flags 18-week "
    "RTT breaches and high DNA rates, standardises staff categories, and validates "
    "UK postcodes."
)

_SME_INFO = (
    "SME & Small Business mode validates UK postcodes, NI numbers (AB123456C format), "
    "VAT registration numbers (GB format), and Companies House numbers. It also detects "
    "overdue invoices, standardises UK phone numbers to +44 E.164 format, normalises "
    "payment terms (Net 30, Net 60, etc.), and flags duplicate invoice numbers."
)

_HOSPITALITY_INFO = (
    "Hospitality & Accommodation mode standardises booking references, validates "
    "check-in / check-out date pairs (flags impossible and zero-night stays), "
    "normalises room type labels (Double, Suite, etc.), standardises booking "
    "status (Confirmed / Cancelled / No-Show) and channel values (OTA / Direct / "
    "Corporate), validates guest counts, and produces ADR (average daily rate) "
    "and revenue summaries."
)


def render_cleaning_options(branding: dict) -> CleaningOptions:
    """
    Render the cleaning configuration widgets and return a CleaningOptions
    dataclass populated from user selections.
    """
    render_step_header(2, "Configure Cleaning Options", branding=branding)

    # ── Dataset type ──────────────────────────────────────────────────────────
    dataset_type = st.selectbox(
        "Dataset type",
        _DATASET_TYPES,
        index=0,
        help="Select 'Clinical Research' to enable ID validation, zfill registry "
             "normalisation, and the researcher → trial sequence results view.",
    )

    _INFO_MAP = {
        _CLINICAL_LABEL:   _CLINICAL_INFO,
        _LOGISTICS_LABEL:  _LOGISTICS_INFO,
        _TRADE_LABEL:      _TRADE_INFO,
        _FINANCE_LABEL:    _FINANCE_INFO,
        _RETAIL_LABEL:     _RETAIL_INFO,
        _CONSULTANT_LABEL: _CONSULTANT_INFO,
        _HEALTHCARE_LABEL:   _HEALTHCARE_INFO,
        _SME_LABEL:          _SME_INFO,
        _HOSPITALITY_LABEL:  _HOSPITALITY_INFO,
    }
    if dataset_type in _INFO_MAP:
        st.info(_INFO_MAP[dataset_type])

    st.divider()

    # ── Standard cleaning options ──────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    with c1:
        remove_duplicates = st.checkbox("Remove duplicates", value=True)
    with c2:
        trim_whitespace = st.checkbox("Trim whitespace", value=True)
    with c3:
        standardise_headers = st.checkbox("Standardise headers", value=True)

    null_handling = st.selectbox(
        "Missing values handling",
        ["No Change", "Fill with blank", "Fill with placeholder"],
    )

    return CleaningOptions(
        remove_duplicates=remove_duplicates,
        trim_whitespace=trim_whitespace,
        standardise_headers=standardise_headers,
        null_handling=null_handling,
        dataset_type=dataset_type,
    )


# ---------------------------------------------------------------------------
# Clinical Research results view  (call after apply_clinical_cleaning())
# ---------------------------------------------------------------------------

def render_clinical_results_view(profiles: List[ResearcherProfile]) -> None:
    """Render verified researcher profiles with their trial sequences as expanders.

    Designed to be called from results_panel after clinical cleaning completes.
    Each researcher profile is one expander; trials are listed inside.
    """
    if not profiles:
        st.info(
            "No researcher profiles found. Ensure your dataset contains a "
            "'researcher_id' column in RES-NNNN format."
        )
        return

    verified_count = sum(1 for p in profiles if p.verified)
    st.caption(
        f"{len(profiles)} researcher profile(s) — "
        f"{verified_count} verified, {len(profiles) - verified_count} flagged"
    )

    for profile in profiles:
        status_icon = "✓" if profile.verified else "⚠"
        label = (
            f"{status_icon}  {profile.researcher_id} "
            f"— {profile.trial_count} trial(s)"
            + ("" if profile.verified else "  · ID format issue")
        )

        with st.expander(label, expanded=False):
            if not profile.trials:
                st.write("No trials recorded.")
                continue

            for trial in profile.trials:
                trial_id = trial.get("trial_id", "—")
                phase    = trial.get("phase",    "—")
                status   = trial.get("status",   "—")
                valid    = trial.get("researcher_valid", True)

                status_lower = str(status).lower()
                if status_lower in ("completed",):
                    badge = "🟢"
                elif status_lower in ("active", "ongoing", "recruiting"):
                    badge = "🔵"
                elif status_lower in ("terminated", "withdrawn", "suspended"):
                    badge = "🔴"
                else:
                    badge = "⚪"

                id_flag = "" if valid else " ⚠ ID unverified"
                st.write(
                    f"{badge} **{trial_id}** &nbsp;|&nbsp; "
                    f"Phase: {phase} &nbsp;|&nbsp; "
                    f"Status: {status}{id_flag}"
                )

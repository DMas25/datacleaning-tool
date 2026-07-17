"""Step 2: Cleaning configuration panel for ColtraDataAi."""
from __future__ import annotations

from typing import List

import streamlit as st

from core.cleaner import CleaningOptions
from core.clinical_cleaner import ResearcherProfile
from ui.branding_components import render_step_header

_DATASET_TYPES = ["General", "🧬 Clinical Research & Trial Registers"]

_CLINICAL_LABEL = "🧬 Clinical Research & Trial Registers"

_CLINICAL_INFO = (
    "Clinical Research mode applies additional validation on top of the "
    "standard cleaning pipeline: NCT ID normalisation, researcher name "
    "standardisation, trial ID zero-padding, registry code normalisation, "
    "and a nested researcher → trial sequence register in your results."
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

    if dataset_type == _CLINICAL_LABEL:
        st.info(_CLINICAL_INFO)

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

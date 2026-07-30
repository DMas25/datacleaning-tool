"""Column rename presets for common accounting software exports.

Presets are applied AFTER header standardisation (step 2 of the cleaning pipeline)
so all source keys are already normalised: lowercase, spaces/hyphens → underscores.

Only columns that genuinely fail keyword detection are included — columns the
cleaners already find via keyword or fuzzy matching are omitted. Each preset is
documented with the gap it closes.
"""
from __future__ import annotations

import pandas as pd

# ── Preset definitions ────────────────────────────────────────────────────────

_PRESET_RENAMES: dict[str, dict[str, str]] = {

    "Xero — Account Transactions": {
        # 'Source Name' (document type) → journal reference field
        "source_name": "journal_ref",
        # 'Journal Number' as an explicit journal ref (backup for 'reference' col)
        "journal_number": "journal_no",
    },

    "Xero — Aged Debtors / Creditors": {
        # 'Date' on aged reports = the invoice issue date, not today's date.
        # The SME cleaner looks for 'invoice_date' not plain 'date'.
        "date": "invoice_date",
    },

    "Sage 50 — Audit Trail": {
        # Sage exports 'T/C' (tax code) which normalises to 't_c'.
        # The finance cleaner keyword 'tc' does not match 't_c' (underscore breaks it).
        "t_c": "vat_code",
        # 'Ref' is only 3 characters — below the 4-char minimum for abbreviation
        # detection in column_mapper._detect(). Explicit rename fixes it.
        "ref": "journal_ref",
    },

    "QuickBooks — Transaction Detail": {
        # QB uses 'Memo/Description' which normalises to 'memo_description'.
        # The narrative keywords ('memo', 'details') are substrings of this,
        # so this is a safety-net rename in case the substring match misses it.
        "memo_description": "narrative",
    },
}

# Labels shown in the UI dropdown (same keys, friendly display text)
PRESET_OPTIONS: list[str] = ["None"] + list(_PRESET_RENAMES.keys())


def apply_preset(
    df: pd.DataFrame, preset_name: str
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Rename columns in *df* according to the named preset.

    Returns ``(renamed_df, applied_renames)`` where ``applied_renames`` is a
    dict of ``{original_col: new_col}`` for every rename that was actually
    applied. Renames are skipped if the target column already exists in the
    DataFrame (avoids duplicate column names).
    """
    if not preset_name or preset_name == "None":
        return df, {}

    renames = _PRESET_RENAMES.get(preset_name, {})
    if not renames:
        return df, {}

    df = df.copy()
    applied: dict[str, str] = {}
    for src, tgt in renames.items():
        if src in df.columns and tgt not in df.columns:
            df = df.rename(columns={src: tgt})
            applied[src] = tgt

    return df, applied

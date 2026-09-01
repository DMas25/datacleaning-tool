"""Clinical Research dataset cleaner for ColtraDataAi.

Domain-specific cleaning pass that runs after the standard pipeline:
  1. Regex identity validation  — researcher IDs and patient IDs
  2. NCT ID normalisation       — ClinicalTrials.gov format (NCT + 8 digits)
  3. Investigator name cleanup  — strips titles, enforces Last, First format
  4. zfill registry logic       — trial IDs and registry codes to fixed width
  5. Trial sequence builder     — groups verified trials under researcher profiles
  6. File-level orchestrator    — load → auto-detect columns → clean → group
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. RESEARCHER & PATIENT ID VALIDATION  (regex identity filters)
# ---------------------------------------------------------------------------

_DEFAULT_RESEARCHER_PATTERN = r"^RES-\d{4}$"   # e.g. RES-0042
_DEFAULT_PATIENT_PATTERN    = r"^PAT-\d{6}$"   # e.g. PAT-001234


def _id_validation(
    df: pd.DataFrame,
    col: str,
    flag_col: str,
    check_name: str,
    pattern: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Shared logic for ID column regex validation."""
    df = df.copy()
    if col not in df.columns:
        return df, pd.DataFrame([{
            "check": check_name, "column": col,
            "valid": 0, "invalid": 0, "missing": 0,
            "note": f"Column '{col}' not found — skipped",
        }])

    rx = re.compile(pattern)
    present = df[col].notna()
    valid_mask = present & df[col].astype(str).map(lambda v: bool(rx.match(v)))
    # Null rows are not invalid — mark True so the flag doesn't mislead
    df[flag_col] = valid_mask | ~present

    return df, pd.DataFrame([{
        "check":   check_name,
        "column":  col,
        "valid":   int(valid_mask.sum()),
        "invalid": int((present & ~valid_mask).sum()),
        "missing": int(df[col].isna().sum()),
        "note":    f"Pattern: {pattern}",
    }])


def validate_researcher_ids(
    df: pd.DataFrame,
    col: str = "researcher_id",
    pattern: str = _DEFAULT_RESEARCHER_PATTERN,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Flag researcher IDs that don't match the expected format.

    Adds a boolean helper column `_researcher_id_valid`.
    Does not alter source data — flags only.
    """
    return _id_validation(df, col, "_researcher_id_valid", "researcher_id_validation", pattern)


def validate_patient_ids(
    df: pd.DataFrame,
    col: str = "patient_id",
    pattern: str = _DEFAULT_PATIENT_PATTERN,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Flag patient IDs that don't match the expected format.

    Adds a boolean helper column `_patient_id_valid`.
    """
    return _id_validation(df, col, "_patient_id_valid", "patient_id_validation", pattern)


# ---------------------------------------------------------------------------
# 2. NCT ID NORMALISATION  (ClinicalTrials.gov identifier format)
# ---------------------------------------------------------------------------

_NCT_SEPARATOR_PATTERN = re.compile(r"[\s\-_:]")
_NCT_DIGITS_PATTERN    = re.compile(r"\D")
# Recognise values that are plausibly NCT IDs before normalisation.
# Accepts optional separators and leading/trailing whitespace, e.g.:
#   "NCT00001234", "nct-1234", " NCT 1234 "
# Rejects ISRCTN, EudraCT, and other registry prefixes so they are
# returned unchanged rather than silently mangled.
_NCT_CANDIDATE_PATTERN = re.compile(r"^\s*n\s*c\s*t[\s\-_:]?\d", re.IGNORECASE)


def clean_nct_id(nct_str: object) -> Optional[str]:
    """Standardise a messy NCT ID to uppercase NCT + 8 digits.

    Only processes values that are recognisably NCT format.  Non-NCT
    registry identifiers (ISRCTN, EudraCT, etc.) are returned unchanged
    so they are not silently converted into a plausible-but-wrong NCT ID.

    Examples:
        "nct-0001234"      → "NCT00001234"
        " NCT 1234 "       → "NCT00001234"
        "NCT00001234"      → "NCT00001234"  (already correct)
        "ISRCTN12345678"   → "ISRCTN12345678"  (non-NCT, left unchanged)
        None / NaN         → None
    """
    if pd.isna(nct_str):
        return None
    raw = str(nct_str)
    if not _NCT_CANDIDATE_PATTERN.match(raw):
        return raw  # not an NCT identifier — leave untouched
    cleaned = _NCT_SEPARATOR_PATTERN.sub("", raw).upper()
    digits  = _NCT_DIGITS_PATTERN.sub("", cleaned)
    if digits:
        return f"NCT{digits.zfill(8)}"
    return cleaned


def normalise_nct_ids(
    df: pd.DataFrame,
    col: str = "nct_id",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply clean_nct_id() across a DataFrame column and return (df, log).

    Column values are updated in-place on the copy; nulls stay null.
    """
    df = df.copy()
    if col not in df.columns:
        return df, pd.DataFrame([{
            "action": "nct_id_normalisation", "column": col,
            "normalised": 0, "already_correct": 0, "missing": 0,
            "note": f"Column '{col}' not found — skipped",
        }])

    original = df[col].copy()
    df[col] = df[col].apply(clean_nct_id)

    missing    = int(original.isna().sum())
    changed    = original.notna() & (df[col] != original)
    # Values that were not NCT candidates are returned unchanged by clean_nct_id;
    # distinguish them from values that were already correctly formatted.
    non_nct    = original.notna() & ~original.astype(str).map(
        lambda v: bool(_NCT_CANDIDATE_PATTERN.match(v))
    )
    normalised = int(changed.sum())
    already_ok = int((original.notna() & ~changed & ~non_nct).sum())
    skipped    = int(non_nct.sum())

    return df, pd.DataFrame([{
        "action":              "nct_id_normalisation",
        "column":              col,
        "normalised":          normalised,
        "already_correct":     already_ok,
        "skipped_non_nct":     skipped,
        "missing":             missing,
        "note":                "Format: NCT + 8 digits (zfill); non-NCT registry IDs left unchanged",
    }])


# ---------------------------------------------------------------------------
# 3. INVESTIGATOR NAME STANDARDISATION
# ---------------------------------------------------------------------------

_TITLE_PATTERN = re.compile(
    # Tokens ending with '.' (Dr., Ph.D., M.D.) can't use trailing \b because
    # '.' is a non-word character — \s* consumes the separator instead.
    # Tokens ending with a letter (MD, PhD) use \b normally.
    r"\b(?:Dr\.|Ph\.D\.|M\.D\.)\s*|\b(?:MD|PhD)\b\s*", flags=re.IGNORECASE
)
_MULTI_SPACE = re.compile(r"\s+")


def standardize_name(name_str: object) -> str:
    """Normalise a physician/researcher name to 'Last, First' format.

    - Strips common title tokens (Dr., MD, PhD, Ph.D., M.D.)
    - Already-comma-formatted names are returned as-is after title stripping
    - Single-token names are returned unchanged
    - Null / NaN → "Unknown Investigator"

    Examples:
        "Dr. Jane Smith"    → "Smith, Jane"
        "John A. Doe MD"    → "Doe, John A."
        "Smith, Jane"       → "Smith, Jane"  (already correct)
        None                → "Unknown Investigator"
    """
    if pd.isna(name_str):
        return "Unknown Investigator"

    name = _TITLE_PATTERN.sub("", str(name_str).strip())
    name = _MULTI_SPACE.sub(" ", name).strip()

    if "," in name:
        return name

    parts = name.split(" ")
    if len(parts) >= 2:
        return f"{parts[-1]}, {' '.join(parts[:-1])}"
    return name


def standardise_researcher_names(
    df: pd.DataFrame,
    col: str = "investigator",
    out_col: str = "standardized_researcher",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply standardize_name() across a DataFrame column and return (df, log).

    Writes results to `out_col` (default "standardized_researcher") so the
    original column is preserved for audit purposes.
    """
    df = df.copy()
    if col not in df.columns:
        return df, pd.DataFrame([{
            "action": "name_standardisation", "source_column": col,
            "output_column": out_col, "standardised": 0, "unknowns": 0,
            "note": f"Column '{col}' not found — skipped",
        }])

    df[out_col] = df[col].apply(standardize_name)
    unknowns    = int((df[out_col] == "Unknown Investigator").sum())
    standardised = int(df[out_col].notna().sum()) - unknowns

    return df, pd.DataFrame([{
        "action":        "name_standardisation",
        "source_column": col,
        "output_column": out_col,
        "standardised":  standardised,
        "unknowns":      unknowns,
        "note":          "Format: Last, First (titles stripped)",
    }])


# ---------------------------------------------------------------------------
# 4. REGISTRY CODE NORMALISATION  (zfill-based padding)
# ---------------------------------------------------------------------------

def normalise_trial_ids(
    df: pd.DataFrame,
    col: str = "trial_id",
    prefix: str = "TRIAL-",
    width: int = 4,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Standardise trial IDs to <prefix><zero-padded number> format.

    Examples (prefix="TRIAL-", width=4):
        "42"         → "TRIAL-0042"
        "TRIAL-7"    → "TRIAL-0007"
        "TRIAL-0042" → unchanged (already correct)

    Non-conforming values that cannot be normalised are left unchanged.
    """
    df = df.copy()
    if col not in df.columns:
        return df, pd.DataFrame([{
            "action": "trial_id_normalisation", "column": col,
            "normalised": 0, "skipped_non_conforming": 0,
            "note": f"Column '{col}' not found — skipped",
        }])

    normalised = 0
    skipped    = 0

    def _normalise(val: object) -> object:
        nonlocal normalised, skipped
        if pd.isna(val):
            return val
        s = str(val).strip()
        s_upper      = s.upper()
        prefix_upper = prefix.upper()
        numeric_part = s[len(prefix):] if s_upper.startswith(prefix_upper) else s
        if numeric_part.isdigit():
            normalised += 1
            return f"{prefix}{numeric_part.zfill(width)}"
        skipped += 1
        return val

    df[col] = df[col].apply(_normalise)
    return df, pd.DataFrame([{
        "action": "trial_id_normalisation",
        "column": col,
        "normalised": normalised,
        "skipped_non_conforming": skipped,
        "note": f"Padded to {prefix}<{width}-digit>",
    }])


def pad_registry_codes(
    df: pd.DataFrame,
    col: str = "registry_code",
    width: int = 6,
    prefix: Optional[str] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Zero-pad registry codes to a fixed character width using zfill.

    With prefix="REG-", width=6:  "REG-42" or "42" → "REG-000042"
    Without prefix, width=6:      "42"              → "000042"

    Bare numerics are accepted even when a prefix is specified — the prefix
    is attached automatically (common in exports that omit it).
    """
    df = df.copy()
    if col not in df.columns:
        return df, pd.DataFrame([{
            "action": "registry_code_padding", "column": col,
            "padded": 0, "skipped": 0,
            "note": f"Column '{col}' not found — skipped",
        }])

    padded  = 0
    skipped = 0

    def _pad(val: object) -> object:
        nonlocal padded, skipped
        if pd.isna(val):
            return val
        s = str(val).strip()
        if prefix:
            prefix_upper = prefix.upper()
            if s.upper().startswith(prefix_upper):
                numeric_part = s[len(prefix):]
            elif s.isdigit():
                numeric_part = s  # bare numeric → attach prefix
            else:
                skipped += 1
                return val
        else:
            numeric_part = s
        if numeric_part.isdigit():
            padded += 1
            return f"{prefix}{numeric_part.zfill(width)}" if prefix else numeric_part.zfill(width)
        skipped += 1
        return val

    df[col] = df[col].apply(_pad)
    return df, pd.DataFrame([{
        "action":  "registry_code_padding",
        "column":  col,
        "padded":  padded,
        "skipped": skipped,
        "note":    f"Width={width}" + (f", prefix='{prefix}'" if prefix else ""),
    }])


# ---------------------------------------------------------------------------
# 5. RESEARCHER ENTITY RESOLUTION
# ---------------------------------------------------------------------------

def _parse_last_first(name: str) -> tuple[str, list[str]]:
    """Split 'Last, First...' into (last_name, [first_tokens]).

    Names without a comma are returned as (name, []) and left unchanged.
    """
    if "," not in name:
        return name.strip(), []
    last, _, rest = name.partition(",")
    return last.strip(), [t for t in rest.strip().split() if t]


def _first_tokens_match(a_tokens: list[str], b_tokens: list[str]) -> bool:
    """Return True when the primary first tokens refer to the same given name.

    Handles three cases:
        - Exact match:   "John"  == "John"
        - Initial match: "J."   matches "John"  (or vice-versa)
        - Prefix match:  "John" matches "John A." (middle initial extension)
    """
    if not a_tokens or not b_tokens:
        return False
    a0, b0 = a_tokens[0].upper(), b_tokens[0].upper()
    if a0 == b0:
        return True
    # One side is a single initial ending with a period
    if a0.endswith(".") and len(a0) == 2 and b0.startswith(a0[0]):
        return True
    if b0.endswith(".") and len(b0) == 2 and a0.startswith(b0[0]):
        return True
    return False


def _canonical_name(variants: list[str]) -> str:
    """Pick the most complete name from a cluster of matched variants.

    'Most complete' = most space-separated tokens after stripping commas,
    breaking ties by preferring the version that already contains a comma
    (i.e. is already in Last, First format).
    """
    def _score(n: str) -> tuple[int, int]:
        tokens = n.replace(",", " ").split()
        return (len(tokens), int("," in n))
    return max(variants, key=_score)


def resolve_researcher_entities(
    df: pd.DataFrame,
    col: str = "standardized_researcher",
    out_col: str = "canonical_researcher",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge name variants of the same researcher into a single canonical form.

    Works in three passes:
        1. Parse each "Last, First" name into (last, [first_tokens])
        2. Within each last-name group, union-find names whose primary first
           tokens match (exact, initial, or prefix)
        3. Replace every variant with the most complete name in its cluster

    Writes the resolved name to *out_col* and leaves *col* unchanged for audit.

    No fuzzy / external library — pure string logic, O(n²) within last-name
    groups (groups are small in practice).
    """
    df = df.copy()
    if col not in df.columns:
        return df, pd.DataFrame([{
            "action": "entity_resolution", "source_column": col,
            "output_column": out_col, "clusters_found": 0,
            "variants_merged": 0, "note": f"Column '{col}' not found — skipped",
        }])

    unique_names = df[col].dropna().unique().tolist()

    # ── Build last-name groups ────────────────────────────────────────────────
    last_groups: dict[str, list[str]] = {}
    for name in unique_names:
        last, _ = _parse_last_first(name)
        last_groups.setdefault(last.upper(), []).append(name)

    # ── Union-find within each last-name group ────────────────────────────────
    # parent[name] = representative of name's cluster
    parent: dict[str, str] = {n: n for n in unique_names}

    def _find(n: str) -> str:
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def _union(a: str, b: str) -> None:
        parent[_find(a)] = _find(b)

    for names_in_group in last_groups.values():
        for i in range(len(names_in_group)):
            for j in range(i + 1, len(names_in_group)):
                na, nb = names_in_group[i], names_in_group[j]
                _, fa = _parse_last_first(na)
                _, fb = _parse_last_first(nb)
                if _first_tokens_match(fa, fb):
                    _union(na, nb)

    # ── Build cluster → canonical mapping ────────────────────────────────────
    clusters: dict[str, list[str]] = {}
    for name in unique_names:
        root = _find(name)
        clusters.setdefault(root, []).append(name)

    name_to_canonical: dict[str, str] = {}
    for members in clusters.values():
        canon = _canonical_name(members)
        for m in members:
            name_to_canonical[m] = canon

    df[out_col] = df[col].map(name_to_canonical).fillna(df[col])

    merged_count  = sum(1 for v in clusters.values() if len(v) > 1)
    variant_count = sum(len(v) - 1 for v in clusters.values() if len(v) > 1)

    log = pd.DataFrame([{
        "action":         "entity_resolution",
        "source_column":  col,
        "output_column":  out_col,
        "clusters_found": merged_count,
        "variants_merged": variant_count,
        "note": (
            f"{merged_count} researcher(s) resolved from {variant_count + merged_count} "
            f"variant(s) → {merged_count} canonical form(s)"
        ),
    }])
    return df, log


# ---------------------------------------------------------------------------
# 6. TRIAL SEQUENCE BUILDER
# ---------------------------------------------------------------------------

@dataclass
class ResearcherProfile:
    researcher_id: str
    trials: List[Dict] = field(default_factory=list)

    @property
    def trial_count(self) -> int:
        return len(self.trials)

    @property
    def verified(self) -> bool:
        """True when ALL trial rows carry a valid researcher ID flag."""
        return all(t.get("researcher_valid", True) for t in self.trials)


def build_trial_sequences(
    df: pd.DataFrame,
    researcher_col: str = "researcher_id",
    trial_col:      str = "trial_id",
    phase_col:      str = "phase",
    status_col:     str = "status",
) -> tuple[List[ResearcherProfile], pd.DataFrame]:
    """Group cleaned trial rows under their researcher profiles.

    Returns (profiles, log) where profiles is a list of ResearcherProfile
    objects ordered by researcher_id, each holding a list of trial dicts.
    """
    if researcher_col not in df.columns:
        log = pd.DataFrame([{
            "action": "build_trial_sequences",
            "researchers_found": 0, "total_trials": 0,
            "note": f"Column '{researcher_col}' not found — skipped",
        }])
        return [], log

    profiles: List[ResearcherProfile] = []
    rows_log: List[Dict] = []

    for researcher_id, group in df.groupby(researcher_col, sort=True):
        profile = ResearcherProfile(researcher_id=str(researcher_id))
        for _, row in group.iterrows():
            profile.trials.append({
                "trial_id":         row[trial_col]  if trial_col  in df.columns else "—",
                "phase":            row[phase_col]   if phase_col  in df.columns else "—",
                "status":           row[status_col]  if status_col in df.columns else "—",
                "researcher_valid": bool(row.get("_researcher_id_valid", True)),
            })
        profiles.append(profile)
        rows_log.append({
            "researcher_id": researcher_id,
            "trials":        profile.trial_count,
            "verified":      profile.verified,
        })

    log = (
        pd.DataFrame(rows_log)
        if rows_log
        else pd.DataFrame(columns=["researcher_id", "trials", "verified"])
    )
    return profiles, log


# ---------------------------------------------------------------------------
# 6b. ROW-LEVEL AUDIT DIFF
# ---------------------------------------------------------------------------

def _diff_changes(
    before: pd.DataFrame,
    after: pd.DataFrame,
    rule: str,
    run_id: str,
    timestamp: str,
) -> pd.DataFrame:
    """Return one row per changed cell between two DataFrames for audit logging."""
    records = []
    shared_cols = [c for c in before.columns if c in after.columns]
    for col in shared_cols:
        b = before[col].fillna("__NULL__")
        a = after[col].fillna("__NULL__")
        changed_idx = before.index[b != a]
        for idx in changed_idx:
            records.append({
                "run_id":    run_id,
                "timestamp": timestamp,
                "row":       int(idx),
                "column":    col,
                "before":    before.at[idx, col],
                "after":     after.at[idx, col],
                "rule":      rule,
            })
    if records:
        return pd.DataFrame(records, columns=["run_id", "timestamp", "row", "column", "before", "after", "rule"])
    return pd.DataFrame(columns=["run_id", "timestamp", "row", "column", "before", "after", "rule"])


# ---------------------------------------------------------------------------
# 7. ORCHESTRATORS
# ---------------------------------------------------------------------------

@dataclass
class ClinicalCleaningResult:
    cleaned_df: pd.DataFrame
    profiles:   List[ResearcherProfile]
    logs:       Dict[str, pd.DataFrame] = field(default_factory=dict)
    grouped_df: Optional[pd.DataFrame]  = None   # researcher → [trial_ids]
    audit_log:  pd.DataFrame             = field(default_factory=pd.DataFrame)  # row-level change log
    flags_df:   Optional[pd.DataFrame]  = None   # per-row ID validity flags for audit
    run_id:     str                      = field(default_factory=lambda: str(uuid.uuid4()))
    cleaned_at: str                      = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_INTERNAL_FLAG_COLS = ["_researcher_id_valid", "_patient_id_valid"]


def apply_clinical_cleaning(
    df: pd.DataFrame,
    researcher_col:      str           = "researcher_id",
    patient_col:         str           = "patient_id",
    trial_col:           str           = "trial_id",
    registry_col:        str           = "registry_code",
    nct_col:             Optional[str] = None,
    researcher_name_col: Optional[str] = None,
    trial_id_prefix:     str           = "TRIAL-",
    trial_id_width:      int           = 4,
    registry_width:      int           = 6,
    registry_prefix:     Optional[str] = None,
) -> ClinicalCleaningResult:
    """Run all clinical-specific cleaning steps in order.

    Steps:
        1. Validate researcher IDs (regex)
        2. Validate patient IDs (regex)
        3. Normalise NCT IDs          (if nct_col is supplied)
        4. Standardise researcher names (if researcher_name_col is supplied)
        5. Normalise internal trial IDs (zfill)
        6. Pad registry codes (zfill)
        7. Build trial sequences under researcher profiles
    """
    run_id     = str(uuid.uuid4())
    cleaned_at = datetime.now(timezone.utc).isoformat()
    cleaned = df.copy()
    logs: Dict[str, pd.DataFrame] = {}
    audit_frames: List[pd.DataFrame] = []

    _before = cleaned.copy()
    cleaned, logs["researcher_id"] = validate_researcher_ids(cleaned, researcher_col)
    audit_frames.append(_diff_changes(_before, cleaned, "researcher_id_validation", run_id, cleaned_at))

    _before = cleaned.copy()
    cleaned, logs["patient_id"]    = validate_patient_ids(cleaned, patient_col)
    audit_frames.append(_diff_changes(_before, cleaned, "patient_id_validation", run_id, cleaned_at))

    if nct_col:
        _before = cleaned.copy()
        cleaned, logs["nct_ids"] = normalise_nct_ids(cleaned, nct_col)
        audit_frames.append(_diff_changes(_before, cleaned, "nct_id_normalisation", run_id, cleaned_at))

    if researcher_name_col:
        _before = cleaned.copy()
        cleaned, logs["researcher_names"] = standardise_researcher_names(
            cleaned, col=researcher_name_col
        )
        audit_frames.append(_diff_changes(_before, cleaned, "researcher_name_standardisation", run_id, cleaned_at))
        # Entity resolution: merge name variants ("J. Smith", "Smith, John",
        # "John A. Smith MD") into a single canonical researcher identity.
        _before = cleaned.copy()
        cleaned, logs["entity_resolution"] = resolve_researcher_entities(
            cleaned, col="standardized_researcher"
        )
        audit_frames.append(_diff_changes(_before, cleaned, "entity_resolution", run_id, cleaned_at))

    _before = cleaned.copy()
    cleaned, logs["trial_ids"] = normalise_trial_ids(
        cleaned, trial_col, prefix=trial_id_prefix, width=trial_id_width,
    )
    audit_frames.append(_diff_changes(_before, cleaned, "trial_id_normalisation", run_id, cleaned_at))

    _before = cleaned.copy()
    cleaned, logs["registry"]  = pad_registry_codes(
        cleaned, registry_col, width=registry_width, prefix=registry_prefix,
    )
    audit_frames.append(_diff_changes(_before, cleaned, "registry_code_padding", run_id, cleaned_at))
    # Prefer canonical_researcher (post entity-resolution) for grouping;
    # fall back to standardized_researcher (name-only) then researcher_col (ID).
    if "canonical_researcher" in cleaned.columns:
        _seq_col = "canonical_researcher"
    elif "standardized_researcher" in cleaned.columns:
        _seq_col = "standardized_researcher"
    else:
        _seq_col = researcher_col
    profiles, logs["sequences"] = build_trial_sequences(
        cleaned,
        researcher_col=_seq_col,
        trial_col=trial_col,
    )

    # Build grouped_df (researcher → list of trial IDs) when both cols exist
    grouped_df: Optional[pd.DataFrame] = None
    if "canonical_researcher" in cleaned.columns:
        group_by_col = "canonical_researcher"
    elif "standardized_researcher" in cleaned.columns:
        group_by_col = "standardized_researcher"
    else:
        group_by_col = researcher_col
    if group_by_col in cleaned.columns and trial_col in cleaned.columns:
        grouped_df = (
            cleaned.groupby(group_by_col)[trial_col]
            .apply(list)
            .reset_index()
            .rename(columns={group_by_col: "researcher", trial_col: "trial_ids"})
        )

    # Capture per-row validity flags into audit output before stripping
    _flag_cols_present = [c for c in _INTERNAL_FLAG_COLS if c in cleaned.columns]
    flags_df: Optional[pd.DataFrame] = (
        cleaned[_flag_cols_present].copy() if _flag_cols_present else None
    )
    cleaned = cleaned.drop(columns=_flag_cols_present, errors="ignore")

    audit_log = (
        pd.concat(audit_frames, ignore_index=True)
        if audit_frames
        else pd.DataFrame(columns=["run_id", "timestamp", "row", "column", "before", "after", "rule"])
    )

    return ClinicalCleaningResult(
        cleaned_df=cleaned,
        profiles=profiles,
        logs=logs,
        grouped_df=grouped_df,
        audit_log=audit_log,
        flags_df=flags_df,
        run_id=run_id,
        cleaned_at=cleaned_at,
    )


def process_clinical_template(file_path: str) -> pd.DataFrame:
    """Load, clean, and group a raw clinical trial file.

    Auto-detects the trial ID and investigator columns by name heuristic,
    applies NCT normalisation and name standardisation, then returns a
    DataFrame of researcher → [cleaned_trial_id] groupings.

    Raises ValueError if the required columns cannot be identified.
    """
    df = (
        pd.read_csv(file_path)
        if str(file_path).endswith(".csv")
        else pd.read_excel(file_path)
    )
    df.columns = [col.lower().strip() for col in df.columns]

    trial_col = next(
        (c for c in df.columns if "trial" in c or "nct" in c), None
    )
    pi_col = next(
        (c for c in df.columns if "investigator" in c or "pi" in c or "name" in c),
        None,
    )

    if not trial_col or not pi_col:
        raise ValueError(
            "Could not identify Trial ID or Investigator columns in dataset. "
            f"Columns found: {list(df.columns)}"
        )

    df["cleaned_trial_id"]       = df[trial_col].apply(clean_nct_id)
    df["standardized_researcher"] = df[pi_col].apply(standardize_name)

    grouped_data = (
        df.groupby("standardized_researcher")["cleaned_trial_id"]
        .apply(list)
        .reset_index()
    )
    return grouped_data

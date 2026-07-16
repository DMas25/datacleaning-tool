"""Free Data Health Check — analysis engine.

Performs a read-only analysis on an uploaded DataFrame and returns a
structured report dict. The original DataFrame is never mutated and no
raw data is stored — only aggregated statistics are returned.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from core.profiler import profile_dataframe

# ── Score weights (must sum to 100) ──────────────────────────────────────────
_W_COMPLETENESS = 35
_W_UNIQUENESS   = 20
_W_CONSISTENCY  = 25
_W_STRUCTURE    = 20

_MAX_FREE_ROWS   = 5_000
_MAX_FREE_MB     = 10.0
_ALLOWED_TYPES   = {"csv", "xlsx"}


# ── File validation ───────────────────────────────────────────────────────────

def validate_upload(file_bytes: bytes, file_name: str, file_size_mb: float) -> Tuple[bool, str]:
    """Return (ok, error_message). Called before any parsing."""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in _ALLOWED_TYPES:
        return False, f"Unsupported file type '.{ext}'. Please upload a CSV or XLSX file."

    if file_size_mb > _MAX_FREE_MB:
        return False, (
            f"File is {file_size_mb:.1f} MB — the free health check is limited to "
            f"{_MAX_FREE_MB:.0f} MB. Upgrade to process larger files."
        )

    # XLSX magic bytes: PK\x03\x04 (ZIP signature)
    if ext == "xlsx" and not file_bytes[:4] == b"PK\x03\x04":
        return False, "The file does not appear to be a valid Excel (.xlsx) file."

    return True, ""


def validate_row_count(df: pd.DataFrame) -> Tuple[bool, str, pd.DataFrame]:
    """Enforce the row limit and return (ok, message, df_to_use)."""
    if len(df) > _MAX_FREE_ROWS:
        return (
            False,
            (
                f"Your file has {len(df):,} rows. The free health check analyses up to "
                f"{_MAX_FREE_ROWS:,} rows. The first {_MAX_FREE_ROWS:,} rows have been used."
            ),
            df.head(_MAX_FREE_ROWS),
        )
    return True, "", df


# ── Score components ──────────────────────────────────────────────────────────

def _completeness_score(profile: dict) -> Tuple[int, str]:
    missing_pct = 100.0 - profile["completeness_pct"]
    if missing_pct == 0:
        return _W_COMPLETENESS, "No missing values"
    if missing_pct < 5:
        return int(_W_COMPLETENESS * 0.85), f"{missing_pct:.1f}% of values are missing"
    if missing_pct < 20:
        return int(_W_COMPLETENESS * 0.55), f"{missing_pct:.1f}% of values are missing"
    if missing_pct < 50:
        return int(_W_COMPLETENESS * 0.25), f"{missing_pct:.1f}% missing — significant gaps detected"
    return 0, f"{missing_pct:.1f}% missing — critical data gaps"


def _uniqueness_score(profile: dict) -> Tuple[int, str]:
    dup  = profile["duplicate_total"]
    rows = max(profile["rows"], 1)
    pct  = (dup / rows) * 100
    if dup == 0:
        return _W_UNIQUENESS, "No duplicate records"
    if pct < 2:
        return int(_W_UNIQUENESS * 0.85), f"{dup:,} duplicate records ({pct:.1f}%)"
    if pct < 10:
        return int(_W_UNIQUENESS * 0.50), f"{dup:,} duplicate records ({pct:.1f}%)"
    return 0, f"{dup:,} duplicate records ({pct:.1f}%) — data integrity concern"


def detect_formatting_issues(df: pd.DataFrame) -> List[Dict]:
    """Return per-column formatting inconsistencies (does not modify df)."""
    issues: List[Dict] = []

    for col in df.select_dtypes(include=["object"]).columns:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue

        # Mixed capitalisation: same string in different cases
        exact = set(series.str.strip())
        lower = set(series.str.strip().str.lower())
        case_variants = len(exact) - len(lower)
        if case_variants >= 2:
            issues.append({
                "column": str(col),
                "issue": "Mixed capitalisation",
                "detail": f"{case_variants} value(s) in multiple casing variants",
                "count": case_variants,
            })

        # Leading/trailing whitespace
        ws_count = int((series != series.str.strip()).sum())
        if ws_count > 0:
            issues.append({
                "column": str(col),
                "issue": "Leading/trailing whitespace",
                "detail": f"{ws_count:,} cell(s) have extra spaces",
                "count": ws_count,
            })

        # Numeric values mixed into a text column
        numeric_like = int(series.str.match(r"^\s*-?\d+(\.\d+)?\s*$").sum())
        text_like    = len(series) - numeric_like
        if 0 < numeric_like < len(series) and text_like > 0:
            issues.append({
                "column": str(col),
                "issue": "Mixed numeric and text",
                "detail": f"{numeric_like:,} numeric-looking value(s) mixed with text",
                "count": numeric_like,
            })

    return issues


def _consistency_score(issues: List[Dict], total_cols: int) -> Tuple[int, str]:
    if not issues:
        return _W_CONSISTENCY, "No formatting inconsistencies found"
    issue_cols = len({i["column"] for i in issues})
    ratio = issue_cols / max(total_cols, 1)
    if ratio < 0.1:
        return int(_W_CONSISTENCY * 0.80), f"{len(issues)} minor formatting issue(s) detected"
    if ratio < 0.3:
        return int(_W_CONSISTENCY * 0.50), f"{len(issues)} issue(s) across {issue_cols} column(s)"
    return int(_W_CONSISTENCY * 0.20), f"{len(issues)} issue(s) across {issue_cols} column(s) — review recommended"


def _structure_score(df: pd.DataFrame) -> Tuple[int, str]:
    penalty = 0
    notes   = []

    empty_cols = [c for c in df.columns if df[c].isnull().all()]
    if empty_cols:
        penalty += min(8, len(empty_cols) * 3)
        notes.append(f"{len(empty_cols)} completely empty column(s)")

    unnamed = [
        c for c in df.columns
        if re.match(r"^(unnamed|column\s*\d+|col\s*\d+)$", str(c).strip().lower())
    ]
    if unnamed:
        penalty += min(6, len(unnamed) * 2)
        notes.append(f"{len(unnamed)} generic/unnamed header(s)")

    empty_rows = int(df.isnull().all(axis=1).sum())
    if empty_rows:
        penalty += min(6, empty_rows)
        notes.append(f"{empty_rows} empty row(s)")

    pts   = max(0, _W_STRUCTURE - penalty)
    label = "; ".join(notes) if notes else "Structure looks healthy"
    return pts, label


# ── Observations ──────────────────────────────────────────────────────────────

def _top_3_observations(df: pd.DataFrame, profile: dict, issues: List[Dict]) -> List[str]:
    obs: List[str] = []

    # 1 — data composition
    n_num  = len(df.select_dtypes(include=[np.number]).columns)
    n_text = len(df.select_dtypes(include=["object"]).columns)
    obs.append(
        f"Your dataset contains {profile['rows']:,} rows and {profile['columns']} columns "
        f"({n_num} numeric, {n_text} text/categorical)."
    )

    # 2 — biggest concern
    missing_pct = 100.0 - profile["completeness_pct"]
    dup_count   = profile["duplicate_total"]
    dup_pct     = round((dup_count / max(profile["rows"], 1)) * 100, 1)

    if missing_pct > 20:
        worst_col = max(profile["missing_by_col"], key=lambda c: profile["missing_by_col"][c])
        worst_pct = round(
            profile["missing_by_col"][worst_col] / max(profile["rows"], 1) * 100, 1
        )
        obs.append(
            f"Column '{worst_col}' has the most missing data at {worst_pct}% — "
            f"overall {missing_pct:.1f}% of all cells are empty."
        )
    elif dup_count > 0:
        obs.append(
            f"{dup_count:,} duplicate row(s) detected ({dup_pct}% of records) — "
            f"removing these improves accuracy of any aggregation or reporting."
        )
    elif issues:
        first = issues[0]
        obs.append(
            f"Column '{first['column']}' has {first['issue'].lower()}: {first['detail']}."
        )
    else:
        complete = sum(1 for v in profile["missing_by_col"].values() if v == 0)
        obs.append(
            f"{complete} of {profile['columns']} columns are 100% complete with no missing values."
        )

    # 3 — numeric insight or overall completeness
    num_df = df.select_dtypes(include=[np.number])
    if not num_df.empty:
        col    = num_df.columns[0]
        series = num_df[col].dropna()
        if len(series) >= 2:
            obs.append(
                f"'{col}' ranges from {series.min():,.2f} to {series.max():,.2f} "
                f"with a mean of {series.mean():,.2f}."
            )
        else:
            obs.append(
                f"The dataset is {profile['completeness_pct']:.1f}% complete overall "
                f"across {profile['rows']:,} rows and {profile['columns']} columns."
            )
    else:
        obs.append(
            f"The dataset is {profile['completeness_pct']:.1f}% complete overall "
            f"across {profile['rows']:,} rows and {profile['columns']} columns."
        )

    return obs[:3]


# ── Charts ────────────────────────────────────────────────────────────────────

def _gauge_chart(score: int, branding: dict) -> go.Figure:
    primary = branding.get("primary_colour", "#1F4E79")
    colour  = "#46D324" if score >= 80 else ("#F59E0B" if score >= 60 else "#DC2626")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": "Data Quality Score", "font": {"size": 13, "color": primary}},
        number={"suffix": "/100", "font": {"size": 26, "color": colour}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#657286"},
            "bar":  {"color": colour},
            "bgcolor": "white",
            "steps": [
                {"range": [0, 40],   "color": "#FEF2F2"},
                {"range": [40, 70],  "color": "#FFFBEB"},
                {"range": [70, 100], "color": "#F0FDF4"},
            ],
        },
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=15, r=15, t=35, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Helvetica, Arial, sans-serif"),
    )
    return fig


def _missing_values_chart(profile: dict, branding: dict) -> Optional[go.Figure]:
    missing = {k: v for k, v in profile["missing_by_col"].items() if v > 0}
    if not missing:
        return None
    top10   = dict(sorted(missing.items(), key=lambda x: x[1], reverse=True)[:10])
    primary = branding.get("primary_colour", "#1F4E79")
    fig = px.bar(
        x=list(top10.values()),
        y=list(top10.keys()),
        orientation="h",
        labels={"x": "Missing Cells", "y": "Column"},
        color_discrete_sequence=[primary],
    )
    fig.update_layout(
        height=max(180, len(top10) * 30 + 60),
        margin=dict(l=10, r=20, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Helvetica, Arial, sans-serif", size=11),
        yaxis=dict(autorange="reversed"),
        xaxis=dict(gridcolor="#E6ECF0"),
    )
    return fig


def _column_type_chart(df: pd.DataFrame, branding: dict) -> go.Figure:
    counts = {
        "Numeric":   len(df.select_dtypes(include=[np.number]).columns),
        "Text":      len(df.select_dtypes(include=["object"]).columns),
        "Date/Time": len(df.select_dtypes(include=["datetime64"]).columns),
    }
    other = len(df.columns) - sum(counts.values())
    if other:
        counts["Other"] = other
    labels = [k for k, v in counts.items() if v > 0]
    values = [v for v in counts.values() if v > 0]
    palette = branding.get("chart_palette", ["#1F4E79", "#2E86AB", "#48C9B0", "#F4D03F"])
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.5,
        marker_colors=palette[:len(labels)],
        textfont_size=11,
    ))
    fig.update_layout(
        height=190,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", y=-0.2, font=dict(size=10)),
        font=dict(family="Helvetica, Arial, sans-serif"),
    )
    return fig


# ── Public API ────────────────────────────────────────────────────────────────

def run_health_check(df: pd.DataFrame, file_name: str, file_size_mb: float, branding: dict) -> Dict:
    """Run the complete health check and return a structured result dict.

    The result dict is JSON-serialisable except for the '_charts' key,
    which contains Plotly Figure objects for in-session rendering only.
    """
    profile = profile_dataframe(df)
    issues  = detect_formatting_issues(df)

    c_pts, c_lbl = _completeness_score(profile)
    u_pts, u_lbl = _uniqueness_score(profile)
    f_pts, f_lbl = _consistency_score(issues, profile["columns"])
    s_pts, s_lbl = _structure_score(df)

    score = c_pts + u_pts + f_pts + s_pts

    return {
        "quality_score": score,
        "score_breakdown": {
            "completeness": {"score": c_pts, "max": _W_COMPLETENESS, "label": c_lbl},
            "uniqueness":   {"score": u_pts, "max": _W_UNIQUENESS,   "label": u_lbl},
            "consistency":  {"score": f_pts, "max": _W_CONSISTENCY,  "label": f_lbl},
            "structure":    {"score": s_pts, "max": _W_STRUCTURE,    "label": s_lbl},
        },
        "file_name":         file_name,
        "file_size_mb":      round(file_size_mb, 2),
        "rows":              profile["rows"],
        "columns":           profile["columns"],
        "completeness_pct":  profile["completeness_pct"],
        "missing_total":     profile["missing_total"],
        "missing_by_col":    {str(k): int(v) for k, v in profile["missing_by_col"].items()},
        "duplicate_total":   profile["duplicate_total"],
        "formatting_issues": issues,
        "observations":      _top_3_observations(df, profile, issues),
        "dtypes":            {str(k): str(v) for k, v in profile["dtypes"].items()},
        "_charts": {
            "gauge":          _gauge_chart(score, branding),
            "missing_values": _missing_values_chart(profile, branding),
            "column_types":   _column_type_chart(df, branding),
        },
    }

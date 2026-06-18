"""ColtraDataAI — tiered Claude advisory insights.

Model, token budget, and prompt depth scale with the subscriber's plan to
minimise API spend while still delivering value at every paid tier.

Tier matrix
───────────────────────────────────────────────────────────────────────────────
Plan           Model                      Max tokens  Summary depth  Insights
─────────────  ─────────────────────────  ──────────  ─────────────  ────────
professional   claude-haiku-4-5-20251001  400         compact        3–5
premium        claude-sonnet-4-6          900         standard       5–8
enterprise     claude-opus-4-8            2800        full           8–12
───────────────────────────────────────────────────────────────────────────────

Returns None gracefully on any failure so callers never need to handle errors.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

# ── Tier → model ──────────────────────────────────────────────────────────────

_MODEL: dict[str, str] = {
    "professional": "claude-haiku-4-5-20251001",
    "premium":      "claude-sonnet-4-6",
    "enterprise":   "claude-opus-4-8",
}

_MAX_TOKENS: dict[str, int] = {
    "professional": 400,
    "premium":      900,
    "enterprise":   2800,
}

# How many numeric / categorical columns to include in the prompt context.
# Reduces input tokens for cheaper tiers without losing the key signals.
_SUMMARY_DEPTH: dict[str, dict] = {
    "professional": {"num_cols": 8,  "cat_cols": 5,  "correlations": False},
    "premium":      {"num_cols": 12, "cat_cols": 8,  "correlations": True},
    "enterprise":   {"num_cols": 20, "cat_cols": 12, "correlations": True},
}

# ── Prompt templates per tier ─────────────────────────────────────────────────

_PROMPT: dict[str, str] = {
    "professional": (
        "You are a data analyst reviewing a freshly cleaned dataset. "
        "Based only on the summary below, give 3–5 concise bullet-point insights. "
        "Focus on: data quality issues, obvious anomalies, and the single most important next step. "
        "Be brief and direct. Do not restate the numbers.\n\n"
        "Dataset summary:\n{summary}"
    ),
    "premium": (
        "You are a senior data advisor reviewing a dataset that a user has just cleaned. "
        "Based on the statistical summary below, provide 5–8 actionable insights.\n\n"
        "Focus on:\n"
        "- What the data suggests about the underlying business or domain\n"
        "- Patterns or anomalies worth investigating further\n"
        "- Data quality risks that may affect downstream analysis\n"
        "- Concrete next steps the user should consider\n\n"
        "Be specific and practical. Use bullet points. Do not merely restate the numbers.\n\n"
        "Dataset summary:\n{summary}"
    ),
    "enterprise": (
        "You are a principal data scientist and business intelligence advisor. "
        "A dataset has just been cleaned and you have been given a full statistical profile. "
        "Provide 8–12 comprehensive insights structured under these headings:\n\n"
        "**Data Quality Assessment** — completeness, consistency, reliability risks\n"
        "**Business & Domain Signals** — what the data reveals about the business context\n"
        "**Statistical Patterns** — distributions, correlations, outliers worth noting\n"
        "**Modelling & Analytics Readiness** — suitability for ML/BI, feature engineering hints\n"
        "**Recommended Next Steps** — prioritised actions, ranked by impact\n\n"
        "Be authoritative, specific, and commercially aware. "
        "Cite column names and figures where relevant. Do not pad with generic advice.\n\n"
        "Dataset summary:\n{summary}"
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────

def generate_ai_advisory(df: pd.DataFrame, plan_key: str = "professional") -> str | None:
    """Return markdown advisory from Claude scaled to the subscriber's plan tier.

    Returns None on any failure — missing key, API error, unconfigured plan.
    """
    try:
        api_key = st.secrets["anthropic"]["api_key"]
    except Exception:
        return None

    if not api_key or api_key.startswith("sk-ant-REPLACE"):
        return None

    model      = _MODEL.get(plan_key)
    max_tokens = _MAX_TOKENS.get(plan_key)
    depth      = _SUMMARY_DEPTH.get(plan_key)
    prompt_tpl = _PROMPT.get(plan_key)

    if not all([model, max_tokens, depth, prompt_tpl]):
        return None

    try:
        import anthropic

        summary = _build_data_summary(df, depth)
        prompt  = prompt_tpl.format(summary=summary)

        client   = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        for block in reversed(response.content):
            if block.type == "text":
                return block.text

        return None

    except Exception:
        return None


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_data_summary(df: pd.DataFrame, depth: dict) -> str:
    """Compact statistical summary scaled to the tier's context-depth budget."""
    parts: list[str] = []

    parts.append(f"Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    total_cells   = len(df) * len(df.columns)
    total_missing = int(df.isnull().sum().sum())
    overall_pct   = round(total_missing / max(total_cells, 1) * 100, 1)
    parts.append(f"Overall missing: {overall_pct}%")

    missing_by_col = df.isnull().mean().mul(100).round(1)
    missing_cols   = [(c, p) for c, p in missing_by_col.items() if p > 0]
    if missing_cols:
        cap     = depth["num_cols"]
        snippet = ", ".join(f"{c} ({p}%)" for c, p in missing_cols[:cap])
        if len(missing_cols) > cap:
            snippet += f" … (+{len(missing_cols) - cap} more)"
        parts.append(f"Columns with missing values: {snippet}")

    dup_count = int(df.duplicated().sum())
    if dup_count:
        parts.append(
            f"Duplicate rows: {dup_count:,} "
            f"({round(dup_count / max(len(df), 1) * 100, 1)}%)"
        )

    num_df  = df.select_dtypes(include=[np.number])
    num_cap = depth["num_cols"]
    if not num_df.empty:
        parts.append("\nNumeric columns:")
        desc = num_df.describe().T
        for col in list(desc.index)[:num_cap]:
            r = desc.loc[col]
            parts.append(
                f"  {col}: min={r['min']:.2f}  max={r['max']:.2f}  "
                f"mean={r['mean']:.2f}  std={r['std']:.2f}"
            )

    cat_df  = df.select_dtypes(include=["object"])
    cat_cap = depth["cat_cols"]
    if not cat_df.empty:
        parts.append("\nCategorical columns:")
        for col in list(cat_df.columns)[:cat_cap]:
            n_unique = int(cat_df[col].nunique())
            top      = cat_df[col].value_counts().head(3)
            top_str  = ", ".join(f"'{v}' ({c})" for v, c in top.items())
            parts.append(f"  {col}: {n_unique} unique  |  top 3: {top_str}")

    if depth["correlations"] and num_df.shape[1] >= 2:
        corr   = num_df.corr(numeric_only=True)
        strong : list[str] = []
        seen   : set[tuple] = set()
        for col_a in corr.columns:
            for col_b in corr.columns:
                if col_a == col_b or (col_b, col_a) in seen:
                    continue
                seen.add((col_a, col_b))
                val = corr.loc[col_a, col_b]
                if pd.notna(val) and abs(val) >= 0.7:
                    strong.append(f"{col_a} & {col_b} (r={val:.2f})")
        if strong:
            parts.append("\nStrong correlations (|r| ≥ 0.70): " + ", ".join(strong[:8]))

    return "\n".join(parts)

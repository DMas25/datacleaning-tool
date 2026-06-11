"""ColtraDataAI — Claude-powered advisory insights for Pro/Enterprise users.

Calls the Anthropic Messages API to generate actionable, interpretive insights
from the cleaned dataset. Returns None gracefully if the API key is absent or
the call fails, allowing the caller to fall back to rules-based insights.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st


def generate_ai_advisory(df: pd.DataFrame) -> str | None:
    """Return markdown advisory insights from Claude, or None on any failure."""
    try:
        api_key = st.secrets["anthropic"]["api_key"]
    except Exception:
        return None

    if not api_key or api_key.startswith("sk-ant-REPLACE"):
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        summary = _build_data_summary(df)

        prompt = (
            "You are a senior data advisor reviewing a dataset that a user has just cleaned "
            "using a data quality tool. Based on the statistical summary below, provide concise, "
            "actionable advisory insights.\n\n"
            "Focus on:\n"
            "- What the data suggests about the underlying business or domain\n"
            "- Patterns or anomalies worth investigating further\n"
            "- Data quality risks that may affect downstream analysis or modelling\n"
            "- Concrete next steps the user should consider\n\n"
            "Be specific, direct, and practical. Use bullet points. Limit to 5-8 key insights. "
            "Do not merely restate the numbers — interpret them.\n\n"
            f"Dataset summary:\n{summary}"
        )

        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in reversed(response.content):
            if block.type == "text":
                return block.text

        return None

    except Exception:
        return None


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_data_summary(df: pd.DataFrame) -> str:
    """Produce a compact statistical summary suitable for an LLM prompt."""
    parts: list[str] = []

    parts.append(f"Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    # Overall missing
    total_cells = len(df) * len(df.columns)
    total_missing = int(df.isnull().sum().sum())
    overall_pct = round(total_missing / max(total_cells, 1) * 100, 1)
    parts.append(f"Overall missing cells: {overall_pct}%")

    # Per-column missing (non-zero only, capped at 10)
    missing_by_col = df.isnull().mean().mul(100).round(1)
    missing_cols = [(col, pct) for col, pct in missing_by_col.items() if pct > 0]
    if missing_cols:
        snippet = ", ".join(f"{col} ({pct}%)" for col, pct in missing_cols[:10])
        if len(missing_cols) > 10:
            snippet += f" … (+{len(missing_cols) - 10} more)"
        parts.append(f"Columns with missing values: {snippet}")

    # Duplicate rows
    dup_count = int(df.duplicated().sum())
    if dup_count:
        parts.append(
            f"Duplicate rows: {dup_count:,} "
            f"({round(dup_count / max(len(df), 1) * 100, 1)}%)"
        )

    # Numeric stats (capped at 15 columns)
    num_df = df.select_dtypes(include=[np.number])
    if not num_df.empty:
        parts.append("\nNumeric columns:")
        desc = num_df.describe().T
        for col in list(desc.index)[:15]:
            r = desc.loc[col]
            parts.append(
                f"  {col}: min={r['min']:.2f}  max={r['max']:.2f}  "
                f"mean={r['mean']:.2f}  std={r['std']:.2f}"
            )

    # Categorical / text columns (capped at 10)
    cat_df = df.select_dtypes(include=["object"])
    if not cat_df.empty:
        parts.append("\nCategorical columns:")
        for col in list(cat_df.columns)[:10]:
            n_unique = int(cat_df[col].nunique())
            top = cat_df[col].value_counts().head(3)
            top_str = ", ".join(f"'{v}' ({c})" for v, c in top.items())
            parts.append(f"  {col}: {n_unique} unique  |  top 3: {top_str}")

    # Strong correlations
    if num_df.shape[1] >= 2:
        corr = num_df.corr(numeric_only=True)
        strong: list[str] = []
        seen: set[tuple] = set()
        for col_a in corr.columns:
            for col_b in corr.columns:
                if col_a == col_b or (col_b, col_a) in seen:
                    continue
                seen.add((col_a, col_b))
                val = corr.loc[col_a, col_b]
                if pd.notna(val) and abs(val) >= 0.7:
                    strong.append(f"{col_a} & {col_b} (r={val:.2f})")
        if strong:
            parts.append(
                "\nStrong correlations (|r| ≥ 0.70): " + ", ".join(strong[:6])
            )

    return "\n".join(parts)

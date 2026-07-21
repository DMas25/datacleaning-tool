"""ColtraDataAI — tiered Claude advisory insights.

Model, token budget, and prompt depth scale with the subscriber's plan to
minimise API spend while still delivering value at every paid tier.

Every tier returns the same fixed six-section structure (Executive Bottom
Line, Key Data Insights, AI Advisory, Modelling & Analytics Readiness, Top
Priority Actions, Bottom Line Summary) — see advisory_text.SECTION_TITLES.
Tiers differ only in depth/length and token budget, not in structure.

Tier matrix
───────────────────────────────────────────────────────────────────────────────
Plan           Model                      Max tokens  Summary depth  Insights
─────────────  ─────────────────────────  ──────────  ─────────────  ────────
professional   claude-haiku-4-5-20251001  1100        compact        2–3/section
premium        claude-sonnet-4-6          1900        standard       4–6/section
enterprise     claude-opus-4-8            3600        full           6–8/section
───────────────────────────────────────────────────────────────────────────────

Returns None gracefully on any failure so callers never need to handle errors.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from services.ledger_analyser import LedgerAnalysis

# ── Tier → model ──────────────────────────────────────────────────────────────

_MODEL: dict[str, str] = {
    "professional": "claude-haiku-4-5-20251001",
    "premium":      "claude-sonnet-4-6",
    "enterprise":   "claude-opus-4-8",
}

_MAX_TOKENS: dict[str, int] = {
    "professional": 1100,
    "premium":      1900,
    "enterprise":   3600,
}

# How many numeric / categorical columns to include in the prompt context.
# Reduces input tokens for cheaper tiers without losing the key signals.
_SUMMARY_DEPTH: dict[str, dict] = {
    "professional": {"num_cols": 8,  "cat_cols": 5,  "correlations": False},
    "premium":      {"num_cols": 12, "cat_cols": 8,  "correlations": True},
    "enterprise":   {"num_cols": 20, "cat_cols": 12, "correlations": True},
}

# ── Prompt templates per tier ─────────────────────────────────────────────────
#
# All tiers return the same fixed section structure (see advisory_text.
# SECTION_TITLES) so the PDF and Excel report builders can split one Claude
# response into the distinct, business-facing sections required by the
# report spec. Tiers differ only in depth/length, not in structure.

_PERSONA = (
    "You are a senior data intelligence analyst, productised within a SaaS platform "
    "called ColtraDataAi (by Coltrane Ltd). Your subscribers are primarily bookkeepers, "
    "accountants, finance managers, and auditors at SMEs. You write for two audiences at "
    "once: a practice owner or CFO who needs a confident, non-technical read, and a data "
    "team who needs precise, trustworthy technical detail. Avoid academic language, "
    "hedging, and generic filler — every line must be specific to this dataset. "
    "When the dataset is financial, surface commercial and compliance implications "
    "(VAT exposure, period-end cut-offs, supplier concentration risk, cash flow signals) "
    "alongside the data quality analysis."
)

_ACCOUNTING_CONTEXT: dict[str, str] = {
    "gl": (
        "This is a General Ledger export. Prioritise: debit/credit balance integrity, "
        "journal entry patterns, account code distribution, period-end concentrations, "
        "and any unusual posting patterns that could indicate errors or manipulation. "
        "In Key Data Insights, lead with cash flow and P&L signals where visible."
    ),
    "bank_statement": (
        "This is a Bank Statement. Prioritise: cash flow rhythm, unusual transaction timing, "
        "round-number payments, duplicate payments, and any large or irregular credits/debits. "
        "In Key Data Insights, frame findings in terms of working capital and cash management."
    ),
    "invoice_list": (
        "This is an Invoice or Purchase List. Prioritise: supplier concentration, duplicate "
        "invoice numbers, round-number invoices, VAT-sensitive amounts, and any gaps in "
        "invoice sequencing. In Key Data Insights, lead with supplier spend analysis and "
        "payment pattern signals."
    ),
}

_SECTION_SPEC = (
    "Return your analysis as markdown using EXACTLY these top-level headings, in this "
    "order, with no other top-level headings:\n\n"
    "## Executive Bottom Line\n"
    "2–3 plain-English sentences: is this dataset usable, and for what. If overall risk "
    "is High and driven mainly by missing values rather than format/type errors or "
    "duplicates, you MUST explicitly state: \"Risk is primarily driven by structurally "
    "expected missing data, not data corruption.\"\n\n"
    "## Key Data Insights\n"
    "Business-focused bullets covering: dominant categories or behaviours, concentration "
    "patterns (e.g. Pareto effects, heavy users), cost/value distribution patterns, time "
    "trends or anomalies, and any cohort/segmentation signals. For each bullet, frame as "
    "what is happening and why it matters.\n\n"
    "## AI Advisory\n"
    "### A. Data Quality Diagnosis\n"
    "Structural vs true missingness, data type risks (e.g. categorical IDs misread as "
    "numeric metrics — never treat IDs/codes as numeric metrics), and integrity risks "
    "(joins, timestamps, relationships).\n"
    "### B. Statistical & Pattern Analysis\n"
    "Distribution shape (normal/skewed/heavy-tailed), outliers and what they mean, data "
    "density and time coverage.\n"
    "### C. Business Interpretation\n"
    "What this dataset represents in its domain, and the key operational or commercial "
    "signals it contains.\n\n"
    "## Modelling & Analytics Readiness\n"
    "State plainly whether this is ready for ML/analytics, what transformations are "
    "required, leakage risks (be specific — this is critical), and a recommended "
    "modelling approach (e.g. regression, clustering, time-series).\n\n"
    "## Top Priority Actions\n"
    "A numbered list of the top 5–7 actions, ranked by impact. Each line must follow this "
    "exact format: \"<action> — <why it matters> (Effort: Low/Medium/High)\".\n\n"
    "## Bottom Line Summary\n"
    "One decisive closing statement: is the dataset Decision-ready, Model-ready, or Needs "
    "refinement — and why.\n\n"
    "Do not impute structurally missing categorical fields and do not treat ID/code "
    "columns as numeric metrics in your analysis."
)

_PROMPT: dict[str, str] = {
    "professional": (
        f"{_PERSONA}\n\n{_SECTION_SPEC}\n\n"
        "Keep this tier concise: 2–3 bullets per section, 5 actions in Top Priority "
        "Actions, and one sentence per remaining heading where a list isn't requested.\n\n"
        "Dataset summary:\n{summary}"
    ),
    "premium": (
        f"{_PERSONA}\n\n{_SECTION_SPEC}\n\n"
        "Standard depth: 4–6 bullets per section and 5–6 Top Priority Actions.\n\n"
        "Dataset summary:\n{summary}"
    ),
    "enterprise": (
        f"{_PERSONA}\n\n{_SECTION_SPEC}\n\n"
        "Full depth: 6–8 bullets per section, 6–7 Top Priority Actions, and cite specific "
        "column names and figures throughout. Be authoritative and commercially aware.\n\n"
        "Dataset summary:\n{summary}"
    ),
}


# ── Public API ────────────────────────────────────────────────────────────────

def generate_ai_advisory(
    df: pd.DataFrame,
    plan_key: str = "professional",
    risk_summary: dict | None = None,
    ledger_analysis: "LedgerAnalysis | None" = None,
) -> str | None:
    """Return markdown advisory from Claude scaled to the subscriber's plan tier.

    risk_summary is the deterministic risk classification from ReportBuilder.
    ledger_analysis, when provided, injects accounting-specific audit context so
    Claude's narrative is grounded in the actual file type and audit flags.

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

        if risk_summary:
            summary += (
                f"\n\nDeterministic risk classification (treat as ground truth — do not "
                f"contradict it): Overall risk = {risk_summary.get('overall_risk')}. "
                f"Top issue = {risk_summary.get('top_issue')}. "
                f"Structural missingness driven = {risk_summary.get('structural_missingness', False)}."
            )

        if ledger_analysis:
            summary += _build_ledger_context(ledger_analysis)

        # Build the prompt, optionally injecting accounting-domain guidance
        accounting_note = ""
        if ledger_analysis and ledger_analysis.file_type in _ACCOUNTING_CONTEXT:
            accounting_note = (
                f"\n\nAccounting domain context: "
                f"{_ACCOUNTING_CONTEXT[ledger_analysis.file_type]}"
            )

        prompt = prompt_tpl.format(summary=summary) + accounting_note

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


# ── Internal usage/strategy insights (admin-only, no customer data) ───────────
#
# Distinct from generate_ai_advisory: this analyses aggregated, anonymised
# subscriber telemetry (industry mix, conversion timing, tenure, feature
# usage) for Coltrane Ltd's own strategic/marketing decisions — never shown
# to customers. Same Anthropic client pattern, dedicated persona and prompt.

_INTERNAL_PERSONA = (
    "You are a senior growth and data analyst advising the Coltrane Ltd leadership team "
    "on ColtraDataAi's product strategy. You work only from aggregated, anonymised "
    "subscriber telemetry — no names, no individual records. Your job is to surface "
    "patterns that inform strategic decisions, KPI tracking, and marketing/promotion "
    "targeting. Be specific and quantitative; never speculate beyond the provided "
    "numbers; explicitly flag when a sample is too small to generalise."
)

_INTERNAL_SECTION_SPEC = (
    "Return your analysis as markdown using EXACTLY these top-level headings, in this "
    "order, with no other top-level headings:\n\n"
    "## Executive Summary\n"
    "## Customer Segments\n"
    "Industry, profession, and position-in-organisation mix — which segments dominate "
    "and which are under-represented.\n\n"
    "## Conversion & Onboarding\n"
    "Signup-to-first-use timing — how fast subscribers activate value, and where the "
    "funnel is slow.\n\n"
    "## Engagement & Tenure\n"
    "Usage frequency, subscriber age/tenure, and which features (exports, AI advisory) "
    "are actually adopted vs ignored.\n\n"
    "## Marketing & Promotion Opportunities\n"
    "Concrete targeting ideas grounded in the segment and conversion data above.\n\n"
    "## Strategic Recommendations & Risks\n"
    "Ranked, actionable recommendations and any data-quality caveats (e.g. small "
    "sample size, high 'Not provided' rates) that limit confidence."
)

_INTERNAL_PROMPT = (
    f"{_INTERNAL_PERSONA}\n\n{_INTERNAL_SECTION_SPEC}\n\n"
    "Aggregated subscriber telemetry:\n{summary}"
)


def generate_internal_insights(stats: dict, plan_key: str = "enterprise") -> str | None:
    """Return a markdown strategic narrative from Claude for internal/admin use only.

    `stats` is the dict returned by services.licence_manager.get_usage_analytics() —
    counts, breakdowns and medians only, never individual subscriber rows.

    Returns None on any failure — missing key, API error — so callers never need
    to handle exceptions.
    """
    try:
        api_key = st.secrets["anthropic"]["api_key"]
    except Exception:
        return None

    if not api_key or api_key.startswith("sk-ant-REPLACE"):
        return None

    model      = _MODEL.get(plan_key, _MODEL["enterprise"])
    max_tokens = _MAX_TOKENS.get(plan_key, _MAX_TOKENS["enterprise"])

    try:
        import anthropic

        summary = _build_usage_summary(stats)
        prompt  = _INTERNAL_PROMPT.format(summary=summary)

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


def _build_usage_summary(stats: dict) -> str:
    """Compact text summary of aggregated usage analytics for the internal prompt."""
    parts: list[str] = []

    parts.append(f"Active subscribers: {stats.get('active_subscribers', 0):,}")
    parts.append(f"Total report runs (all time): {stats.get('total_runs', 0):,}")

    def _fmt_breakdown(title: str, breakdown: dict) -> None:
        if not breakdown:
            return
        total = sum(breakdown.values()) or 1
        items = ", ".join(f"{k} ({v}, {round(v / total * 100, 1)}%)" for k, v in breakdown.items())
        parts.append(f"{title}: {items}")

    _fmt_breakdown("Industry breakdown", stats.get("industry_breakdown", {}))
    _fmt_breakdown("Profession breakdown", stats.get("profession_breakdown", {}))
    _fmt_breakdown("Position-in-organisation breakdown", stats.get("position_breakdown", {}))
    _fmt_breakdown("Plan breakdown", stats.get("plan_breakdown", {}))
    _fmt_breakdown("Feature usage breakdown (event counts)", stats.get("feature_usage_breakdown", {}))

    median_conv = stats.get("median_conversion_days")
    n_conv      = len(stats.get("conversion_times_days", []))
    if median_conv is not None:
        parts.append(f"Median signup-to-first-use time: {median_conv} days (n={n_conv})")
    else:
        parts.append("Median signup-to-first-use time: no data yet")

    median_tenure = stats.get("median_tenure_days")
    n_tenure      = len(stats.get("tenure_days", []))
    if median_tenure is not None:
        parts.append(f"Median subscriber tenure: {median_tenure} days (n={n_tenure})")

    runs_trend = stats.get("runs_last_30_days", {})
    if runs_trend:
        total_30d = sum(runs_trend.values())
        parts.append(f"Runs in last 30 days: {total_30d:,} across {len(runs_trend)} active day(s)")

    return "\n".join(parts)


# ── Private helpers ───────────────────────────────────────────────────────────

_FILE_TYPE_LABELS = {
    "gl":             "General Ledger Export",
    "bank_statement": "Bank Statement",
    "invoice_list":   "Invoice / Purchase List",
    "general":        "General Financial Data",
}


def _build_ledger_context(ledger_analysis: "LedgerAnalysis") -> str:
    """Compact audit-findings block for injection into the advisory prompt."""
    from services.ledger_analyser import LedgerAnalysis  # local to avoid circular import

    parts = ["\n\nAudit Intelligence (treat as ground truth — do not contradict):"]
    file_label = _FILE_TYPE_LABELS.get(ledger_analysis.file_type, "Financial Data")
    parts.append(f"File type: {file_label}")

    if ledger_analysis.amount_col:
        parts.append(f"Amount column: {ledger_analysis.amount_col}")
    if ledger_analysis.date_col:
        parts.append(f"Date column: {ledger_analysis.date_col}")

    actionable = [f for f in ledger_analysis.flags if f.severity in ("high", "medium")]
    if actionable:
        parts.append("Significant audit flags:")
        for flag in actionable:
            parts.append(f"  [{flag.severity.upper()}] {flag.check}: {flag.finding}")
    else:
        parts.append("No high or medium audit flags detected.")

    return "\n".join(parts)


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

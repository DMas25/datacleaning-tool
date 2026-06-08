import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from core.dashboard_analytics import (
    numeric_columns,
    categorical_columns,
    frequency_table,
    correlation_matrix,
    time_series_counts,
)

# ---------------------------------------------------------------------------
# Builds a gallery of polished, branded Plotly figures from a cleaned dataset.
# Each card carries a title/description alongside its figure so the same set
# can be rendered live on the dashboard, embedded as images in the Excel
# Executive Summary sheet, and placed into the downloadable PDF report.
# ---------------------------------------------------------------------------


# Fixed render dimensions for exported chart images — shared by the Excel
# Executive Summary embedding and the PDF report so both stay crisp and
# proportionate without re-inspecting each rendered PNG.
CHART_IMAGE_WIDTH = 760
CHART_IMAGE_HEIGHT = 400
CHART_IMAGE_SCALE = 2
CHART_IMAGE_ASPECT = CHART_IMAGE_WIDTH / CHART_IMAGE_HEIGHT


@dataclass
class ChartCard:
    key: str
    title: str
    description: str
    figure: go.Figure


def _premium_theme(fig: go.Figure, branding, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=30, r=30, t=60, b=50),
        font=dict(family="Segoe UI, Helvetica, Arial, sans-serif", size=12, color="#33414E"),
        title_font=dict(size=16, color=branding["primary_colour"]),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def render_chart_images(cards: List[ChartCard]) -> List[Tuple[ChartCard, bytes]]:
    """
    Renders every chart card to PNG bytes in a single batched Kaleido session
    (via plotly.io.write_images) — far faster than exporting one figure at a
    time, since each export would otherwise spin up its own browser instance.
    """
    if not cards:
        return []

    with tempfile.TemporaryDirectory() as tmp_dir:
        paths = [os.path.join(tmp_dir, f"{card.key}.png") for card in cards]
        pio.write_images(
            fig=[card.figure for card in cards],
            file=paths,
            format="png",
            width=CHART_IMAGE_WIDTH,
            height=CHART_IMAGE_HEIGHT,
            scale=CHART_IMAGE_SCALE,
        )

        assets = []
        for card, path in zip(cards, paths):
            with open(path, "rb") as f:
                assets.append((card, f.read()))

    return assets


def build_chart_gallery(
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    branding,
    quality_breakdown_df: Optional[pd.DataFrame] = None,
    date_cols: Optional[List[str]] = None,
    max_numeric: int = 3,
    max_categorical: int = 3,
) -> List[ChartCard]:
    cards: List[ChartCard] = []
    palette = [
        branding["primary_colour"],
        branding["secondary_colour"],
        "#7FB3D5",
        "#48C9B0",
        "#F4D03F",
    ]

    # Missing values by column
    missing_by_col = cleaned_df.isnull().sum().sort_values(ascending=False)
    missing_by_col = missing_by_col[missing_by_col > 0].head(12)
    if not missing_by_col.empty:
        fig = px.bar(
            x=missing_by_col.index.astype(str),
            y=missing_by_col.values,
            labels={"x": "Column", "y": "Missing Values"},
            color=missing_by_col.values,
            color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]],
            title="Missing Values by Column",
        )
        fig.update_layout(coloraxis_showscale=False)
        _premium_theme(fig, branding)
        cards.append(ChartCard(
            "missing_values",
            "Missing Values by Column",
            "Highlights which fields carry the most missing data after cleaning.",
            fig,
        ))

    # Original vs cleaned row volume
    rows_compare = pd.DataFrame({"Stage": ["Original", "Cleaned"], "Rows": [len(raw_df), len(cleaned_df)]})
    fig = px.bar(
        rows_compare, x="Stage", y="Rows", color="Stage", text="Rows",
        color_discrete_map={"Original": branding["secondary_colour"], "Cleaned": branding["primary_colour"]},
        title="Original vs Cleaned Row Volume",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    _premium_theme(fig, branding)
    cards.append(ChartCard(
        "rows_comparison",
        "Original vs Cleaned Row Volume",
        "Shows how many records remain after duplicate removal and cleansing.",
        fig,
    ))

    # Overall data completeness donut
    total_cells = cleaned_df.shape[0] * cleaned_df.shape[1]
    missing_total = int(cleaned_df.isnull().sum().sum())
    if total_cells:
        complete_cells = total_cells - missing_total
        completeness_pct = round((complete_cells / total_cells) * 100, 1)
        fig = go.Figure(data=[go.Pie(
            labels=["Complete", "Missing"],
            values=[complete_cells, missing_total],
            hole=0.62,
            marker=dict(colors=[branding["primary_colour"], "#E8EDF1"]),
            textinfo="percent",
            sort=False,
        )])
        fig.update_layout(
            title="Overall Data Completeness",
            annotations=[dict(
                text=f"{completeness_pct}%", x=0.5, y=0.5, font_size=22, showarrow=False,
                font_color=branding["primary_colour"],
            )],
        )
        _premium_theme(fig, branding, height=360)
        cards.append(ChartCard(
            "completeness",
            "Overall Data Completeness",
            "Proportion of populated cells across the cleaned dataset.",
            fig,
        ))

    # Column risk mix (requires the column-level quality breakdown)
    if quality_breakdown_df is not None and not quality_breakdown_df.empty and "Risk Level" in quality_breakdown_df.columns:
        risk_counts = quality_breakdown_df["Risk Level"].value_counts().reindex(["High", "Medium", "Low"]).fillna(0)
        if risk_counts.sum() > 0:
            fig = go.Figure(data=[go.Pie(
                labels=risk_counts.index,
                values=risk_counts.values,
                hole=0.55,
                marker=dict(colors=["#E74C3C", "#F39C12", "#2ECC71"]),
                textinfo="label+value",
                sort=False,
            )])
            fig.update_layout(title="Column Risk Mix")
            _premium_theme(fig, branding, height=360)
            cards.append(ChartCard(
                "risk_mix",
                "Column Risk Mix",
                "Number of columns flagged at each data-quality risk level.",
                fig,
            ))

    # Numeric distributions — automatically generated for the leading numeric columns
    num_cols = numeric_columns(cleaned_df)
    for i, col in enumerate(num_cols[:max_numeric]):
        fig = px.histogram(
            cleaned_df, x=col, nbins=30,
            color_discrete_sequence=[palette[i % len(palette)]],
            title=f"Distribution — {col}",
        )
        fig.update_layout(bargap=0.05)
        _premium_theme(fig, branding, height=340)
        cards.append(ChartCard(
            f"dist_{col}",
            f"Distribution — {col}",
            f"Frequency spread of values observed in '{col}'.",
            fig,
        ))

    # Categorical frequency — automatically generated for the leading categorical columns
    cat_cols = categorical_columns(cleaned_df, date_cols)
    for i, col in enumerate(cat_cols[:max_categorical]):
        freq_df = frequency_table(cleaned_df, col, top_n=8)
        fig = px.bar(
            freq_df, x=str(col), y="Count",
            color_discrete_sequence=[palette[(i + 1) % len(palette)]],
            title=f"Top Categories — {col}",
        )
        _premium_theme(fig, branding, height=340)
        cards.append(ChartCard(
            f"freq_{col}",
            f"Top Categories — {col}",
            f"Most frequently occurring values in '{col}'.",
            fig,
        ))

    # Trend — first detected date-like column
    if date_cols:
        trend_df = time_series_counts(cleaned_df, date_cols[0])
        if trend_df is not None and not trend_df.empty:
            fig = px.area(
                trend_df, x="Date", y="Records",
                color_discrete_sequence=[branding["primary_colour"]],
                title=f"Records Over Time — {date_cols[0]}",
            )
            fig.update_traces(line=dict(width=2))
            _premium_theme(fig, branding)
            cards.append(ChartCard(
                "trend",
                f"Records Over Time — {date_cols[0]}",
                "Volume of records by date — useful for spotting gaps, spikes or seasonality.",
                fig,
            ))

    # Correlation heatmap
    corr = correlation_matrix(cleaned_df)
    if corr is not None:
        fig = px.imshow(
            corr, text_auto=".2f",
            color_continuous_scale=["#D7F3F7", branding["secondary_colour"], branding["primary_colour"]],
            aspect="auto",
            title="Correlation Between Numeric Fields",
        )
        _premium_theme(fig, branding, height=420)
        cards.append(ChartCard(
            "correlation",
            "Correlation Between Numeric Fields",
            "Pairwise relationships (Pearson correlation) between numeric columns.",
            fig,
        ))

    return cards

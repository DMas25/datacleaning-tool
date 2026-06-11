"""Centralised export orchestration for ColtraDataAi.

Single entry point for generating both the Excel workbook and the PDF
executive summary, so callers never need to know which underlying library
produces each format.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from core.report_builder import ReportBuilder
from core.pdf_report import build_pdf_report
from core.chart_gallery import ChartCard


@dataclass
class ExportBundle:
    """Holds all generated report artefacts for a single processing run."""
    excel_path:   str
    pdf_bytes:    bytes
    pdf_filename: str
    chart_assets: List[Tuple[ChartCard, bytes]]
    risk_summary: Dict


def generate_reports(
    branding:              dict,
    raw_df:                pd.DataFrame,
    cleaned_df:            pd.DataFrame,
    log_df:                pd.DataFrame,
    quality_df:            pd.DataFrame,
    quality_breakdown_df:  pd.DataFrame,
    chart_assets:          List[Tuple[ChartCard, bytes]],
    risk_summary:          Dict,
    dictionary_df:         Optional[pd.DataFrame] = None,
) -> ExportBundle:
    """
    Generate both the Excel workbook and PDF executive summary in one call.

    Returns an ExportBundle containing paths / bytes ready for Streamlit
    download buttons.
    """
    builder = ReportBuilder(branding)

    excel_path = builder.build_report(
        raw_df, cleaned_df, log_df, quality_df,
        dictionary_df=dictionary_df,
        quality_breakdown_df=quality_breakdown_df,
        chart_assets=chart_assets,
    )

    pdf_bytes = build_pdf_report(branding, raw_df, cleaned_df, risk_summary, chart_assets)
    pdf_filename = excel_path.rsplit(".", 1)[0] + ".pdf"

    return ExportBundle(
        excel_path=excel_path,
        pdf_bytes=pdf_bytes,
        pdf_filename=pdf_filename,
        chart_assets=chart_assets,
        risk_summary=risk_summary,
    )


def build_chart_and_risk(
    branding:   dict,
    raw_df:     pd.DataFrame,
    cleaned_df: pd.DataFrame,
    date_cols:  Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict, List[Tuple[ChartCard, bytes]]]:
    """
    Convenience helper: build quality breakdown, risk summary and chart assets
    in one call and return the triple (quality_breakdown_df, risk_summary, chart_assets).
    """
    builder = ReportBuilder(branding)
    quality_breakdown_df = builder.build_quality_breakdown(cleaned_df)
    risk_summary = builder.build_risk_summary(quality_breakdown_df)
    chart_assets = builder.build_chart_assets(
        raw_df, cleaned_df, quality_breakdown_df, date_cols=date_cols
    )
    return quality_breakdown_df, risk_summary, chart_assets

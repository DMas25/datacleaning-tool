"""Tests for report builder and PDF output — file-level smoke tests."""
import os
import pytest
import pandas as pd

from config.branding_config import branding
from core.cleaner import CleaningOptions, apply_cleaning
from core.profiler import build_quality_summary_df
from core.report_builder import ReportBuilder
from core.pdf_report import build_pdf_report
from core.insights_engine import detect_date_columns


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "name":       ["Alice", "Bob", "Charlie", "Alice", None],
        "age":        [30, 25, 35, 30, 28],
        "department": ["Finance", "HR", "Finance", "Finance", "IT"],
        "salary":     [50000, 45000, 60000, 50000, 55000],
        "joined":     ["2020-01-15", "2019-06-01", "2021-03-20", "2020-01-15", "2022-07-10"],
    })


@pytest.fixture
def cleaned_result(sample_df):
    opts = CleaningOptions(remove_duplicates=True, trim_whitespace=True, standardise_headers=True)
    return apply_cleaning(sample_df, opts)


@pytest.fixture
def builder():
    return ReportBuilder(branding)


# ── ReportBuilder ─────────────────────────────────────────────────────────────

def test_build_quality_breakdown_returns_dataframe(builder, cleaned_result):
    qbd = builder.build_quality_breakdown(cleaned_result.cleaned_df)
    assert isinstance(qbd, pd.DataFrame)
    assert "Risk Level" in qbd.columns


def test_build_risk_summary_keys(builder, cleaned_result):
    qbd = builder.build_quality_breakdown(cleaned_result.cleaned_df)
    summary = builder.build_risk_summary(qbd)
    required_keys = {"overall_risk", "high_count", "medium_count", "low_count", "top_issue", "avg_issue_pct"}
    assert required_keys.issubset(summary.keys())


def test_build_risk_summary_valid_risk_level(builder, cleaned_result):
    qbd = builder.build_quality_breakdown(cleaned_result.cleaned_df)
    summary = builder.build_risk_summary(qbd)
    assert summary["overall_risk"] in ("High", "Medium", "Low")


def test_build_report_creates_file(builder, sample_df, cleaned_result, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs(tmp_path / "assets" / "logo", exist_ok=True)

    opts = CleaningOptions()
    result = apply_cleaning(sample_df, opts)
    qbd = builder.build_quality_breakdown(result.cleaned_df)
    quality_df = build_quality_summary_df(sample_df, result.cleaned_df, "No Change")

    filename = builder.build_report(
        sample_df, result.cleaned_df, result.log_df, quality_df,
        quality_breakdown_df=qbd,
        chart_assets=[],
    )
    assert os.path.exists(filename)
    assert filename.endswith(".xlsx")


# ── PDF report ────────────────────────────────────────────────────────────────

def test_build_pdf_report_returns_bytes(sample_df, cleaned_result):
    builder = ReportBuilder(branding)
    qbd = builder.build_quality_breakdown(cleaned_result.cleaned_df)
    risk = builder.build_risk_summary(qbd)
    pdf_bytes = build_pdf_report(branding, sample_df, cleaned_result.cleaned_df, risk, [])
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # PDF magic bytes
    assert pdf_bytes[:4] == b"%PDF"


def test_pdf_report_nonempty_with_charts(sample_df, cleaned_result):
    builder = ReportBuilder(branding)
    qbd     = builder.build_quality_breakdown(cleaned_result.cleaned_df)
    risk    = builder.build_risk_summary(qbd)
    # Chart assets list empty — should still produce valid PDF
    pdf_bytes = build_pdf_report(branding, sample_df, cleaned_result.cleaned_df, risk, [])
    assert len(pdf_bytes) > 1000

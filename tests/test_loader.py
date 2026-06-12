"""Tests for core.file_loader."""
import io
import pytest
import pandas as pd

from core.file_loader import _get_extension, apply_row_limit


# ── _get_extension ────────────────────────────────────────────────────────────

def test_get_extension_csv():
    assert _get_extension("data.csv") == "csv"


def test_get_extension_xlsx():
    assert _get_extension("report.xlsx") == "xlsx"


def test_get_extension_xls():
    assert _get_extension("legacy.xls") == "xls"


def test_get_extension_case_insensitive():
    assert _get_extension("DATA.CSV") == "csv"


def test_get_extension_unsupported_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        _get_extension("document.pdf")


def test_get_extension_no_extension_raises():
    with pytest.raises(ValueError):
        _get_extension("no_extension")


# ── apply_row_limit ───────────────────────────────────────────────────────────

def _make_df(n_rows: int) -> pd.DataFrame:
    return pd.DataFrame({"a": range(n_rows), "b": range(n_rows)})


def test_apply_row_limit_no_limit():
    df = _make_df(500)
    result = apply_row_limit(df, limit=None, tier_name="Free")
    assert len(result) == 500


def test_apply_row_limit_not_exceeded():
    df = _make_df(100)
    result = apply_row_limit(df, limit=200, tier_name="Free")
    assert len(result) == 100


def test_apply_row_limit_truncates(monkeypatch):
    # Patch st.warning so we can test without a Streamlit runtime
    import streamlit as st
    monkeypatch.setattr(st, "warning", lambda *a, **kw: None)

    df = _make_df(1000)
    result = apply_row_limit(df, limit=500, tier_name="Free")
    assert len(result) == 500


def test_apply_row_limit_exact_boundary():
    df = _make_df(200)
    result = apply_row_limit(df, limit=200, tier_name="Pro")
    assert len(result) == 200

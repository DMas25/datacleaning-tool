"""Tests for core.cleaner — cleaning operations and log building."""
import pandas as pd
import pytest

from core.cleaner import CleaningOptions, apply_cleaning, diff_summary


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame({
        "First Name": [" Alice ", "Bob", "Alice", None],
        "Age":        [30, 25, 30, 40],
        "Email":      ["alice@test.com", "bob@test.com", "alice@test.com", "dave@test.com"],
    })


# ── Header standardisation ────────────────────────────────────────────────────

def test_standardise_headers_on():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions(standardise_headers=True))
    assert "first_name" in result.cleaned_df.columns
    assert "First Name" not in result.cleaned_df.columns


def test_standardise_headers_off():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions(standardise_headers=False))
    assert "First Name" in result.cleaned_df.columns


# ── Whitespace trimming ───────────────────────────────────────────────────────

def test_trim_whitespace_on():
    df = pd.DataFrame({"name": ["  Alice  ", " Bob"]})
    result = apply_cleaning(df, CleaningOptions(trim_whitespace=True, standardise_headers=False))
    assert result.cleaned_df["name"].tolist() == ["Alice", "Bob"]


def test_trim_whitespace_off():
    df = pd.DataFrame({"name": ["  Alice  "]})
    result = apply_cleaning(df, CleaningOptions(trim_whitespace=False, standardise_headers=False))
    assert result.cleaned_df["name"].iloc[0] == "  Alice  "


# ── Duplicate removal ─────────────────────────────────────────────────────────

def test_remove_duplicates_on():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions(remove_duplicates=True, standardise_headers=False))
    assert len(result.cleaned_df) < len(df)


def test_remove_duplicates_off():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions(remove_duplicates=False, standardise_headers=False))
    assert len(result.cleaned_df) == len(df)


# ── Null handling ─────────────────────────────────────────────────────────────

def test_null_handling_no_change():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions(null_handling="No Change", remove_duplicates=False))
    assert result.cleaned_df.isnull().sum().sum() > 0


def test_null_handling_fill_blank():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions(null_handling="Fill with blank", remove_duplicates=False))
    assert result.cleaned_df.isnull().sum().sum() == 0


def test_null_handling_fill_placeholder():
    df = _sample_df()
    result = apply_cleaning(
        df, CleaningOptions(null_handling="Fill with placeholder", remove_duplicates=False, standardise_headers=False)
    )
    assert "MISSING" in result.cleaned_df.values


# ── Log structure ─────────────────────────────────────────────────────────────

def test_log_has_nine_steps():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions())
    assert len(result.log_df) == 9
    assert list(result.log_df.columns) == ["Step", "Action", "Result"]
    assert list(result.log_df["Action"]) == [
        "File Loaded",
        "Header Standardisation",
        "Whitespace Trimming",
        "Sentinel Normalisation",
        "Numeric Coercion",
        "Arithmetic Recovery",
        "Item Recovery",
        "Duplicate Removal",
        "Missing Value Handling",
    ]


def test_log_skipped_step_marked():
    df = _sample_df()
    opts = CleaningOptions(remove_duplicates=False)
    result = apply_cleaning(df, opts)
    dup_row = result.log_df[result.log_df["Action"] == "Duplicate Removal"].iloc[0]
    assert dup_row["Result"] == "Skipped"


# ── diff_summary ──────────────────────────────────────────────────────────────

def test_diff_summary_keys():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions())
    summary = diff_summary(df, result.cleaned_df)
    assert set(summary.keys()) == {"rows_original", "rows_cleaned", "rows_removed", "cols_original", "cols_cleaned"}


def test_diff_summary_rows_removed():
    df = _sample_df()
    result = apply_cleaning(df, CleaningOptions(remove_duplicates=True))
    summary = diff_summary(df, result.cleaned_df)
    assert summary["rows_removed"] >= 0
    assert summary["rows_original"] == len(df)

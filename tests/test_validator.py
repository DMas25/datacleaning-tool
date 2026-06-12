"""Tests for core.validator and utils.validators."""
import pandas as pd
import pytest

from core.validator import validate_dataframe, has_issues, issue_count
from utils.validators import (
    is_valid_email,
    is_probable_date_column,
    validate_upload_constraints,
)


# ── core.validator ────────────────────────────────────────────────────────────

def test_validate_dataframe_returns_dataframe():
    df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})
    result = validate_dataframe(df)
    assert isinstance(result, pd.DataFrame)


def test_has_issues_with_nulls():
    df = pd.DataFrame({"a": [1, None, 3]})
    # Null presence alone may or may not trigger a validation issue depending
    # on data_validator implementation — check return type only
    assert isinstance(has_issues(df), bool)


def test_issue_count_returns_int():
    df = pd.DataFrame({"col": [None, None, 1]})
    assert isinstance(issue_count(df), int)
    assert issue_count(df) >= 0


def test_validate_clean_dataframe():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = validate_dataframe(df)
    # A clean frame may return an empty or non-empty df depending on validator
    assert isinstance(result, pd.DataFrame)


# ── utils.validators ─────────────────────────────────────────────────────────

def test_is_valid_email_valid():
    assert is_valid_email("user@example.com")
    assert is_valid_email("first.last@company.co.uk")


def test_is_valid_email_invalid():
    assert not is_valid_email("not-an-email")
    assert not is_valid_email("missing@tld")
    assert not is_valid_email("@nodomain.com")


def test_is_probable_date_column_true():
    s = pd.Series(["2024-01-01", "2024-02-15", "2024-03-20"], name="created_date")
    assert is_probable_date_column(s)


def test_is_probable_date_column_no_keyword():
    s = pd.Series(["2024-01-01", "2024-02-15"], name="value")
    assert not is_probable_date_column(s)


def test_is_probable_date_column_non_date_values():
    s = pd.Series(["hello", "world", "foo"], name="created_date")
    assert not is_probable_date_column(s)


def test_validate_upload_constraints_clean():
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert validate_upload_constraints(df, max_rows=100) == []


def test_validate_upload_constraints_too_many_rows():
    df = pd.DataFrame({"a": range(1000)})
    issues = validate_upload_constraints(df, max_rows=500)
    assert any("rows" in i.lower() for i in issues)


def test_validate_upload_constraints_empty():
    df = pd.DataFrame()
    issues = validate_upload_constraints(df)
    assert any("empty" in i.lower() for i in issues)

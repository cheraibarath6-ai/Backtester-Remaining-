import pandas as pd

from crypto_research.data import months


def test_months_includes_partial_first_and_last_months():
    result = months("2021-11-14", "2026-11-14")
    assert result[0] == pd.Timestamp("2021-11-01", tz="UTC")
    assert result[-1] == pd.Timestamp("2026-11-01", tz="UTC")
    assert len(result) == 61


def test_months_respects_exclusive_end_at_month_boundary():
    result = months("2021-11-14", "2021-12-01")
    assert list(result) == [pd.Timestamp("2021-11-01", tz="UTC")]


def test_months_empty_for_empty_or_reversed_range():
    assert len(months("2021-11-14", "2021-11-14")) == 0
    assert len(months("2021-12-01", "2021-11-01")) == 0

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


def test_months_accepts_timezone_aware_timestamps():
    start = pd.Timestamp("2021-11-14", tz="UTC")
    end = pd.Timestamp("2026-11-14", tz="UTC")
    result = months(start, end)
    assert len(result) == 61
    assert result[0] == pd.Timestamp("2021-11-01", tz="UTC")
    assert result[-1] == pd.Timestamp("2026-11-01", tz="UTC")



def test_quality_report_accepts_timezone_aware_bounds():
    from crypto_research.data import quality_report

    index = pd.date_range("2025-01-01", periods=2, freq="min", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": [100.0, 100.0],
            "high": [101.0, 101.0],
            "low": [99.0, 99.0],
            "close": [100.0, 100.0],
            "volume": [1.0, 1.0],
        },
        index=index,
    )
    report = quality_report(frame, "BTCUSDT", index.min(), index.max() + pd.Timedelta(minutes=1))
    assert report["coverage_pct"] == 100.0

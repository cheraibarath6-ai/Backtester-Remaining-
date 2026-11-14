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


def _write_kline_archive(path, timestamps):
    import zipfile

    rows = []
    for timestamp in timestamps:
        rows.append(",".join([
            str(timestamp), "100", "101", "99", "100", "1",
            str(timestamp + 59999), "100", "1", "0.5", "50", "0",
        ]))
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("klines.csv", "\n".join(rows))


def test_acquire_klines_fills_monthly_gaps_from_official_daily_archive(tmp_path, monkeypatch):
    from crypto_research import data

    base_ms = int(pd.Timestamp("2022-01-01 00:00:00", tz="UTC").timestamp() * 1000)
    monthly_path = tmp_path / "monthly.zip"
    daily_path = tmp_path / "daily.zip"
    _write_kline_archive(monthly_path, [base_ms, base_ms + 120000])
    _write_kline_archive(daily_path, [base_ms + 60000])

    def fake_get_zip(url, dest, verify_checksum=False):
        if "/monthly/" in url:
            return monthly_path
        if "/daily/" in url:
            return daily_path
        raise AssertionError(f"Unexpected archive URL: {url}")

    monkeypatch.setattr(data, "get_zip", fake_get_zip)
    result = data.acquire_klines(
        "BTCUSDT", "2022-01-01 00:00:00+00:00",
        "2022-01-01 00:03:00+00:00", root=tmp_path / "cache",
    )

    report = data.quality_report(
        result, "BTCUSDT", "2022-01-01 00:00:00+00:00",
        "2022-01-01 00:03:00+00:00",
    )
    assert len(result) == 3
    assert report["coverage_pct"] == 100.0
    assert result.attrs["source"] == "binance_vision_official_usdm_1m_monthly_plus_daily"
    assert result.attrs["daily_gap_fill_attempted_days"] == ["2022-01-01"]
    assert result.attrs["daily_gap_fill_successful_days"] == ["2022-01-01"]

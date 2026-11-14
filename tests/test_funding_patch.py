from pathlib import Path

import pandas as pd

from crypto_research import funding_patch


def test_official_daily_archive_fills_missing_month_without_api(monkeypatch, tmp_path):
    def fake_get_zip(url, dest, verify_checksum=False):
        if "/monthly/" in url and url.endswith("BTCUSDT-fundingRate-2021-11.zip"):
            return Path(dest)
        if "/daily/" in url and url.endswith("BTCUSDT-fundingRate-2021-12-01.zip"):
            return Path(dest)
        return None

    def fake_read(path):
        if path.name.endswith("2021-11.zip"):
            index = pd.DatetimeIndex(["2021-11-30 16:00:00+00:00"], name="funding_time")
        else:
            index = pd.DatetimeIndex(
                ["2021-12-01 00:00:00+00:00", "2021-12-01 08:00:00+00:00"],
                name="funding_time",
            )
        return pd.DataFrame(
            {"funding_rate": [0.0001] * len(index), "mark_price": [50000.0] * len(index)},
            index=index,
        )

    monkeypatch.setattr(funding_patch._data, "get_zip", fake_get_zip)
    monkeypatch.setattr(funding_patch._data, "_read_funding_zip", fake_read)

    result = funding_patch.acquire_funding(
        "BTCUSDT", "2021-11-30T16:00:00Z", "2021-12-01T16:00:00Z", root=tmp_path
    )

    assert len(result) == 3
    assert result.attrs["source"] == "binance_vision_monthly_plus_daily_official_archive"
    assert result.attrs["missing_archive_months"] == ["2021-12"]
    assert result.attrs["daily_archive_days"] == ["2021-12-01"]


def test_official_funding_loader_fails_closed_when_no_archive_exists(monkeypatch, tmp_path):
    monkeypatch.setattr(funding_patch._data, "get_zip", lambda *args, **kwargs: None)

    try:
        funding_patch.acquire_funding(
            "BTCUSDT", "2021-11-14", "2021-11-16", root=tmp_path
        )
    except RuntimeError as error:
        assert "No official Binance Vision funding archives" in str(error)
    else:
        raise AssertionError("Missing official funding must fail closed")

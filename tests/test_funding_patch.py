from pathlib import Path

import pandas as pd

from crypto_research import funding_patch


class FakeResponse:
    def __init__(self, rows):
        self._rows = rows

    def raise_for_status(self):
        return None

    def json(self):
        return self._rows


def test_official_daily_archive_fills_missing_month_when_all_requested_days_exist(monkeypatch, tmp_path):
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
    monkeypatch.setattr(
        funding_patch._data.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("API should not be needed")),
    )

    result = funding_patch.acquire_funding(
        "BTCUSDT", "2021-11-30T16:00:00Z", "2021-12-01T16:00:00Z", root=tmp_path
    )

    assert len(result) == 3
    assert result.attrs["source"] == "binance_vision_monthly_plus_daily_official_archive"
    assert result.attrs["missing_archive_months"] == ["2021-12"]
    assert result.attrs["daily_archive_days"] == ["2021-12-01"]
    assert result.attrs["api_filled_months"] == []


def test_official_binance_api_mirror_fills_missing_partial_month(monkeypatch, tmp_path):
    def fake_get_zip(url, dest, verify_checksum=False):
        if "/monthly/" in url and url.endswith("BTCUSDT-fundingRate-2026-10.zip"):
            return Path(dest)
        return None

    def fake_read(path):
        index = pd.DatetimeIndex(["2026-10-31 16:00:00+00:00"], name="funding_time")
        return pd.DataFrame(
            {"funding_rate": [0.0001], "mark_price": [60000.0]}, index=index
        )

    calls = []

    def fake_api_get(url, params, timeout):
        calls.append(url)
        if url.startswith("https://fapi.binance.com"):
            raise RuntimeError("HTTP 451 region restricted")
        assert url.startswith("https://fapi1.binance.com/fapi/v1/fundingRate")
        rows = [
            {
                "symbol": "BTCUSDT",
                "fundingTime": int(pd.Timestamp(ts, tz="UTC").timestamp() * 1000),
                "fundingRate": "0.0002",
                "markPrice": "61000",
            }
            for ts in ("2026-11-01 00:00:00", "2026-11-01 08:00:00", "2026-11-01 16:00:00")
        ]
        return FakeResponse(rows)

    monkeypatch.setattr(funding_patch._data, "get_zip", fake_get_zip)
    monkeypatch.setattr(funding_patch._data, "_read_funding_zip", fake_read)
    monkeypatch.setattr(funding_patch._data.requests, "get", fake_api_get)

    result = funding_patch.acquire_funding(
        "BTCUSDT", "2026-10-31T16:00:00Z", "2026-11-01T16:00:00Z", root=tmp_path
    )

    assert len(result) == 3
    assert result.index[-1] == pd.Timestamp("2026-11-01 08:00:00", tz="UTC")
    assert result.attrs["source"] == "binance_vision_archive_plus_official_api"
    assert result.attrs["api_filled_months"] == ["2026-11"]
    assert result.attrs["api_hosts"] == ["https://fapi1.binance.com"]
    assert any(url.startswith("https://fapi.binance.com") for url in calls)


def test_official_funding_loader_fails_closed_when_all_official_sources_are_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(funding_patch._data, "get_zip", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        funding_patch._data.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network unavailable")),
    )

    try:
        funding_patch.acquire_funding(
            "BTCUSDT", "2021-11-14", "2021-11-16", root=tmp_path
        )
    except RuntimeError as error:
        assert "No complete official Binance funding coverage" in str(error)
    else:
        raise AssertionError("Missing official funding must fail closed")

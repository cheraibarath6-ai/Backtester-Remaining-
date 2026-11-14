from __future__ import annotations

"""Official Binance Vision daily funding archive completion for partial monthly coverage."""

from pathlib import Path
import pandas as pd

from . import data as _data


def acquire_funding(symbol, start, end, root=Path("data")):
    base = _data.acquire_funding(symbol, start, end, root=root)
    base_source = base.attrs.get("source", "unknown")
    missing_months = list(base.attrs.get("missing_archive_months", []))
    # Never relabel third-party fallback rows as official merely because they
    # are concatenated with official daily files. Keep only verified Binance
    # monthly/API rows in an official-source result.
    official_base_sources = {
        "binance_vision_official_monthly_archive",
        "binance_vision_archive_plus_official_api",
        "binance_official_api",
        "binance_vision_official_monthly_archive_partial",
    }
    if base_source in {
        "binance_vision_official_monthly_archive",
        "binance_vision_archive_plus_official_api",
        "binance_official_api",
    }:
        return base
    if base_source not in official_base_sources:
        base = pd.DataFrame(columns=["funding_rate", "mark_price"])
        base.index = pd.DatetimeIndex([], tz="UTC", name="funding_time")
    if not missing_months:
        return base

    daily_parts = []
    for ym in missing_months:
        month_start = pd.Timestamp(f"{ym}-01", tz="UTC")
        month_end = month_start + pd.offsets.MonthBegin(1)
        range_start = max(month_start, _data._utc_timestamp(start))
        range_end = min(month_end, _data._utc_timestamp(end))
        for day in pd.date_range(range_start.normalize(), range_end.normalize(), freq="D", inclusive="left"):
            # Binance Vision publishes official daily funding archives.
            ymd = day.strftime("%Y-%m-%d")
            name = f"{symbol}-fundingRate-{ymd}.zip"
            url = f"{_data.BASE.replace('/monthly', '/daily')}/fundingRate/{symbol}/{name}"
            path = _data.get_zip(
                url,
                root / "raw" / "funding_daily" / symbol / name,
                verify_checksum=True,
            )
            if path:
                daily_parts.append(_data._read_funding_zip(path))

    if daily_parts:
        daily = pd.concat(daily_parts).sort_index()
        combined = pd.concat([base, daily]).sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]
        combined = combined.loc[
            (combined.index >= _data._utc_timestamp(start))
            & (combined.index < _data._utc_timestamp(end))
        ]
        combined.attrs["source"] = "binance_vision_monthly_plus_daily_official_archive"
        combined.attrs["missing_archive_months"] = missing_months
        return combined
    return base

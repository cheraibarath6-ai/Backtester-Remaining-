from __future__ import annotations

"""Official Binance Vision daily funding archive completion for partial monthly coverage."""

from pathlib import Path
import pandas as pd

from . import data as _data


def acquire_funding(symbol, start, end, root=Path("data")):
    base = _data.acquire_funding(symbol, start, end, root=root)
    missing_months = list(base.attrs.get("missing_archive_months", []))
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
            (combined.index >= pd.Timestamp(start, tz="UTC"))
            & (combined.index < pd.Timestamp(end, tz="UTC"))
        ]
        combined.attrs["source"] = "binance_vision_monthly_plus_daily_official_archive"
        combined.attrs["missing_archive_months"] = missing_months
        return combined
    return base

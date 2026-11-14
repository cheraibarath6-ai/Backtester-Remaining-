from __future__ import annotations

"""Strict official Binance Vision funding-history loader for HEAD.

The public REST funding endpoint can be region-blocked (HTTP 451). This loader
uses only checksum-verified Binance Vision monthly/daily USD-M funding archives;
it never substitutes a third-party data source or zero funding.
"""

from pathlib import Path

import pandas as pd

from . import data as _data


def acquire_funding(symbol, start, end, root=Path("data")):
    start_ts = _data._utc_timestamp(start)
    end_ts = _data._utc_timestamp(end)
    if end_ts <= start_ts:
        raise ValueError("Funding end must be later than start")

    expected_months = [month.strftime("%Y-%m") for month in _data.months(start_ts, end_ts)]
    monthly_parts = []
    monthly_found = []
    monthly_errors = {}
    for ym in expected_months:
        name = f"{symbol}-fundingRate-{ym}.zip"
        url = f"{_data.BASE}/fundingRate/{symbol}/{name}"
        try:
            path = _data.get_zip(
                url,
                Path(root) / "raw" / "funding" / symbol / name,
                verify_checksum=True,
            )
            if path is None:
                continue
            part = _data._read_funding_zip(path)
            if part.empty:
                raise ValueError("Monthly funding archive contains no usable rows")
            monthly_parts.append(part)
            monthly_found.append(ym)
        except Exception as error:
            monthly_errors[ym] = str(error)

    missing_months = sorted(set(expected_months) - set(monthly_found))
    daily_parts = []
    daily_found = []
    daily_errors = {}
    for ym in missing_months:
        month_start = pd.Timestamp(f"{ym}-01", tz="UTC")
        month_end = month_start + pd.offsets.MonthBegin(1)
        range_start = max(month_start, start_ts)
        range_end = min(month_end, end_ts)
        if range_end <= range_start:
            continue
        last_day = (range_end - pd.Timedelta(nanoseconds=1)).normalize()
        for day in pd.date_range(range_start.normalize(), last_day, freq="D"):
            ymd = day.strftime("%Y-%m-%d")
            name = f"{symbol}-fundingRate-{ymd}.zip"
            url = f"{_data.BASE.replace('/monthly', '/daily')}/fundingRate/{symbol}/{name}"
            try:
                path = _data.get_zip(
                    url,
                    Path(root) / "raw" / "funding_daily" / symbol / name,
                    verify_checksum=True,
                )
                if path is None:
                    continue
                part = _data._read_funding_zip(path)
                if part.empty:
                    raise ValueError("Daily funding archive contains no usable rows")
                daily_parts.append(part)
                daily_found.append(ymd)
            except Exception as error:
                daily_errors[ymd] = str(error)

    parts = monthly_parts + daily_parts
    if not parts:
        raise RuntimeError(
            f"No official Binance Vision funding archives found for {symbol} "
            f"between {start_ts} and {end_ts}; monthly_errors={monthly_errors}; "
            f"daily_errors={daily_errors}"
        )

    out = pd.concat(parts).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out.loc[(out.index >= start_ts) & (out.index < end_ts)]
    if out.empty:
        raise RuntimeError(f"Official Binance Vision funding archives contain no in-range rows for {symbol}")

    out.attrs["source"] = (
        "binance_vision_monthly_plus_daily_official_archive"
        if daily_parts else "binance_vision_official_monthly_archive"
    )
    out.attrs["missing_archive_months"] = missing_months
    out.attrs["monthly_archive_months"] = monthly_found
    out.attrs["daily_archive_days"] = daily_found
    out.attrs["monthly_archive_errors"] = monthly_errors
    out.attrs["daily_archive_errors"] = daily_errors
    return out

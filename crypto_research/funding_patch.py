from __future__ import annotations

"""Strict official Binance Vision/API funding loader for HEAD.

Complete monthly history is sourced from checksum-verified Binance Vision
archives. An incomplete current month is completed from Binance's official
USD-M funding-history API. No third-party source or zero-funding fallback is
permitted.
"""

from pathlib import Path

import pandas as pd

from . import data as _data

# Binance-operated USD-M REST origins. The canonical host is tried first;
# numbered mirrors are attempted only when the canonical host is unavailable.
OFFICIAL_API_BASES = (
    "https://fapi.binance.com",
    "https://fapi1.binance.com",
    "https://fapi2.binance.com",
    "https://fapi3.binance.com",
    "https://fapi4.binance.com",
)


def _fetch_api_funding_month(symbol, start, end):
    """Fetch one missing month from Binance's public USD-M funding endpoint."""
    start_ts = _data._utc_timestamp(start)
    end_ts = _data._utc_timestamp(end)
    if end_ts <= start_ts:
        raise ValueError("Funding API range must be positive")

    start_ms = int(start_ts.timestamp() * 1000)
    end_ms = int(end_ts.timestamp() * 1000)
    errors = {}

    for base in OFFICIAL_API_BASES:
        try:
            rows = []
            cursor = start_ms
            while cursor < end_ms:
                response = _data.requests.get(
                    f"{base}/fapi/v1/fundingRate",
                    params={
                        "symbol": symbol,
                        "startTime": cursor,
                        "endTime": end_ms,
                        "limit": 1000,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                batch = response.json()
                if not isinstance(batch, list):
                    raise ValueError("Binance funding API response was not a JSON array")
                if not batch:
                    break

                rows.extend(batch)
                last_ms = int(batch[-1]["fundingTime"])
                next_cursor = last_ms + 1
                if next_cursor <= cursor:
                    raise RuntimeError("Binance funding API pagination did not advance")
                cursor = next_cursor
                if len(batch) < 1000:
                    break

            if not rows:
                raise RuntimeError("Binance funding API returned no rows for the missing month")

            frame = pd.DataFrame(rows)
            if not {"fundingTime", "fundingRate"}.issubset(frame.columns):
                raise ValueError(
                    f"Unexpected Binance funding API fields: {list(frame.columns)}"
                )
            frame["funding_time"] = pd.to_datetime(
                pd.to_numeric(frame["fundingTime"], errors="coerce"),
                unit="ms",
                utc=True,
            )
            frame["funding_rate"] = pd.to_numeric(
                frame["fundingRate"], errors="coerce"
            )
            frame["mark_price"] = pd.to_numeric(
                frame.get("markPrice", pd.Series(index=frame.index, dtype="object")),
                errors="coerce",
            )
            out = (
                frame.dropna(subset=["funding_time", "funding_rate"])
                .drop_duplicates("funding_time")
                .set_index("funding_time")[["funding_rate", "mark_price"]]
                .sort_index()
            )
            out = out.loc[(out.index >= start_ts) & (out.index < end_ts)]
            if out.empty:
                raise RuntimeError("Binance funding API returned no in-range rows")
            return out, base, errors
        except Exception as error:
            errors[base] = f"{type(error).__name__}: {error}"

    raise RuntimeError(
        f"All official Binance USD-M funding API hosts failed for {symbol} "
        f"{start_ts}..{end_ts}: {errors}"
    )


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

    api_parts = []
    api_hosts = []
    api_attempt_errors = {}
    for ym in missing_months:
        month_start = pd.Timestamp(f"{ym}-01", tz="UTC")
        month_end = month_start + pd.offsets.MonthBegin(1)
        range_start = max(month_start, start_ts)
        range_end = min(month_end, end_ts)
        if range_end <= range_start:
            continue

        expected_days = {
            day.strftime("%Y-%m-%d")
            for day in pd.date_range(
                range_start.normalize(),
                (range_end - pd.Timedelta(nanoseconds=1)).normalize(),
                freq="D",
            )
        }
        found_days = set(daily_found)
        # If official daily archives cover every requested day in this missing
        # monthly file, they are sufficient; otherwise fill the month from API.
        if expected_days.issubset(found_days):
            continue

        try:
            part, host, host_errors = _fetch_api_funding_month(
                symbol, range_start, range_end
            )
            api_parts.append(part)
            api_hosts.append(host)
            if host_errors:
                api_attempt_errors[ym] = host_errors
        except Exception as error:
            api_attempt_errors[ym] = str(error)
            raise RuntimeError(
                f"No complete official Binance funding coverage for {symbol} "
                f"in missing archive month {ym}; monthly_errors={monthly_errors}; "
                f"daily_errors={daily_errors}; api_error={error}"
            ) from error

    parts = monthly_parts + daily_parts + api_parts
    if not parts:
        raise RuntimeError(
            f"No official Binance Vision funding archives or Binance API funding "
            f"found for {symbol} between {start_ts} and {end_ts}; "
            f"monthly_errors={monthly_errors}; daily_errors={daily_errors}; "
            f"api_errors={api_attempt_errors}"
        )

    out = pd.concat(parts).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out.loc[(out.index >= start_ts) & (out.index < end_ts)]
    if out.empty:
        raise RuntimeError(
            f"Official Binance funding sources contain no in-range rows for {symbol}"
        )

    if api_parts:
        source = (
            "binance_vision_archive_plus_official_api"
            if monthly_parts or daily_parts
            else "binance_official_api"
        )
    elif daily_parts:
        source = "binance_vision_monthly_plus_daily_official_archive"
    else:
        source = "binance_vision_official_monthly_archive"

    out.attrs["source"] = source
    out.attrs["missing_archive_months"] = missing_months
    out.attrs["monthly_archive_months"] = monthly_found
    out.attrs["daily_archive_days"] = daily_found
    out.attrs["api_filled_months"] = [
        ym for ym in missing_months if any(
            (part.index >= pd.Timestamp(f"{ym}-01", tz="UTC"))
            & (part.index < pd.Timestamp(f"{ym}-01", tz="UTC") + pd.offsets.MonthBegin(1))
            for part in api_parts
        )
    ]
    out.attrs["api_hosts"] = list(dict.fromkeys(api_hosts))
    out.attrs["api_attempt_errors"] = api_attempt_errors
    out.attrs["monthly_archive_errors"] = monthly_errors
    out.attrs["daily_archive_errors"] = daily_errors
    return out

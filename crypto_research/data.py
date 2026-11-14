from __future__ import annotations

import hashlib
import io
import time
import zipfile
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.binance.vision/data/futures/um/monthly"
COLS = [
    "open_time", "open", "high", "low", "close", "volume", "close_time",
    "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore",
]

def _utc_timestamp(value):
    """Normalize strings and naive/aware datetime values to UTC timestamps."""
    timestamp = pd.Timestamp(value)
    return timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp.tz_convert("UTC")


def months(start, end):
    """Return every UTC calendar month intersecting [start, end)."""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    start_ts = start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC")
    end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
    if end_ts <= start_ts:
        return pd.DatetimeIndex([], tz="UTC")
    # Period range includes partial first and last months while respecting the
    # exclusive end boundary (including the final month only if it intersects).
    periods = pd.period_range(
        start=start_ts.tz_localize(None),
        end=(end_ts - pd.Timedelta(nanoseconds=1)).tz_localize(None),
        freq="M",
    )
    return periods.to_timestamp(how="start").tz_localize("UTC")


def _checksum_ok(url: str, path: Path) -> bool | None:
    """Verify a Binance Vision SHA256 companion file; None means unavailable."""
    response = requests.get(url + ".CHECKSUM", timeout=30)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    expected = response.text.strip().split()[0].lower()
    actual = hashlib.sha256(path.read_bytes()).hexdigest().lower()
    if actual != expected:
        raise ValueError(f"SHA256 mismatch for {path.name}: expected {expected}, got {actual}")
    return True


def get_zip(url: str, dest: Path, verify_checksum: bool = False):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100:
        if verify_checksum:
            try:
                _checksum_ok(url, dest)
            except Exception:
                dest.unlink(missing_ok=True)
            else:
                return dest
        else:
            return dest

    for attempt in range(4):
        try:
            response = requests.get(url, timeout=120)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            if not response.content.startswith(b"PK"):
                raise ValueError(f"Archive response is not ZIP: {url}")
            dest.write_bytes(response.content)
            if verify_checksum:
                _checksum_ok(url, dest)
            return dest
        except Exception:
            dest.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    return None


def _timestamp_unit(values: pd.Series) -> str:
    sample = pd.to_numeric(values, errors="coerce").dropna()
    if sample.empty:
        raise ValueError("No numeric timestamps in archive")
    magnitude = float(sample.abs().median())
    if magnitude >= 1e17:
        return "ns"
    if magnitude >= 1e14:
        return "us"
    return "ms"


def read_zip(path: Path):
    with zipfile.ZipFile(path) as archive:
        csvs = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csvs:
            raise ValueError(f"No CSV in {path}")
        with archive.open(csvs[0]) as stream:
            data = pd.read_csv(stream, header=None)

    data = data.iloc[:, :12].copy()
    data.columns = COLS
    open_time = pd.to_numeric(data["open_time"], errors="coerce")
    data = data.loc[open_time.notna()].copy()
    unit = _timestamp_unit(open_time)
    data["open_time"] = pd.to_datetime(open_time.loc[data.index], unit=unit, utc=True)

    numeric = [
        "open", "high", "low", "close", "volume", "quote_volume",
        "taker_buy_base", "taker_buy_quote",
    ]
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["trades"] = pd.to_numeric(data.trades, errors="coerce").fillna(0)
    data = data.dropna(subset=["open", "high", "low", "close", "volume"])
    data = data.sort_values("open_time").drop_duplicates("open_time")
    return data.set_index("open_time")


def acquire_klines(symbol, start, end, root=Path("data")):
    parts = []
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    start_ts = start_ts.tz_localize("UTC") if start_ts.tzinfo is None else start_ts.tz_convert("UTC")
    end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
    for month in months(start_ts, end_ts):
        ym = month.strftime("%Y-%m")
        name = f"{symbol}-1m-{ym}.zip"
        url = f"{BASE}/klines/{symbol}/1m/{name}"
        path = get_zip(url, root / "raw" / "klines" / symbol / name, verify_checksum=True)
        if path:
            parts.append(read_zip(path))
            continue

        # Binance publishes daily archives for an incomplete current month.
        # Use them only when the corresponding monthly archive is unavailable.
        month_end = month + pd.offsets.MonthBegin(1)
        day_start = max(month.normalize(), start_ts.normalize())
        day_end = min(month_end, end_ts)
        for day in pd.date_range(day_start, day_end.normalize(), freq="D", inclusive="left"):
            ymd = day.strftime("%Y-%m-%d")
            daily_name = f"{symbol}-1m-{ymd}.zip"
            daily_url = f"{BASE.replace('/monthly', '/daily')}/klines/{symbol}/1m/{daily_name}"
            daily_path = get_zip(
                daily_url,
                root / "raw" / "klines_daily" / symbol / daily_name,
                verify_checksum=True,
            )
            if daily_path:
                parts.append(read_zip(daily_path))
    if not parts:
        raise RuntimeError(f"No monthly or daily kline archives found for {symbol}")

    data = pd.concat(parts).sort_index()
    duplicate_count = int(data.index.duplicated().sum())
    data = data[~data.index.duplicated(keep="last")]
    data = data.loc[
        (data.index >= _utc_timestamp(start))
        & (data.index < _utc_timestamp(end))
    ]
    data.attrs["duplicate_timestamps_before_dedup"] = duplicate_count
    data.attrs["source"] = "binance_vision_official_usdm_1m"
    return data


def _read_funding_zip(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        csvs = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csvs:
            raise ValueError(f"No funding CSV in {path}")
        with archive.open(csvs[0]) as stream:
            data = pd.read_csv(stream)

    if "calc_time" not in data.columns:
        with zipfile.ZipFile(path) as archive:
            with archive.open(csvs[0]) as stream:
                raw = pd.read_csv(
                    stream,
                    header=None,
                    names=["calc_time", "funding_interval_hours", "last_funding_rate"],
                )
        data = raw

    rate_col = "last_funding_rate" if "last_funding_rate" in data.columns else "funding_rate"
    if "calc_time" not in data.columns or rate_col not in data.columns:
        raise ValueError(f"Unexpected Binance funding archive schema in {path}: {list(data.columns)}")

    timestamp = pd.to_numeric(data["calc_time"], errors="coerce")
    data = data.loc[timestamp.notna()].copy()
    data["funding_time"] = pd.to_datetime(
        timestamp.loc[data.index], unit=_timestamp_unit(timestamp), utc=True
    )
    data["funding_rate"] = pd.to_numeric(data[rate_col], errors="coerce")
    out = data.dropna(subset=["funding_rate"]).drop_duplicates("funding_time")
    out = out.set_index("funding_time")[["funding_rate"]].sort_index()
    out["mark_price"] = float("nan")
    return out


def _funding_from_official_api(symbol, start, end):
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    cursor = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)
    rows = []
    while cursor < end_ms:
        response = requests.get(
            url,
            params={"symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": 1000},
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        rows.extend(batch)
        next_cursor = int(batch[-1]["fundingTime"]) + 1
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        time.sleep(0.12)

    data = pd.DataFrame(rows)
    if data.empty:
        raise RuntimeError("Official Binance funding API returned no rows")
    data["funding_time"] = pd.to_datetime(data.fundingTime.astype("int64"), unit="ms", utc=True)
    data["funding_rate"] = pd.to_numeric(data.fundingRate)
    data["mark_price"] = pd.to_numeric(data.markPrice, errors="coerce")
    return data.drop_duplicates("funding_time").set_index("funding_time")[
        ["funding_rate", "mark_price"]
    ].sort_index()


def acquire_funding(symbol, start, end, root=Path("data")):
    """Prefer official Binance monthly funding archives, with coverage checks."""
    archive_parts = []
    found_months = []
    expected_months = [month.strftime("%Y-%m") for month in months(start, end)]
    archive_error = None

    try:
        for ym in expected_months:
            name = f"{symbol}-fundingRate-{ym}.zip"
            url = f"{BASE}/fundingRate/{symbol}/{name}"
            path = get_zip(
                url,
                root / "raw" / "funding" / symbol / name,
                verify_checksum=True,
            )
            if path:
                archive_parts.append(_read_funding_zip(path))
                found_months.append(ym)

        if archive_parts:
            archive = pd.concat(archive_parts).sort_index()
            archive = archive[~archive.index.duplicated(keep="last")]
            archive = archive.loc[
                (archive.index >= pd.Timestamp(start, tz="UTC"))
                & (archive.index < pd.Timestamp(end, tz="UTC"))
            ]
            missing_months = sorted(set(expected_months) - set(found_months))
            if not archive.empty and not missing_months:
                archive.attrs["source"] = "binance_vision_official_monthly_archive"
                archive.attrs["missing_archive_months"] = []
                return archive
        else:
            archive = pd.DataFrame(columns=["funding_rate", "mark_price"])
            missing_months = list(expected_months)
    except Exception as error:
        archive_error = error
        archive = pd.DataFrame(columns=["funding_rate", "mark_price"])
        missing_months = list(expected_months)

    # If official monthly files are absent or malformed, ask the official API
    # for the complete requested range and merge it with verified archive rows.
    try:
        api = _funding_from_official_api(symbol, start, end)
        if not archive.empty:
            out = pd.concat([archive, api]).sort_index()
            out = out[~out.index.duplicated(keep="last")]
            source = "binance_vision_archive_plus_official_api"
        else:
            out = api
            source = "binance_official_api"
        out = out.loc[
            (out.index >= pd.Timestamp(start, tz="UTC"))
            & (out.index < pd.Timestamp(end, tz="UTC"))
        ]
        out.attrs["source"] = source
        out.attrs["missing_archive_months"] = missing_months
        return out
    except Exception as official_error:
        if not archive.empty:
            archive.attrs["source"] = "binance_vision_official_monthly_archive_partial"
            archive.attrs["missing_archive_months"] = missing_months
            archive.attrs["archive_error"] = str(archive_error) if archive_error else None
            archive.attrs["official_api_error"] = str(official_error)
            return archive

        fallback = (
            "https://huggingface.co/datasets/Crypt-dataset/Binance_Top40/"
            f"resolve/main/funding/{symbol}.parquet"
        )
        response = requests.get(fallback, timeout=90)
        response.raise_for_status()
        data = pd.read_parquet(io.BytesIO(response.content))
        if not {"funding_time", "funding_rate"}.issubset(data.columns):
            raise RuntimeError("Third-party funding dataset has an unexpected schema") from official_error
        data["funding_time"] = pd.to_datetime(
            pd.to_numeric(data.funding_time), unit="ms", utc=True
        )
        data["funding_rate"] = pd.to_numeric(data.funding_rate, errors="coerce")
        if "symbol" in data.columns:
            data = data[data.symbol == symbol]
        out = data.dropna(subset=["funding_rate"]).drop_duplicates("funding_time")
        out = out.set_index("funding_time")[["funding_rate"]].sort_index()
        out["mark_price"] = float("nan")
        out = out.loc[
            (out.index >= pd.Timestamp(start, tz="UTC"))
            & (out.index < pd.Timestamp(end, tz="UTC"))
        ]
        out.attrs["source"] = "third_party_huggingface_archive_unverified"
        out.attrs["official_archive_error"] = str(archive_error) if archive_error else None
        out.attrs["official_api_error"] = str(official_error)
        out.attrs["missing_archive_months"] = missing_months
        return out


def quality_report(data, symbol, start=None, end=None):
    if data.empty:
        return {
            "symbol": symbol, "rows": 0, "start": None, "end": None,
            "expected_minutes": 0, "missing_minutes": None, "coverage_pct": 0.0,
            "duplicate_timestamps": int(data.attrs.get("duplicate_timestamps_before_dedup", 0)),
            "bad_ohlc_rows": 0,
        }

    if start is not None and end is not None:
        expected_start = pd.Timestamp(start, tz="UTC")
        expected_end = pd.Timestamp(end, tz="UTC")
        expected = pd.date_range(
            expected_start, expected_end - pd.Timedelta(minutes=1), freq="1min"
        )
    else:
        expected = pd.date_range(data.index.min(), data.index.max(), freq="1min")

    bad = (
        (data.high < data[["open", "close", "low"]].max(axis=1))
        | (data.low > data[["open", "close", "high"]].min(axis=1))
        | (data.high < data.low)
    ).sum()
    missing_index = expected.difference(data.index)
    missing = len(missing_index)
    missing_intervals = []
    if missing:
        missing_frame = pd.DataFrame({"timestamp": missing_index})
        missing_frame["gap_group"] = (
            missing_frame.timestamp.diff().ne(pd.Timedelta(minutes=1)).cumsum()
        )
        for _, group in missing_frame.groupby("gap_group", sort=True):
            missing_intervals.append({
                "start": str(group.timestamp.iloc[0]),
                "end": str(group.timestamp.iloc[-1]),
                "minutes": int(len(group)),
            })
    coverage = 100 * (len(expected) - missing) / len(expected) if len(expected) else 0.0
    return {
        "symbol": symbol,
        "rows": len(data),
        "start": str(data.index.min()),
        "end": str(data.index.max()),
        "expected_minutes": len(expected),
        "missing_minutes": missing,
        "missing_interval_count": len(missing_intervals),
        "missing_intervals": missing_intervals[:100],
        "missing_intervals_truncated": len(missing_intervals) > 100,
        "coverage_pct": round(coverage, 4),
        "duplicate_timestamps": int(data.attrs.get("duplicate_timestamps_before_dedup", 0)),
        "bad_ohlc_rows": int(bad),
        "source": data.attrs.get("source", "unknown"),
    }

from __future__ import annotations

import pandas as pd
from pathlib import Path
import zipfile

from .data import get_zip, _timestamp_unit

METRICS_BASE = "https://data.binance.vision/data/futures/um/daily/metrics"
METRIC_COLUMNS = [
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
]
NUMERIC_COLUMNS = METRIC_COLUMNS[2:]


def read_metrics_zip(path: Path, symbol: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        csvs = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csvs:
            raise ValueError(f"No metrics CSV in {path}")
        with archive.open(csvs[0]) as stream:
            data = pd.read_csv(stream)

    if "create_time" not in data.columns:
        with zipfile.ZipFile(path) as archive:
            with archive.open(csvs[0]) as stream:
                data = pd.read_csv(stream, header=None, names=METRIC_COLUMNS)

    if "create_time" not in data.columns:
        raise ValueError(f"Unexpected metrics schema in {path}: {list(data.columns)}")

    raw_time = data["create_time"]
    numeric_time = pd.to_numeric(raw_time, errors="coerce")
    if numeric_time.notna().sum() >= max(1, int(0.8 * len(data))):
        time_index = pd.to_datetime(
            numeric_time, unit=_timestamp_unit(numeric_time), errors="coerce", utc=True
        )
    else:
        time_index = pd.to_datetime(raw_time, errors="coerce", utc=True)

    data = data.copy()
    data["time"] = time_index
    data = data.dropna(subset=["time"])
    for column in NUMERIC_COLUMNS:
        if column not in data.columns:
            data[column] = float("nan")
        data[column] = pd.to_numeric(data[column], errors="coerce")

    # Keep direct 5-minute source observations only; never synthesize missing OI.
    data["time"] = data.time.dt.floor("5min")
    data = data.sort_values("time")
    grouped = data.groupby("time", sort=True)[NUMERIC_COLUMNS].last()
    grouped.index = pd.DatetimeIndex(grouped.index).tz_convert("UTC")
    grouped["symbol"] = symbol
    grouped.attrs["source"] = "binance_vision_official_daily_metrics"
    return grouped


def acquire_open_interest(symbol, start, end, root=Path("data")) -> pd.DataFrame:
    """Load Binance Vision 5-minute futures metrics, including OI, over [start, end)."""
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    first_day = start_ts.floor("D") - pd.Timedelta(days=1)
    last_day = end_ts.floor("D")
    days = pd.date_range(first_day, last_day, freq="D")
    parts = []
    missing_days = []

    for day in days:
        date_text = day.strftime("%Y-%m-%d")
        name = f"{symbol}-metrics-{date_text}.zip"
        url = f"{METRICS_BASE}/{symbol}/{name}"
        path = get_zip(
            url,
            root / "raw" / "metrics" / symbol / name,
            verify_checksum=True,
        )
        if path is None:
            missing_days.append(date_text)
            continue
        part = read_metrics_zip(path, symbol)
        if not part.empty:
            parts.append(part)

    if not parts:
        raise RuntimeError(f"No Binance Vision open-interest metrics found for {symbol}")

    data = pd.concat(parts).sort_index()
    data = data[~data.index.duplicated(keep="last")]
    data = data.loc[(data.index >= start_ts) & (data.index < end_ts)]
    data.attrs["source"] = "binance_vision_official_daily_metrics"
    data.attrs["missing_archive_days"] = missing_days
    return data


def metrics_quality_report(data: pd.DataFrame, symbol: str, start, end) -> dict:
    start_ts = pd.Timestamp(start, tz="UTC").floor("5min")
    end_ts = pd.Timestamp(end, tz="UTC").ceil("5min")
    expected = pd.date_range(start_ts, end_ts, freq="5min", inclusive="left")
    missing = len(expected.difference(data.index)) if not data.empty else len(expected)
    return {
        "symbol": symbol,
        "rows": int(len(data)),
        "start": str(data.index.min()) if not data.empty else None,
        "end": str(data.index.max()) if not data.empty else None,
        "expected_5m_buckets": int(len(expected)),
        "missing_5m_buckets": int(missing),
        "coverage_pct": round(100 * (len(expected) - missing) / len(expected), 4) if len(expected) else 0.0,
        "source": data.attrs.get("source", "unknown"),
        "missing_archive_days": len(data.attrs.get("missing_archive_days", [])),
    }

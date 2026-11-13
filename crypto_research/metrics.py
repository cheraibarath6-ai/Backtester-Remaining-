from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
import requests

from .data import get_zip, _timestamp_unit

METRICS_BASE = "https://data.binance.vision/data/futures/um/daily/metrics"
S3_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
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

    # Coalesce each field independently to the final non-null source value
    # inside its five-minute bucket. No missing values are synthesized.
    data["time"] = data.time.dt.floor("5min")
    data = data.sort_values("time")
    grouped = data.groupby("time", sort=True)[NUMERIC_COLUMNS].last()
    grouped.index = pd.DatetimeIndex(grouped.index).tz_convert("UTC")
    grouped["symbol"] = symbol
    grouped.attrs["source"] = "binance_vision_official_daily_metrics"
    return grouped


def _list_metric_archive_days(symbol: str) -> list[str]:
    """List existing daily metrics objects with the public Binance Vision S3 index."""
    prefix = f"data/futures/um/daily/metrics/{symbol}/"
    keys = []
    marker = None
    while True:
        params = {"prefix": prefix, "max-keys": "1000"}
        if marker:
            params["marker"] = marker
        response = requests.get(S3_LIST_URL, params=params, timeout=60)
        response.raise_for_status()
        root = ET.fromstring(response.text)
        batch = [
            node.findtext("s3:Key", namespaces=S3_NS)
            for node in root.findall("s3:Contents", S3_NS)
        ]
        batch = [key for key in batch if key and key.endswith(".zip")]
        keys.extend(batch)
        truncated = root.findtext("s3:IsTruncated", default="false", namespaces=S3_NS) == "true"
        if not truncated or not batch:
            break
        marker = batch[-1]

    days = []
    for key in keys:
        match = re.search(r"metrics-(\d{4}-\d{2}-\d{2})\.zip$", key)
        if match:
            days.append(match.group(1))
    return sorted(set(days))


def acquire_open_interest(symbol, start, end, root=Path("data")) -> pd.DataFrame:
    """Load Binance Vision 5-minute futures metrics, including OI, over [start, end)."""
    start_ts = pd.Timestamp(start, tz="UTC")
    end_ts = pd.Timestamp(end, tz="UTC")
    first_day = (start_ts.floor("D") - pd.Timedelta(days=1)).date()
    last_day = end_ts.floor("D").date()

    try:
        available_days = _list_metric_archive_days(symbol)
        if not available_days:
            raise RuntimeError("Binance Vision S3 listing returned no metric archive keys")
    except Exception:
        # S3 listing is an index optimisation only; fall back to daily key probes.
        available_days = [
            day.strftime("%Y-%m-%d")
            for day in pd.date_range(first_day, last_day, freq="D")
        ]

    requested_days = [
        day for day in available_days
        if first_day <= pd.Timestamp(day).date() <= last_day
    ]
    parts = []
    missing_days = []

    for date_text in requested_days:
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
    data.attrs["archive_days_downloaded"] = len(requested_days)
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
        "archive_days_downloaded": int(data.attrs.get("archive_days_downloaded", 0)),
    }

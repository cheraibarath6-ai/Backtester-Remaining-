from __future__ import annotations

import argparse
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .backtest import run_backtest, summarize
from .combination_run import combination_profiles
from .data import COLS, _read_funding_zip, get_zip, quality_report
from .independent_models import make_independent_signals
from .metrics import metrics_quality_report

VISION_BASE = "https://data.binance.vision/data/futures/um/daily"
OI_TIMESTAMP_SHIFT_START = pd.Timestamp("2026-06-25 00:00:00", tz="UTC")

FORWARD_VARIANTS = {
    "M6": {"D100_STOP2_H168", "RR3_H168", "STOP2_H168"},
    "M11": {"OI05_H48", "PRICE025_RR3_H48", "OI05_PRICE025_H36"},
}


def _utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _naive_utc_text(value) -> str:
    return _utc(value).strftime("%Y-%m-%d %H:%M:%S")


def _request_json(url: str, params: dict, timeout: int = 40):
    last_error = None
    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and payload.get("code") is not None:
                raise RuntimeError(f"Binance API error: {payload}")
            if not isinstance(payload, list):
                raise RuntimeError(f"Unexpected Binance API response: {payload}")
            return payload
        except Exception as error:
            last_error = error
            if attempt == 4:
                break
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"Binance API request failed after retries: {last_error}")


def parse_kline_rows(rows: list) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=[
            "open", "high", "low", "close", "volume", "quote_volume",
            "trades", "taker_buy_base", "taker_buy_quote",
        ])
    data = pd.DataFrame(rows, columns=COLS)
    data["open_time"] = pd.to_datetime(
        pd.to_numeric(data["open_time"], errors="coerce"), unit="ms", utc=True
    )
    numeric = [
        "open", "high", "low", "close", "volume", "quote_volume",
        "taker_buy_base", "taker_buy_quote",
    ]
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["trades"] = pd.to_numeric(data["trades"], errors="coerce").fillna(0)
    data = data.dropna(subset=["open_time", *numeric])
    data = data.sort_values("open_time").drop_duplicates("open_time")
    return data.set_index("open_time")[
        [
            "open", "high", "low", "close", "volume", "quote_volume",
            "trades", "taker_buy_base", "taker_buy_quote",
        ]
    ]


def _timestamp_unit_from_values(values: pd.Series) -> str:
    sample = pd.to_numeric(values, errors="coerce").dropna()
    if sample.empty:
        raise ValueError("Daily archive contains no numeric timestamps")
    magnitude = float(sample.abs().median())
    if magnitude >= 1e17:
        return "ns"
    if magnitude >= 1e14:
        return "us"
    return "ms"


def parse_daily_kline_archive(path: Path) -> pd.DataFrame:
    """Parse an official USD-M daily kline ZIP with or without a CSV header."""
    with zipfile.ZipFile(path) as archive:
        csvs = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csvs:
            raise ValueError(f"No kline CSV in {path}")
        with archive.open(csvs[0]) as stream:
            data = pd.read_csv(stream, header=None)

    first = data.iloc[0, 0] if not data.empty else None
    if pd.isna(pd.to_numeric(pd.Series([first]), errors="coerce").iloc[0]):
        headers = [str(value).strip().lower().replace(" ", "_") for value in data.iloc[0].tolist()]
        data = data.iloc[1:].copy()
        data.columns = headers
        aliases = {
            "quote_asset_volume": "quote_volume",
            "number_of_trades": "trades",
            "taker_buy_base_asset_volume": "taker_buy_base",
            "taker_buy_quote_asset_volume": "taker_buy_quote",
        }
        data = data.rename(columns=aliases)
    else:
        data.columns = COLS[:len(data.columns)]

    required = [
        "open_time", "open", "high", "low", "close", "volume",
        "quote_volume", "trades", "taker_buy_base", "taker_buy_quote",
    ]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Daily kline archive schema missing {missing}; got {list(data.columns)}")

    unit = _timestamp_unit_from_values(data.open_time)
    data["open_time"] = pd.to_datetime(
        pd.to_numeric(data.open_time, errors="coerce"), unit=unit, utc=True
    )
    numeric = [
        "open", "high", "low", "close", "volume", "quote_volume",
        "taker_buy_base", "taker_buy_quote",
    ]
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["trades"] = pd.to_numeric(data.trades, errors="coerce").fillna(0)
    data = data.dropna(subset=["open_time", *numeric]).sort_values("open_time")
    data = data.drop_duplicates("open_time", keep="last")
    return data.set_index("open_time")[required[1:]].sort_index()


def _completed_daily_archive_end(end) -> pd.Timestamp:
    """Only include days whose official daily ZIP could already be published."""
    return _utc(end).floor("D")


def acquire_recent_klines(symbol: str, start, end) -> pd.DataFrame:
    """Fetch completed recent 1m candles from official Binance Vision daily ZIPs.

    Binance's REST API can be region-restricted (HTTP 451). Daily archives avoid
    that endpoint and intentionally exclude the current UTC day, which is not
    yet a complete published daily file.
    """
    start_ts = _utc(start)
    archive_end = _completed_daily_archive_end(end)
    if start_ts >= archive_end:
        raise RuntimeError("No completed Binance Vision daily candle days in requested window")
    parts = []
    missing_days = []
    for day in pd.date_range(start_ts.floor("D"), archive_end - pd.Timedelta(days=1), freq="D"):
        date = day.strftime("%Y-%m-%d")
        name = f"{symbol}-1m-{date}.zip"
        url = f"{VISION_BASE}/klines/{symbol}/1m/{name}"
        path = get_zip(url, Path("data") / "raw" / "forward_klines" / symbol / name, verify_checksum=True)
        if path is None:
            missing_days.append(date)
            continue
        part = parse_daily_kline_archive(path)
        part = part.loc[(part.index >= start_ts) & (part.index < archive_end)]
        if not part.empty:
            parts.append(part)

    if not parts:
        raise RuntimeError(f"No completed Binance Vision daily 1m candles for {symbol}")
    data = pd.concat(parts).sort_index()
    duplicate_count = int(data.index.duplicated().sum())
    data = data[~data.index.duplicated(keep="last")]
    data.attrs["source"] = "binance_vision_official_usdm_daily_1m"
    data.attrs["duplicate_timestamps_before_dedup"] = duplicate_count
    data.attrs["missing_archive_days"] = missing_days
    data.attrs["effective_end"] = str(archive_end)
    return data


def parse_metrics_archive(path: Path, symbol: str) -> pd.DataFrame:
    """Parse daily USD-M metrics; shift post-2026-06-25 OI labels to availability time."""
    with zipfile.ZipFile(path) as archive:
        csvs = [name for name in archive.namelist() if name.endswith(".csv")]
        if not csvs:
            raise ValueError(f"No metrics CSV in {path}")
        with archive.open(csvs[0]) as stream:
            data = pd.read_csv(stream)
    required = {"create_time", "sum_open_interest_value"}
    if not required.issubset(data.columns):
        raise ValueError(f"Unexpected Binance metrics schema for {symbol}: {list(data.columns)}")
    raw_time = data["create_time"]
    if pd.api.types.is_numeric_dtype(raw_time):
        unit = _timestamp_unit_from_values(raw_time)
        timestamp = pd.to_datetime(pd.to_numeric(raw_time, errors="coerce"), unit=unit, utc=True)
    else:
        timestamp = pd.to_datetime(raw_time, utc=True, errors="coerce")
    out = pd.DataFrame(index=pd.DatetimeIndex(timestamp, name="time"))
    out["sum_open_interest_value"] = pd.to_numeric(data["sum_open_interest_value"], errors="coerce").to_numpy()
    if "sum_open_interest" in data:
        out["sum_open_interest"] = pd.to_numeric(data["sum_open_interest"], errors="coerce").to_numpy()
    out = out.dropna(subset=["sum_open_interest_value"]).sort_index()
    # Binance USD-M metrics daily archives changed timestamp labeling on 2026-06-25:
    # OI snapshots labeled T represent T+5m from that date onward. Move the row
    # timestamp to the actual availability time to prevent a 5-minute lookahead.
    shift_mask = out.index >= OI_TIMESTAMP_SHIFT_START
    if shift_mask.any():
        out.index = out.index + pd.to_timedelta(shift_mask.astype(int) * 5, unit="min")
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out["symbol"] = symbol
    out.attrs["timestamp_alignment"] = "post_2026-06-25 labels shifted +5m to actual snapshot availability"
    return out


def acquire_recent_open_interest(symbol: str, start, end) -> pd.DataFrame:
    """Fetch recent official 5m OI metrics from Binance Vision daily archives."""
    start_ts, end_ts = _utc(start), _utc(end)
    parts = []
    missing_days = []
    for day in pd.date_range(start_ts.floor("D"), end_ts.floor("D") - pd.Timedelta(days=1), freq="D"):
        date = day.strftime("%Y-%m-%d")
        name = f"{symbol}-metrics-{date}.zip"
        url = f"{VISION_BASE}/metrics/{symbol}/{name}"
        path = get_zip(url, Path("data") / "raw" / "forward_metrics" / symbol / name, verify_checksum=True)
        if path is None:
            missing_days.append(date)
            continue
        part = parse_metrics_archive(path, symbol)
        parts.append(part)
    if not parts:
        raise RuntimeError(f"No recent official Binance OI metrics archives for {symbol}")
    data = pd.concat(parts).sort_index()
    duplicate_count = int(data.index.duplicated().sum())
    data = data[~data.index.duplicated(keep="last")]
    data = data.loc[(data.index >= start_ts) & (data.index <= end_ts)]
    data.attrs["source"] = "binance_vision_official_daily_metrics"
    data.attrs["missing_archive_days"] = missing_days
    data.attrs["duplicate_timestamps_before_dedup"] = duplicate_count
    data.attrs["timestamp_alignment"] = "post_2026-06-25 create_time shifted +5m; no forward-filled future snapshots"
    return data


def acquire_recent_funding(symbol: str, start, end) -> pd.DataFrame:
    """Fetch official daily funding archives; fail closed if any day is missing."""
    start_ts, end_ts = _utc(start), _utc(end)
    parts = []
    missing_days = []
    for day in pd.date_range(start_ts.floor("D"), end_ts.floor("D") - pd.Timedelta(days=1), freq="D"):
        date = day.strftime("%Y-%m-%d")
        name = f"{symbol}-fundingRate-{date}.zip"
        url = f"{VISION_BASE}/fundingRate/{symbol}/{name}"
        path = get_zip(url, Path("data") / "raw" / "forward_funding" / symbol / name, verify_checksum=True)
        if path is None:
            missing_days.append(date)
            continue
        parts.append(_read_funding_zip(path))
    if missing_days:
        raise RuntimeError(f"Missing official daily funding archives for {symbol}: {missing_days}")
    if not parts:
        raise RuntimeError(f"No official daily funding archives for {symbol}")
    data = pd.concat(parts).sort_index()
    duplicate_count = int(data.index.duplicated().sum())
    data = data[~data.index.duplicated(keep="last")]
    data = data.loc[(data.index >= start_ts) & (data.index < end_ts)]
    if data.empty:
        raise RuntimeError(f"No official funding settlements in forward window for {symbol}")
    data.attrs["source"] = "binance_vision_official_daily_funding_archive"
    data.attrs["missing_archive_days"] = []
    data.attrs["duplicate_timestamps_before_dedup"] = duplicate_count
    return data


def parse_open_interest_rows(rows: list, symbol: str) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    data = pd.DataFrame(rows)
    if "timestamp" not in data or "sumOpenInterestValue" not in data:
        raise RuntimeError(f"Unexpected open-interest API schema: {list(data.columns)}")
    data["time"] = pd.to_datetime(
        pd.to_numeric(data["timestamp"], errors="coerce"), unit="ms", utc=True
    ).dt.floor("5min")
    data["sum_open_interest_value"] = pd.to_numeric(
        data["sumOpenInterestValue"], errors="coerce"
    )
    if "sumOpenInterest" in data:
        data["sum_open_interest"] = pd.to_numeric(data["sumOpenInterest"], errors="coerce")
    else:
        data["sum_open_interest"] = float("nan")
    data = data.dropna(subset=["time", "sum_open_interest_value"])
    data = data.sort_values("time").drop_duplicates("time")
    out = data.set_index("time")[
        ["sum_open_interest", "sum_open_interest_value"]
    ].sort_index()
    out["symbol"] = symbol
    return out




def mask_pre_evaluation_signals(signals: pd.DataFrame, evaluation_start) -> pd.DataFrame:
    """Keep warm-up indicator history but prohibit entries before the forward window."""
    out = signals.copy()
    start_ts = _utc(evaluation_start)
    out.loc[out.index < start_ts, "signal"] = 0
    return out


def selected_forward_profiles() -> dict[str, list[dict]]:
    chosen = {}
    for model, names in FORWARD_VARIANTS.items():
        chosen[model] = [
            profile for profile in combination_profiles(model)
            if profile["variant"] in names
        ]
        found = {profile["variant"] for profile in chosen[model]}
        if found != names:
            raise RuntimeError(f"Forward profile mismatch for {model}: {found} != {names}")
    return chosen


def main():
    parser = argparse.ArgumentParser(
        description="Forward-only M6/M11 validation after 2026-11-01"
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--warmup-start", default="2026-10-12")
    parser.add_argument("--evaluation-start", default="2026-11-01")
    parser.add_argument("--end", default=None, help="Exclusive UTC end; defaults to current completed minute")
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--out", default="forward_holdout_artifacts")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    start_ts = _utc(args.warmup_start)
    evaluation_start = _utc(args.evaluation_start)
    end_ts = _utc(args.end) if args.end else pd.Timestamp.now(tz="UTC").floor("min")
    if start_ts >= evaluation_start or evaluation_start >= end_ts:
        parser.error("Require warmup-start < evaluation-start < end")

    start_text, end_text = _naive_utc_text(start_ts), _naive_utc_text(end_ts)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(
        f"FORWARD HOLDOUT START {symbol}: warmup={start_text}, "
        f"evaluation={evaluation_start}, end_exclusive={end_text}",
        flush=True,
    )

    raw = acquire_recent_klines(symbol, start_ts, end_ts)
    end_ts = _utc(raw.attrs["effective_end"])
    end_text = _naive_utc_text(end_ts)
    if evaluation_start >= end_ts:
        raise RuntimeError("No completed daily archive data exists after the forward evaluation start")
    funding = acquire_recent_funding(symbol, evaluation_start, end_ts)
    candle_quality = quality_report(raw, symbol, start_text, end_text)
    candle_quality["missing_archive_days"] = raw.attrs.get("missing_archive_days", [])
    candle_quality["source"] = raw.attrs.get("source", "unknown")

    oi = None
    oi_quality = None
    try:
        oi_end = end_ts.floor("5min")
        oi_start = max(start_ts, evaluation_start - pd.Timedelta(days=5))
        oi = acquire_recent_open_interest(symbol, oi_start, oi_end)
        oi_quality = metrics_quality_report(
            oi, symbol, _naive_utc_text(oi_start), _naive_utc_text(oi_end)
        )
        oi_quality["source"] = oi.attrs.get("source", "unknown")
        oi.to_csv(out / f"{symbol}_forward_open_interest.csv")
    except Exception as error:
        oi_quality = {"symbol": symbol, "status": "DATA_UNAVAILABLE", "error": str(error)}

    funding_gaps = funding.index.to_series().diff().dropna()
    funding_max_gap = (
        float(funding_gaps.max().total_seconds() / 3600)
        if not funding_gaps.empty else None
    )

    rows, yearly, ledgers = [], [], []
    profiles = selected_forward_profiles()
    expected_last_bar = end_ts.floor("4h")
    for model in ("M6", "M11"):
        if model == "M11" and (oi is None or oi.empty):
            rows.append({
                "model": model, "variant": "FORWARD_SET", "symbol": symbol,
                "timeframe": "4h", "status": "DATA_GATED",
                "skip_reason": "Official recent open-interest history unavailable",
                "trades": 0,
            })
            continue
        for profile in profiles[model]:
            variant = profile["variant"]
            signals = make_independent_signals(
                raw,
                model,
                "4h",
                open_interest=oi if model == "M11" else None,
                parameters=profile["parameters"],
            )
            signals = mask_pre_evaluation_signals(signals, evaluation_start)
            max_hold_bars = max(1, int(round(profile["hold_hours"] / 4)))
            trades = run_backtest(
                signals,
                funding,
                symbol,
                model,
                "4h",
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
                rr=profile["rr"],
                max_hold_bars=max_hold_bars,
                trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                expected_end=expected_last_bar,
            )
            if not trades.empty:
                trades = trades.copy()
                trades["variant"] = variant
                trades["parameters_json"] = json.dumps(profile["parameters"], sort_keys=True)
                trades["evaluation_start"] = str(evaluation_start)
                ledgers.append(trades)
            stats = summarize(trades)
            rows.append({
                "model": model,
                "variant": variant,
                "symbol": symbol,
                "timeframe": "4h",
                "status": "COMPLETED",
                "skip_reason": "",
                "evaluation_start": str(evaluation_start),
                "end_exclusive": end_text,
                "fee_bps_per_side": args.fee_bps,
                "slippage_bps_per_side": args.slippage_bps,
                "rr": profile["rr"],
                "max_hold_hours": profile["hold_hours"],
                "parameters_json": json.dumps(profile["parameters"], sort_keys=True),
                **stats,
            })
            if not trades.empty:
                years = pd.to_datetime(trades.exit_time, utc=True).dt.year
                for year in sorted(years.unique()):
                    part = trades[years == year]
                    yearly.append({
                        "model": model, "variant": variant, "symbol": symbol,
                        "timeframe": "4h", "year": int(year), **summarize(part),
                    })
            print(
                f"FORWARD MODEL END {symbol} {model} {variant}: "
                f"trades={stats['trades']} PF_R={stats['profit_factor_r']} "
                f"net_R={stats['net_R']}",
                flush=True,
            )

    pd.DataFrame(rows).to_csv(out / "screen_results.csv", index=False)
    pd.DataFrame(yearly).to_csv(out / "screen_yearly.csv", index=False)
    if ledgers:
        pd.concat(ledgers, ignore_index=True).to_csv(out / "trade_ledger.csv", index=False)
    else:
        pd.DataFrame().to_csv(out / "trade_ledger.csv", index=False)

    metadata = {
        "symbol": symbol,
        "warmup_start": start_text,
        "evaluation_start": str(evaluation_start),
        "end_exclusive": end_text,
        "models": ["M6", "M11"],
        "variants": {key: [p["variant"] for p in value] for key, value in profiles.items()},
        "timeframe": "4h",
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "candle_quality": candle_quality,
        "candle_source": raw.attrs.get("source", "unknown"),
        "funding_source": funding.attrs.get("source", "unknown"),
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding.attrs.get("missing_archive_months", []),
        "open_interest_quality": oi_quality,
        "note": (
            "Only entries with signal bars at/after evaluation_start are scored. "
            "Warm-up bars are used only to initialize causal indicators. M6 and M11 "
            "are independent. This is a forward-only period after 2026-11-01; "
            "M11 uses official OI history only, no liquidation proxy."
        ),
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(f"FORWARD HOLDOUT COMPLETE {symbol}", flush=True)


if __name__ == "__main__":
    main()

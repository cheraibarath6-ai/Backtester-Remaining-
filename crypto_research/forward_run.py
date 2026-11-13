from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from .backtest import run_backtest, summarize
from .combination_run import combination_profiles
from .data import COLS, acquire_funding, quality_report
from .independent_models import make_independent_signals
from .metrics import metrics_quality_report

KLINE_URL = "https://fapi.binance.com/fapi/v1/klines"
OI_URL = "https://fapi.binance.com/futures/data/openInterestHist"

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


def acquire_recent_klines(symbol: str, start, end) -> pd.DataFrame:
    """Fetch recent completed 1m USD-M candles from Binance's official API."""
    start_ts, end_ts = _utc(start), _utc(end)
    cursor = int(start_ts.timestamp() * 1000)
    end_ms = int(end_ts.timestamp() * 1000)
    rows = []
    while cursor < end_ms:
        batch = _request_json(
            KLINE_URL,
            {
                "symbol": symbol,
                "interval": "1m",
                "startTime": cursor,
                "endTime": end_ms - 1,
                "limit": 1500,
            },
        )
        if not batch:
            break
        rows.extend(batch)
        next_cursor = int(batch[-1][0]) + 60_000
        if next_cursor <= cursor:
            raise RuntimeError("Kline API pagination did not advance")
        cursor = next_cursor
        if len(batch) < 1500:
            break
        time.sleep(0.12)

    data = parse_kline_rows(rows)
    data = data.loc[(data.index >= start_ts) & (data.index < end_ts)]
    if data.empty:
        raise RuntimeError(f"No recent Binance USD-M 1m candles for {symbol}")
    data.attrs["source"] = "binance_official_fapi_klines_api"
    data.attrs["duplicate_timestamps_before_dedup"] = 0
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


def acquire_recent_open_interest(symbol: str, start, end) -> pd.DataFrame:
    """Fetch official 5m OI history; Binance limits this endpoint to recent history."""
    start_ts, end_ts = _utc(start), _utc(end)
    cursor = int(start_ts.timestamp() * 1000)
    end_ms = int(end_ts.timestamp() * 1000)
    rows = []
    step_ms = 5 * 60_000
    while cursor < end_ms:
        batch = _request_json(
            OI_URL,
            {
                "symbol": symbol,
                "period": "5m",
                "startTime": cursor,
                "endTime": end_ms - 1,
                "limit": 500,
            },
        )
        if not batch:
            break
        rows.extend(batch)
        next_cursor = int(batch[-1]["timestamp"]) + step_ms
        if next_cursor <= cursor:
            raise RuntimeError("Open-interest API pagination did not advance")
        cursor = next_cursor
        if len(batch) < 500:
            break
        time.sleep(0.12)

    data = parse_open_interest_rows(rows, symbol)
    data = data.loc[(data.index >= start_ts) & (data.index < end_ts)]
    if data.empty:
        raise RuntimeError(f"No recent Binance open-interest history for {symbol}")
    data.attrs["source"] = "binance_official_open_interest_hist_api"
    data.attrs["missing_archive_days"] = []
    data.attrs["archive_days_downloaded"] = 0
    return data


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
    funding = acquire_funding(symbol, start_text, end_text)
    candle_quality = quality_report(raw, symbol, start_text, end_text)
    candle_quality["source"] = raw.attrs.get("source", "unknown")

    oi = None
    oi_quality = None
    try:
        oi_end = end_ts.floor("5min")
        oi = acquire_recent_open_interest(symbol, start_ts, oi_end)
        oi_quality = metrics_quality_report(oi, symbol, start_ts, oi_end)
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

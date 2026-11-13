from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import run_backtest, summarize
from .data import acquire_funding, acquire_klines, quality_report
from .independent_models import make_independent_signals
from .metrics import acquire_open_interest, metrics_quality_report


def sensitivity_profiles(model: str) -> list[dict]:
    """One-factor-at-a-time profiles; each run remains an independent model."""
    if model == "M6":
        base = {
            "donchian_period": 55,
            "volume_ratio_min": 1.0,
            "stop_atr": 2.5,
        }
        return [
            {"variant": "BASELINE", "parameters": base.copy(), "rr": 2.0, "hold_hours": 24.0},
            {"variant": "DONCHIAN_20", "parameters": {**base, "donchian_period": 20}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "DONCHIAN_100", "parameters": {**base, "donchian_period": 100}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "STOP_ATR_2.0", "parameters": {**base, "stop_atr": 2.0}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "STOP_ATR_3.0", "parameters": {**base, "stop_atr": 3.0}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "VOLUME_0.8", "parameters": {**base, "volume_ratio_min": 0.8}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "VOLUME_1.2", "parameters": {**base, "volume_ratio_min": 1.2}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "RR_1.5", "parameters": base.copy(), "rr": 1.5, "hold_hours": 24.0},
            {"variant": "RR_3.0", "parameters": base.copy(), "rr": 3.0, "hold_hours": 24.0},
            {"variant": "HOLD_48H", "parameters": base.copy(), "rr": 2.0, "hold_hours": 48.0},
            {"variant": "HOLD_72H", "parameters": base.copy(), "rr": 2.0, "hold_hours": 72.0},
            {"variant": "HOLD_168H", "parameters": base.copy(), "rr": 2.0, "hold_hours": 168.0},
            {"variant": "ATR_TRAIL_2.5", "parameters": base.copy(), "rr": 2.0, "hold_hours": 24.0, "trailing_atr_multiple": 2.5},
        ]

    if model == "M11":
        base = {
            "oi_lookback": 12,
            "oi_change_min": 0.01,
            "price_change_min": 0.005,
            "taker_threshold": 0.55,
            "stop_atr": 2.0,
        }
        return [
            {"variant": "BASELINE", "parameters": base.copy(), "rr": 2.0, "hold_hours": 24.0},
            {"variant": "OI_LOOKBACK_6", "parameters": {**base, "oi_lookback": 6}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "OI_LOOKBACK_24", "parameters": {**base, "oi_lookback": 24}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "OI_THRESHOLD_0.5PCT", "parameters": {**base, "oi_change_min": 0.005}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "OI_THRESHOLD_1.5PCT", "parameters": {**base, "oi_change_min": 0.015}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "PRICE_THRESHOLD_0.25PCT", "parameters": {**base, "price_change_min": 0.0025}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "PRICE_THRESHOLD_1.0PCT", "parameters": {**base, "price_change_min": 0.01}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "TAKER_0.52", "parameters": {**base, "taker_threshold": 0.52}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "TAKER_0.60", "parameters": {**base, "taker_threshold": 0.60}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "STOP_ATR_1.5", "parameters": {**base, "stop_atr": 1.5}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "STOP_ATR_2.5", "parameters": {**base, "stop_atr": 2.5}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "RR_1.5", "parameters": base.copy(), "rr": 1.5, "hold_hours": 24.0},
            {"variant": "RR_3.0", "parameters": base.copy(), "rr": 3.0, "hold_hours": 24.0},
            {"variant": "HOLD_48H", "parameters": base.copy(), "rr": 2.0, "hold_hours": 48.0},
            {"variant": "HOLD_72H", "parameters": base.copy(), "rr": 2.0, "hold_hours": 72.0},
            {"variant": "HOLD_168H", "parameters": base.copy(), "rr": 2.0, "hold_hours": 168.0},
        ]

    raise ValueError(f"Unsupported sensitivity model: {model}")


def period_summary(trades: pd.DataFrame, start_year: int, end_year: int) -> dict:
    if trades.empty:
        return summarize(trades)
    years = pd.to_datetime(trades.exit_time, utc=True).dt.year
    return summarize(trades[(years >= start_year) & (years <= end_year)])


def yearly_rows(trades: pd.DataFrame, base: dict) -> list[dict]:
    out = []
    years = pd.to_datetime(trades.exit_time, utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
    for year in range(2021, 2027):
        part = trades[years == year] if not trades.empty else trades
        out.append({**base, "year": year, **summarize(part)})
    return out


def main():
    parser = argparse.ArgumentParser(description="One-factor-at-a-time M6/M11 futures sensitivity screen")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--models", nargs="+", choices=["M6", "M11"], default=["M6", "M11"])
    parser.add_argument("--timeframes", nargs="+", choices=["1h", "4h"], default=["1h", "4h"])
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--out", default="sensitivity_artifacts")
    args = parser.parse_args()

    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be later than --start")

    symbol = args.symbol.upper()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"SENSITIVITY START {symbol} {args.start}..{args.end}", flush=True)

    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    candle_quality = quality_report(raw, symbol, args.start, args.end)
    funding_gaps = funding.index.to_series().diff().dropna()
    funding_max_gap = (
        float(funding_gaps.max().total_seconds() / 3600)
        if not funding_gaps.empty else None
    )
    funding_missing_months = funding.attrs.get("missing_archive_months", [])

    oi = None
    oi_quality = None
    if "M11" in args.models:
        try:
            oi = acquire_open_interest(symbol, args.start, args.end)
            oi_quality = metrics_quality_report(oi, symbol, args.start, args.end)
            oi.to_csv(out / f"{symbol}_open_interest_metrics.csv")
        except Exception as error:
            oi_quality = {"symbol": symbol, "status": "DATA_UNAVAILABLE", "error": str(error)}

    results = []
    yearly = []
    ledgers = []
    for model in args.models:
        profiles = sensitivity_profiles(model)
        for timeframe in args.timeframes:
            for profile in profiles:
                variant = profile["variant"]
                parameters = profile["parameters"]
                hold_hours = float(profile["hold_hours"])
                trailing = profile.get("trailing_atr_multiple")
                if model == "M11" and (oi is None or oi.empty):
                    stats = {"status": "DATA_GATED", "skip_reason": "Official historical OI metrics unavailable"}
                    trades = pd.DataFrame()
                    years = []
                else:
                    signals = make_independent_signals(
                        raw, model, timeframe,
                        open_interest=oi if model == "M11" else None,
                        parameters=parameters,
                    )
                    bar_minutes = {"1h": 60, "4h": 240}[timeframe]
                    max_hold_bars = max(1, int(round(hold_hours * 60 / bar_minutes)))
                    trades = run_backtest(
                        signals, funding, symbol, model, timeframe,
                        fee_bps=args.fee_bps,
                        slippage_bps=args.slippage_bps,
                        rr=float(profile["rr"]),
                        max_hold_bars=max_hold_bars,
                        trailing_atr_multiple=trailing,
                        expected_end=args.end,
                    )
                    stats = summarize(trades)
                    stats.update({
                        "status": "COMPLETED",
                        "skip_reason": "",
                        "signal_bars": int(signals.signal.ne(0).sum()),
                        "bars": int(len(signals)),
                        "max_hold_hours": hold_hours,
                        "max_hold_bars": max_hold_bars,
                        "rr": float(profile["rr"]),
                        "trailing_atr_multiple": trailing,
                        "parameters_json": json.dumps(parameters, sort_keys=True),
                    })
                    if not trades.empty:
                        trades = trades.copy()
                        trades["variant"] = variant
                        trades["parameters_json"] = json.dumps(parameters, sort_keys=True)
                    base = {"model": model, "variant": variant, "symbol": symbol, "timeframe": timeframe}
                    years = yearly_rows(trades, base)
                    stats.update({f"development_{k}": v for k, v in period_summary(trades, 2021, 2024).items()})
                    stats.update({f"validation_2025_{k}": v for k, v in period_summary(trades, 2025, 2025).items()})
                    stats.update({f"holdout_2026_{k}": v for k, v in period_summary(trades, 2026, 2026).items()})

                row = {
                    "model": model,
                    "variant": variant,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start": args.start,
                    "end_exclusive": args.end,
                    "fee_bps_per_side": args.fee_bps,
                    "slippage_bps_per_side": args.slippage_bps,
                    "funding_source": funding.attrs.get("source", "unknown"),
                    "funding_rows": int(len(funding)),
                    "funding_max_gap_hours": funding_max_gap,
                    "funding_missing_archive_months": json.dumps(funding_missing_months),
                    "candle_coverage_pct": candle_quality.get("coverage_pct"),
                    "oi_coverage_pct": oi_quality.get("coverage_pct") if oi_quality else None,
                    "rr": float(profile["rr"]),
                    "max_hold_hours": hold_hours,
                    "trailing_atr_multiple": trailing,
                    "parameters_json": json.dumps(parameters, sort_keys=True),
                    **stats,
                }
                results.append(row)
                yearly.extend(years)
                if not trades.empty:
                    ledgers.append(trades)
                print(
                    f"{symbol} {model} {variant} {timeframe}: "
                    f"status={row.get('status')} trades={row.get('trades', 0)} "
                    f"PF={row.get('profit_factor')} netR={row.get('net_R')}",
                    flush=True,
                )

    pd.DataFrame(results).to_csv(out / "screen_results.csv", index=False)
    pd.DataFrame(yearly).to_csv(out / "screen_yearly.csv", index=False)
    if ledgers:
        pd.concat(ledgers, ignore_index=True).to_csv(out / "trade_ledger.csv", index=False)
    else:
        pd.DataFrame().to_csv(out / "trade_ledger.csv", index=False)

    metadata = {
        "symbol": symbol,
        "period": {"start_inclusive": args.start, "end_exclusive": args.end},
        "models": args.models,
        "timeframes": args.timeframes,
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "candle_quality": candle_quality,
        "funding_source": funding.attrs.get("source", "unknown"),
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding_missing_months,
        "open_interest_quality": oi_quality,
        "note": (
            "M6 and M11 are evaluated independently. This is a one-factor-at-a-time "
            "sensitivity screen, not an ensemble or a deployment selection. "
            "M11 uses official historical OI only; no liquidation or price-only proxy is substituted. "
            "2021-2024 is development, 2025 is validation, and 2026 is reported as a retrospective holdout."
        ),
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(f"SENSITIVITY COMPLETE {symbol}", flush=True)


if __name__ == "__main__":
    main()

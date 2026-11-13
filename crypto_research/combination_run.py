from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import completed_period_cohort, run_backtest, summarize
from .data import acquire_funding, acquire_klines, quality_report
from .independent_models import make_independent_signals
from .metrics import acquire_open_interest, metrics_quality_report


def combination_profiles(model: str) -> list[dict]:
    """Predeclared within-model combinations; M6 and M11 remain separate."""
    if model == "M6":
        base = {"donchian_period": 55, "volume_ratio_min": 1.0, "stop_atr": 2.5}
        return [
            {"variant": "BASELINE_H24", "parameters": base.copy(), "rr": 2.0, "hold_hours": 24.0},
            {"variant": "HOLD_48H", "parameters": base.copy(), "rr": 2.0, "hold_hours": 48.0},
            {"variant": "STOP2_H24", "parameters": {**base, "stop_atr": 2.0}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "RR3_H24", "parameters": base.copy(), "rr": 3.0, "hold_hours": 24.0},
            {"variant": "TRAIL25_H24", "parameters": base.copy(), "rr": 2.0, "hold_hours": 24.0, "trailing_atr_multiple": 2.5},
            {"variant": "VOLUME12_H24", "parameters": {**base, "volume_ratio_min": 1.2}, "rr": 2.0, "hold_hours": 24.0},
            {"variant": "ANCHOR_H168", "parameters": base.copy(), "rr": 2.0, "hold_hours": 168.0},
            {"variant": "D100_H168", "parameters": {**base, "donchian_period": 100}, "rr": 2.0, "hold_hours": 168.0},
            {"variant": "STOP2_H168", "parameters": {**base, "stop_atr": 2.0}, "rr": 2.0, "hold_hours": 168.0},
            {"variant": "D100_STOP2_H168", "parameters": {**base, "donchian_period": 100, "stop_atr": 2.0}, "rr": 2.0, "hold_hours": 168.0},
            {"variant": "D100_VOL12_H168", "parameters": {**base, "donchian_period": 100, "volume_ratio_min": 1.2}, "rr": 2.0, "hold_hours": 168.0},
            {"variant": "RR3_H168", "parameters": base.copy(), "rr": 3.0, "hold_hours": 168.0},
            {"variant": "D100_RR3_H168", "parameters": {**base, "donchian_period": 100}, "rr": 3.0, "hold_hours": 168.0},
            {"variant": "D100_STOP2_RR3_H168", "parameters": {**base, "donchian_period": 100, "stop_atr": 2.0}, "rr": 3.0, "hold_hours": 168.0},
            {"variant": "TRAIL25_H168", "parameters": base.copy(), "rr": 2.0, "hold_hours": 168.0, "trailing_atr_multiple": 2.5},
            {"variant": "D100_TRAIL25_H168", "parameters": {**base, "donchian_period": 100}, "rr": 2.0, "hold_hours": 168.0, "trailing_atr_multiple": 2.5},
            {"variant": "D100_VOL12_RR3_H168", "parameters": {**base, "donchian_period": 100, "volume_ratio_min": 1.2}, "rr": 3.0, "hold_hours": 168.0},
            {"variant": "D100_H120", "parameters": {**base, "donchian_period": 100}, "rr": 2.0, "hold_hours": 120.0},
            {"variant": "D100_H144", "parameters": {**base, "donchian_period": 100}, "rr": 2.0, "hold_hours": 144.0},
            {"variant": "D100_H192", "parameters": {**base, "donchian_period": 100}, "rr": 2.0, "hold_hours": 192.0},
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
            {"variant": "BASELINE_H24", "parameters": base.copy(), "rr": 2.0, "hold_hours": 24.0},
            {"variant": "ANCHOR_H48", "parameters": base.copy(), "rr": 2.0, "hold_hours": 48.0},
            {"variant": "OI05_PRICE025_H48", "parameters": {**base, "oi_change_min": 0.005, "price_change_min": 0.0025}, "rr": 2.0, "hold_hours": 48.0},
            {"variant": "OI05_PRICE025_RR3_H48", "parameters": {**base, "oi_change_min": 0.005, "price_change_min": 0.0025}, "rr": 3.0, "hold_hours": 48.0},
            {"variant": "PRICE025_RR3_H48", "parameters": {**base, "price_change_min": 0.0025}, "rr": 3.0, "hold_hours": 48.0},
            {"variant": "OI05_RR3_H48", "parameters": {**base, "oi_change_min": 0.005}, "rr": 3.0, "hold_hours": 48.0},
            {"variant": "OI05_PRICE025_H72", "parameters": {**base, "oi_change_min": 0.005, "price_change_min": 0.0025}, "rr": 2.0, "hold_hours": 72.0},
            {"variant": "OI05_PRICE025_STOP25_H48", "parameters": {**base, "oi_change_min": 0.005, "price_change_min": 0.0025, "stop_atr": 2.5}, "rr": 2.0, "hold_hours": 48.0},
            {"variant": "OI05_PRICE025_RR3_H72", "parameters": {**base, "oi_change_min": 0.005, "price_change_min": 0.0025}, "rr": 3.0, "hold_hours": 72.0},
            {"variant": "PRICE025_H48", "parameters": {**base, "price_change_min": 0.0025}, "rr": 2.0, "hold_hours": 48.0},
            {"variant": "OI05_H48", "parameters": {**base, "oi_change_min": 0.005}, "rr": 2.0, "hold_hours": 48.0},
            {"variant": "RR3_H48", "parameters": base.copy(), "rr": 3.0, "hold_hours": 48.0},
            {"variant": "OI05_PRICE025_H36", "parameters": {**base, "oi_change_min": 0.005, "price_change_min": 0.0025}, "rr": 2.0, "hold_hours": 36.0},
            {"variant": "OI05_PRICE025_H60", "parameters": {**base, "oi_change_min": 0.005, "price_change_min": 0.0025}, "rr": 2.0, "hold_hours": 60.0},
        ]

    raise ValueError(f"Unsupported combination model: {model}")


def _period_summary(trades: pd.DataFrame, start_year: int, end_year: int) -> dict:
    start = pd.Timestamp(year=start_year, month=1, day=1, tz="UTC")
    end_exclusive = pd.Timestamp(year=end_year + 1, month=1, day=1, tz="UTC")
    return summarize(completed_period_cohort(trades, start, end_exclusive))


def _yearly_rows(trades: pd.DataFrame, base: dict) -> list[dict]:
    rows = []
    years = pd.to_datetime(trades.exit_time, utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
    for year in range(2021, 2027):
        part = trades[years == year] if not trades.empty else trades
        rows.append({**base, "year": year, **summarize(part)})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Independent M6/M11 combined-parameter research")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--models", nargs="+", choices=["M6", "M11"], default=["M6", "M11"])
    parser.add_argument("--timeframe", choices=["1h", "4h"], default="4h")
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--out", default="combination_artifacts")
    args = parser.parse_args()

    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be later than --start")

    symbol = args.symbol.upper()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"COMBINATION START {symbol} {args.start}..{args.end}", flush=True)

    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    candle_quality = quality_report(raw, symbol, args.start, args.end)
    funding_gaps = funding.index.to_series().diff().dropna()
    funding_max_gap = float(funding_gaps.max().total_seconds() / 3600) if not funding_gaps.empty else None

    oi = None
    oi_quality = None
    if "M11" in args.models:
        try:
            oi = acquire_open_interest(symbol, args.start, args.end)
            oi_quality = metrics_quality_report(oi, symbol, args.start, args.end)
            oi.to_csv(out / f"{symbol}_open_interest_metrics.csv")
        except Exception as error:
            oi_quality = {"symbol": symbol, "status": "DATA_UNAVAILABLE", "error": str(error)}

    result_rows, yearly, ledgers = [], [], []
    bar_minutes = {"1h": 60, "4h": 240}[args.timeframe]
    for model in args.models:
        if model == "M11" and (oi is None or oi.empty):
            result_rows.append({
                "model": model, "variant": "ALL", "symbol": symbol, "timeframe": args.timeframe,
                "status": "DATA_GATED", "skip_reason": "Historical Binance OI unavailable",
                "trades": 0,
            })
            continue
        for profile in combination_profiles(model):
            variant = profile["variant"]
            print(f"MODEL START {model} {variant} {symbol} {args.timeframe}", flush=True)
            try:
                signals = make_independent_signals(
                    raw, model, args.timeframe,
                    open_interest=oi if model == "M11" else None,
                    parameters=profile["parameters"],
                )
                max_hold_bars = max(1, int(round(profile["hold_hours"] * 60 / bar_minutes)))
                trades = run_backtest(
                    signals, funding, symbol, model, args.timeframe,
                    fee_bps=args.fee_bps,
                    slippage_bps=args.slippage_bps,
                    rr=profile["rr"],
                    max_hold_bars=max_hold_bars,
                    trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                    expected_end=args.end,
                )
                base = {
                    "model": model, "variant": variant, "symbol": symbol, "timeframe": args.timeframe,
                }
                if not trades.empty:
                    trades = trades.copy()
                    trades["variant"] = variant
                    trades["parameters_json"] = json.dumps(profile["parameters"], sort_keys=True)
                    ledgers.append(trades)
                dev = _period_summary(trades, 2021, 2024)
                val = _period_summary(trades, 2025, 2025)
                retrospective = _period_summary(trades, 2026, 2026)
                stats = summarize(trades)
                stats.update({
                    "status": "COMPLETED",
                    "skip_reason": "",
                    "rr": profile["rr"],
                    "max_hold_hours": profile["hold_hours"],
                    "max_hold_bars": max_hold_bars,
                    "trailing_atr_multiple": profile.get("trailing_atr_multiple"),
                    "parameters_json": json.dumps(profile["parameters"], sort_keys=True),
                    **{f"development_{k}": v for k, v in dev.items()},
                    **{f"validation_2025_{k}": v for k, v in val.items()},
                    **{f"retrospective_2026_{k}": v for k, v in retrospective.items()},
                })
                result_rows.append({**base, **stats})
                yearly.extend(_yearly_rows(trades, base))
                print(f"MODEL END {model} {variant} trades={stats['trades']} PF_R={stats['profit_factor_r']} net_R={stats['net_R']}", flush=True)
            except Exception as error:
                result_rows.append({
                    "model": model, "variant": variant, "symbol": symbol, "timeframe": args.timeframe,
                    "status": "FAILED", "skip_reason": f"{type(error).__name__}: {error}", "trades": 0,
                })
                print(f"MODEL ERROR {model} {variant}: {error}", flush=True)

    pd.DataFrame(result_rows).to_csv(out / "screen_results.csv", index=False)
    pd.DataFrame(yearly).to_csv(out / "screen_yearly.csv", index=False)
    pd.concat(ledgers, ignore_index=True).to_csv(out / "trade_ledger.csv", index=False) if ledgers else pd.DataFrame().to_csv(out / "trade_ledger.csv", index=False)
    metadata = {
        "symbol": symbol,
        "period": {"start_inclusive": args.start, "end_exclusive": args.end},
        "models": args.models,
        "timeframe": args.timeframe,
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "candle_quality": candle_quality,
        "funding_source": funding.attrs.get("source", "unknown"),
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding.attrs.get("missing_archive_months", []),
        "open_interest_quality": oi_quality,
        "note": "Each within-model parameter combination is an independent strategy. M6 and M11 are never combined. 2021-2024 is development, 2025 validation, and 2026 is reported as a later audit period. M11 is OI-only; no liquidation proxy is used.",
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(f"COMBINATION COMPLETE {symbol}", flush=True)


if __name__ == "__main__":
    main()

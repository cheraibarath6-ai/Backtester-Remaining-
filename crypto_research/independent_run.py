from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import run_backtest, summarize
from .data import acquire_funding, acquire_klines, quality_report
from .grid import make_grid_signals
from .independent_models import INDEPENDENT_MODELS, make_independent_signals
from .metrics import acquire_open_interest, metrics_quality_report
from .pfi_stage4 import PROFILES

ALL_MODELS = ("M1", "M2", "M4", "M5", *INDEPENDENT_MODELS)
TIMEFRAMES = ("5m", "15m", "1h", "4h")


def _period_summary(trades: pd.DataFrame, start_year: int, end_year: int) -> dict:
    if trades.empty:
        return summarize(trades)
    years = pd.to_datetime(trades.exit_time, utc=True).dt.year
    return summarize(trades[(years >= start_year) & (years <= end_year)])


def _year_rows(trades: pd.DataFrame, base: dict, years=range(2021, 2027)) -> list[dict]:
    out = []
    if trades.empty:
        for year in years:
            out.append({**base, "year": year, **summarize(trades)})
        return out
    trade_years = pd.to_datetime(trades.exit_time, utc=True).dt.year
    for year in years:
        out.append({
            **base,
            "year": year,
            **summarize(trades[trade_years == year]),
        })
    return out


def _evaluate(
    raw: pd.DataFrame,
    funding: pd.DataFrame,
    symbol: str,
    model: str,
    variant: str,
    timeframe: str,
    fee_bps: float,
    slippage_bps: float,
    rr: float,
    max_hold_hours: float,
    benchmark_raw: pd.DataFrame | None,
    oi: pd.DataFrame | None,
) -> tuple[dict, pd.DataFrame, list[dict]]:
    if model == "M11" and (oi is None or oi.empty):
        return {
            "status": "DATA_GATED",
            "skip_reason": "Historical Binance open-interest metrics were unavailable for this symbol/period",
        }, pd.DataFrame(), []
    if model in ("M1", "M2", "M4", "M5"):
        if timeframe not in ("5m", "15m"):
            return {"status": "BASELINE_TIMEFRAME_UNSUPPORTED", "skip_reason": "Existing PFI baseline implementation supports 5m/15m only"}, pd.DataFrame(), []
        if symbol not in ("BTCUSDT", "ETHUSDT"):
            return {"status": "BASELINE_SYMBOL_NOT_IN_STAGE4", "skip_reason": "Existing PFI baseline anchors were validated on BTCUSDT/ETHUSDT"}, pd.DataFrame(), []
        profile = next(p for p in PROFILES[model] if p["profile"] == variant)
        params = profile["parameters"]
        signals = make_grid_signals(raw, model, timeframe, funding if model == "M5" else None, params)
    else:
        if model in ("M10", "M13") and symbol == "BTCUSDT":
            return {"status": "NOT_APPLICABLE", "skip_reason": "BTC is the benchmark, not a traded leg, for this standalone relative strategy"}, pd.DataFrame(), []
        signals = make_independent_signals(
            raw,
            model,
            timeframe,
            benchmark_raw=benchmark_raw,
            open_interest=oi if model == "M11" else None,
        )
        params = {"profile": "baseline_v1"}

    bar_minutes = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}[timeframe]
    max_hold_bars = max(1, int(round(max_hold_hours * 60 / bar_minutes)))
    signal_count = int(signals.signal.ne(0).sum())
    trades = run_backtest(
        signals,
        funding,
        symbol,
        model,
        timeframe,
        fee_bps,
        slippage_bps,
        rr,
        max_hold_bars=max_hold_bars,
    )
    stats = summarize(trades)
    stats.update({
        "status": "COMPLETED",
        "skip_reason": "",
        "variant": variant,
        "signal_bars": signal_count,
        "bars": int(len(signals)),
        "max_hold_hours": max_hold_hours,
        "max_hold_bars": max_hold_bars,
        "parameters_json": json.dumps(params, sort_keys=True),
    })
    if not trades.empty:
        trades = trades.copy()
        trades["variant"] = variant
        trades["signal_bars"] = signal_count
        trades["parameters_json"] = json.dumps(params, sort_keys=True)
    base = {"model": model, "variant": variant, "symbol": symbol, "timeframe": timeframe}
    yearly = _year_rows(trades, base)
    development = _period_summary(trades, 2021, 2024)
    validation = _period_summary(trades, 2025, 2025)
    holdout = _period_summary(trades, 2026, 2026)
    stats.update({f"development_{key}": value for key, value in development.items()})
    stats.update({f"validation_2025_{key}": value for key, value in validation.items()})
    stats.update({f"holdout_2026_{key}": value for key, value in holdout.items()})
    return stats, trades, yearly


def main():
    parser = argparse.ArgumentParser(description="Independent crypto-futures core-engine screen")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--benchmark-symbol", default="BTCUSDT")
    parser.add_argument("--models", nargs="+", choices=ALL_MODELS, default=list(ALL_MODELS))
    parser.add_argument("--timeframes", nargs="+", choices=TIMEFRAMES, default=list(TIMEFRAMES))
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--max-hold-hours", type=float, default=24.0)
    parser.add_argument("--out", default="independent_screen_artifacts")
    args = parser.parse_args()

    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be later than --start")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    symbol = args.symbol.upper()
    print(f"SCREEN START {symbol} {args.start}..{args.end}", flush=True)

    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    candle_quality = quality_report(raw, symbol, args.start, args.end)
    funding.to_csv(out / f"{symbol}_funding.csv")
    funding_gaps = funding.index.to_series().diff().dropna()
    funding_max_gap_hours = (
        float(funding_gaps.max().total_seconds() / 3600)
        if not funding_gaps.empty else None
    )
    funding_missing_months = funding.attrs.get("missing_archive_months", [])

    benchmark_raw = None
    if symbol != args.benchmark_symbol and any(m in args.models for m in ("M10", "M13")):
        benchmark_raw = acquire_klines(args.benchmark_symbol, args.start, args.end)

    oi = None
    oi_quality = None
    if "M11" in args.models:
        try:
            oi = acquire_open_interest(symbol, args.start, args.end)
            oi_quality = metrics_quality_report(oi, symbol, args.start, args.end)
            oi.to_csv(out / f"{symbol}_open_interest_metrics.csv")
        except Exception as error:
            oi_quality = {"symbol": symbol, "status": "DATA_UNAVAILABLE", "error": str(error)}

    result_rows = []
    yearly_rows = []
    trade_parts = []
    for model in args.models:
        variants = ["P1", "P2"] if model in ("M1", "M2", "M4", "M5") else ["BASELINE"]
        for timeframe in args.timeframes:
            for variant in variants:
                base = {
                    "model": model,
                    "variant": variant,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "start": args.start,
                    "end_exclusive": args.end,
                    "fee_bps_per_side": args.fee_bps,
                    "slippage_bps_per_side": args.slippage_bps,
                    "planned_rr": args.rr,
                    "funding_source": funding.attrs.get("source", "unknown"),
                    "funding_rows": int(len(funding)),
                    "funding_max_gap_hours": funding_max_gap_hours,
                    "funding_missing_archive_months": json.dumps(funding_missing_months),
                    "candle_coverage_pct": candle_quality.get("coverage_pct"),
                    "oi_coverage_pct": oi_quality.get("coverage_pct") if oi_quality else None,
                }
                print(f"MODEL START {model} {variant} {symbol} {timeframe}", flush=True)
                try:
                    stats, trades, years = _evaluate(
                        raw, funding, symbol, model, variant, timeframe,
                        args.fee_bps, args.slippage_bps, args.rr,
                        args.max_hold_hours, benchmark_raw, oi,
                    )
                    row = {**base, **stats}
                    if not trades.empty:
                        trades = trades.copy()
                        trades["model"] = model
                        trades["symbol"] = symbol
                        trades["timeframe"] = timeframe
                        trade_parts.append(trades)
                    yearly_rows.extend(years)
                except Exception as error:
                    row = {
                        **base,
                        "status": "FAILED",
                        "skip_reason": f"{type(error).__name__}: {error}",
                        "trades": 0,
                        "wins": 0,
                        "losses": 0,
                        "win_rate_pct": 0.0,
                        "profit_factor": None,
                        "net_return_pct": 0.0,
                        "net_bps": 0.0,
                        "net_R": 0.0,
                        "max_drawdown_pct": 0.0,
                    }
                    print(f"MODEL ERROR {model} {variant} {timeframe}: {error}", flush=True)
                result_rows.append(row)
                print(
                    f"MODEL END {model} {variant} {timeframe} "
                    f"status={row.get('status')} trades={row.get('trades', 0)} "
                    f"PF={row.get('profit_factor')}",
                    flush=True,
                )

    results = pd.DataFrame(result_rows)
    yearly = pd.DataFrame(yearly_rows)
    results.to_csv(out / "screen_results.csv", index=False)
    yearly.to_csv(out / "screen_yearly.csv", index=False)
    if trade_parts:
        pd.concat(trade_parts, ignore_index=True).to_csv(out / "trade_ledger.csv", index=False)
    else:
        pd.DataFrame().to_csv(out / "trade_ledger.csv", index=False)

    metadata = {
        "symbol": symbol,
        "benchmark_symbol": args.benchmark_symbol,
        "period": {"start_inclusive": args.start, "end_exclusive": args.end},
        "models": args.models,
        "timeframes": args.timeframes,
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "planned_rr": args.rr,
        "max_hold_hours": args.max_hold_hours,
        "candle_quality": candle_quality,
        "funding_source": funding.attrs.get("source", "unknown"),
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap_hours,
        "funding_missing_archive_months": funding_missing_months,
        "open_interest_quality": oi_quality,
        "open_interest_rows": int(len(oi)) if oi is not None else 0,
        "note": (
            "Each model/profile is evaluated independently. Funding cashflows are charged to every "
            "perpetual position held across a settlement timestamp; funding-derived entry signals are "
            "used only by M5. M3 is intentionally excluded. Baseline P1/P2 profiles are the user's "
            "previous Stage 4 candidates. New M6-M15 are fixed first-pass baselines, not optimized."
        ),
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(json.dumps(metadata, indent=2, default=str), flush=True)
    print(f"SCREEN COMPLETE {symbol}", flush=True)


if __name__ == "__main__":
    main()

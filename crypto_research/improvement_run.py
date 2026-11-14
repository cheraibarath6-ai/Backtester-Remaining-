from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import completed_period_cohort, run_backtest, summarize
from .data import acquire_funding, acquire_klines, quality_report
from .independent_models import make_independent_signals

ACTIVE_MODELS = ("M6", "M7", "M8", "M10", "M12", "M13", "M14", "M15")
TIMEFRAME_MINUTES = {"5m": 5, "15m": 15, "1h": 60, "4h": 240}
OFFICIAL_FUNDING_SOURCES = {
    "binance_vision_official_monthly_archive",
    "binance_vision_archive_plus_official_api",
    "binance_official_api",
}


def _profile(model, variant, parameters, rr=2.0, hold_hours=24.0, trailing=None):
    row = {
        "model": model,
        "variant": variant,
        "parameters": parameters,
        "rr": float(rr),
        "hold_hours": float(hold_hours),
    }
    if trailing is not None:
        row["trailing_atr_multiple"] = float(trailing)
    return row


def improvement_profiles():
    p = {}
    b = {"donchian_period": 55, "volume_ratio_min": 1.0, "stop_atr": 2.5}
    p["M6"] = [
        _profile("M6", "BASELINE", b.copy()),
        _profile("M6", "DONCHIAN_20", {**b, "donchian_period": 20}),
        _profile("M6", "DONCHIAN_100", {**b, "donchian_period": 100}),
        _profile("M6", "STOP_ATR_2_0", {**b, "stop_atr": 2.0}),
        _profile("M6", "STOP_ATR_3_0", {**b, "stop_atr": 3.0}),
        _profile("M6", "VOLUME_0_8", {**b, "volume_ratio_min": 0.8}),
        _profile("M6", "VOLUME_1_2", {**b, "volume_ratio_min": 1.2}),
        _profile("M6", "RR_3_0", b.copy(), rr=3.0),
        _profile("M6", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M6", "HOLD_168H", b.copy(), hold_hours=168),
        _profile("M6", "ATR_TRAIL_2_5", b.copy(), hold_hours=72, trailing=2.5),
    ]

    b = {"bb_z_entry": 2.0, "rsi_long_max": 35.0, "rsi_short_min": 65.0, "stop_atr": 1.5}
    p["M7"] = [
        _profile("M7", "BASELINE", b.copy()),
        _profile("M7", "BB_Z_1_8", {**b, "bb_z_entry": 1.8}),
        _profile("M7", "BB_Z_2_2", {**b, "bb_z_entry": 2.2}),
        _profile("M7", "RSI_30_70", {**b, "rsi_long_max": 30.0, "rsi_short_min": 70.0}),
        _profile("M7", "STOP_ATR_1_25", {**b, "stop_atr": 1.25}),
        _profile("M7", "STOP_ATR_1_75", {**b, "stop_atr": 1.75}),
        _profile("M7", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M7", "HOLD_72H", b.copy(), hold_hours=72),
        _profile("M7", "TRAIL_2_0", b.copy(), hold_hours=48, trailing=2.0),
    ]

    b = {"squeeze_lookback": 100, "squeeze_quantile": 0.20, "breakout_period": 20,
         "expansion_atr": 1.2, "volume_ratio_min": 1.2, "stop_atr": 2.0}
    p["M8"] = [
        _profile("M8", "BASELINE", b.copy()),
        _profile("M8", "SQUEEZE_Q10", {**b, "squeeze_quantile": 0.10}),
        _profile("M8", "SQUEEZE_Q30", {**b, "squeeze_quantile": 0.30}),
        _profile("M8", "BREAKOUT_10", {**b, "breakout_period": 10}),
        _profile("M8", "BREAKOUT_40", {**b, "breakout_period": 40}),
        _profile("M8", "EXPANSION_1_0", {**b, "expansion_atr": 1.0}),
        _profile("M8", "EXPANSION_1_5", {**b, "expansion_atr": 1.5}),
        _profile("M8", "VOLUME_1_0", {**b, "volume_ratio_min": 1.0}),
        _profile("M8", "VOLUME_1_5", {**b, "volume_ratio_min": 1.5}),
        _profile("M8", "STOP_ATR_1_5", {**b, "stop_atr": 1.5}),
        _profile("M8", "STOP_ATR_2_5", {**b, "stop_atr": 2.5}),
        _profile("M8", "RR_3_0", b.copy(), rr=3.0),
        _profile("M8", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M8", "ATR_TRAIL_2_5", b.copy(), hold_hours=72, trailing=2.5),
    ]

    b = {"lookback": 20, "relative_threshold": 0.01, "ema_fast": 50, "ema_slow": 200, "stop_atr": 2.0}
    p["M10"] = [
        _profile("M10", "BASELINE", b.copy()),
        _profile("M10", "RELATIVE_0_5PCT", {**b, "relative_threshold": 0.005}),
        _profile("M10", "RELATIVE_1_5PCT", {**b, "relative_threshold": 0.015}),
        _profile("M10", "LOOKBACK_10", {**b, "lookback": 10}),
        _profile("M10", "LOOKBACK_40", {**b, "lookback": 40}),
        _profile("M10", "EMA_FAST_34", {**b, "ema_fast": 34}),
        _profile("M10", "EMA_FAST_100", {**b, "ema_fast": 100}),
        _profile("M10", "STOP_ATR_1_5", {**b, "stop_atr": 1.5}),
        _profile("M10", "STOP_ATR_2_5", {**b, "stop_atr": 2.5}),
        _profile("M10", "RR_3_0", b.copy(), rr=3.0),
        _profile("M10", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M10", "ATR_TRAIL_2_5", b.copy(), hold_hours=72, trailing=2.5),
    ]

    b = {"breakout_period": 20, "trend_adx_min": 25.0, "range_adx_max": 18.0,
         "range_bb_z": 2.0, "range_rsi": 35.0, "stop_atr": 2.0, "range_stop_atr": 0.5}
    p["M12"] = [
        _profile("M12", "BASELINE", b.copy()),
        _profile("M12", "BREAKOUT_10", {**b, "breakout_period": 10}),
        _profile("M12", "BREAKOUT_40", {**b, "breakout_period": 40}),
        _profile("M12", "TREND_ADX_20", {**b, "trend_adx_min": 20.0}),
        _profile("M12", "TREND_ADX_30", {**b, "trend_adx_min": 30.0}),
        _profile("M12", "RANGE_ADX_15", {**b, "range_adx_max": 15.0}),
        _profile("M12", "RANGE_ADX_20", {**b, "range_adx_max": 20.0}),
        _profile("M12", "RANGE_Z_1_8", {**b, "range_bb_z": 1.8}),
        _profile("M12", "RANGE_Z_2_2", {**b, "range_bb_z": 2.2}),
        _profile("M12", "STOP_ATR_1_5", {**b, "stop_atr": 1.5}),
        _profile("M12", "STOP_ATR_2_5", {**b, "stop_atr": 2.5}),
        _profile("M12", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M12", "HOLD_72H", b.copy(), hold_hours=72),
    ]

    b = {"btc_lookback": 3, "impulse_threshold": 0.006, "divergence_threshold": 0.003,
         "ema_period": 20, "stop_atr": 2.0}
    p["M13"] = [
        _profile("M13", "BASELINE", b.copy()),
        _profile("M13", "BTC_LOOKBACK_2", {**b, "btc_lookback": 2}),
        _profile("M13", "BTC_LOOKBACK_4", {**b, "btc_lookback": 4}),
        _profile("M13", "IMPULSE_0_4PCT", {**b, "impulse_threshold": 0.004}),
        _profile("M13", "IMPULSE_0_8PCT", {**b, "impulse_threshold": 0.008}),
        _profile("M13", "DIVERGENCE_0_2PCT", {**b, "divergence_threshold": 0.002}),
        _profile("M13", "DIVERGENCE_0_4PCT", {**b, "divergence_threshold": 0.004}),
        _profile("M13", "EMA_50", {**b, "ema_period": 50}),
        _profile("M13", "STOP_ATR_1_5", {**b, "stop_atr": 1.5}),
        _profile("M13", "STOP_ATR_2_5", {**b, "stop_atr": 2.5}),
        _profile("M13", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M13", "HOLD_72H", b.copy(), hold_hours=72),
    ]

    b = {"adx_min": 25.0, "di_min": 25.0, "momentum_lookback": 14, "stop_atr": 2.0}
    p["M14"] = [
        _profile("M14", "BASELINE", b.copy()),
        _profile("M14", "ADX_20", {**b, "adx_min": 20.0}),
        _profile("M14", "ADX_30", {**b, "adx_min": 30.0}),
        _profile("M14", "DI_20", {**b, "di_min": 20.0}),
        _profile("M14", "DI_30", {**b, "di_min": 30.0}),
        _profile("M14", "MOMENTUM_7", {**b, "momentum_lookback": 7}),
        _profile("M14", "MOMENTUM_21", {**b, "momentum_lookback": 21}),
        _profile("M14", "STOP_ATR_1_5", {**b, "stop_atr": 1.5}),
        _profile("M14", "STOP_ATR_2_5", {**b, "stop_atr": 2.5}),
        _profile("M14", "RR_3_0", b.copy(), rr=3.0),
        _profile("M14", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M14", "ATR_TRAIL_2_5", b.copy(), hold_hours=72, trailing=2.5),
    ]

    b = {"ao_cross_min_atr": 0.0, "macd_min_atr": 0.0, "stop_atr": 2.0}
    p["M15"] = [
        _profile("M15", "BASELINE", b.copy()),
        _profile("M15", "AO_MIN_0_05_ATR", {**b, "ao_cross_min_atr": 0.05}),
        _profile("M15", "AO_MIN_0_10_ATR", {**b, "ao_cross_min_atr": 0.10}),
        _profile("M15", "MACD_MIN_0_05_ATR", {**b, "macd_min_atr": 0.05}),
        _profile("M15", "MACD_MIN_0_10_ATR", {**b, "macd_min_atr": 0.10}),
        _profile("M15", "STOP_ATR_1_5", {**b, "stop_atr": 1.5}),
        _profile("M15", "STOP_ATR_2_5", {**b, "stop_atr": 2.5}),
        _profile("M15", "RR_3_0", b.copy(), rr=3.0),
        _profile("M15", "HOLD_48H", b.copy(), hold_hours=48),
        _profile("M15", "ATR_TRAIL_2_5", b.copy(), hold_hours=72, trailing=2.5),
    ]
    return p


def _valid(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty or "exit_reason" not in trades:
        return trades.copy()
    return trades.loc[~trades.exit_reason.isin(["DATA_GAP", "END_OF_SAMPLE"])].copy()


def cost_diagnostics(trades: pd.DataFrame) -> dict:
    frame = _valid(trades)
    if frame.empty:
        return {
            "gross_price_move_bps": 0.0, "gross_price_points": 0.0,
            "gross_executed_bps": 0.0, "fees_bps": 0.0,
            "slippage_bps": 0.0, "funding_bps": 0.0,
            "total_cost_bps": 0.0, "net_pnl_bps": 0.0,
            "gross_positive_move_bps": 0.0, "cost_share_of_gross_positive_pct": None,
            "avg_gross_move_bps_per_trade": None, "avg_total_cost_bps_per_trade": None,
        }
    gross_move = pd.to_numeric(frame.get("gross_price_move_bps", 0.0), errors="coerce").fillna(0.0)
    gross_exec = pd.to_numeric(frame.get("gross_return_pct", 0.0), errors="coerce").fillna(0.0) * 100.0
    fees = pd.to_numeric(frame.get("fees_pct", 0.0), errors="coerce").fillna(0.0) * 100.0
    slippage = pd.to_numeric(frame.get("slippage_cost_pct", 0.0), errors="coerce").fillna(0.0) * 100.0
    funding = pd.to_numeric(frame.get("funding_cost_pct", 0.0), errors="coerce").fillna(0.0) * 100.0
    total_cost = fees + slippage + funding
    side_sign = frame.side.map({"LONG": 1.0, "SHORT": -1.0}).fillna(0.0)
    points = side_sign * (
        pd.to_numeric(frame.raw_exit, errors="coerce")
        - pd.to_numeric(frame.raw_entry, errors="coerce")
    )
    gross_positive = float(gross_move.clip(lower=0.0).sum())
    return {
        "gross_price_move_bps": round(float(gross_move.sum()), 2),
        "gross_price_points": round(float(points.sum()), 8),
        "gross_executed_bps": round(float(gross_exec.sum()), 2),
        "fees_bps": round(float(fees.sum()), 2),
        "slippage_bps": round(float(slippage.sum()), 2),
        "funding_bps": round(float(funding.sum()), 2),
        "total_cost_bps": round(float(total_cost.sum()), 2),
        "net_pnl_bps": round(float(pd.to_numeric(frame.net_bps, errors="coerce").fillna(0.0).sum()), 2),
        "gross_positive_move_bps": round(gross_positive, 2),
        "cost_share_of_gross_positive_pct": round(float(total_cost.sum() / gross_positive * 100), 2) if gross_positive > 0 else None,
        "avg_gross_move_bps_per_trade": round(float(gross_move.mean()), 3),
        "avg_total_cost_bps_per_trade": round(float(total_cost.mean()), 3),
    }


def _period_summary(trades: pd.DataFrame, start_year: int, end_year: int) -> dict:
    start = pd.Timestamp(year=start_year, month=1, day=1, tz="UTC")
    end = pd.Timestamp(year=end_year + 1, month=1, day=1, tz="UTC")
    cohort = completed_period_cohort(trades, start, end)
    return {**summarize(cohort), **cost_diagnostics(cohort)}


def _yearly_rows(trades: pd.DataFrame, base: dict) -> list[dict]:
    years = pd.to_datetime(trades.exit_time, utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
    rows = []
    for year in range(2021, 2027):
        part = trades.loc[years == year] if not trades.empty else trades
        rows.append({**base, "year": year, **summarize(part), **cost_diagnostics(part)})
    return rows


def _retention_band(value):
    if value is None or pd.isna(value):
        return "NO_BASELINE"
    for threshold in (100, 95, 90, 85, 80):
        if value >= threshold:
            return f">={threshold}%"
    return "<80%"


def main():
    parser = argparse.ArgumentParser(description="Independent eight-engine cost-aware one-factor improvement research")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--benchmark-symbol", default="BTCUSDT")
    parser.add_argument("--models", nargs="+", choices=ACTIVE_MODELS, default=list(ACTIVE_MODELS))
    parser.add_argument("--timeframes", nargs="+", choices=tuple(TIMEFRAME_MINUTES), default=["15m", "1h", "4h"])
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--out", default="improvement_artifacts")
    args = parser.parse_args()

    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be later than --start")
    if not set(args.models).issubset(ACTIVE_MODELS):
        parser.error("Only the eight selected models may be run")

    symbol = args.symbol.upper()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"IMPROVEMENT START {symbol} {args.start}..{args.end}", flush=True)

    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    funding_source = funding.attrs.get("source", "unknown")
    funding_gaps = funding.index.to_series().diff().dropna() if not funding.empty else pd.Series(dtype="timedelta64[ns]")
    funding_max_gap = float(funding_gaps.max().total_seconds() / 3600) if not funding_gaps.empty else None
    if (
        funding.empty
        or funding_source not in OFFICIAL_FUNDING_SOURCES
        or funding_max_gap is None
        or funding_max_gap > 8.5
    ):
        raise RuntimeError(
            f"Funding data failed closed: source={funding_source}, rows={len(funding)}, "
            f"max_gap_hours={funding_max_gap}; no zero-funding fallback is permitted"
        )

    candle_quality = quality_report(raw, symbol, args.start, args.end)
    benchmark_raw = None
    benchmark_quality = None
    if symbol != args.benchmark_symbol and any(m in args.models for m in ("M10", "M13")):
        benchmark_raw = acquire_klines(args.benchmark_symbol, args.start, args.end)
        benchmark_quality = quality_report(benchmark_raw, args.benchmark_symbol, args.start, args.end)

    profiles = improvement_profiles()
    result_rows, yearly, ledgers = [], [], {}
    for model in args.models:
        for timeframe in args.timeframes:
            for profile in profiles[model]:
                variant = profile["variant"]
                if model in ("M10", "M13") and symbol == args.benchmark_symbol:
                    result_rows.append({
                        "model": model, "variant": variant, "symbol": symbol, "timeframe": timeframe,
                        "status": "NOT_APPLICABLE", "skip_reason": "BTC is the benchmark, not a traded leg",
                        "trades": 0,
                    })
                    continue

                print(f"MODEL START {model} {variant} {symbol} {timeframe}", flush=True)
                signals = make_independent_signals(
                    raw,
                    model,
                    timeframe,
                    benchmark_raw=benchmark_raw if model in ("M10", "M13") else None,
                    parameters=profile["parameters"],
                )
                max_hold_bars = max(1, int(round(profile["hold_hours"] * 60 / TIMEFRAME_MINUTES[timeframe])))
                trades = run_backtest(
                    signals,
                    funding,
                    symbol,
                    model,
                    timeframe,
                    fee_bps=args.fee_bps,
                    slippage_bps=args.slippage_bps,
                    rr=profile["rr"],
                    max_hold_bars=max_hold_bars,
                    trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                    expected_end=args.end,
                )
                base = {
                    "model": model, "variant": variant, "symbol": symbol, "timeframe": timeframe,
                    "rr": profile["rr"], "max_hold_hours": profile["hold_hours"],
                    "trailing_atr_multiple": profile.get("trailing_atr_multiple"),
                    "parameters_json": json.dumps(profile["parameters"], sort_keys=True),
                }
                stats = {
                    **summarize(trades),
                    **cost_diagnostics(trades),
                    "status": "COMPLETED",
                    "skip_reason": "",
                    "signal_bars": int(signals.signal.ne(0).sum()),
                    "bars": int(len(signals)),
                    "max_hold_bars": max_hold_bars,
                    **{f"development_{k}": v for k, v in _period_summary(trades, 2021, 2024).items()},
                    **{f"validation_2025_{k}": v for k, v in _period_summary(trades, 2025, 2025).items()},
                    **{f"retrospective_2026_{k}": v for k, v in _period_summary(trades, 2026, 2026).items()},
                }
                result_rows.append({
                    **base,
                    "start_inclusive": args.start,
                    "end_exclusive": args.end,
                    "fee_bps_per_side": args.fee_bps,
                    "slippage_bps_per_side": args.slippage_bps,
                    "funding_source": funding_source,
                    "funding_rows": int(len(funding)),
                    "funding_max_gap_hours": funding_max_gap,
                    "candle_coverage_pct": candle_quality.get("coverage_pct"),
                    "benchmark_coverage_pct": benchmark_quality.get("coverage_pct") if benchmark_quality else None,
                    **stats,
                })
                yearly.extend(_yearly_rows(trades, base))
                if not trades.empty:
                    ledger = trades.copy()
                    for key, value in base.items():
                        ledger[key] = value
                    ledgers[(model, timeframe, variant)] = ledger
                print(
                    f"MODEL END {model} {variant} {symbol} {timeframe}: "
                    f"trades={stats['trades']} PF={stats['profit_factor']} "
                    f"net_bps={stats['net_bps']} net_R={stats['net_R']}",
                    flush=True,
                )

    for row in result_rows:
        model, timeframe, variant = row["model"], row["timeframe"], row["variant"]
        baseline = _valid(ledgers.get((model, timeframe, "BASELINE"), pd.DataFrame()))
        current = _valid(ledgers.get((model, timeframe, variant), pd.DataFrame()))
        if row.get("status") != "COMPLETED" or baseline.empty:
            row.update({
                "baseline_trades": int(len(baseline)),
                "trade_count_retention_pct": None,
                "baseline_entry_retention_pct": None,
                "retention_band": "NO_BASELINE",
                "retained_baseline_entries": 0,
                "new_entries": 0,
                "rejected_baseline_entries": 0,
                "rejected_baseline_net_bps": 0.0,
                "rejected_baseline_net_R": 0.0,
            })
            continue
        baseline_entries = set(baseline.entry_time.astype(str))
        current_entries = set(current.entry_time.astype(str))
        retained = baseline_entries & current_entries
        rejected = baseline.loc[~baseline.entry_time.astype(str).isin(current_entries)]
        retention = 100.0 * len(retained) / len(baseline_entries) if baseline_entries else None
        count_retention = 100.0 * len(current) / len(baseline) if len(baseline) else None
        row.update({
            "baseline_trades": int(len(baseline)),
            "trade_count_retention_pct": round(count_retention, 2) if count_retention is not None else None,
            "baseline_entry_retention_pct": round(retention, 2) if retention is not None else None,
            "retention_band": _retention_band(retention),
            "retained_baseline_entries": int(len(retained)),
            "new_entries": int(len(current_entries - baseline_entries)),
            "rejected_baseline_entries": int(len(rejected)),
            "rejected_baseline_net_bps": round(float(pd.to_numeric(rejected.net_bps, errors="coerce").fillna(0).sum()), 2),
            "rejected_baseline_net_R": round(float(pd.to_numeric(rejected.net_R, errors="coerce").fillna(0).sum()), 3),
        })

    results = pd.DataFrame(result_rows)
    yearly_frame = pd.DataFrame(yearly)
    ledger_frame = pd.concat(list(ledgers.values()), ignore_index=True) if ledgers else pd.DataFrame()
    results.to_csv(out / "screen_results.csv", index=False)
    yearly_frame.to_csv(out / "screen_yearly.csv", index=False)
    ledger_frame.to_csv(out / "trade_ledger.csv", index=False)
    results.sort_values(["model", "timeframe", "baseline_entry_retention_pct"], ascending=[True, True, False]).to_csv(
        out / "retention_pareto.csv", index=False
    )

    metadata = {
        "symbol": symbol,
        "period": {"start_inclusive": args.start, "end_exclusive": args.end},
        "models": list(args.models),
        "timeframes": list(args.timeframes),
        "profiles_per_model": {model: [p["variant"] for p in profiles[model]] for model in args.models},
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "candle_quality": candle_quality,
        "benchmark_quality": benchmark_quality,
        "funding_source": funding_source,
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding.attrs.get("missing_archive_months", []),
        "notes": [
            "All models are independent; no ensemble or cross-model confirmation is used.",
            "Trade-retention compares each variant's entry timestamps with its same-model/symbol/timeframe baseline. Rejected baseline entries retain their baseline counterfactual net_bps and net_R.",
            "DATA_GAP and END_OF_SAMPLE records remain in the ledger but are excluded from performance metrics.",
            "Cross-symbol sums are trade-stream diagnostics, not portfolio returns.",
            "2021-2024 is development, 2025 is validation, and 2026 is retrospective audit only, not a pristine holdout.",
            "5m is reserved for a later targeted sweep; this first improvement pass covers 15m, 1h and 4h. The baseline screen separately includes 5m.",
            "Net bps and net-R are comparable across crypto symbols. gross_price_points is symbol-specific raw directional price movement, not a universal pip measure.",
            "Funding is fail-closed to official Binance sources with no gap above 8.5 hours; no zero or unverified third-party funding fallback is scored.",
        ],
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(f"IMPROVEMENT COMPLETE {symbol}", flush=True)


if __name__ == "__main__":
    main()

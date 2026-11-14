from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import completed_period_cohort, run_backtest, summarize
from .data import acquire_funding, acquire_klines, quality_report
from .improvement_run import (
    ACTIVE_MODELS,
    TIMEFRAME_MINUTES,
    _profile,
    cost_diagnostics,
    improvement_profiles,
    _period_summary,
    _yearly_rows,
)
from .independent_models import make_independent_signals

COST_SCENARIOS = (
    {"name": "BASE_5_2", "fee_bps": 5.0, "slippage_bps": 2.0},
    {"name": "MODERATE_7_3", "fee_bps": 7.5, "slippage_bps": 3.0},
    {"name": "HIGH_10_5", "fee_bps": 10.0, "slippage_bps": 5.0},
    {"name": "SEVERE_15_10", "fee_bps": 15.0, "slippage_bps": 10.0},
)
OFFICIAL_FUNDING_SOURCES = {
    "binance_vision_official_monthly_archive",
    "binance_vision_archive_plus_official_api",
    "binance_official_api",
}


def cost_stress_profiles() -> dict[str, list[dict]]:
    """Predeclared cost-stress profiles; each model remains standalone."""
    base_profiles = improvement_profiles()

    def take(model: str, names: tuple[str, ...]) -> list[dict]:
        lookup = {item["variant"]: item for item in base_profiles[model]}
        missing = set(names) - set(lookup)
        if missing:
            raise ValueError(f"Missing {model} profiles: {sorted(missing)}")
        return [dict(lookup[name]) for name in names]

    selected = {
        "M6": take("M6", ("BASELINE", "RR_3_0", "HOLD_48H")),
        "M7": take("M7", ("BASELINE", "BB_Z_1_8", "HOLD_72H")),
        "M8": take("M8", ("BASELINE", "VOLUME_1_0", "HOLD_48H", "EXPANSION_1_5")),
        "M10": take("M10", ("BASELINE", "EMA_FAST_100", "LOOKBACK_10")),
        "M12": take("M12", ("BASELINE", "BREAKOUT_40", "STOP_ATR_1_5", "HOLD_72H")),
        "M13": take("M13", ("BASELINE", "HOLD_48H", "BTC_LOOKBACK_4")),
        "M14": take("M14", ("BASELINE", "MOMENTUM_21", "HOLD_48H")),
        "M15": take("M15", ("BASELINE", "ATR_TRAIL_2_5")),
    }

    m6 = {"donchian_period": 55, "volume_ratio_min": 1.0, "stop_atr": 2.5}
    selected["M6"].extend([
        _profile("M6", "RR3_VOL12", {**m6, "volume_ratio_min": 1.2}, rr=3.0),
        _profile("M6", "HOLD48_STOP3", {**m6, "stop_atr": 3.0}, hold_hours=48),
    ])

    m8 = {
        "squeeze_lookback": 100,
        "squeeze_quantile": 0.20,
        "breakout_period": 20,
        "expansion_atr": 1.2,
        "volume_ratio_min": 1.2,
        "stop_atr": 2.0,
    }
    selected["M8"].extend([
        _profile("M8", "HOLD48_VOL10", {**m8, "volume_ratio_min": 1.0}, hold_hours=48),
        _profile("M8", "HOLD48_EXP15", {**m8, "expansion_atr": 1.5}, hold_hours=48),
    ])

    m15 = {"ao_cross_min_atr": 0.0, "macd_min_atr": 0.0, "stop_atr": 2.0}
    selected["M15"].append(
        _profile("M15", "ATR_TRAIL_2_5_H48", m15.copy(), hold_hours=48, trailing=2.5)
    )

    for model, items in selected.items():
        variants = [item["variant"] for item in items]
        if not variants or variants[0] != "BASELINE" or len(variants) != len(set(variants)):
            raise ValueError(f"{model} profiles must be unique and start with BASELINE")
    if set(selected) != set(ACTIVE_MODELS):
        raise ValueError("Cost-stress model scope must exactly match the eight approved engines")
    return selected


def attach_excursions(trades: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Attach complete 1m-path MAE/MFE; leave incomplete paths unscored."""
    out = trades.copy()
    if out.empty:
        for name in ("excursion_complete", "mae_bps", "mfe_bps", "mae_R", "mfe_R"):
            out[name] = pd.Series(dtype=float if name != "excursion_complete" else bool)
        return out

    raw_index = raw.index
    highs = pd.to_numeric(raw.high, errors="coerce").to_numpy(dtype=float)
    lows = pd.to_numeric(raw.low, errors="coerce").to_numpy(dtype=float)
    entry_times = pd.to_datetime(out.entry_time, utc=True)
    exit_times = pd.to_datetime(out.exit_time, utc=True)
    values = {
        "excursion_complete": [],
        "mae_bps": [],
        "mfe_bps": [],
        "mae_R": [],
        "mfe_R": [],
        "expected_excursion_minutes": [],
        "observed_excursion_minutes": [],
    }

    for row, entry_time, exit_time in zip(out.itertuples(index=False), entry_times, exit_times):
        expected = int((exit_time - entry_time).total_seconds() // 60)
        start = int(raw_index.searchsorted(entry_time, side="left"))
        stop = int(raw_index.searchsorted(exit_time, side="left"))
        observed = max(0, stop - start)
        complete = expected > 0 and observed == expected and start >= 0 and stop <= len(raw_index)
        if not complete:
            values["excursion_complete"].append(False)
            values["mae_bps"].append(np.nan)
            values["mfe_bps"].append(np.nan)
            values["mae_R"].append(np.nan)
            values["mfe_R"].append(np.nan)
            values["expected_excursion_minutes"].append(expected)
            values["observed_excursion_minutes"].append(observed)
            continue

        path_high = float(np.max(highs[start:stop]))
        path_low = float(np.min(lows[start:stop]))
        raw_entry = float(row.raw_entry)
        side = 1 if row.side == "LONG" else -1
        if side == 1:
            mae = max(0.0, (raw_entry - path_low) / raw_entry * 10000.0)
            mfe = max(0.0, (path_high - raw_entry) / raw_entry * 10000.0)
        else:
            mae = max(0.0, (path_high - raw_entry) / raw_entry * 10000.0)
            mfe = max(0.0, (raw_entry - path_low) / raw_entry * 10000.0)
        risk = abs(float(row.entry) - float(row.initial_stop)) / float(row.entry) * 10000.0
        values["excursion_complete"].append(True)
        values["mae_bps"].append(mae)
        values["mfe_bps"].append(mfe)
        values["mae_R"].append(mae / risk if risk > 0 else np.nan)
        values["mfe_R"].append(mfe / risk if risk > 0 else np.nan)
        values["expected_excursion_minutes"].append(expected)
        values["observed_excursion_minutes"].append(observed)

    for name, value in values.items():
        out[name] = value
    return out


def block_bootstrap_metrics(
    trades: pd.DataFrame, *, seed: int, resamples: int = 500, block_size: int = 20
) -> dict:
    """Contiguous trade-order block bootstrap; diagnostic, not a forecast."""
    if trades.empty:
        return {"resamples": 0, "block_size": block_size, "prob_net_R_positive_pct": None}
    ordered = trades.sort_values("exit_time")
    ordered = ordered.loc[~ordered.exit_reason.isin(["DATA_GAP", "END_OF_SAMPLE"])]
    values = pd.to_numeric(ordered.net_R, errors="coerce").dropna().to_numpy(dtype=float)
    n = len(values)
    if n < block_size * 2:
        return {
            "resamples": 0, "block_size": block_size, "trades": n,
            "prob_net_R_positive_pct": None,
        }
    rng = np.random.default_rng(seed)
    starts = np.arange(0, n - block_size + 1)
    blocks_needed = int(np.ceil(n / block_size))
    final_r = np.empty(resamples, dtype=float)
    max_dd_r = np.empty(resamples, dtype=float)
    for i in range(resamples):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        sample = np.concatenate([values[start:start + block_size] for start in chosen])[:n]
        curve = np.cumsum(sample)
        peak = np.maximum.accumulate(np.maximum(curve, 0.0))
        final_r[i] = curve[-1]
        max_dd_r[i] = np.min(curve - peak)
    return {
        "resamples": int(resamples),
        "block_size": int(block_size),
        "trades": int(n),
        "prob_net_R_positive_pct": round(float((final_r > 0).mean() * 100), 2),
        "net_R_p05": round(float(np.quantile(final_r, 0.05)), 3),
        "net_R_median": round(float(np.quantile(final_r, 0.50)), 3),
        "net_R_p95": round(float(np.quantile(final_r, 0.95)), 3),
        "max_drawdown_R_p95": round(float(np.quantile(max_dd_r, 0.95)), 3),
        "max_drawdown_R_p05": round(float(np.quantile(max_dd_r, 0.05)), 3),
        "note": "Contiguous 20-trade blocks preserve some local clustering; not a guarantee of future returns",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Independent eight-engine fee/slippage/funding stress and MAE/MFE diagnostics"
    )
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--benchmark-symbol", default="BTCUSDT")
    parser.add_argument("--models", nargs="+", choices=ACTIVE_MODELS, default=list(ACTIVE_MODELS))
    parser.add_argument("--timeframe", choices=("1h", "4h"), default="4h")
    parser.add_argument("--out", default="eight_engine_cost_stress_artifacts")
    args = parser.parse_args()

    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be later than --start")
    if not set(args.models).issubset(ACTIVE_MODELS):
        parser.error("Only the eight approved independent models may be run")

    symbol = args.symbol.upper()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"EIGHT-ENGINE COST STRESS START {symbol} {args.start}..{args.end}", flush=True)

    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    funding_gaps = funding.index.to_series().diff().dropna() if not funding.empty else pd.Series(dtype="timedelta64[ns]")
    funding_max_gap = float(funding_gaps.max().total_seconds() / 3600) if not funding_gaps.empty else None
    funding_source = funding.attrs.get("source", "unknown")
    if (
        funding.empty
        or funding_source not in OFFICIAL_FUNDING_SOURCES
        or funding_max_gap is None
        or funding_max_gap > 8.5
    ):
        raise RuntimeError(
            f"Funding failed closed: source={funding_source}, rows={len(funding)}, "
            f"max_gap_hours={funding_max_gap}; no zero-funding fallback is permitted"
        )

    candle_quality = quality_report(raw, symbol, args.start, args.end)
    benchmark_raw = None
    benchmark_quality = None
    if symbol != args.benchmark_symbol and any(model in args.models for model in ("M10", "M13")):
        benchmark_raw = acquire_klines(args.benchmark_symbol, args.start, args.end)
        benchmark_quality = quality_report(benchmark_raw, args.benchmark_symbol, args.start, args.end)

    profiles = cost_stress_profiles()
    rows, yearly, ledgers, monte_carlo = [], [], [], []
    bar_minutes = TIMEFRAME_MINUTES[args.timeframe]

    for model in args.models:
        for profile in profiles[model]:
            variant = profile["variant"]
            if model in ("M10", "M13") and symbol == args.benchmark_symbol:
                for scenario in COST_SCENARIOS:
                    rows.append({
                        "model": model, "variant": variant, "symbol": symbol,
                        "timeframe": args.timeframe, "cost_scenario": scenario["name"],
                        "status": "NOT_APPLICABLE",
                        "skip_reason": "BTC is the benchmark, not a traded leg",
                        "trades": 0,
                    })
                continue

            print(f"MODEL START {symbol} {model} {variant}", flush=True)
            signals = make_independent_signals(
                raw,
                model,
                args.timeframe,
                benchmark_raw=benchmark_raw if model in ("M10", "M13") else None,
                parameters=profile["parameters"],
            )
            max_hold_bars = max(1, int(round(profile["hold_hours"] * 60 / bar_minutes)))

            for scenario in COST_SCENARIOS:
                print(
                    f"STRESS START {symbol} {model} {variant} {scenario['name']}",
                    flush=True,
                )
                trades = run_backtest(
                    signals,
                    funding,
                    symbol,
                    model,
                    args.timeframe,
                    fee_bps=scenario["fee_bps"],
                    slippage_bps=scenario["slippage_bps"],
                    rr=profile["rr"],
                    max_hold_bars=max_hold_bars,
                    trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                    expected_end=args.end,
                )
                trades = attach_excursions(trades, raw)
                base = {
                    "model": model,
                    "variant": variant,
                    "symbol": symbol,
                    "timeframe": args.timeframe,
                    "cost_scenario": scenario["name"],
                    "fee_bps_per_side": scenario["fee_bps"],
                    "slippage_bps_per_side": scenario["slippage_bps"],
                    "rr": profile["rr"],
                    "max_hold_hours": profile["hold_hours"],
                    "trailing_atr_multiple": profile.get("trailing_atr_multiple"),
                    "parameters_json": json.dumps(profile["parameters"], sort_keys=True),
                }
                stats = {
                    **summarize(trades),
                    **cost_diagnostics(trades),
                    "status": "COMPLETED",
                    "skip_reason": "",
                    "excursion_complete_trades": int(trades.excursion_complete.sum()) if not trades.empty else 0,
                    "avg_mae_bps": round(float(trades.loc[trades.excursion_complete, "mae_bps"].mean()), 3) if not trades.empty and trades.excursion_complete.any() else None,
                    "avg_mfe_bps": round(float(trades.loc[trades.excursion_complete, "mfe_bps"].mean()), 3) if not trades.empty and trades.excursion_complete.any() else None,
                    "avg_mae_R": round(float(trades.loc[trades.excursion_complete, "mae_R"].mean()), 3) if not trades.empty and trades.excursion_complete.any() else None,
                    "avg_mfe_R": round(float(trades.loc[trades.excursion_complete, "mfe_R"].mean()), 3) if not trades.empty and trades.excursion_complete.any() else None,
                    **{f"development_{k}": v for k, v in _period_summary(trades, 2021, 2024).items()},
                    **{f"validation_2025_{k}": v for k, v in _period_summary(trades, 2025, 2025).items()},
                    **{f"retrospective_2026_{k}": v for k, v in _period_summary(trades, 2026, 2026).items()},
                }
                rows.append({**base, **stats})
                yearly.extend(_yearly_rows(trades, base))
                if not trades.empty:
                    ledger = trades.copy()
                    for key, value in base.items():
                        ledger[key] = value
                    ledgers.append(ledger)
                    seed = zlib.crc32(
                        f"{symbol}|{model}|{variant}|{scenario['name']}".encode()
                    )
                    monte_carlo.append({
                        **base,
                        **block_bootstrap_metrics(trades, seed=seed),
                    })
                print(
                    f"STRESS END {symbol} {model} {variant} {scenario['name']}: "
                    f"trades={stats['trades']} PF={stats['profit_factor']} "
                    f"net_bps={stats['net_bps']} net_R={stats['net_R']}",
                    flush=True,
                )

    pd.DataFrame(rows).to_csv(out / "screen_results.csv", index=False)
    pd.DataFrame(yearly).to_csv(out / "screen_yearly.csv", index=False)
    pd.DataFrame(monte_carlo).to_csv(out / "monte_carlo.csv", index=False)
    ledger_frame = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
    ledger_frame.to_csv(out / "trade_ledger.csv", index=False)
    metadata = {
        "symbol": symbol,
        "period": {"start_inclusive": args.start, "end_exclusive": args.end},
        "timeframe": args.timeframe,
        "models_tested_independently": list(args.models),
        "selected_variants": {
            model: [profile["variant"] for profile in profiles[model]]
            for model in args.models
        },
        "cost_scenarios": list(COST_SCENARIOS),
        "fee_slippage_are_reexecuted": True,
        "candle_quality": candle_quality,
        "benchmark_quality": benchmark_quality,
        "funding_source": funding_source,
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding.attrs.get("missing_archive_months", []),
        "notes": [
            "Only M6, M7, M8, M10, M12, M13, M14 and M15 are in scope; every model is independent.",
            "Fee and slippage scenarios re-execute the OHLC path; they are not simple repricing of the base ledger.",
            "MAE/MFE use the complete underlying 1m candle path between entry and exit; incomplete minute paths are left unscored.",
            "DATA_GAP and END_OF_SAMPLE remain in the audit ledger and are excluded from performance metrics.",
            "2021-2024 is development, 2025 validation, and 2026 retrospective audit only.",
            "Cross-symbol sums are trade-stream diagnostics, not portfolio returns.",
            "Funding is fail-closed to official Binance sources; no zero-funding fallback is permitted.",
        ],
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(f"EIGHT-ENGINE COST STRESS COMPLETE {symbol}", flush=True)


if __name__ == "__main__":
    main()

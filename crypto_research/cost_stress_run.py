from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import completed_period_cohort, run_backtest, summarize
from .combination_run import combination_profiles
from .data import acquire_funding, acquire_klines, quality_report
from .independent_models import make_independent_signals
from .metrics import acquire_open_interest, metrics_quality_report

COST_SCENARIOS = (
    {"name": "BASE_5_2", "fee_bps": 5.0, "slippage_bps": 2.0},
    {"name": "MODERATE_7_3", "fee_bps": 7.5, "slippage_bps": 3.0},
    {"name": "HIGH_10_5", "fee_bps": 10.0, "slippage_bps": 5.0},
    {"name": "SEVERE_15_10", "fee_bps": 15.0, "slippage_bps": 10.0},
)

SELECTED_VARIANTS = {
    "M6": {"BASELINE_H24", "HOLD_48H", "STOP2_H24", "RR3_H24", "VOLUME12_H24", "D100_RR3_H168", "D100_STOP2_H168", "D100_VOL12_RR3_H168"},
    "M11": {"BASELINE_H24", "OI05_PRICE025_H36", "OI05_RR3_H48", "OI05_PRICE025_RR3_H48", "OI05_PRICE025_RR3_H72"},
}


def selected_profiles() -> dict[str, list[dict]]:
    chosen = {}
    for model, names in SELECTED_VARIANTS.items():
        profiles = [p for p in combination_profiles(model) if p["variant"] in names]
        found = {p["variant"] for p in profiles}
        if found != names:
            raise RuntimeError(f"Selected profile mismatch for {model}: {found} != {names}")
        chosen[model] = profiles
    return chosen


def _period_summary(trades: pd.DataFrame, start_year: int, end_year: int) -> dict:
    start = pd.Timestamp(year=start_year, month=1, day=1, tz="UTC")
    end_exclusive = pd.Timestamp(year=end_year + 1, month=1, day=1, tz="UTC")
    return summarize(completed_period_cohort(trades, start, end_exclusive))


def _yearly_rows(trades: pd.DataFrame, base: dict) -> list[dict]:
    rows = []
    years = pd.to_datetime(trades.exit_time, utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
    for year in range(2021, 2027):
        part = trades.loc[years == year] if not trades.empty else trades
        rows.append({**base, "year": year, **summarize(part)})
    return rows


def block_bootstrap_metrics(
    trades: pd.DataFrame, *, seed: int, resamples: int = 500, block_size: int = 20
) -> dict:
    """Trade-order block bootstrap; diagnostic only, not a forecast guarantee."""
    if trades.empty or "net_R" not in trades:
        return {"resamples": 0, "block_size": block_size, "prob_net_R_positive_pct": None}
    ordered = trades.sort_values("exit_time")
    ordered = ordered.loc[~ordered.exit_reason.isin(["DATA_GAP", "END_OF_SAMPLE"])] if "exit_reason" in ordered else ordered
    values = pd.to_numeric(ordered.net_R, errors="coerce").dropna().to_numpy(dtype=float)
    n = len(values)
    if n < block_size * 2:
        return {"resamples": 0, "block_size": block_size, "trades": n, "prob_net_R_positive_pct": None}
    rng = np.random.default_rng(seed)
    starts = np.arange(0, n - block_size + 1)
    final_r = np.empty(resamples, dtype=float)
    max_dd_r = np.empty(resamples, dtype=float)
    blocks_needed = int(np.ceil(n / block_size))
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
        "note": "Contiguous 20-trade blocks preserve some local clustering; this is a diagnostic, not a guarantee of future returns",
    }


def main():
    parser = argparse.ArgumentParser(description="Independent M6/M11 full OHLC cost stress and block bootstrap")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", choices=["1h", "4h"], default="4h")
    parser.add_argument("--out", default="cost_stress_artifacts")
    args = parser.parse_args()
    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be later than --start")

    symbol = args.symbol.upper()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"COST STRESS START {symbol} {args.start}..{args.end}", flush=True)

    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    candle_quality = quality_report(raw, symbol, args.start, args.end)
    funding_gaps = funding.index.to_series().diff().dropna()
    funding_max_gap = float(funding_gaps.max().total_seconds() / 3600) if not funding_gaps.empty else None

    oi = None
    oi_quality = None
    try:
        oi = acquire_open_interest(symbol, args.start, args.end)
        oi_quality = metrics_quality_report(oi, symbol, args.start, args.end)
        oi.to_csv(out / f"{symbol}_open_interest_metrics.csv")
    except Exception as error:
        oi_quality = {"symbol": symbol, "status": "DATA_UNAVAILABLE", "error": str(error)}

    profiles = selected_profiles()
    rows, yearly, ledgers, monte_carlo = [], [], [], []
    bar_minutes = {"1h": 60, "4h": 240}[args.timeframe]
    for model in ("M6", "M11"):
        if model == "M11" and (oi is None or oi.empty):
            rows.append({
                "model": model, "variant": "SELECTED_SET", "symbol": symbol,
                "timeframe": args.timeframe, "status": "DATA_GATED",
                "skip_reason": "Official historical OI metrics unavailable", "trades": 0,
            })
            continue
        for profile in profiles[model]:
            variant = profile["variant"]
            signals = make_independent_signals(
                raw, model, args.timeframe,
                open_interest=oi if model == "M11" else None,
                parameters=profile["parameters"],
            )
            max_hold_bars = max(1, int(round(profile["hold_hours"] * 60 / bar_minutes)))
            for scenario in COST_SCENARIOS:
                print(f"STRESS START {symbol} {model} {variant} {scenario['name']}", flush=True)
                trades = run_backtest(
                    signals, funding, symbol, model, args.timeframe,
                    fee_bps=scenario["fee_bps"],
                    slippage_bps=scenario["slippage_bps"],
                    rr=profile["rr"],
                    max_hold_bars=max_hold_bars,
                    trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                    expected_end=args.end,
                )
                base = {
                    "model": model, "variant": variant, "symbol": symbol,
                    "timeframe": args.timeframe, "cost_scenario": scenario["name"],
                    "fee_bps_per_side": scenario["fee_bps"],
                    "slippage_bps_per_side": scenario["slippage_bps"],
                    "rr": profile["rr"], "max_hold_hours": profile["hold_hours"],
                    "parameters_json": json.dumps(profile["parameters"], sort_keys=True),
                }
                stats = summarize(trades)
                dev = _period_summary(trades, 2021, 2024)
                val = _period_summary(trades, 2025, 2025)
                audit = _period_summary(trades, 2026, 2026)
                rows.append({
                    **base, **stats, "status": "COMPLETED", "skip_reason": "",
                    **{f"development_{k}": v for k, v in dev.items()},
                    **{f"validation_2025_{k}": v for k, v in val.items()},
                    **{f"retrospective_2026_{k}": v for k, v in audit.items()},
                })
                if not trades.empty:
                    ledger = trades.copy()
                    for key, value in base.items():
                        ledger[key] = value
                    ledgers.append(ledger)
                    yearly.extend(_yearly_rows(trades, base))
                    seed = zlib.crc32(f"{symbol}|{model}|{variant}|{scenario['name']}".encode())
                    monte_carlo.append({
                        **base,
                        **block_bootstrap_metrics(trades, seed=seed),
                    })
                print(
                    f"STRESS END {symbol} {model} {variant} {scenario['name']}: "
                    f"trades={stats['trades']} PF_R={stats['profit_factor_r']} net_R={stats['net_R']}",
                    flush=True,
                )

    pd.DataFrame(rows).to_csv(out / "screen_results.csv", index=False)
    pd.DataFrame(yearly).to_csv(out / "screen_yearly.csv", index=False)
    pd.DataFrame(monte_carlo).to_csv(out / "monte_carlo.csv", index=False)
    pd.concat(ledgers, ignore_index=True).to_csv(out / "trade_ledger.csv", index=False) if ledgers else pd.DataFrame().to_csv(out / "trade_ledger.csv", index=False)
    metadata = {
        "symbol": symbol, "period_start_inclusive": args.start,
        "period_end_exclusive": args.end, "timeframe": args.timeframe,
        "models_tested_independently": ["M6", "M11"],
        "selected_variants": {model: [p["variant"] for p in group] for model, group in profiles.items()},
        "cost_scenarios": list(COST_SCENARIOS),
        "candle_quality": candle_quality,
        "funding_source": funding.attrs.get("source", "unknown"),
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding.attrs.get("missing_archive_months", []),
        "open_interest_quality": oi_quality,
        "note": "All scenarios re-execute the same OHLC path with altered entry/exit fees and slippage. Annual rows are chronological fixed-parameter diagnostics; 2026 is retrospective because it was included in earlier broad sweeps. M3 is untouched.",
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))
    print(f"COST STRESS COMPLETE {symbol}", flush=True)


if __name__ == "__main__":
    main()

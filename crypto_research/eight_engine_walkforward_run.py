from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import run_backtest, summarize
from .data import acquire_funding, acquire_klines, quality_report
from .eight_engine_cost_stress_run import cost_stress_profiles
from .improvement_run import ACTIVE_MODELS, TIMEFRAME_MINUTES, OFFICIAL_FUNDING_SOURCES, cost_diagnostics
from .independent_models import make_independent_signals

BAR_MINUTES = {"1h": 60, "4h": 240}
TEST_YEARS = (2023, 2024, 2025, 2026)


def _utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def valid_trades(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    return trades.loc[~trades.exit_reason.isin(["DATA_GAP", "END_OF_SAMPLE"])].copy()


def completed_training_cohort(trades: pd.DataFrame, start, end_exclusive) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    entry = pd.to_datetime(trades.entry_time, utc=True, errors="coerce")
    exit_time = pd.to_datetime(trades.exit_time, utc=True, errors="coerce")
    mask = (
        entry.ge(_utc(start))
        & entry.lt(_utc(end_exclusive))
        & exit_time.lt(_utc(end_exclusive))
        & ~trades.exit_reason.isin(["DATA_GAP", "END_OF_SAMPLE"])
    )
    return trades.loc[mask].copy()


def build_test_window(signals: pd.DataFrame, start, end_exclusive) -> pd.DataFrame:
    out = signals.loc[signals.index >= _utc(start)].copy()
    if not out.empty:
        out.loc[out.index >= _utc(end_exclusive), "signal"] = 0
    return out


def entry_keys(trades: pd.DataFrame) -> set[tuple[str, str]]:
    frame = valid_trades(trades)
    if frame.empty:
        return set()
    times = pd.to_datetime(frame.entry_time, utc=True).astype(str)
    return set(zip(frame.side.astype(str), times))


def retention_metrics(baseline: pd.DataFrame, candidate: pd.DataFrame) -> dict:
    base = valid_trades(baseline)
    current = valid_trades(candidate)
    base_keys = entry_keys(base)
    current_keys = entry_keys(current)
    overlap = len(base_keys & current_keys)
    rejected_keys = base_keys - current_keys
    rejected = base[
        [
            (str(side), str(pd.Timestamp(ts).tz_convert("UTC"))) in rejected_keys
            for side, ts in zip(base.side, pd.to_datetime(base.entry_time, utc=True))
        ]
    ] if not base.empty else base
    return {
        "baseline_trades": int(len(base)),
        "candidate_trades": int(len(current)),
        "trade_count_retention_pct": round(len(current) / len(base) * 100, 3) if len(base) else None,
        "baseline_entry_retention_pct": round(overlap / len(base_keys) * 100, 3) if base_keys else None,
        "rejected_baseline_entries": int(len(rejected_keys)),
        "rejected_baseline_net_bps": round(float(pd.to_numeric(rejected.net_bps, errors="coerce").fillna(0).sum()), 3) if not rejected.empty else 0.0,
        "new_entries": int(len(current_keys - base_keys)),
    }


def metric_summary(trades: pd.DataFrame) -> dict:
    total = int(len(trades))
    gaps = int(trades.exit_reason.eq("DATA_GAP").sum()) if total else 0
    censored = int(trades.exit_reason.eq("END_OF_SAMPLE").sum()) if total else 0
    valid = valid_trades(trades)
    return {
        **summarize(valid),
        **cost_diagnostics(valid),
        "total_trade_records": total,
        "data_gap_trades": gaps,
        "end_of_sample_trades": censored,
    }


def select_candidate(
    candidates: list[dict],
    start,
    train_end,
    min_train_trades: int = 30,
    min_entry_retention_pct: float = 80.0,
    min_count_retention_pct: float = 80.0,
) -> tuple[dict | None, list[dict]]:
    baseline = next((item for item in candidates if item["profile"]["variant"] == "BASELINE"), None)
    if baseline is None:
        raise ValueError("Each model candidate set must include BASELINE")
    baseline_train = completed_training_cohort(baseline["trades"], start, train_end)
    rows = []
    for item in candidates:
        profile = item["profile"]
        train = completed_training_cohort(item["trades"], start, train_end)
        retention = retention_metrics(baseline_train, train)
        stats = summarize(train)
        eligible = (
            int(stats.get("trades", 0)) >= min_train_trades
            and (
                profile["variant"] == "BASELINE"
                or (
                    retention["baseline_entry_retention_pct"] is not None
                    and retention["baseline_entry_retention_pct"] >= min_entry_retention_pct
                    and retention["trade_count_retention_pct"] is not None
                    and retention["trade_count_retention_pct"] >= min_count_retention_pct
                )
            )
        )
        rows.append({
            "model": profile["model"],
            "variant": profile["variant"],
            "train_trades": int(stats.get("trades", 0)),
            "train_net_bps": float(stats.get("net_bps", 0.0)),
            "train_net_R": float(stats.get("net_R", 0.0)),
            "train_pf_bps": stats.get("profit_factor"),
            "train_pf_r": stats.get("profit_factor_r"),
            "train_max_drawdown_pct": float(stats.get("max_drawdown_pct", 0.0)),
            **retention,
            "eligible": bool(eligible),
        })
    eligible_rows = [row for row in rows if row["eligible"]]
    if not eligible_rows:
        return None, rows

    def rank(row):
        pf_r = row["train_pf_r"]
        pf_r = float(pf_r) if pf_r is not None and pd.notna(pf_r) else -1e12
        dd = float(row["train_max_drawdown_pct"])
        return (
            float(row["train_net_R"]),
            pf_r,
            dd,
            float(row.get("baseline_entry_retention_pct") or 0.0),
            float(row.get("trade_count_retention_pct") or 0.0),
        )

    selected_row = max(eligible_rows, key=rank)
    selected = next(
        item for item in candidates
        if item["profile"]["model"] == selected_row["model"]
        and item["profile"]["variant"] == selected_row["variant"]
    )
    return selected, rows


def _period_label(year: int) -> str:
    return "RETROSPECTIVE_2026_NOT_HOLDOUT" if year == 2026 else f"FORWARD_YEAR_{year}"


def run_symbol(args) -> None:
    symbol = args.symbol.upper()
    timeframe = args.timeframe
    start_ts, end_ts = _utc(args.start), _utc(args.end)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    candle_quality = quality_report(raw, symbol, args.start, args.end)
    funding_gaps = funding.index.to_series().diff().dropna() if not funding.empty else pd.Series(dtype="timedelta64[ns]")
    funding_max_gap = float(funding_gaps.max().total_seconds() / 3600) if not funding_gaps.empty else None
    funding_source = funding.attrs.get("source", "unknown")
    funding_missing_months = funding.attrs.get("missing_archive_months", [])
    funding_ok = (
        funding_source in OFFICIAL_FUNDING_SOURCES
        and not funding.empty
        and funding_max_gap is not None
        and funding_max_gap <= 8.5
    )

    benchmark_raw = None
    benchmark_quality = None
    if symbol != "BTCUSDT" and any(model in args.models for model in ("M10", "M13")):
        benchmark_raw = acquire_klines("BTCUSDT", args.start, args.end)
        benchmark_quality = quality_report(benchmark_raw, "BTCUSDT", args.start, args.end)

    profiles = cost_stress_profiles()
    metadata = {
        "symbol": symbol,
        "timeframe": timeframe,
        "start_inclusive": args.start,
        "end_exclusive": args.end,
        "models_tested_independently": list(args.models),
        "candidate_variants": {model: [p["variant"] for p in profiles[model]] for model in args.models},
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "min_training_trades": args.min_train_trades,
        "min_baseline_entry_retention_pct": args.min_entry_retention_pct,
        "min_trade_count_retention_pct": args.min_count_retention_pct,
        "test_years": list(args.test_years),
        "candle_quality": candle_quality,
        "benchmark_quality": benchmark_quality,
        "funding_source": funding_source,
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding_missing_months,
        "funding_gate_passed": bool(funding_ok),
        "selection_rule": "Each model selects only from its own predeclared profiles using completed training trades; maximize training net-R, then R-PF and drawdown, with at least 80% baseline-entry overlap and total trade-count retention for non-baseline candidates.",
        "test_design": "Flat-start annual test windows; completed-bar signals and next-bar execution. Entries after the exclusive year boundary are disabled; positions opened within the year may use their predeclared exit horizon. DATA_GAP and END_OF_SAMPLE remain in audit files and are excluded from metrics.",
        "selection_bias_note": "Profiles were identified after earlier broad historical sweeps; these expanding-window results are retrospective diagnostics, not a pristine holdout. 2026 is retrospective only.",
        "cross_symbol_note": "Symbol-stream diagnostics only; no portfolio return is computed.",
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))

    result_rows, candidate_rows, ledger_parts = [], [], []
    if not funding_ok:
        for model in args.models:
            for year in args.test_years:
                result_rows.append({
                    "symbol": symbol, "timeframe": timeframe, "model": model,
                    "year": year, "period_label": _period_label(year),
                    "status": "DATA_GATED_FUNDING",
                    "skip_reason": f"Funding source/coverage failed: {funding_source}; max_gap_hours={funding_max_gap}; missing_archive_months={funding_missing_months}",
                })
        pd.DataFrame(result_rows).to_csv(out / "walkforward_results.csv", index=False)
        pd.DataFrame(candidate_rows).to_csv(out / "candidate_training_scores.csv", index=False)
        pd.DataFrame().to_csv(out / "walkforward_trade_ledger.csv", index=False)
        return

    for model in args.models:
        if model in ("M10", "M13") and symbol == "BTCUSDT":
            for year in args.test_years:
                result_rows.append({
                    "symbol": symbol, "timeframe": timeframe, "model": model,
                    "year": year, "period_label": _period_label(year),
                    "status": "NOT_APPLICABLE",
                    "skip_reason": "BTC is the benchmark, not a traded leg",
                })
            continue

        candidate_cache = []
        for profile in profiles[model]:
            variant = profile["variant"]
            try:
                signals = make_independent_signals(
                    raw,
                    model,
                    timeframe,
                    benchmark_raw=benchmark_raw if model in ("M10", "M13") else None,
                    parameters=profile["parameters"],
                )
                max_hold_bars = max(1, int(round(profile["hold_hours"] * 60 / BAR_MINUTES[timeframe])))
                trades = run_backtest(
                    signals, funding, symbol, model, timeframe,
                    fee_bps=args.fee_bps,
                    slippage_bps=args.slippage_bps,
                    rr=profile["rr"],
                    max_hold_bars=max_hold_bars,
                    trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                    expected_end=args.end,
                )
                candidate_cache.append({
                    "profile": {**profile, "model": model, "max_hold_bars": max_hold_bars},
                    "signals": signals,
                    "trades": trades,
                })
            except Exception as error:
                candidate_rows.append({
                    "symbol": symbol, "timeframe": timeframe, "model": model,
                    "variant": variant, "status": "FAILED",
                    "skip_reason": f"{type(error).__name__}: {error}",
                })

        if not any(item["profile"]["variant"] == "BASELINE" for item in candidate_cache):
            for year in args.test_years:
                result_rows.append({
                    "symbol": symbol, "timeframe": timeframe, "model": model,
                    "year": year, "period_label": _period_label(year),
                    "status": "BASELINE_FAILED",
                    "skip_reason": "Baseline profile did not complete",
                })
            continue

        for year in args.test_years:
            year_start = pd.Timestamp(year=year, month=1, day=1, tz="UTC")
            next_year = pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC")
            year_end = min(next_year, end_ts)
            if year_start >= end_ts:
                continue

            selected, scores = select_candidate(
                candidate_cache, start_ts, year_start,
                min_train_trades=args.min_train_trades,
                min_entry_retention_pct=args.min_entry_retention_pct,
                min_count_retention_pct=args.min_count_retention_pct,
            )
            for score in scores:
                candidate_rows.append({
                    "symbol": symbol, "timeframe": timeframe, "year": year,
                    "period_label": _period_label(year),
                    "selection_train_end_exclusive": str(year_start),
                    "status": "SCORED",
                    **score,
                })

            if selected is None:
                result_rows.append({
                    "symbol": symbol, "timeframe": timeframe, "model": model,
                    "year": year, "period_label": _period_label(year),
                    "status": "NO_TRAINING_SAMPLE",
                    "skip_reason": f"No candidate reached {args.min_train_trades} completed training trades",
                })
                continue

            baseline = next(item for item in candidate_cache if item["profile"]["variant"] == "BASELINE")
            selected_window = build_test_window(selected["signals"], year_start, year_end)
            baseline_window = build_test_window(baseline["signals"], year_start, year_end)
            if selected_window.empty or baseline_window.empty:
                result_rows.append({
                    "symbol": symbol, "timeframe": timeframe, "model": model,
                    "year": year, "period_label": _period_label(year),
                    "status": "NO_TEST_BARS",
                    "selected_variant": selected["profile"]["variant"],
                })
                continue

            selected_trades = run_backtest(
                selected_window, funding, symbol, model, timeframe,
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
                rr=selected["profile"]["rr"],
                max_hold_bars=selected["profile"]["max_hold_bars"],
                trailing_atr_multiple=selected["profile"].get("trailing_atr_multiple"),
                expected_end=args.end,
            )
            if selected["profile"]["variant"] == "BASELINE":
                baseline_trades = selected_trades.copy()
            else:
                baseline_trades = run_backtest(
                    baseline_window, funding, symbol, model, timeframe,
                    fee_bps=args.fee_bps,
                    slippage_bps=args.slippage_bps,
                    rr=baseline["profile"]["rr"],
                    max_hold_bars=baseline["profile"]["max_hold_bars"],
                    trailing_atr_multiple=baseline["profile"].get("trailing_atr_multiple"),
                    expected_end=args.end,
                )

            selected_entry = pd.to_datetime(selected_trades.entry_time, utc=True) if not selected_trades.empty else pd.Series(dtype="datetime64[ns, UTC]")
            selected_cohort = selected_trades.loc[
                selected_entry.ge(year_start) & selected_entry.lt(year_end)
            ].copy() if not selected_trades.empty else selected_trades.copy()
            base_entry = pd.to_datetime(baseline_trades.entry_time, utc=True) if not baseline_trades.empty else pd.Series(dtype="datetime64[ns, UTC]")
            baseline_cohort = baseline_trades.loc[
                base_entry.ge(year_start) & base_entry.lt(year_end)
            ].copy() if not baseline_trades.empty else baseline_trades.copy()

            test_retention = retention_metrics(baseline_cohort, selected_cohort)
            stats = metric_summary(selected_cohort)
            baseline_stats = metric_summary(baseline_cohort)
            row = {
                "symbol": symbol, "timeframe": timeframe, "model": model,
                "year": year, "period_label": _period_label(year),
                "status": "COMPLETED",
                "selected_variant": selected["profile"]["variant"],
                "selected_parameters_json": json.dumps(selected["profile"]["parameters"], sort_keys=True),
                "rr": selected["profile"]["rr"],
                "max_hold_hours": selected["profile"]["hold_hours"],
                "max_hold_bars": selected["profile"]["max_hold_bars"],
                "trailing_atr_multiple": selected["profile"].get("trailing_atr_multiple"),
                "candidate_profiles": len(candidate_cache),
                "eligible_training_profiles": sum(bool(score["eligible"]) for score in scores),
                "training_baseline_entry_retention_gate_pct": args.min_entry_retention_pct,
                "training_trade_count_retention_gate_pct": args.min_count_retention_pct,
                "training_selected_net_R": next((score["train_net_R"] for score in scores if score["variant"] == selected["profile"]["variant"]), None),
                "training_selected_pf_bps": next((score["train_pf_bps"] for score in scores if score["variant"] == selected["profile"]["variant"]), None),
                "training_selected_pf_r": next((score["train_pf_r"] for score in scores if score["variant"] == selected["profile"]["variant"]), None),
                **{f"baseline_test_{key}": value for key, value in baseline_stats.items()},
                **{f"test_{key}": value for key, value in stats.items()},
                **{f"test_retention_{key}": value for key, value in test_retention.items()},
                "selection_rule": "max training net-R; R-PF and drawdown tie-breakers; >=80% training trade-count and baseline-entry retention",
            }
            result_rows.append(row)

            if not selected_cohort.empty:
                ledger = selected_cohort.copy()
                ledger["walkforward_year"] = year
                ledger["period_label"] = _period_label(year)
                ledger["variant"] = selected["profile"]["variant"]
                ledger["parameters_json"] = json.dumps(selected["profile"]["parameters"], sort_keys=True)
                ledger["timeframe"] = timeframe
                ledger_parts.append(ledger)

    pd.DataFrame(result_rows).to_csv(out / "walkforward_results.csv", index=False)
    pd.DataFrame(candidate_rows).to_csv(out / "candidate_training_scores.csv", index=False)
    pd.concat(ledger_parts, ignore_index=True).to_csv(out / "walkforward_trade_ledger.csv", index=False) if ledger_parts else pd.DataFrame().to_csv(out / "walkforward_trade_ledger.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Independent eight-engine expanding-window walk-forward diagnostics")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", choices=("1h", "4h"), default="4h")
    parser.add_argument("--models", nargs="+", choices=ACTIVE_MODELS, default=list(ACTIVE_MODELS))
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--min-train-trades", type=int, default=30)
    parser.add_argument("--min-entry-retention-pct", type=float, default=80.0)
    parser.add_argument("--min-count-retention-pct", type=float, default=80.0)
    parser.add_argument("--test-years", nargs="+", type=int, default=list(TEST_YEARS))
    parser.add_argument("--out", default="eight_engine_walkforward_artifacts")
    args = parser.parse_args()
    if _utc(args.end) <= _utc(args.start):
        parser.error("--end must be later than --start")
    if args.min_train_trades < 1:
        parser.error("--min-train-trades must be >= 1")
    if any(year < 2022 or year > 2026 for year in args.test_years):
        parser.error("--test-years must be between 2022 and 2026")
    if not set(args.models).issubset(ACTIVE_MODELS):
        parser.error("Only the eight approved independent models may be run")
    run_symbol(args)


if __name__ == "__main__":
    main()

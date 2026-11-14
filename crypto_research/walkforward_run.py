from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import run_backtest, summarize
from .combination_run import combination_profiles
from .data import acquire_funding, acquire_klines, quality_report
from .independent_models import make_independent_signals
from .metrics import acquire_open_interest, metrics_quality_report

BAR_MINUTES = {"1h": 60, "4h": 240}
TEST_YEARS = (2023, 2024, 2025, 2026)
OFFICIAL_FUNDING_SOURCES = {
    "binance_vision_official_monthly_archive",
    "binance_vision_archive_plus_official_api",
    "binance_official_api",
}


def _utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _trade_times(trades: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    entry = pd.to_datetime(trades.get("entry_time", pd.Series(index=trades.index, dtype=object)), utc=True, errors="coerce")
    exit_time = pd.to_datetime(trades.get("exit_time", pd.Series(index=trades.index, dtype=object)), utc=True, errors="coerce")
    return entry, exit_time


def completed_training_cohort(
    trades: pd.DataFrame, start: str | pd.Timestamp, end_exclusive: str | pd.Timestamp
) -> pd.DataFrame:
    """Only trades entered in the training window and fully exited before its end."""
    if trades.empty:
        return trades.copy()
    start_ts, end_ts = _utc(start), _utc(end_exclusive)
    entry, exit_time = _trade_times(trades)
    mask = (
        entry.ge(start_ts)
        & entry.lt(end_ts)
        & exit_time.lt(end_ts)
        & ~trades.exit_reason.eq("END_OF_SAMPLE")
    )
    return trades.loc[mask].copy()


def build_test_year_window(
    signals: pd.DataFrame, start: str | pd.Timestamp, end_exclusive: str | pd.Timestamp
) -> pd.DataFrame:
    """
    Create a flat-start test window using right-labelled completed bars.
    A first bar whose close label is after the boundary is fully inside the
    test period; its signal is available at that close and may enter at the
    next bar open. A bar labelled exactly at the boundary may enter at the
    boundary open. Signals at/after the exclusive end are disabled, while
    positions opened within the year may use their predeclared exit horizon.
    """
    start_ts, end_ts = _utc(start), _utc(end_exclusive)
    out = signals.loc[signals.index >= start_ts].copy()
    if out.empty:
        return out
    out.loc[out.index >= end_ts, "signal"] = 0
    return out


def select_candidate(
    candidates: list[dict], start: str | pd.Timestamp, train_end: str | pd.Timestamp,
    min_train_trades: int = 10,
) -> tuple[dict | None, list[dict]]:
    """
    Rank each model's own predeclared parameter profiles using completed
    training trades only. Net-R is the primary rank key; PF is a secondary
    tie-breaker, never the sole selection criterion. Negative and near-flat
    candidates remain in the score table.
    """
    rows = []
    for candidate in candidates:
        profile = candidate["profile"]
        train = completed_training_cohort(candidate["trades"], start, train_end)
        stats = summarize(train)
        pf_bps = stats.get("profit_factor")
        pf_r = stats.get("profit_factor_r")
        rows.append({
            "model": profile["model"],
            "variant": profile["variant"],
            "train_trades": int(stats.get("trades", 0)),
            "train_data_gap_trades": int(stats.get("data_gap_trades", 0)),
            "train_pf_bps": pf_bps,
            "train_pf_r": pf_r,
            "train_net_R": float(stats.get("net_R", 0.0)),
            "train_fixed_risk_return_pct": float(stats.get("net_return_pct", 0.0)),
            "train_max_drawdown_pct": float(stats.get("max_drawdown_pct", 0.0)),
            "train_win_rate_pct": float(stats.get("win_rate_pct", 0.0)),
            "train_avg_holding_minutes": stats.get("avg_holding_minutes"),
            "eligible_sample": bool(stats.get("trades", 0) >= min_train_trades),
        })

    eligible = [row for row in rows if row["eligible_sample"]]
    if not eligible:
        return None, rows

    def sort_key(row):
        pf_r = row["train_pf_r"]
        pf_r = float(pf_r) if pf_r is not None and pd.notna(pf_r) else -1e12
        dd = float(row["train_max_drawdown_pct"])
        return (
            float(row["train_net_R"]),
            pf_r,
            dd,
            row["variant"],
        )

    selected_row = max(eligible, key=sort_key)
    selected = next(
        item for item in candidates
        if item["profile"]["variant"] == selected_row["variant"]
        and item["profile"]["model"] == selected_row["model"]
    )
    return selected, rows


def _period_label(year: int) -> str:
    return "RETROSPECTIVE_2026_NOT_HOLDOUT" if year == 2026 else f"FORWARD_YEAR_{year}"


def _metric_summary(trades: pd.DataFrame) -> dict:
    """Keep DATA_GAP and END_OF_SAMPLE rows in audit counts, not performance."""
    total_records = int(len(trades))
    data_gaps = int(trades.exit_reason.eq("DATA_GAP").sum()) if not trades.empty else 0
    censored = int(trades.exit_reason.eq("END_OF_SAMPLE").sum()) if not trades.empty else 0
    scored_input = trades.loc[~trades.exit_reason.eq("END_OF_SAMPLE")].copy() if not trades.empty else trades
    stats = summarize(scored_input)
    stats["total_trade_records"] = total_records
    stats["data_gap_trades"] = data_gaps
    stats["end_of_sample_trades"] = censored
    return stats


def run_symbol(args) -> None:
    symbol = args.symbol.upper()
    timeframe = args.timeframe
    bar_delta = pd.Timedelta(minutes=BAR_MINUTES[timeframe])
    start_ts, end_ts = _utc(args.start), _utc(args.end)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"WALKFORWARD START {symbol} {args.start}..{args.end}", flush=True)
    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    candle_quality = quality_report(raw, symbol, args.start, args.end)
    funding_gaps = funding.index.to_series().diff().dropna()
    funding_max_gap = (
        float(funding_gaps.max().total_seconds() / 3600)
        if not funding_gaps.empty else None
    )
    funding_source = funding.attrs.get("source", "unknown")
    funding_missing_months = funding.attrs.get("missing_archive_months", [])
    funding_ok = (
        funding_source in OFFICIAL_FUNDING_SOURCES
        and not funding.empty
        and funding_max_gap is not None
        and funding_max_gap <= 8.5
    )

    oi = None
    oi_quality = None
    try:
        oi = acquire_open_interest(symbol, args.start, args.end)
        oi_quality = metrics_quality_report(oi, symbol, args.start, args.end)
        oi.to_csv(out / f"{symbol}_open_interest_metrics.csv")
    except Exception as error:
        oi_quality = {"symbol": symbol, "status": "DATA_UNAVAILABLE", "error": str(error)}

    metadata = {
        "symbol": symbol,
        "period": {"start_inclusive": args.start, "end_exclusive": args.end},
        "timeframe": timeframe,
        "models_tested_independently": ["M6", "M11"],
        "test_years": list(args.test_years),
        "minimum_training_trades": args.min_train_trades,
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "candle_quality": candle_quality,
        "funding_source": funding_source,
        "funding_rows": int(len(funding)),
        "funding_max_gap_hours": funding_max_gap,
        "funding_missing_archive_months": funding_missing_months,
        "funding_gate_passed": bool(funding_ok),
        "open_interest_quality": oi_quality,
        "oi_timestamp_alignment": "post-2026-06-25 create_time shifted +5m to actual snapshot availability",
        "selection_rule": "For each symbol/model/year, select among that model's predeclared combination_profiles using only trades entered in the training window and fully exited before the test-year start. Primary rank is net-R; R-PF is a tie-breaker. No cross-model inputs.",
        "test_design": "Each annual test starts flat at the UTC year boundary. Signals are disabled at/after the exclusive year end; trades entered in the year may use their full predeclared holding horizon to exit. DATA_GAP and END_OF_SAMPLE remain in the audit ledger and are excluded from performance metrics.",
        "2026_label": "Retrospective audit only; not a pristine holdout because 2026 was exposed in earlier broad sweeps.",
        "note": "M11 is open-interest pressure only. No historical liquidation-event proxy is used. M3 is untouched.",
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))

    result_rows, candidate_rows, ledger_parts = [], [], []
    if not funding_ok:
        for model in ("M6", "M11"):
            for year in args.test_years:
                result_rows.append({
                    "symbol": symbol, "model": model, "year": year,
                    "period_label": _period_label(year),
                    "status": "DATA_GATED_FUNDING",
                    "skip_reason": f"Funding source/coverage failed: {funding_source}; max_gap_hours={funding_max_gap}; missing_archive_months={funding_missing_months}",
                })
        pd.DataFrame(result_rows).to_csv(out / "walkforward_results.csv", index=False)
        pd.DataFrame(candidate_rows).to_csv(out / "candidate_training_scores.csv", index=False)
        pd.DataFrame().to_csv(out / "walkforward_trade_ledger.csv", index=False)
        print(f"WALKFORWARD DATA GATED {symbol}", flush=True)
        return

    for model in ("M6", "M11"):
        if model == "M11" and (oi is None or oi.empty):
            for year in args.test_years:
                result_rows.append({
                    "symbol": symbol, "model": model, "year": year,
                    "period_label": _period_label(year),
                    "status": "DATA_GATED_OI",
                    "skip_reason": "Official historical OI metrics unavailable; no price-only proxy is permitted",
                })
            continue

        candidate_cache = []
        for profile in combination_profiles(model):
            variant = profile["variant"]
            max_hold_bars = max(1, int(round(profile["hold_hours"] * 60 / BAR_MINUTES[timeframe])))
            try:
                signals = make_independent_signals(
                    raw, model, timeframe,
                    open_interest=oi if model == "M11" else None,
                    parameters=profile["parameters"],
                )
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
                    "symbol": symbol, "model": model, "variant": variant,
                    "status": "FAILED",
                    "skip_reason": f"{type(error).__name__}: {error}",
                })
                print(f"WALKFORWARD CANDIDATE ERROR {symbol} {model} {variant}: {error}", flush=True)

        for year in args.test_years:
            year_start = pd.Timestamp(year=year, month=1, day=1, tz="UTC")
            next_year = pd.Timestamp(year=year + 1, month=1, day=1, tz="UTC")
            year_end = min(next_year, end_ts)
            if year_start >= end_ts:
                continue

            selected, scores = select_candidate(
                candidate_cache, start_ts, year_start, min_train_trades=args.min_train_trades
            )
            for score in scores:
                candidate_rows.append({
                    "symbol": symbol, "year": year,
                    "period_label": _period_label(year),
                    "selection_train_end_exclusive": str(year_start),
                    **score,
                })

            if selected is None:
                result_rows.append({
                    "symbol": symbol, "model": model, "year": year,
                    "period_label": _period_label(year),
                    "status": "NO_TRAINING_SAMPLE",
                    "skip_reason": f"No candidate reached {args.min_train_trades} valid completed training trades",
                    "candidate_profiles": len(candidate_cache),
                })
                continue

            profile = selected["profile"]
            test_bars = build_test_year_window(selected["signals"], year_start, year_end)
            if test_bars.empty:
                result_rows.append({
                    "symbol": symbol, "model": model, "year": year,
                    "period_label": _period_label(year),
                    "status": "NO_TEST_BARS",
                    "selected_variant": profile["variant"],
                })
                continue

            try:
                test_trades = run_backtest(
                    test_bars, funding, symbol, model, timeframe,
                    fee_bps=args.fee_bps,
                    slippage_bps=args.slippage_bps,
                    rr=profile["rr"],
                    max_hold_bars=profile["max_hold_bars"],
                    trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                    expected_end=args.end,
                )
                if not test_trades.empty:
                    entry_time, _ = _trade_times(test_trades)
                    cohort = test_trades.loc[entry_time.ge(year_start) & entry_time.lt(year_end)].copy()
                    cohort["walkforward_year"] = year
                    cohort["period_label"] = _period_label(year)
                    cohort["variant"] = profile["variant"]
                    cohort["parameters_json"] = json.dumps(profile["parameters"], sort_keys=True)
                    ledger_parts.append(cohort)
                else:
                    cohort = test_trades

                stats = _metric_summary(cohort)
                train = completed_training_cohort(selected["trades"], start_ts, year_start)
                train_stats = summarize(train)
                result_rows.append({
                    "symbol": symbol, "model": model, "year": year,
                    "period_label": _period_label(year),
                    "status": "COMPLETED",
                    "selected_variant": profile["variant"],
                    "selected_parameters_json": json.dumps(profile["parameters"], sort_keys=True),
                    "rr": profile["rr"],
                    "max_hold_hours": profile["hold_hours"],
                    "max_hold_bars": profile["max_hold_bars"],
                    "trailing_atr_multiple": profile.get("trailing_atr_multiple"),
                    "training_trades": train_stats["trades"],
                    "training_pf_bps": train_stats["profit_factor"],
                    "training_pf_r": train_stats["profit_factor_r"],
                    "training_net_R": train_stats["net_R"],
                    "training_fixed_risk_return_pct": train_stats["net_return_pct"],
                    "training_max_drawdown_pct": train_stats["max_drawdown_pct"],
                    "training_win_rate_pct": train_stats["win_rate_pct"],
                    "training_positive_by_both_pf": bool(
                        train_stats["net_R"] > 0
                        and (train_stats["profit_factor"] or 0) > 1
                        and (train_stats["profit_factor_r"] or 0) > 1
                    ),
                    **{f"test_{key}": value for key, value in stats.items()},
                    "selection_rule": "max training net-R; R-PF tie-breaker",
                })
                print(
                    f"WALKFORWARD END {symbol} {model} {year} {profile['variant']}: "
                    f"trades={stats['trades']} PF_R={stats['profit_factor_r']} net_R={stats['net_R']}",
                    flush=True,
                )
            except Exception as error:
                result_rows.append({
                    "symbol": symbol, "model": model, "year": year,
                    "period_label": _period_label(year),
                    "status": "FAILED",
                    "selected_variant": profile["variant"],
                    "skip_reason": f"{type(error).__name__}: {error}",
                })
                print(f"WALKFORWARD TEST ERROR {symbol} {model} {year}: {error}", flush=True)

    pd.DataFrame(result_rows).to_csv(out / "walkforward_results.csv", index=False)
    pd.DataFrame(candidate_rows).to_csv(out / "candidate_training_scores.csv", index=False)
    ledger = pd.concat(ledger_parts, ignore_index=True) if ledger_parts else pd.DataFrame()
    ledger.to_csv(out / "walkforward_trade_ledger.csv", index=False)
    print(f"WALKFORWARD COMPLETE {symbol}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Independent expanding-window M6/M11 walk-forward research"
    )
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default="2026-11-01")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", choices=["1h", "4h"], default="4h")
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--min-train-trades", type=int, default=10)
    parser.add_argument("--test-years", nargs="+", type=int, default=list(TEST_YEARS))
    parser.add_argument("--out", default="walkforward_artifacts")
    args = parser.parse_args()
    if _utc(args.end) <= _utc(args.start):
        parser.error("--end must be later than --start")
    if args.min_train_trades < 1:
        parser.error("--min-train-trades must be >= 1")
    if any(year < 2022 or year > 2026 for year in args.test_years):
        parser.error("--test-years must be between 2022 and 2026")
    run_symbol(args)


if __name__ == "__main__":
    main()

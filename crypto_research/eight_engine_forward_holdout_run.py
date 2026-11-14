from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .data import (
    BASE, _checksum_ok, acquire_funding, acquire_klines, get_zip,
    quality_report, read_zip,
)
from .eight_engine_cost_stress_run import cost_stress_profiles
from .improvement_run import ACTIVE_MODELS, OFFICIAL_FUNDING_SOURCES
from .independent_models import make_independent_signals
from .eight_engine_walkforward_run import build_test_window, metric_summary

BAR_MINUTES = {"1h": 60, "4h": 240}
HOLDOUT_START = "2026-11-01"
MINIMUM_HOLDOUT_DAYS = 30

# Frozen using only the pre-2026-11-01 development/validation record.
# None means no candidate cleared the pre-registered improvement standard;
# the baseline remains a diagnostic control for that engine.
FROZEN_VARIANTS = {
    "M6": "RR3_VOL12",
    "M7": None,
    "M8": "HOLD48_VOL10",
    "M10": "EMA_FAST_100",
    "M12": None,
    "M13": "BTC_LOOKBACK_4",
    "M14": "MOMENTUM_21",
    "M15": "ATR_TRAIL_2_5_H48",
}


def _utc(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def expected_daily_dates(start, end) -> list[pd.Timestamp]:
    return list(pd.date_range(_utc(start).normalize(), _utc(end).normalize(), freq="D", inclusive="left"))


def daily_archive_url(symbol: str, day) -> str:
    date = _utc(day).strftime("%Y-%m-%d")
    name = f"{symbol}-1m-{date}.zip"
    return f"{BASE.replace('/monthly', '/daily')}/klines/{symbol}/1m/{name}"


def acquire_forward_klines(symbol, start, holdout_start, end, root=Path("data")):
    """Use verified monthly history plus checksum-verified daily holdout archives."""
    history = acquire_klines(symbol, start, holdout_start, root=root)
    tail_parts = []
    missing_days, unverified_days, errors = [], [], []
    verified_days = []
    for day in expected_daily_dates(holdout_start, end):
        url = daily_archive_url(symbol, day)
        date = day.strftime("%Y-%m-%d")
        name = f"{symbol}-1m-{date}.zip"
        try:
            path = get_zip(
                url,
                root / "raw" / "klines" / symbol / "daily" / name,
                verify_checksum=True,
            )
            if path is None:
                missing_days.append(date)
                continue
            checksum = _checksum_ok(url, path)
            if checksum is not True:
                unverified_days.append(date)
                continue
            tail_parts.append(read_zip(path))
            verified_days.append(date)
        except Exception as error:
            errors.append({"date": date, "error": f"{type(error).__name__}: {error}"})

    if tail_parts:
        tail = pd.concat(tail_parts).sort_index()
        combined = pd.concat([history, tail]).sort_index()
    else:
        combined = history.copy()
    duplicate_count = int(combined.index.duplicated().sum())
    combined = combined[~combined.index.duplicated(keep="last")]
    combined = combined.loc[
        (combined.index >= _utc(start))
        & (combined.index < _utc(end))
    ]
    combined.attrs["duplicate_timestamps_before_dedup"] = duplicate_count
    combined.attrs["source"] = "binance_vision_official_usdm_monthly_history_plus_daily_holdout"
    audit = {
        "expected_daily_archives": len(expected_daily_dates(holdout_start, end)),
        "verified_daily_archives": len(verified_days),
        "verified_days": verified_days,
        "missing_days": missing_days,
        "unverified_checksum_days": unverified_days,
        "archive_errors": errors,
        "complete_daily_tail": (
            len(verified_days) == len(expected_daily_dates(holdout_start, end))
            and not missing_days and not unverified_days and not errors
        ),
    }
    return combined, audit


def _funding_quality(funding: pd.DataFrame, holdout_start, end) -> dict:
    source = funding.attrs.get("source", "unknown")
    missing_months = funding.attrs.get("missing_archive_months", [])
    holdout = funding.loc[
        (funding.index >= _utc(holdout_start)) & (funding.index < _utc(end))
    ] if not funding.empty else funding
    gaps = holdout.index.to_series().diff().dropna() if not holdout.empty else pd.Series(dtype="timedelta64[ns]")
    if not holdout.empty:
        boundary_gaps = [
            holdout.index[0] - _utc(holdout_start),
            _utc(end) - holdout.index[-1],
        ]
        all_gaps = list(gaps) + boundary_gaps
        max_gap = max(float(gap.total_seconds() / 3600) for gap in all_gaps)
    else:
        max_gap = None
    passed = (
        source in OFFICIAL_FUNDING_SOURCES
        and not holdout.empty
        and max_gap is not None
        and max_gap <= 8.5
    )
    return {
        "source": source,
        "missing_archive_months": missing_months,
        "holdout_funding_rows": int(len(holdout)),
        "holdout_max_gap_hours": max_gap,
        "passed": bool(passed),
    }


def _profile_lookup():
    profiles = cost_stress_profiles()
    if set(profiles) != set(ACTIVE_MODELS):
        raise ValueError("Frozen forward profiles do not match the approved eight-model scope")
    result = {}
    for model in ACTIVE_MODELS:
        rows = {row["variant"]: row for row in profiles[model]}
        if "BASELINE" not in rows:
            raise ValueError(f"{model} is missing its baseline profile")
        candidate = FROZEN_VARIANTS[model]
        if candidate is not None and candidate not in rows:
            raise ValueError(f"Frozen variant {candidate} is unavailable for {model}")
        result[model] = rows
    return result


def run_symbol(args):
    symbol, timeframe = args.symbol.upper(), args.timeframe
    start, holdout_start, end = _utc(args.start), _utc(args.holdout_start), _utc(args.end)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    raw, daily_audit = acquire_forward_klines(
        symbol, args.start, args.holdout_start, args.end
    )
    holdout_quality = quality_report(raw, symbol, args.holdout_start, args.end)
    funding = acquire_funding(symbol, args.start, args.end)
    funding_quality = _funding_quality(funding, args.holdout_start, args.end)
    candle_ok = (
        daily_audit["complete_daily_tail"]
        and float(holdout_quality.get("coverage_pct", 0.0)) >= args.minimum_candle_coverage_pct
    )
    funding_ok = funding_quality["passed"]

    benchmark_raw, benchmark_audit, benchmark_quality = None, None, None
    if symbol != "BTCUSDT":
        benchmark_raw, benchmark_audit = acquire_forward_klines(
            "BTCUSDT", args.start, args.holdout_start, args.end
        )
        benchmark_quality = quality_report(
            benchmark_raw, "BTCUSDT", args.holdout_start, args.end
        )

    profiles = _profile_lookup()
    metadata = {
        "symbol": symbol,
        "timeframe": timeframe,
        "history_start": args.start,
        "holdout_start_inclusive": args.holdout_start,
        "holdout_end_exclusive": args.end,
        "freeze_date": HOLDOUT_START,
        "models_tested_independently": list(ACTIVE_MODELS),
        "frozen_variants": FROZEN_VARIANTS,
        "fee_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "minimum_candle_coverage_pct": args.minimum_candle_coverage_pct,
        "candle_quality": holdout_quality,
        "daily_archive_audit": daily_audit,
        "benchmark_daily_archive_audit": benchmark_audit,
        "benchmark_candle_quality": benchmark_quality,
        "funding_quality": funding_quality,
        "selection_policy": "No selection or tuning on holdout data. Baseline and pre-frozen candidate versions are run independently and compared only after the holdout period.",
        "data_policy": "Official Binance Vision USD-M monthly history plus checksum-verified daily 1m archives for the holdout tail; official Binance Vision monthly funding archives or official Binance funding API only. No zero-funding or third-party fallback is scored.",
        "holdout_policy": "Require at least 30 complete UTC days after 2026-11-01. Current UTC day is excluded by the exclusive end date.",
        "cross_symbol_policy": "Symbol-stream diagnostics only; no portfolio return or cross-model aggregation.",
    }
    (out / "run_summary.json").write_text(json.dumps(metadata, indent=2, default=str))

    result_rows, ledger_parts = [], []
    benchmark_ok = (
        symbol == "BTCUSDT"
        or (
            benchmark_audit["complete_daily_tail"]
            and float(benchmark_quality.get("coverage_pct", 0.0)) >= args.minimum_candle_coverage_pct
        )
    )

    for model in ACTIVE_MODELS:
        if model in ("M10", "M13") and symbol == "BTCUSDT":
            result_rows.append({
                "symbol": symbol, "timeframe": timeframe, "model": model,
                "variant": "NOT_APPLICABLE", "role": "BENCHMARK_ONLY",
                "status": "NOT_APPLICABLE",
                "skip_reason": "BTC is the benchmark, not a traded leg",
            })
            continue

        candidate = FROZEN_VARIANTS[model]
        variants = ["BASELINE"] if candidate is None or candidate == "BASELINE" else ["BASELINE", candidate]
        for variant in variants:
            role = "BASELINE_CONTROL" if variant == "BASELINE" else "FROZEN_CANDIDATE"
            base_row = {
                "symbol": symbol, "timeframe": timeframe, "model": model,
                "variant": variant, "role": role,
                "holdout_start": args.holdout_start, "holdout_end_exclusive": args.end,
                "candle_coverage_pct": holdout_quality.get("coverage_pct"),
                "daily_archives_complete": daily_audit["complete_daily_tail"],
                "funding_source": funding_quality["source"],
                "funding_max_gap_hours": funding_quality["holdout_max_gap_hours"],
            }
            if not candle_ok:
                result_rows.append({
                    **base_row, "status": "DATA_GATED_CANDLES",
                    "skip_reason": "Daily holdout archives are missing/unverified or candle coverage is below threshold",
                })
                continue
            if not funding_ok:
                result_rows.append({
                    **base_row, "status": "DATA_GATED_FUNDING",
                    "skip_reason": f"Funding source/coverage failed: {funding_quality}",
                })
                continue
            if model in ("M10", "M13") and not benchmark_ok:
                result_rows.append({
                    **base_row, "status": "DATA_GATED_BENCHMARK",
                    "skip_reason": "BTC benchmark daily archive tail is incomplete or below coverage threshold",
                })
                continue

            profile = profiles[model][variant]
            signals = make_independent_signals(
                raw,
                model,
                timeframe,
                benchmark_raw=benchmark_raw if model in ("M10", "M13") else None,
                parameters=profile["parameters"],
            )
            window = build_test_window(signals, holdout_start, end)
            max_hold_bars = max(1, int(round(profile["hold_hours"] * 60 / BAR_MINUTES[timeframe])))
            trades = run_backtest(
                window, funding, symbol, model, timeframe,
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
                rr=profile["rr"],
                max_hold_bars=max_hold_bars,
                trailing_atr_multiple=profile.get("trailing_atr_multiple"),
                expected_end=args.end,
            )
            entry = pd.to_datetime(trades.entry_time, utc=True) if not trades.empty else pd.Series(dtype="datetime64[ns, UTC]")
            cohort = trades.loc[
                entry.ge(holdout_start) & entry.lt(end)
            ].copy() if not trades.empty else trades.copy()
            stats = metric_summary(cohort)
            valid = cohort.loc[~cohort.exit_reason.isin(["DATA_GAP", "END_OF_SAMPLE"])] if not cohort.empty else cohort
            exposure = (
                float(pd.to_numeric(valid.holding_minutes, errors="coerce").fillna(0).sum())
                / max(1.0, (end - holdout_start).total_seconds() / 60)
                * 100.0
            )
            result_rows.append({
                **base_row,
                "status": "COMPLETED",
                "rr": profile["rr"],
                "max_hold_hours": profile["hold_hours"],
                "max_hold_bars": max_hold_bars,
                "trailing_atr_multiple": profile.get("trailing_atr_multiple"),
                **stats,
                "time_exposure_pct": round(exposure, 3),
            })
            if not cohort.empty:
                ledger = cohort.copy()
                ledger["symbol"] = symbol
                ledger["timeframe"] = timeframe
                ledger["model"] = model
                ledger["variant"] = variant
                ledger["role"] = role
                ledger["holdout_start"] = args.holdout_start
                ledger["holdout_end_exclusive"] = args.end
                ledger_parts.append(ledger)

    pd.DataFrame(result_rows).to_csv(out / "forward_holdout_results.csv", index=False)
    pd.concat(ledger_parts, ignore_index=True).to_csv(out / "forward_holdout_trade_ledger.csv", index=False) if ledger_parts else pd.DataFrame().to_csv(out / "forward_holdout_trade_ledger.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Frozen eight-engine forward holdout; no tuning or selection")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--holdout-start", default=HOLDOUT_START)
    parser.add_argument("--end", required=True, help="Exclusive UTC date; use the last fully completed UTC day")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", choices=("1h", "4h"), default="4h")
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--minimum-candle-coverage-pct", type=float, default=99.5)
    parser.add_argument("--out", default="eight_engine_forward_holdout_artifacts")
    args = parser.parse_args()
    end = _utc(args.end)
    if end <= _utc(args.holdout_start):
        parser.error("--end must be later than --holdout-start")
    if (end - _utc(args.holdout_start)).days < MINIMUM_HOLDOUT_DAYS:
        parser.error("Forward holdout requires at least 30 complete UTC days after 2026-11-01")
    if _utc(args.start) >= _utc(args.holdout_start):
        parser.error("--start must precede --holdout-start")
    run_symbol(args)


if __name__ == "__main__":
    main()

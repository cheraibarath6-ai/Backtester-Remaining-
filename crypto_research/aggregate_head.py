from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import summarize

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "DOGEUSDT", "ADAUSDT", "LINKUSDT", "LTCUSDT", "AVAXUSDT",
]
AUDIT_EXITS = {"DATA_GAP", "END_OF_SAMPLE"}
MODEL_ORDER = ("M6", "M8", "M12", "M14", "M15")


def _as_utc(value):
    ts = pd.Timestamp(value)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _read_batch_artifacts(root):
    summaries = []
    ledgers = []
    triggers = []
    for path in sorted(root.rglob("*_summary.json")):
        row = json.loads(path.read_text())
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            raise RuntimeError(f"Summary has no symbol: {path}")
        summaries.append(row)

        trade_path = path.parent / f"{symbol}_trades.csv"
        if trade_path.exists() and trade_path.stat().st_size:
            try:
                trades = pd.read_csv(trade_path)
            except pd.errors.EmptyDataError:
                trades = pd.DataFrame()
            if not trades.empty:
                trades["symbol"] = symbol
                ledgers.append(trades)

        trigger_path = path.parent / f"{symbol}_trigger_audit.csv"
        if trigger_path.exists() and trigger_path.stat().st_size:
            try:
                audit = pd.read_csv(trigger_path)
            except pd.errors.EmptyDataError:
                audit = pd.DataFrame()
            if not audit.empty:
                first = audit.columns[0]
                if str(first).startswith("Unnamed") or first == "bar_close_time":
                    audit = audit.rename(columns={first: "signal_time"})
                audit["symbol"] = symbol
                triggers.append(audit)

    if not summaries:
        raise RuntimeError("No HEAD symbol summaries found in downloaded batch artifacts")
    return summaries, ledgers, triggers


def _dedupe_trigger_audit(trigger_audit):
    """Deduplicate repeated exports without collapsing distinct trigger bars."""
    if trigger_audit.empty:
        return trigger_audit.copy()
    audit = trigger_audit.copy()
    audit["symbol"] = audit.symbol.astype(str).str.upper()
    time_col = next(
        (column for column in ("signal_time", "open_time", "bar_close_time")
         if column in audit.columns),
        None,
    )
    keys = ["symbol"]
    if time_col:
        audit[time_col] = pd.to_datetime(
            audit[time_col], utc=True, errors="coerce"
        )
        keys.append(time_col)
    keys.extend(
        column for column in ("head_source", "trigger_sources")
        if column in audit.columns
    )
    return audit.drop_duplicates(keys).reset_index(drop=True)


def _valid_trades(all_trades):
    if all_trades.empty:
        return all_trades.copy()
    valid = all_trades.loc[~all_trades.exit_reason.isin(AUDIT_EXITS)].copy()
    if valid.empty:
        return valid
    valid["exit_time"] = pd.to_datetime(valid.exit_time, utc=True)
    key = [c for c in ("symbol", "entry_time", "exit_time", "source_model") if c in valid]
    return valid.drop_duplicates(key).sort_values(["exit_time", "symbol"]).reset_index(drop=True)


def _window_coverage(group, expected_start, expected_end):
    rows = 0
    expected_minutes = 0
    actual_starts = []
    actual_ends = []
    for row in group:
        q = row.get("candle_quality") or {}
        rows += int(q.get("rows") or 0)
        expected_minutes += int(q.get("expected_minutes") or 0)
        if row.get("actual_candle_start"):
            actual_starts.append(_as_utc(row["actual_candle_start"]))
        if row.get("actual_candle_end_exclusive"):
            actual_ends.append(_as_utc(row["actual_candle_end_exclusive"]))

    coverage = 100.0 * rows / expected_minutes if expected_minutes else 0.0
    actual_start = min(actual_starts) if actual_starts else None
    actual_end = max(actual_ends) if actual_ends else None
    listed_minutes = (
        max(0.0, (actual_end - actual_start).total_seconds() / 60.0)
        if actual_start is not None and actual_end is not None else 0.0
    )
    listed_coverage = 100.0 * rows / listed_minutes if listed_minutes else 0.0
    return {
        "candle_rows": rows,
        "expected_minutes": expected_minutes,
        "requested_window_coverage_pct": round(coverage, 4),
        "listed_span_minutes": round(listed_minutes, 2),
        "listed_span_coverage_pct": round(listed_coverage, 4),
        "actual_data_start": str(actual_start) if actual_start is not None else None,
        "actual_data_end_exclusive": str(actual_end) if actual_end is not None else None,
        "listing_delay_days": (
            round(max(0.0, (actual_start - expected_start).total_seconds() / 86400), 4)
            if actual_start is not None else None
        ),
    }


def _aggregate_metrics(frame):
    return summarize(frame) if not frame.empty else summarize(pd.DataFrame())


def _year_tables(valid):
    yearly_rows = []
    symbol_year_rows = []
    if valid.empty:
        return pd.DataFrame(), pd.DataFrame()
    work = valid.copy()
    work["year"] = pd.to_datetime(work.exit_time, utc=True).dt.year
    for year, group in work.groupby("year", sort=True):
        yearly_rows.append({"year": int(year), **_aggregate_metrics(group)})
    for (symbol, year), group in work.groupby(["symbol", "year"], sort=True):
        symbol_year_rows.append({
            "symbol": symbol, "year": int(year), **_aggregate_metrics(group)
        })
    return pd.DataFrame(yearly_rows), pd.DataFrame(symbol_year_rows)


def _model_attribution(valid, trigger_audit, expected_symbols):
    trigger_counts = {(symbol, model): 0 for symbol in expected_symbols for model in MODEL_ORDER}
    selected_counts = {(symbol, model): 0 for symbol in expected_symbols for model in MODEL_ORDER}
    if not trigger_audit.empty:
        for row in trigger_audit.to_dict("records"):
            symbol = str(row.get("symbol", "")).upper()
            fired = str(row.get("trigger_sources", "") or "")
            for model in set(x.strip() for x in fired.split(",") if x.strip()):
                if model in MODEL_ORDER:
                    trigger_counts[(symbol, model)] = trigger_counts.get((symbol, model), 0) + 1
            selected = str(row.get("head_source", "") or "")
            if selected in MODEL_ORDER:
                selected_counts[(symbol, selected)] = selected_counts.get((symbol, selected), 0) + 1

    rows = []
    for symbol in expected_symbols:
        for model in MODEL_ORDER:
            group = (
                valid.loc[
                    (valid.symbol == symbol) & (valid.source_model == model)
                ].copy()
                if not valid.empty else pd.DataFrame()
            )
            metrics = _aggregate_metrics(group)
            rows.append({
                "symbol": symbol,
                "model": model,
                "trigger_bars": int(trigger_counts.get((symbol, model), 0)),
                "selected_bars": int(selected_counts.get((symbol, model), 0)),
                "trades": metrics["trades"],
                "wins": metrics["wins"],
                "losses": metrics["losses"],
                "win_rate_pct": metrics["win_rate_pct"],
                "profit_factor": metrics["profit_factor"],
                "net_bps": metrics["net_bps"],
                "net_R": metrics["net_R"],
            })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate cumulative HEAD OR-engine batches across the full ten-asset universe"
    )
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="head_results")
    parser.add_argument("--expected-symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--expected-start", default="2021-11-14")
    parser.add_argument("--expected-end", required=True)
    parser.add_argument("--current-start", required=True)
    parser.add_argument("--current-end", required=True)
    args = parser.parse_args()

    root = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    expected_symbols = [str(s).upper() for s in args.expected_symbols]
    expected_start = _as_utc(args.expected_start)
    expected_end = _as_utc(args.expected_end)
    current_start = _as_utc(args.current_start)
    current_end = _as_utc(args.current_end)
    if expected_end <= expected_start or current_end <= current_start:
        raise RuntimeError("Invalid expected or current batch window")

    summaries, ledgers, trigger_frames = _read_batch_artifacts(root)
    sdf = pd.DataFrame(summaries)
    sdf["symbol"] = sdf.symbol.astype(str).str.upper()
    sdf["start_inclusive"] = sdf.start_inclusive.astype(str)
    sdf["end_exclusive"] = sdf.end_exclusive.astype(str)

    current_rows = sdf.loc[
        (sdf.start_inclusive == args.current_start)
        & (sdf.end_exclusive == args.current_end)
    ]
    current_found = set(current_rows.symbol)
    current_missing = sorted(set(expected_symbols) - current_found)
    current_duplicates = sorted(
        symbol for symbol, count in current_rows.symbol.value_counts().items()
        if count != 1
    )
    if current_missing or current_duplicates:
        raise RuntimeError(
            f"Current batch is incomplete: missing={current_missing}, "
            f"duplicate_summaries={current_duplicates}"
        )

    windows = sorted(set(zip(sdf.start_inclusive, sdf.end_exclusive)))
    cursor = expected_start
    for start_text, end_text in windows:
        start_ts, end_ts = _as_utc(start_text), _as_utc(end_text)
        if start_ts != cursor:
            raise RuntimeError(
                f"Batch coverage is not contiguous: expected next start {cursor}, "
                f"found {start_ts}..{end_ts}"
            )
        if end_ts <= start_ts:
            raise RuntimeError(f"Invalid batch interval {start_text}..{end_text}")
        cursor = end_ts
    if cursor != expected_end:
        raise RuntimeError(
            f"Batch history ends at {cursor}, expected {expected_end}"
        )
    expected_windows = set(windows)
    for symbol in expected_symbols:
        symbol_windows = set(
            zip(
                sdf.loc[sdf.symbol == symbol, "start_inclusive"],
                sdf.loc[sdf.symbol == symbol, "end_exclusive"],
            )
        )
        if symbol_windows != expected_windows:
            raise RuntimeError(
                f"{symbol} does not have a complete summary for every batch: "
                f"missing={sorted(expected_windows - symbol_windows)}"
            )

    all_trades = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
    if not all_trades.empty:
        all_trades["symbol"] = all_trades.symbol.astype(str).str.upper()
        all_trades = all_trades.drop_duplicates(
            [c for c in ("symbol", "entry_time", "exit_time", "exit_reason", "source_model")
             if c in all_trades]
        )
        all_trades.to_csv(out / "head_complete_trade_ledger.csv", index=False)
    valid = _valid_trades(all_trades)
    if not valid.empty:
        valid.to_csv(out / "head_valid_trade_ledger.csv", index=False)

    trigger_audit = (
        pd.concat(trigger_frames, ignore_index=True)
        if trigger_frames else pd.DataFrame()
    )
    if not trigger_audit.empty:
        trigger_audit = _dedupe_trigger_audit(trigger_audit)
        trigger_audit.to_csv(out / "head_trigger_audit_all_symbols.csv", index=False)

    per_symbol_rows = []
    quality_rows = []
    for symbol in expected_symbols:
        group = sdf.loc[sdf.symbol == symbol].to_dict("records")
        symbol_trades = (
            all_trades.loc[all_trades.symbol == symbol].copy()
            if not all_trades.empty else pd.DataFrame()
        )
        metrics = _aggregate_metrics(symbol_trades)
        coverage = _window_coverage(group, expected_start, expected_end)
        model_counts = {model: 0 for model in MODEL_ORDER}
        funding_sources = set()
        funding_rows = 0
        funding_starts = []
        funding_ends = []
        funding_max_gaps = []
        funding_first_gaps = []
        funding_last_gaps = []
        candle_sources = set()
        missing_minutes = 0
        missing_interval_count = 0
        missing_intervals = []
        conflict_bars = 0
        multi_trigger_bars = 0
        head_trigger_bars = 0
        for row in group:
            candle_quality = row.get("candle_quality") or {}
            candle_source = candle_quality.get("source")
            if candle_source:
                candle_sources.add(str(candle_source))
            missing_minutes += int(candle_quality.get("missing_minutes") or 0)
            missing_interval_count += int(candle_quality.get("missing_interval_count") or 0)
            for interval in candle_quality.get("missing_intervals") or []:
                missing_intervals.append({
                    "batch_start": row.get("start_inclusive"),
                    "batch_end": row.get("end_exclusive"),
                    **interval,
                })
            for model, count in (row.get("model_trigger_bars") or {}).items():
                if model in model_counts:
                    model_counts[model] += int(count or 0)
            source = row.get("funding_source")
            if source:
                funding_sources.add(str(source))
            funding_rows += int(row.get("funding_rows") or 0)
            for field, target in (
                ("funding_actual_start", funding_starts),
                ("funding_actual_end", funding_ends),
                ("funding_max_gap_hours", funding_max_gaps),
                ("funding_first_gap_hours", funding_first_gaps),
                ("funding_last_gap_hours", funding_last_gaps),
            ):
                value = row.get(field)
                if value is not None:
                    target.append(value)
            conflict_bars += int(row.get("conflict_bars") or 0)
            multi_trigger_bars += int(row.get("multi_trigger_bars") or 0)
            head_trigger_bars += int(row.get("head_trigger_bars") or 0)

        funding_sources.discard("not_applicable_no_official_candle_data")
        funding_source = (
            ";".join(sorted(funding_sources))
            if funding_sources else "not_applicable_no_official_candle_data"
        )
        data_status = (
            "NO_OFFICIAL_CANDLE_DATA" if coverage["candle_rows"] == 0
            else "PARTIAL_CANDLE_COVERAGE"
            if coverage["requested_window_coverage_pct"] < 100
            else "OK"
        )
        per_symbol_rows.append({
            "symbol": symbol,
            **metrics,
            "head_trigger_bars": head_trigger_bars,
            "model_trigger_bars": model_counts,
            "conflict_bars": conflict_bars,
            "multi_trigger_bars": multi_trigger_bars,
            "same_bar_conflict_trades": (
                int(valid.loc[valid.symbol == symbol, "same_bar_conflict"].sum())
                if not valid.empty and "same_bar_conflict" in valid else 0
            ),
            "candle_source": ";".join(sorted(candle_sources)) if candle_sources else "unknown",
            "missing_minutes": missing_minutes,
            "missing_interval_count": missing_interval_count,
            "missing_intervals": missing_intervals,
            "funding_source": funding_source,
            "funding_rows": funding_rows,
            "funding_actual_start": min(funding_starts) if funding_starts else None,
            "funding_actual_end": max(funding_ends) if funding_ends else None,
            "funding_max_gap_hours": max(funding_max_gaps) if funding_max_gaps else None,
            "data_status": data_status,
            **coverage,
        })
        quality_rows.append({
            "symbol": symbol,
            "data_status": data_status,
            **coverage,
            "candle_source": ";".join(sorted(candle_sources)) if candle_sources else "unknown",
            "missing_minutes": missing_minutes,
            "missing_interval_count": missing_interval_count,
            "missing_intervals_json": json.dumps(missing_intervals, separators=(",", ":")),
            "funding_source": funding_source,
            "funding_rows": funding_rows,
            "funding_actual_start": min(funding_starts) if funding_starts else None,
            "funding_actual_end": max(funding_ends) if funding_ends else None,
            "funding_max_gap_hours": max(funding_max_gaps) if funding_max_gaps else None,
            "funding_worst_first_gap_hours": max(funding_first_gaps) if funding_first_gaps else None,
            "funding_worst_last_gap_hours": max(funding_last_gaps) if funding_last_gaps else None,
            "batches_with_data": sum(
                1 for row in group
                if int((row.get("candle_quality") or {}).get("rows") or 0) > 0
            ),
            "batches_total": len(group),
        })

    per_symbol = pd.DataFrame(per_symbol_rows)
    per_symbol.to_csv(out / "head_per_symbol_results.csv", index=False)
    data_quality = pd.DataFrame(quality_rows)
    data_quality.to_csv(out / "head_data_quality.csv", index=False)

    overall = _aggregate_metrics(all_trades)
    overall.update({
        "same_bar_conflict_trades": (
            int(valid.same_bar_conflict.sum())
            if not valid.empty and "same_bar_conflict" in valid else 0
        ),
        "conflict_bars": (
            int(trigger_audit.same_bar_conflict.sum())
            if not trigger_audit.empty and "same_bar_conflict" in trigger_audit else 0
        ),
        "multi_trigger_bars": (
            int((pd.to_numeric(trigger_audit.trigger_count, errors="coerce") > 1).sum())
            if not trigger_audit.empty and "trigger_count" in trigger_audit else 0
        ),
        "trade_stream_not_portfolio": True,
    })
    yearly, symbol_yearly = _year_tables(valid)
    yearly.to_csv(out / "head_yearly_trade_stream.csv", index=False)
    symbol_yearly.to_csv(out / "head_symbol_yearly_results.csv", index=False)
    attribution = _model_attribution(valid, trigger_audit, expected_symbols)
    attribution.to_csv(out / "head_model_attribution.csv", index=False)

    report = {
        "engine": "HEAD",
        "logic": "OR: any one of M6/M8/M12/M14/M15 triggers; no voting or confirmation",
        "same_bar_policy": (
            "Same-direction triggers are coalesced into one entry. If opposite "
            "directions fire on the same completed bar, deterministic priority "
            "M6 > M8 > M14 > M12 > M15 selects the side and source; the conflict "
            "is logged. Priority does not add a confirmation filter."
        ),
        "timeframe": "4h",
        "requested_window": [args.expected_start, args.expected_end],
        "batches": [{"start_inclusive": s, "end_exclusive": e} for s, e in windows],
        "expected_symbols": expected_symbols,
        "completed_symbols": expected_symbols,
        "all_symbols_completed": True,
        "per_symbol_results": per_symbol_rows,
        "aggregate_trade_stream_diagnostic_not_portfolio": overall,
        "yearly_trade_stream": yearly.to_dict("records"),
        "model_attribution_file": "head_model_attribution.csv",
        "data_quality_file": "head_data_quality.csv",
        "caveat": (
            "Cross-symbol trade-stream metrics are diagnostics, not portfolio "
            "returns. No capital allocation, margin, concurrent exposure or "
            "portfolio sizing model is applied. DATA_GAP and END_OF_SAMPLE rows "
            "remain in the complete audit ledger and are excluded from all "
            "performance metrics. Candle coverage includes pre-listing periods; "
            "listed-span coverage is reported separately."
        ),
    }
    (out / "HEAD_FIVE_YEAR_RESULTS.json").write_text(
        json.dumps(report, indent=2, default=str)
    )

    lines = [
        "# HEAD — five-model OR engine cumulative backtest",
        "",
        "Any one of M6, M8, M12, M14 or M15 can trigger an entry; there is no voting, consensus or added confirmation.",
        "Same-direction triggers are coalesced. Opposing same-bar triggers use deterministic priority M6 > M8 > M14 > M12 > M15 and are logged.",
        "",
        f"Requested window: {args.expected_start} to {args.expected_end} (end exclusive)",
        f"Completed date batches: {len(windows)}",
        "Timeframe: 4h",
        "Execution costs: 5 bps fee + 2 bps slippage per side",
        "",
        "## Per-symbol results",
        "",
        "| Symbol | Trades | Wins/Losses | PF | Net bps | Net-R | Win rate | Max DD | Window coverage | Listed-span coverage | Actual data dates |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in per_symbol_rows:
        dates = (
            f"{row['actual_data_start']} to {row['actual_data_end_exclusive']}"
            if row["actual_data_start"] else "No official candles"
        )
        lines.append(
            f"| {row['symbol']} | {row['trades']} | {row['wins']}/{row['losses']} | "
            f"{row['profit_factor']} | {row['net_bps']} | {row['net_R']} | "
            f"{row['win_rate_pct']}% | {row['max_drawdown_pct']}% | "
            f"{row['requested_window_coverage_pct']}% | "
            f"{row['listed_span_coverage_pct']}% | {dates} |"
        )
    lines += [
        "",
        "## Official candle and funding coverage",
        "",
        "| Symbol | Candle source | Candle coverage | Funding source | Funding rows | Funding actual range | Funding max gap (h) | DATA_GAP | END_OF_SAMPLE |",
        "|---|---|---:|---|---:|---|---:|---:|---:|",
    ]
    for row in per_symbol_rows:
        funding_range = (
            f"{row['funding_actual_start']} to {row['funding_actual_end']}"
            if row.get("funding_actual_start") and row.get("funding_actual_end")
            else "No official funding rows"
        )
        lines.append(
            f"| {row['symbol']} | {row['candle_source']} | "
            f"{row['requested_window_coverage_pct']}% | {row['funding_source']} | "
            f"{row['funding_rows']} | {funding_range} | "
            f"{row['funding_max_gap_hours']} | {row['data_gap_trades']} | "
            f"{row['end_of_sample_trades']} |"
        )
    lines += ["", "## Official candle gaps"]
    gap_lines = []
    for row in per_symbol_rows:
        for gap in row.get("missing_intervals", []):
            gap_lines.append(
                f"- {row['symbol']}: {gap['start']} to {gap['end']} "
                f"({gap['minutes']} missing minutes; batch "
                f"{gap['batch_start']} to {gap['batch_end']})"
            )
    lines += gap_lines if gap_lines else ["- No missing 1-minute candle intervals in the requested window."]
    lines += [
        "",
        "## Combined trade-stream diagnostic (not portfolio return)",
        f"- Valid trades: {overall.get('trades')}",
        f"- DATA_GAP audit rows: {overall.get('data_gap_trades')}",
        f"- END_OF_SAMPLE audit rows: {overall.get('end_of_sample_trades')}",
        f"- Wins / losses: {overall.get('wins')} / {overall.get('losses')}",
        f"- Win rate: {overall.get('win_rate_pct')}%",
        f"- Profit factor: {overall.get('profit_factor')}",
        f"- Net bps: {overall.get('net_bps')}",
        f"- Net-R: {overall.get('net_R')}",
        f"- Fixed-risk max drawdown: {overall.get('max_drawdown_pct')}%",
        f"- Same-bar conflict bars: {overall.get('conflict_bars')}",
        f"- Same-bar conflict trades: {overall.get('same_bar_conflict_trades')}",
        "",
        "## Year-wise trade-stream performance",
        "",
        "| Year | Trades | PF | Net bps | Net-R | Win rate | Max DD |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in yearly.to_dict("records"):
        lines.append(
            f"| {row['year']} | {row['trades']} | {row['profit_factor']} | "
            f"{row['net_bps']} | {row['net_R']} | {row['win_rate_pct']}% | "
            f"{row['max_drawdown_pct']}% |"
        )
    lines += [
        "",
        "## Source-model trigger and trade attribution",
        "",
        "See head_model_attribution.csv for trigger bars, selected bars, trades, PF, net bps and net-R by symbol and source model.",
        "",
        "## Data and audit files",
        "- head_data_quality.csv — official candle/funding sources, actual dates, requested-window and listed-span coverage",
        "- head_complete_trade_ledger.csv — all trade and audit records",
        "- head_valid_trade_ledger.csv — performance-eligible trades only",
        "- head_trigger_audit_all_symbols.csv — trigger and same-bar conflict audit",
        "- head_yearly_trade_stream.csv — annual combined trade-stream metrics",
        "- head_symbol_yearly_results.csv — annual metrics by symbol",
        "- head_model_attribution.csv — trigger and selected-trade attribution",
        "",
        "Cross-symbol metrics are not portfolio returns. No capital allocation, margin, concurrency or exposure model is applied. DATA_GAP and END_OF_SAMPLE rows remain in the complete audit ledger but are excluded from performance metrics.",
    ]
    (out / "HEAD_FIVE_YEAR_RESULTS.md").write_text("\n".join(lines) + "\n")
    print(
        f"HEAD CUMULATIVE AGGREGATE batches={len(windows)} "
        f"symbols={len(expected_symbols)} trades={overall.get('trades')} "
        f"PF={overall.get('profit_factor')} net_bps={overall.get('net_bps')}",
        flush=True,
    )


if __name__ == "__main__":
    main()

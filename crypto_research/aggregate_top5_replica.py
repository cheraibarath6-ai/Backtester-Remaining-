from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

INVALID = {"DATA_GAP", "END_OF_SAMPLE"}


def _read_all(root: Path, filename: str) -> pd.DataFrame:
    parts = []
    for path in sorted(root.rglob(filename)):
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if not frame.empty:
            frame["artifact_source"] = str(path.parent)
            parts.append(frame)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _metrics(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    rows = []
    for key, all_rows in frame.groupby(keys, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        valid = all_rows.loc[~all_rows.exit_reason.isin(INVALID)].copy()
        net = pd.to_numeric(valid.net_bps, errors="coerce").fillna(0.0)
        net_r = pd.to_numeric(valid.net_R, errors="coerce").fillna(0.0)
        gross = pd.to_numeric(valid.gross_price_move_bps, errors="coerce").fillna(0.0)
        fees = pd.to_numeric(valid.fees_pct, errors="coerce").fillna(0.0) * 100.0
        slip = pd.to_numeric(valid.slippage_cost_pct, errors="coerce").fillna(0.0) * 100.0
        funding = pd.to_numeric(valid.funding_cost_pct, errors="coerce").fillna(0.0) * 100.0
        costs = fees + slip + funding
        gp = float(net[net > 0].sum())
        gl = abs(float(net[net < 0].sum()))
        gp_r = float(net_r[net_r > 0].sum())
        gl_r = abs(float(net_r[net_r < 0].sum()))
        wins = int((net > 0).sum())
        row = dict(zip(keys, key))
        positive_move = float(gross.clip(lower=0).sum())
        row.update({
            "trades": int(len(valid)),
            "audit_data_gap": int(all_rows.exit_reason.eq("DATA_GAP").sum()),
            "audit_end_of_sample": int(all_rows.exit_reason.eq("END_OF_SAMPLE").sum()),
            "win_rate_pct": round(100.0 * wins / len(valid), 3) if len(valid) else None,
            "net_pf_bps": round(gp / gl, 5) if gl else None,
            "net_pf_R": round(gp_r / gl_r, 5) if gl_r else None,
            "net_bps": round(float(net.sum()), 3),
            "net_R": round(float(net_r.sum()), 4),
            "gross_price_move_bps": round(float(gross.sum()), 3),
            "gross_positive_move_bps": round(positive_move, 3),
            "fees_bps": round(float(fees.sum()), 3),
            "slippage_bps": round(float(slip.sum()), 3),
            "funding_bps": round(float(funding.sum()), 3),
            "total_cost_bps": round(float(costs.sum()), 3),
            "cost_share_of_gross_positive_pct": round(float(costs.sum() / positive_move * 100), 3)
                if positive_move > 0 else None,
            "avg_net_bps_per_trade": round(float(net.mean()), 4) if len(valid) else None,
            "avg_holding_minutes": round(float(pd.to_numeric(valid.holding_minutes, errors="coerce").mean()), 3)
                if len(valid) else None,
            "median_holding_minutes": round(float(pd.to_numeric(valid.holding_minutes, errors="coerce").median()), 3)
                if len(valid) else None,
        })
        rows.append(row)
    return pd.DataFrame(rows)


def _fmt(value, digits=2):
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.{digits}f}"


def main():
    parser = argparse.ArgumentParser(description="Aggregate independent top-five multi-factor replica backtests")
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="top5_replica_results")
    args = parser.parse_args()
    root, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = _read_all(root, "screen_results.csv")
    yearly_rows = _read_all(root, "screen_yearly.csv")
    trades = _read_all(root, "trade_ledger.csv")
    quality = []
    for path in sorted(root.rglob("run_summary.json")):
        try:
            quality.append(json.loads(path.read_text()))
        except Exception as exc:
            quality.append({"source": str(path), "error": str(exc)})

    if results.empty or trades.empty:
        (out / "REPLICA_STATUS.md").write_text(
            "# Top-five multi-factor replicate status\n\n"
            "No complete result/trade-ledger set was available to aggregate. "
            "Inspect symbol jobs and artifacts before interpreting this run.\n"
        )
        return

    results.to_csv(out / "per_symbol_variant_results.csv", index=False)
    yearly_rows.to_csv(out / "per_symbol_yearly_results.csv", index=False)
    trades.to_csv(out / "complete_trade_ledger.csv", index=False)
    (out / "data_quality_and_run_metadata.json").write_text(json.dumps(quality, indent=2, default=str))

    all_metrics = _metrics(trades, ["model", "variant", "timeframe"])
    yearly_trades = trades.copy()
    yearly_trades["year"] = pd.to_datetime(yearly_trades.exit_time, utc=True).dt.year
    year_metrics = _metrics(yearly_trades, ["model", "variant", "timeframe", "year"])
    all_metrics.to_csv(out / "variant_trade_stream_summary.csv", index=False)
    year_metrics.to_csv(out / "variant_yearly_trade_stream_summary.csv", index=False)

    retention_rows = []
    for (model, variant, timeframe), group in results.groupby(["model", "variant", "timeframe"], dropna=False):
        completed = group.loc[group.status.eq("COMPLETED")]
        base_n = pd.to_numeric(completed.baseline_trades, errors="coerce").fillna(0).sum()
        count_n = pd.to_numeric(completed.trades, errors="coerce").fillna(0).sum()
        base_overlap = pd.to_numeric(completed.baseline_entry_retention_pct, errors="coerce")
        weights = pd.to_numeric(completed.baseline_trades, errors="coerce").fillna(0)
        overlap = float((base_overlap.fillna(0) * weights).sum() / weights.sum()) if weights.sum() else None
        rejected_bps = pd.to_numeric(completed.rejected_baseline_net_bps, errors="coerce").fillna(0).sum()
        rejected_count = pd.to_numeric(completed.rejected_baseline_entries, errors="coerce").fillna(0).sum()
        retention_rows.append({
            "model": model, "variant": variant, "timeframe": timeframe,
            "baseline_trades": int(base_n), "candidate_trades_from_results": int(count_n),
            "trade_count_retention_pct": round(100 * count_n / base_n, 3) if base_n else None,
            "baseline_entry_retention_pct_weighted": round(overlap, 3) if overlap is not None else None,
            "rejected_baseline_entries": int(rejected_count),
            "rejected_baseline_net_bps_counterfactual": round(float(rejected_bps), 3),
            "completed_symbol_jobs": int(len(completed)),
            "noncompleted_symbol_jobs": int(len(group) - len(completed)),
        })
    retention = pd.DataFrame(retention_rows)
    summary = all_metrics.merge(retention, on=["model", "variant", "timeframe"], how="left")
    summary.to_csv(out / "top5_replica_comparison.csv", index=False)

    lines = [
        "# Top-five independent multi-factor replicate results",
        "",
        "One new multi-factor replicate was tested for each of M6, M8, M12, M14 and M15. "
        "Each strategy was run independently at 4h; there is no cross-model voting or combined portfolio.",
        "",
        "The five were selected by 4h expanding walk-forward median PF rank: M6, M8, M14, M12 and M15. "
        "M12 and M15 are research candidates, not profitable approvals; they were retained to test whether "
        "their documented exit/regime weaknesses can be improved. M10 was not included because its 4h "
        "walk-forward median PF was 0.896 and net result was -1,858 bps.",
        "",
        "## Variant comparison",
        "",
        "| Model | Variant | Trades | Count retention | Baseline-entry overlap | Net PF | Net bps | Net-R | Cost share |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.sort_values(["model", "variant"]).to_dict("records"):
        lines.append(
            f"| {row['model']} | {row['variant']} | {int(row['trades'])} | "
            f"{_fmt(row.get('trade_count_retention_pct'))}% | "
            f"{_fmt(row.get('baseline_entry_retention_pct_weighted'))}% | "
            f"{_fmt(row.get('net_pf_bps'), 3)} | {_fmt(row.get('net_bps'))} | "
            f"{_fmt(row.get('net_R'), 2)} | {_fmt(row.get('cost_share_of_gross_positive_pct'))}% |"
        )

    lines += [
        "",
        "## Yearwise trade-stream results",
        "",
        "| Model | Variant | Year | Trades | Net PF | Net bps | Net-R |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in year_metrics.sort_values(["model", "variant", "year"]).to_dict("records"):
        lines.append(
            f"| {row['model']} | {row['variant']} | {int(row['year'])} | {int(row['trades'])} | "
            f"{_fmt(row.get('net_pf_bps'), 3)} | {_fmt(row.get('net_bps'))} | {_fmt(row.get('net_R'), 2)} |"
        )

    lines += [
        "",
        "## Interpretation and safeguards",
        "",
        "- Per-symbol CSVs preserve symbol-specific raw price points; there is no universal crypto pip.",
        "- Cross-symbol trade-stream sums and PF are diagnostics, not capital-weighted portfolio returns.",
        "- DATA_GAP and END_OF_SAMPLE records are retained in the trade ledger but excluded from scored metrics.",
        "- Official Binance USD-M funding must pass the existing fail-closed source and maximum-gap gate for every symbol.",
        "- Development is 2021-2024, 2025 is validation, and 2026 is retrospective audit only.",
        "- This new replicate is a retrospective research experiment; it is not a pristine forward holdout and must not replace the frozen holdout definitions.",
        "- Compare the R2 variant against BASELINE and earlier tested profiles. Do not select on full-period PF alone.",
        "",
        "## Files",
        "",
        "- per_symbol_variant_results.csv: complete per-symbol metrics and retention/counterfactual outcomes.",
        "- per_symbol_yearly_results.csv: yearwise per-symbol metrics.",
        "- complete_trade_ledger.csv: all trade records including DATA_GAP and END_OF_SAMPLE audit rows.",
        "- variant_trade_stream_summary.csv: same-model cross-symbol trade-stream diagnostics.",
        "- variant_yearly_trade_stream_summary.csv: yearwise same-model trade-stream diagnostics.",
        "- data_quality_and_run_metadata.json: candle/funding source and quality checks.",
    ]
    (out / "TOP5_MULTI_FACTOR_REPLICA_RESULTS_2026-11-14.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

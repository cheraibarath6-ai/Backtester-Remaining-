from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


MODEL_SCOPE = {"M6", "M7", "M8", "M10", "M12", "M13", "M14", "M15"}


def _load(root: Path, filename: str) -> pd.DataFrame:
    parts = []
    for path in root.rglob(filename):
        try:
            frame = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            continue
        if not frame.empty:
            parts.append(frame)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate frozen independent eight-engine forward holdout")
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="eight_engine_forward_holdout_results")
    args = parser.parse_args()
    root, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = _load(root, "forward_holdout_results.csv")
    ledger = _load(root, "forward_holdout_trade_ledger.csv")
    summaries = []
    for path in root.rglob("run_summary.json"):
        try:
            summaries.append(json.loads(path.read_text()))
        except Exception:
            continue

    if not results.empty:
        unexpected = set(results.model.dropna().astype(str)) - MODEL_SCOPE
        if unexpected:
            raise ValueError(f"Out-of-scope model rows found: {sorted(unexpected)}")

    results.to_csv(out / "all_forward_holdout_results.csv", index=False)
    ledger.to_csv(out / "all_forward_holdout_trade_ledger.csv", index=False)
    (out / "data_and_run_quality.json").write_text(json.dumps(summaries, indent=2, default=str))

    aggregate_rows = []
    if not results.empty:
        completed = results.loc[results.status.eq("COMPLETED")].copy()
        for (model, timeframe, variant, role), group in completed.groupby(
            ["model", "timeframe", "variant", "role"], dropna=False
        ):
            def median(column):
                values = pd.to_numeric(group.get(column, pd.Series(dtype=float)), errors="coerce").dropna()
                return round(float(values.median()), 4) if not values.empty else None
            aggregate_rows.append({
                "model": model,
                "timeframe": timeframe,
                "variant": variant,
                "role": role,
                "completed_symbol_streams": int(len(group)),
                "total_valid_trades_across_streams": int(pd.to_numeric(group.get("trades", 0), errors="coerce").fillna(0).sum()),
                "trade_stream_net_bps_sum_not_portfolio": round(float(pd.to_numeric(group.get("net_bps", 0), errors="coerce").fillna(0).sum()), 3),
                "median_symbol_net_PF": median("profit_factor"),
                "median_symbol_R_PF": median("profit_factor_r"),
                "median_symbol_net_R": median("net_R"),
                "median_symbol_win_rate_pct": median("win_rate_pct"),
                "median_symbol_max_drawdown_pct": median("max_drawdown_pct"),
                "median_symbol_time_exposure_pct": median("time_exposure_pct"),
                "positive_net_bps_symbols": int((pd.to_numeric(group.get("net_bps", 0), errors="coerce") > 0).sum()),
                "positive_PF_symbols": int((pd.to_numeric(group.get("profit_factor", 0), errors="coerce") > 1).sum()),
                "note": "Independent symbol-stream summary; not a portfolio equity curve.",
            })
    aggregate = pd.DataFrame(aggregate_rows)
    aggregate.to_csv(out / "forward_holdout_symbol_stream_summary.csv", index=False)

    comparison_rows = []
    if not results.empty:
        for (model, timeframe, symbol), group in results.groupby(["model", "timeframe", "symbol"]):
            baseline = group.loc[(group.variant == "BASELINE") & group.status.eq("COMPLETED")]
            candidate = group.loc[(group.role == "FROZEN_CANDIDATE") & group.status.eq("COMPLETED")]
            if baseline.empty or candidate.empty:
                continue
            b, c = baseline.iloc[0], candidate.iloc[0]
            comparison_rows.append({
                "model": model,
                "timeframe": timeframe,
                "symbol": symbol,
                "baseline_trades": b.get("trades"),
                "candidate_variant": c.variant,
                "candidate_trades": c.get("trades"),
                "trade_count_delta": int(c.get("trades", 0) - b.get("trades", 0)),
                "baseline_net_bps": b.get("net_bps"),
                "candidate_net_bps": c.get("net_bps"),
                "delta_net_bps": round(float(c.get("net_bps", 0) - b.get("net_bps", 0)), 3),
                "baseline_net_PF": b.get("profit_factor"),
                "candidate_net_PF": c.get("profit_factor"),
                "delta_net_PF": round(float(c.get("profit_factor", 0) - b.get("profit_factor", 0)), 4),
                "baseline_net_R": b.get("net_R"),
                "candidate_net_R": c.get("net_R"),
                "delta_net_R": round(float(c.get("net_R", 0) - b.get("net_R", 0)), 4),
            })
    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(out / "candidate_vs_baseline_by_symbol.csv", index=False)

    status = (
        results.status.value_counts(dropna=False).rename_axis("status").reset_index(name="rows")
        if not results.empty else pd.DataFrame()
    )
    status.to_csv(out / "status_counts.csv", index=False)

    lines = [
        "# Frozen eight-engine forward holdout",
        "",
        f"- Result rows: {len(results)}",
        f"- Trade-ledger rows: {len(ledger)}",
        f"- Models: {', '.join(sorted(set(results.model.dropna().astype(str)))) if not results.empty else 'none'}",
        "",
        "Only the pre-frozen variants and their baseline controls are evaluated. No parameter selection, tuning, model combination or voting is performed on holdout data.",
        "The holdout starts 2026-11-01 and requires at least 30 complete UTC days. Current UTC day is excluded. Official Binance Vision daily 1m archives must have verified checksums; funding must come from official Binance sources with no settlement gap over 8.5 hours.",
        "DATA_GAP and END_OF_SAMPLE records remain in the audit ledger and are excluded from scored metrics.",
        "Aggregate bps and net-R are trade-stream diagnostics across independent symbol streams, not portfolio returns. Per-symbol rows and baseline comparisons are retained.",
    ]
    (out / "FORWARD_HOLDOUT_REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()

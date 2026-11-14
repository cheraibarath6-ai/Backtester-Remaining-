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

    parser = argparse.ArgumentParser(description="Aggregate independent eight-engine walk-forward diagnostics")
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="eight_engine_walkforward_results")
    args = parser.parse_args()

    root, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = _load(root, "walkforward_results.csv")
    candidates = _load(root, "candidate_training_scores.csv")
    ledger = _load(root, "walkforward_trade_ledger.csv")
    summaries = []
    for path in root.rglob("run_summary.json"):
        try:
            summaries.append(json.loads(path.read_text()))
        except Exception:
            continue

    if not results.empty:
        unexpected = set(results.model.dropna().astype(str)) - MODEL_SCOPE
        if unexpected:
            raise ValueError(f"Out-of-scope models found in walk-forward artifacts: {sorted(unexpected)}")

    results.to_csv(out / "all_walkforward_results.csv", index=False)
    candidates.to_csv(out / "all_candidate_training_scores.csv", index=False)
    ledger.to_csv(out / "all_walkforward_trade_ledger.csv", index=False)
    (out / "data_and_run_quality.json").write_text(json.dumps(summaries, indent=2, default=str))

    rows = []
    if not results.empty:
        for (model, timeframe, year, label), group in results.groupby(
            ["model", "timeframe", "year", "period_label"], dropna=False
        ):
            completed = group.loc[group.status.eq("COMPLETED")].copy()
            def med(column):
                if column not in completed:
                    return None
                values = pd.to_numeric(completed[column], errors="coerce").dropna()
                return round(float(values.median()), 4) if not values.empty else None
            rows.append({
                "model": model,
                "timeframe": timeframe,
                "year": int(year),
                "period_label": label,
                "symbol_streams": int(len(group)),
                "completed_symbol_streams": int(len(completed)),
                "positive_net_R_symbols": int((pd.to_numeric(completed.get("test_net_R", pd.Series(dtype=float)), errors="coerce") > 0).sum()),
                "positive_net_bps_PF_symbols": int((pd.to_numeric(completed.get("test_profit_factor", pd.Series(dtype=float)), errors="coerce") > 1).sum()),
                "median_test_trades": med("test_trades"),
                "median_test_net_bps": med("test_net_bps"),
                "median_test_net_R": med("test_net_R"),
                "median_test_net_PF": med("test_profit_factor"),
                "median_test_R_PF": med("test_profit_factor_r"),
                "median_test_max_drawdown_pct": med("test_max_drawdown_pct"),
                "median_baseline_entry_retention_pct": med("test_retention_baseline_entry_retention_pct"),
                "median_trade_count_retention_pct": med("test_retention_trade_count_retention_pct"),
                "note": "Symbol-stream medians only; not a portfolio return or portfolio drawdown.",
            })
    summary = pd.DataFrame(rows)
    summary.to_csv(out / "walkforward_symbol_stream_summary.csv", index=False)

    status = (
        results.status.value_counts(dropna=False).rename_axis("status").reset_index(name="rows")
        if not results.empty else pd.DataFrame()
    )
    status.to_csv(out / "status_counts.csv", index=False)

    lines = [
        "# Independent eight-engine expanding walk-forward",
        "",
        f"- Result rows: {len(results)}",
        f"- Candidate training-score rows: {len(candidates)}",
        f"- Selected test-trade ledger rows: {len(ledger)}",
        f"- Models: {', '.join(sorted(set(results.model.dropna().astype(str)))) if not results.empty else 'none'}",
        "",
        "Each model selects only from its own predeclared candidate profiles. Selection uses completed training trades, maximizes net-R, and requires at least 80% training baseline-entry overlap and 80% total trade-count retention for non-baseline candidates.",
        "The current candidate profiles were discovered after earlier historical sweeps, so this is a retrospective expanding-window diagnostic, not a pristine untouched holdout.",
        "2026 is retrospective only. DATA_GAP and END_OF_SAMPLE records remain in the ledger and are excluded from scored metrics.",
        "Cross-symbol summaries are symbol-stream diagnostics, not portfolio returns.",
    ]
    (out / "WALKFORWARD_REPORT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)


if __name__ == "__main__":
    main()

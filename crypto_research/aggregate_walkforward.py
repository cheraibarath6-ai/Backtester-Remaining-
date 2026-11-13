from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _load(root: Path, name: str) -> pd.DataFrame:
    parts = [pd.read_csv(path) for path in root.rglob(name)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main():
    parser = argparse.ArgumentParser(description="Aggregate independent M6/M11 walk-forward artifacts")
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="walkforward_results")
    args = parser.parse_args()
    root, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = _load(root, "walkforward_results.csv")
    candidates = _load(root, "candidate_training_scores.csv")
    ledgers = _load(root, "walkforward_trade_ledger.csv")
    summaries = []
    if not results.empty:
        for (model, year, period_label), group in results.groupby(
            ["model", "year", "period_label"], dropna=False
        ):
            completed = group.loc[group.status.eq("COMPLETED")].copy()
            valid_net = pd.to_numeric(completed.get("test_net_R"), errors="coerce")
            valid_pf = pd.to_numeric(completed.get("test_profit_factor_r"), errors="coerce")
            summaries.append({
                "model": model,
                "year": int(year),
                "period_label": period_label,
                "symbol_streams": int(len(group)),
                "completed_symbol_streams": int(len(completed)),
                "positive_net_R_symbols": int((valid_net > 0).sum()),
                "positive_R_PF_symbols": int((valid_pf > 1).sum()),
                "median_symbol_net_R": round(float(valid_net.median()), 3) if valid_net.notna().any() else None,
                "median_symbol_R_PF": round(float(valid_pf.median()), 4) if valid_pf.notna().any() else None,
                "median_symbol_max_drawdown_pct": round(
                    float(pd.to_numeric(completed.get("test_max_drawdown_pct"), errors="coerce").median()), 3
                ) if not completed.empty else None,
                "note": "Symbol-stream diagnostics only; no cross-symbol return or portfolio drawdown is calculated.",
            })
    summary = pd.DataFrame(summaries)
    results.to_csv(out / "all_walkforward_results.csv", index=False)
    candidates.to_csv(out / "all_candidate_training_scores.csv", index=False)
    ledgers.to_csv(out / "all_walkforward_trade_ledger.csv", index=False)
    summary.to_csv(out / "symbol_consistency_summary.csv", index=False)

    status = (
        results.status.value_counts(dropna=False).rename_axis("status").reset_index(name="rows")
        if not results.empty else pd.DataFrame()
    )
    status.to_csv(out / "status_counts.csv", index=False)

    report = [
        "# Independent M6/M11 Expanding-Window Walk-Forward",
        "",
        f"- Symbol result rows: {len(results)}",
        f"- Candidate training-score rows: {len(candidates)}",
        f"- Test trade-ledger rows: {len(ledgers)}",
        f"- DATA_GAP exits retained in ledger: {int(ledgers.exit_reason.eq('DATA_GAP').sum()) if not ledgers.empty and 'exit_reason' in ledgers else 0}",
        f"- END_OF_SAMPLE rows retained in ledger: {int(ledgers.exit_reason.eq('END_OF_SAMPLE').sum()) if not ledgers.empty and 'exit_reason' in ledgers else 0}",
        "",
        "Each symbol and model is evaluated independently. The selector uses only completed trades before each test-year boundary; net-R is the primary ranking key and R-PF is only a tie-breaker. No M3, ensemble, or cross-model inputs are used.",
        "",
        "Annual tests start flat at the UTC year boundary. New signals are disabled at/after the exclusive year end, while trades entered within the year may use their predeclared holding horizon to exit. DATA_GAP and END_OF_SAMPLE records are visible in audit ledgers but excluded from performance metrics.",
        "",
        "2026 is labelled retrospective audit evidence, not a pristine holdout. 2023-2025 are expanding-window tests from the predeclared within-model profile grids; the 2025 selector uses only 2021-2024 data.",
        "",
        "Cross-symbol summaries show medians and counts of positive symbol streams only. They are not portfolio returns or portfolio drawdowns.",
        "",
        "## Symbol consistency",
        "",
        summary.to_markdown(index=False) if not summary.empty else "No completed symbol streams.",
        "",
        "## Status counts",
        "",
        status.to_markdown(index=False) if not status.empty else "No status rows.",
    ]
    (out / "WALK_FORWARD_REPORT.md").write_text("\n".join(report) + "\n")
    print(f"Aggregated {len(results)} symbol/year rows, {len(candidates)} candidate scores, {len(ledgers)} trades.")


if __name__ == "__main__":
    main()

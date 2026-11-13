from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


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


def _aggregate_trade_rows(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    keys = ["model", "variant", "timeframe"]
    for key, frame in trades.groupby(keys, dropna=False):
        net = pd.to_numeric(frame.net_bps, errors="coerce").fillna(0)
        gross_profit = float(net[net > 0].sum())
        gross_loss = abs(float(net[net <= 0].sum()))
        wins = int((net > 0).sum())
        rows.append({
            "model": key[0],
            "variant": key[1],
            "timeframe": key[2],
            "symbol_streams": int(frame.symbol.nunique()),
            "trades": int(len(frame)),
            "wins": wins,
            "losses": int(len(frame) - wins),
            "win_rate_pct": round(100 * wins / len(frame), 2),
            "aggregate_trade_pf": round(gross_profit / gross_loss, 4) if gross_loss else None,
            "net_bps_sum": round(float(net.sum()), 2),
            "net_R_sum": round(float(pd.to_numeric(frame.net_R, errors="coerce").fillna(0).sum()), 3),
            "avg_holding_minutes": round(float(pd.to_numeric(frame.holding_minutes, errors="coerce").mean()), 2),
            "note": "Trade-level aggregation across symbols; not a capital-weighted portfolio return or drawdown",
        })
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Aggregate independent model screening artifacts")
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="independent_engine_results")
    args = parser.parse_args()
    root = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = _read_all(root, "screen_results.csv")
    yearly = _read_all(root, "screen_yearly.csv")
    trades = _read_all(root, "trade_ledger.csv")
    if not results.empty:
        results.to_csv(out / "all_screen_results.csv", index=False)
    if not yearly.empty:
        yearly.to_csv(out / "all_yearly_results.csv", index=False)
    if not trades.empty:
        trades.to_csv(out / "all_trade_ledger.csv", index=False)
        _aggregate_trade_rows(trades).to_csv(out / "same_model_cross_symbol_trade_summary.csv", index=False)

    metadata = []
    for path in sorted(root.rglob("run_summary.json")):
        try:
            metadata.append(json.loads(path.read_text()))
        except Exception as error:
            metadata.append({"source": str(path), "error": str(error)})
    (out / "data_and_run_quality.json").write_text(json.dumps(metadata, indent=2, default=str))

    eligible = pd.DataFrame()
    if not results.empty:
        eligible = results[
            (results.status == "COMPLETED")
            & (pd.to_numeric(results.trades, errors="coerce").fillna(0) >= 100)
            & (pd.to_numeric(results.profit_factor, errors="coerce") > 1.0)
            & (pd.to_numeric(results.net_R, errors="coerce") > 0)
        ].copy()
        eligible.to_csv(out / "initial_positive_candidates.csv", index=False)

    report = [
        "# Independent Core Engine Screening",
        "",
        "This is a first-pass baseline screen. It is not final selection or a deployment recommendation.",
        "",
        f"- Result rows: {len(results)}",
        f"- Yearly result rows: {len(yearly)}",
        f"- Trade ledger rows: {len(trades)}",
        f"- Initial positive candidates (PF > 1, net-R > 0, 100+ trades per stream): {len(eligible)}",
        "",
        "## Important interpretation",
        "",
        "- Each model is tested independently. Cross-symbol aggregation below is within the same model only.",
        "- same_model_cross_symbol_trade_summary.csv reports trade-level PF and net-R sums; it is not a capital-weighted portfolio return or drawdown.",
        "- Year 2021-2024 is development, 2025 is validation, and 2026 YTD is a later holdout slice. Do not optimise against the holdout.",
        "- M11 is marked data-gated if historical open-interest metrics are missing; no price-only OI proxy is substituted.",
        "- M3 is excluded and untouched.",
        "",
        "See the CSVs and data_and_run_quality.json for the full result ledger.",
    ]
    (out / "SCREENING_REPORT.md").write_text("\n".join(report) + "\n")
    print("\n".join(report), flush=True)


if __name__ == "__main__":
    main()

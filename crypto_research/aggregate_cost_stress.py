from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _risk_drawdown(frame: pd.DataFrame) -> float:
    ordered = frame.sort_values("exit_time")
    r = pd.to_numeric(ordered.net_R, errors="coerce").fillna(0.0)
    equity = 1.0 + r.cumsum() * 0.01
    peak = equity.cummax().clip(lower=1.0)
    return float(((equity / peak - 1.0).clip(lower=-1.0) * 100.0).min()) if len(equity) else 0.0


def _load(root: Path, filename: str) -> pd.DataFrame:
    parts = [pd.read_csv(path) for path in root.rglob(filename)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _summary(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    for key, all_rows in frame.groupby(keys, dropna=False):
        gaps = all_rows.exit_reason.eq("DATA_GAP") if "exit_reason" in all_rows else pd.Series(False, index=all_rows.index)
        censored = all_rows.exit_reason.eq("END_OF_SAMPLE") if "exit_reason" in all_rows else pd.Series(False, index=all_rows.index)
        data_gap = int(gaps.sum())
        end_of_sample = int(censored.sum())
        valid = all_rows.loc[~(gaps | censored)].copy()
        net = pd.to_numeric(valid.net_bps, errors="coerce").fillna(0.0)
        net_r = pd.to_numeric(valid.net_R, errors="coerce").fillna(0.0)
        positive, negative = net[net > 0].sum(), abs(net[net <= 0].sum())
        positive_r, negative_r = net_r[net_r > 0].sum(), abs(net_r[net_r < 0].sum())
        wins = int((net > 0).sum())
        dd = [_risk_drawdown(g) for _, g in valid.groupby("symbol")] if not valid.empty else []
        holding = pd.to_numeric(valid.holding_minutes, errors="coerce")
        row = dict(zip(keys, key if isinstance(key, tuple) else (key,)))
        row.update({
            "symbol_streams": int(valid.symbol.nunique()) if not valid.empty else 0,
            "trades": int(len(valid)),
            "total_trade_records": int(len(all_rows)),
            "data_gap_trades": data_gap,
            "end_of_sample_trades": end_of_sample,
            "win_rate_pct": round(100 * wins / len(valid), 2) if len(valid) else 0.0,
            "net_bps_pf": round(float(positive / negative), 4) if negative else None,
            "r_based_pf": round(float(positive_r / negative_r), 4) if negative_r else None,
            "net_bps_sum": round(float(net.sum()), 2),
            "net_R_sum": round(float(net_r.sum()), 3),
            "fixed_initial_equity_risk_return_pct_at_1pct": round(float(net_r.sum()), 3),
            "worst_symbol_max_drawdown_pct_at_1pct_risk": round(min(dd), 3) if dd else None,
            "avg_holding_minutes": round(float(holding.mean()), 2) if holding.notna().any() else None,
            "note": "Cross-symbol sums are not portfolio returns; DATA_GAP and END_OF_SAMPLE records remain in audit ledgers but are excluded from metrics",
        })
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Aggregate independent M6/M11 cost stress artifacts")
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="cost_stress_results")
    args = parser.parse_args()
    root, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = _load(root, "screen_results.csv")
    yearly = _load(root, "screen_yearly.csv")
    ledgers = _load(root, "trade_ledger.csv")
    monte_carlo = _load(root, "monte_carlo.csv")
    results.to_csv(out / "all_screen_results.csv", index=False)
    yearly.to_csv(out / "all_yearly_results.csv", index=False)
    monte_carlo.to_csv(out / "all_monte_carlo.csv", index=False)
    if not ledgers.empty:
        ledgers.to_csv(out / "all_trade_ledger.csv", index=False)
        keys = ["model", "variant", "timeframe", "cost_scenario", "fee_bps_per_side", "slippage_bps_per_side"]
        summary = _summary(ledgers, keys)
        summary.to_csv(out / "same_model_cross_symbol_cost_summary.csv", index=False)
        ledgers["year"] = pd.to_datetime(ledgers.exit_time, utc=True).dt.year
        yearly_summary = _summary(
            ledgers, keys + ["year"]
        )
        yearly_summary.to_csv(out / "same_model_cross_symbol_cost_yearly.csv", index=False)
    else:
        summary = pd.DataFrame()
        summary.to_csv(out / "same_model_cross_symbol_cost_summary.csv", index=False)
    status = results.status.value_counts(dropna=False).rename_axis("status").reset_index(name="rows") if not results.empty else pd.DataFrame()
    status.to_csv(out / "status_counts.csv", index=False)
    report = [
        "# M6/M11 Full Cost Re-execution",
        "",
        f"- Symbol result rows: {len(results)}",
        f"- Trade ledger rows: {len(ledgers)}",
        f"- DATA_GAP exits in ledger: {int(ledgers.exit_reason.eq('DATA_GAP').sum()) if not ledgers.empty and 'exit_reason' in ledgers else 0}",
        f"- END_OF_SAMPLE records in ledger: {int(ledgers.exit_reason.eq('END_OF_SAMPLE').sum()) if not ledgers.empty and 'exit_reason' in ledgers else 0}",
        f"- Monte Carlo symbol-stream rows: {len(monte_carlo)}",
        "",
        "Each cost scenario re-executes the OHLC path with altered fees and slippage; this is not simple ledger repricing.",
        "M6 and M11 remain separate strategies. Cross-symbol sums are not portfolio returns.",
        "Annual rows are fixed-parameter chronological diagnostics. 2026 is retrospective audit evidence, not a pristine holdout.",
        "M11 uses historical OI only; no liquidation proxy is used. M3 is untouched.",
    ]
    (out / "COST_STRESS_REPORT.md").write_text("\n".join(report) + "\n")
    print("\n".join(report), flush=True)


if __name__ == "__main__":
    main()

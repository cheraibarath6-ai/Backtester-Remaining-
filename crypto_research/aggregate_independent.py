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


def _risk_curve_metrics(frame: pd.DataFrame) -> dict:
    ordered = frame.sort_values("exit_time")
    net_r = pd.to_numeric(ordered.net_R, errors="coerce").fillna(0.0)
    cumulative = net_r.cumsum()
    peak = cumulative.cummax().clip(lower=0.0)
    drawdown_r = cumulative - peak
    risk_equity = 1.0 + cumulative * 0.01
    risk_peak = risk_equity.cummax().clip(lower=1.0)
    drawdown_pct = (risk_equity / risk_peak - 1.0).clip(lower=-1.0) * 100.0
    return {
        "max_drawdown_R": round(float(drawdown_r.min()), 3) if len(drawdown_r) else 0.0,
        "max_drawdown_pct_at_1pct_risk": round(float(drawdown_pct.min()), 3) if len(drawdown_pct) else 0.0,
        "risk_equity_ruined_at_1pct_risk": bool((risk_equity <= 0).any()),
    }


def _aggregate_trade_rows(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    rows = []
    keys = ["model", "variant", "timeframe"]
    for key, all_frame in trades.groupby(keys, dropna=False):
        gap_mask = all_frame.exit_reason.eq("DATA_GAP") if "exit_reason" in all_frame.columns else pd.Series(False, index=all_frame.index)
        eos_mask = all_frame.exit_reason.eq("END_OF_SAMPLE") if "exit_reason" in all_frame.columns else pd.Series(False, index=all_frame.index)
        data_gap_trades = int(gap_mask.sum())
        end_of_sample_trades = int(eos_mask.sum())
        frame = all_frame.loc[~(gap_mask | eos_mask)].copy()
        net = pd.to_numeric(frame.net_bps, errors="coerce").fillna(0.0)
        net_r = pd.to_numeric(frame.net_R, errors="coerce").fillna(0.0)
        gross_profit = float(net[net > 0].sum())
        gross_loss = abs(float(net[net <= 0].sum()))
        gross_profit_r = float(net_r[net_r > 0].sum())
        gross_loss_r = abs(float(net_r[net_r < 0].sum()))
        wins = int((net > 0).sum())
        symbol_drawdowns = []
        for symbol, symbol_frame in frame.groupby("symbol"):
            symbol_drawdowns.append({
                "symbol": symbol,
                **_risk_curve_metrics(symbol_frame),
            })
        dd_values = [x["max_drawdown_pct_at_1pct_risk"] for x in symbol_drawdowns]
        holding = pd.to_numeric(frame.holding_minutes, errors="coerce") if not frame.empty else pd.Series(dtype=float)
        rows.append({
            "model": key[0],
            "variant": key[1],
            "timeframe": key[2],
            "symbol_streams": int(frame.symbol.nunique()) if not frame.empty else 0,
            "trades": int(len(frame)),
            "total_trade_records": int(len(all_frame)),
            "data_gap_trades": data_gap_trades,
            "end_of_sample_trades": end_of_sample_trades,
            "wins": wins,
            "losses": int(len(frame) - wins),
            "win_rate_pct": round(100 * wins / len(frame), 2) if len(frame) else 0.0,
            "aggregate_trade_pf_bps": round(gross_profit / gross_loss, 4) if gross_loss else None,
            "aggregate_profit_factor_R": round(gross_profit_r / gross_loss_r, 4) if gross_loss_r else None,
            "net_bps_sum": round(float(net.sum()), 2),
            "net_R_sum": round(float(net_r.sum()), 3),
            "fixed_initial_equity_risk_return_pct_at_1pct": round(float(net_r.sum()), 3),
            "avg_trade_bps": round(float(net.mean()), 3) if len(frame) else None,
            "avg_holding_minutes": round(float(holding.mean()), 2) if holding.notna().any() else None,
            "median_holding_minutes": round(float(holding.median()), 2) if holding.notna().any() else None,
            "worst_symbol_max_drawdown_pct_at_1pct_risk": round(min(dd_values), 3) if dd_values else None,
            "median_symbol_max_drawdown_pct_at_1pct_risk": round(float(pd.Series(dd_values).median()), 3) if dd_values else None,
            "symbol_drawdowns_json": json.dumps(symbol_drawdowns, sort_keys=True),
            "note": "DATA_GAP and END_OF_SAMPLE records are retained in the ledger but excluded from performance metrics; cross-symbol sums are not a capital-weighted portfolio return or drawdown",
        })
    return pd.DataFrame(rows)


def _aggregate_yearly_trade_rows(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    frame = trades.copy()
    frame["year"] = pd.to_datetime(frame.exit_time, utc=True).dt.year
    rows = []
    for key, all_group in frame.groupby(["model", "variant", "timeframe", "year"], dropna=False):
        gap_mask = all_group.exit_reason.eq("DATA_GAP") if "exit_reason" in all_group.columns else pd.Series(False, index=all_group.index)
        eos_mask = all_group.exit_reason.eq("END_OF_SAMPLE") if "exit_reason" in all_group.columns else pd.Series(False, index=all_group.index)
        data_gap_trades = int(gap_mask.sum())
        end_of_sample_trades = int(eos_mask.sum())
        group = all_group.loc[~(gap_mask | eos_mask)].copy()
        net = pd.to_numeric(group.net_bps, errors="coerce").fillna(0.0)
        net_r = pd.to_numeric(group.net_R, errors="coerce").fillna(0.0)
        gp = float(net[net > 0].sum())
        gl = abs(float(net[net <= 0].sum()))
        gp_r = float(net_r[net_r > 0].sum())
        gl_r = abs(float(net_r[net_r < 0].sum()))
        wins = int((net > 0).sum())
        holding = pd.to_numeric(group.holding_minutes, errors="coerce") if not group.empty else pd.Series(dtype=float)
        rows.append({
            "model": key[0],
            "variant": key[1],
            "timeframe": key[2],
            "year": int(key[3]),
            "symbol_streams": int(group.symbol.nunique()) if not group.empty else 0,
            "trades": int(len(group)),
            "total_trade_records": int(len(all_group)),
            "data_gap_trades": data_gap_trades,
            "end_of_sample_trades": end_of_sample_trades,
            "win_rate_pct": round(100 * wins / len(group), 2) if len(group) else 0.0,
            "aggregate_trade_pf_bps": round(gp / gl, 4) if gl else None,
            "aggregate_profit_factor_R": round(gp_r / gl_r, 4) if gl_r else None,
            "net_bps_sum": round(float(net.sum()), 2),
            "net_R_sum": round(float(net_r.sum()), 3),
            "fixed_initial_equity_risk_return_pct_at_1pct": round(float(net_r.sum()), 3),
            "avg_holding_minutes": round(float(holding.mean()), 2) if holding.notna().any() else None,
            "note": "DATA_GAP and END_OF_SAMPLE records are retained in the ledger but excluded from yearly performance metrics",
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
        _aggregate_yearly_trade_rows(trades).to_csv(out / "same_model_cross_symbol_yearly_summary.csv", index=False)

    metadata = []
    for path in sorted(root.rglob("run_summary.json")):
        try:
            metadata.append(json.loads(path.read_text()))
        except Exception as error:
            metadata.append({"source": str(path), "error": str(error)})
    (out / "data_and_run_quality.json").write_text(json.dumps(metadata, indent=2, default=str))

    development_positive = pd.DataFrame()
    development_and_validation_positive = pd.DataFrame()
    status_counts = results.status.value_counts(dropna=False).rename_axis("status").reset_index(name="rows") if not results.empty and "status" in results.columns else pd.DataFrame()
    if not status_counts.empty:
        status_counts.to_csv(out / "status_counts.csv", index=False)
    required_dev = {"development_trades", "development_profit_factor", "development_net_R"}
    required_val = {"validation_2025_trades", "validation_2025_profit_factor", "validation_2025_net_R"}
    if not results.empty and required_dev.issubset(results.columns):
        development_positive = results[
            (results.status == "COMPLETED")
            & (pd.to_numeric(results.development_trades, errors="coerce").fillna(0) >= 100)
            & (pd.to_numeric(results.development_profit_factor, errors="coerce") > 1.0)
            & (pd.to_numeric(results.development_net_R, errors="coerce") > 0)
        ].copy()
        development_positive.to_csv(out / "development_positive_candidates.csv", index=False)
        if required_val.issubset(development_positive.columns):
            development_and_validation_positive = development_positive[
                (pd.to_numeric(development_positive.validation_2025_trades, errors="coerce").fillna(0) >= 50)
                & (pd.to_numeric(development_positive.validation_2025_profit_factor, errors="coerce") > 1.0)
                & (pd.to_numeric(development_positive.validation_2025_net_R, errors="coerce") > 0)
            ].copy()
        development_and_validation_positive.to_csv(
            out / "development_and_2025_positive_candidates.csv", index=False
        )

    data_gap_trades = int(trades.exit_reason.eq("DATA_GAP").sum()) if not trades.empty and "exit_reason" in trades.columns else 0
    end_of_sample_trades = int(trades.exit_reason.eq("END_OF_SAMPLE").sum()) if not trades.empty and "exit_reason" in trades.columns else 0
    report = [
        "# Independent Core Engine Screening",
        "",
        "This is a first-pass baseline screen. It is not final selection or a deployment recommendation.",
        "",
        f"- Result rows: {len(results)}",
        f"- Yearly result rows: {len(yearly)}",
        f"- Trade ledger rows: {len(trades)}",
        f"- DATA_GAP exits retained for audit but excluded from performance metrics: {data_gap_trades}",
        f"- END_OF_SAMPLE records retained for audit but excluded from performance metrics: {end_of_sample_trades}",
        f"- Development-positive candidates (PF > 1, net-R > 0, 100+ trades): {len(development_positive)}",
        f"- Development plus 2025 validation positive: {len(development_and_validation_positive)}",
        "",
        "## Important interpretation",
        "",
        "- Each model is tested independently. Cross-symbol aggregation below is within the same model only.",
        "- same_model_cross_symbol_trade_summary.csv reports trade-level PF and net-R sums; it is not a capital-weighted portfolio return or drawdown.",
        "- Candidate screening uses 2021-2024 development and 2025 validation only. 2026 YTD is retrospective audit evidence because it was included in broad sweeps; it is not a pristine untouched holdout and must not be used for selection.",
        "- M11 is marked data-gated if historical open-interest metrics are missing; no price-only OI proxy is substituted.",
        "- M3 is excluded and untouched.",
        "",
        "See the CSVs and data_and_run_quality.json for the full result ledger.",
    ]
    (out / "SCREENING_REPORT.md").write_text("\n".join(report) + "\n")
    print("\n".join(report), flush=True)


if __name__ == "__main__":
    main()

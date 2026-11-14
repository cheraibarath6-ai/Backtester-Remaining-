from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


KEYS = [
    "model", "variant", "timeframe", "cost_scenario",
    "fee_bps_per_side", "slippage_bps_per_side",
]


def _load(root: Path, filename: str) -> pd.DataFrame:
    parts = [pd.read_csv(path) for path in root.rglob(filename)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _pf(values: pd.Series) -> float | None:
    series = pd.to_numeric(values, errors="coerce").fillna(0.0)
    gains = float(series[series > 0].sum())
    losses = abs(float(series[series <= 0].sum()))
    return round(gains / losses, 4) if losses > 0 else (None if gains <= 0 else float("inf"))


def _drawdown_r(frame: pd.DataFrame) -> float:
    ordered = frame.sort_values("exit_time")
    r = pd.to_numeric(ordered.net_R, errors="coerce").fillna(0.0)
    curve = r.cumsum()
    peak = curve.cummax().clip(lower=0.0)
    return float((curve - peak).min()) if len(curve) else 0.0


def _summary(frame: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = []
    if frame.empty:
        return pd.DataFrame()
    for key, all_rows in frame.groupby(keys, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        row = dict(zip(keys, key_tuple))
        reason = all_rows.exit_reason.astype(str)
        gap_count = int(reason.eq("DATA_GAP").sum())
        censored_count = int(reason.eq("END_OF_SAMPLE").sum())
        valid = all_rows.loc[~reason.isin(["DATA_GAP", "END_OF_SAMPLE"])].copy()
        net = pd.to_numeric(valid.net_bps, errors="coerce").fillna(0.0)
        net_r = pd.to_numeric(valid.net_R, errors="coerce").fillna(0.0)
        fees = pd.to_numeric(valid.fees_pct, errors="coerce").fillna(0.0).sum() * 100.0
        slippage = pd.to_numeric(valid.slippage_cost_pct, errors="coerce").fillna(0.0).sum() * 100.0
        funding = pd.to_numeric(valid.funding_cost_pct, errors="coerce").fillna(0.0).sum() * 100.0
        total_cost = fees + slippage + funding
        gross_move = pd.to_numeric(valid.gross_price_move_bps, errors="coerce").fillna(0.0)
        gross_positive = float(gross_move.clip(lower=0.0).sum())
        holding = pd.to_numeric(valid.holding_minutes, errors="coerce")
        complete_mask = valid["excursion_complete"].astype(str).str.lower().eq("true") if "excursion_complete" in valid else pd.Series(False, index=valid.index)
        complete = valid.loc[complete_mask]
        dd = [
            _drawdown_r(group)
            for _, group in valid.groupby("symbol")
        ] if not valid.empty else []
        row.update({
            "symbol_streams": int(valid.symbol.nunique()) if not valid.empty else 0,
            "trades": int(len(valid)),
            "total_trade_records": int(len(all_rows)),
            "data_gap_trades": gap_count,
            "end_of_sample_trades": censored_count,
            "wins": int((net > 0).sum()),
            "losses": int((net <= 0).sum()),
            "win_rate_pct": round(float((net > 0).mean() * 100), 2) if len(net) else 0.0,
            "net_bps_pf": _pf(net),
            "r_based_pf": _pf(net_r),
            "net_bps_sum": round(float(net.sum()), 2),
            "net_R_sum": round(float(net_r.sum()), 3),
            "worst_symbol_max_drawdown_R": round(min(dd), 3) if dd else None,
            "avg_trade_bps": round(float(net.mean()), 3) if len(net) else None,
            "avg_holding_minutes": round(float(holding.mean()), 2) if holding.notna().any() else None,
            "median_holding_minutes": round(float(holding.median()), 2) if holding.notna().any() else None,
            "gross_price_move_bps_sum": round(float(gross_move.sum()), 2),
            "gross_positive_move_bps": round(gross_positive, 2),
            "fees_bps": round(float(fees), 2),
            "slippage_bps": round(float(slippage), 2),
            "funding_bps": round(float(funding), 2),
            "total_cost_bps": round(float(total_cost), 2),
            "cost_share_of_gross_positive_pct": round(float(total_cost / gross_positive * 100), 3) if gross_positive > 0 else None,
            "avg_cost_bps_per_trade": round(float(total_cost / len(valid)), 3) if len(valid) else None,
            "avg_gross_positive_move_bps_per_trade": round(float(gross_positive / len(valid)), 3) if len(valid) else None,
            "excursion_complete_trades": int(len(complete)),
            "avg_mae_bps": round(float(pd.to_numeric(complete.mae_bps, errors="coerce").mean()), 3) if len(complete) else None,
            "avg_mfe_bps": round(float(pd.to_numeric(complete.mfe_bps, errors="coerce").mean()), 3) if len(complete) else None,
            "avg_mae_R": round(float(pd.to_numeric(complete.mae_R, errors="coerce").mean()), 3) if len(complete) else None,
            "avg_mfe_R": round(float(pd.to_numeric(complete.mfe_R, errors="coerce").mean()), 3) if len(complete) else None,
            "note": "Cross-symbol trade-stream diagnostics, not a capital-weighted portfolio return",
        })
        rows.append(row)
    return pd.DataFrame(rows)


def _cohort_rows(ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame()
    entry = pd.to_datetime(ledger.entry_time, utc=True, errors="coerce")
    exit_time = pd.to_datetime(ledger.exit_time, utc=True, errors="coerce")
    cohorts = {
        "DEVELOPMENT_2021_2024": (pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2025-01-01", tz="UTC")),
        "VALIDATION_2025": (pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2026-01-01", tz="UTC")),
        "RETROSPECTIVE_2026": (pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-11-01", tz="UTC")),
    }
    parts = []
    for label, (start, end) in cohorts.items():
        mask = entry.ge(start) & entry.lt(end) & exit_time.lt(end)
        part = ledger.loc[mask].copy()
        if part.empty:
            continue
        part["cohort"] = label
        parts.append(part)
    if not parts:
        return pd.DataFrame()
    return _summary(pd.concat(parts, ignore_index=True), KEYS + ["cohort"])


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate independent eight-engine cost stress artifacts")
    parser.add_argument("--input", default="input-artifacts")
    parser.add_argument("--out", default="eight_engine_cost_stress_results")
    args = parser.parse_args()
    root, out = Path(args.input), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = _load(root, "screen_results.csv")
    yearly = _load(root, "screen_yearly.csv")
    ledger = _load(root, "trade_ledger.csv")
    monte_carlo = _load(root, "monte_carlo.csv")
    summaries = []
    for path in root.rglob("run_summary.json"):
        try:
            summaries.append(json.loads(path.read_text()))
        except Exception:
            continue

    results.to_csv(out / "all_screen_results.csv", index=False)
    yearly.to_csv(out / "all_yearly_results.csv", index=False)
    monte_carlo.to_csv(out / "all_monte_carlo.csv", index=False)
    if not ledger.empty:
        ledger.to_csv(out / "all_trade_ledger.csv", index=False)
        ledger["year"] = pd.to_datetime(ledger.exit_time, utc=True).dt.year
        _summary(ledger, KEYS).to_csv(out / "same_model_cross_symbol_cost_summary.csv", index=False)
        _summary(ledger, KEYS + ["year"]).to_csv(out / "same_model_cross_symbol_cost_yearly.csv", index=False)
        _summary(ledger, KEYS + ["exit_reason"]).to_csv(out / "exit_reason_diagnostics.csv", index=False)
        _cohort_rows(ledger).to_csv(out / "same_model_cross_symbol_cost_cohorts.csv", index=False)
    else:
        for name in (
            "same_model_cross_symbol_cost_summary.csv",
            "same_model_cross_symbol_cost_yearly.csv",
            "exit_reason_diagnostics.csv",
            "same_model_cross_symbol_cost_cohorts.csv",
        ):
            pd.DataFrame().to_csv(out / name, index=False)

    if not monte_carlo.empty:
        keys = ["model", "variant", "timeframe", "cost_scenario"]
        mc = monte_carlo.groupby(keys, dropna=False).agg(
            symbol_streams=("symbol", "nunique"),
            median_probability_net_R_positive_pct=("prob_net_R_positive_pct", "median"),
            min_probability_net_R_positive_pct=("prob_net_R_positive_pct", "min"),
            max_probability_net_R_positive_pct=("prob_net_R_positive_pct", "max"),
            median_net_R_p05=("net_R_p05", "median"),
            median_net_R_p50=("net_R_median", "median"),
            median_net_R_p95=("net_R_p95", "median"),
        ).reset_index()
        mc.to_csv(out / "monte_carlo_cross_symbol_diagnostics.csv", index=False)
    else:
        pd.DataFrame().to_csv(out / "monte_carlo_cross_symbol_diagnostics.csv", index=False)

    status = (
        results.status.value_counts(dropna=False).rename_axis("status").reset_index(name="rows")
        if not results.empty else pd.DataFrame()
    )
    status.to_csv(out / "status_counts.csv", index=False)
    (out / "data_and_run_quality.json").write_text(json.dumps(summaries, indent=2, default=str))

    model_names = sorted(set(results.model.dropna().astype(str))) if not results.empty else []
    report = [
        "# Independent Eight-Engine Cost Stress",
        "",
        f"- Symbol result rows: {len(results)}",
        f"- Yearly symbol rows: {len(yearly)}",
        f"- Trade ledger rows: {len(ledger)}",
        f"- Monte Carlo symbol-stream rows: {len(monte_carlo)}",
        f"- Models present: {', '.join(model_names)}",
        f"- DATA_GAP ledger records: {int(ledger.exit_reason.eq('DATA_GAP').sum()) if not ledger.empty else 0}",
        f"- END_OF_SAMPLE ledger records: {int(ledger.exit_reason.eq('END_OF_SAMPLE').sum()) if not ledger.empty else 0}",
        "",
        "The four fee/slippage scenarios re-execute the OHLC path; they are not simple repricing.",
        "MAE/MFE are measured from the complete underlying 1m path; incomplete paths are left unscored.",
        "Funding is sourced only from the official Binance source and fails closed on missing coverage.",
        "Each model is independent. Cross-symbol sums are trade-stream diagnostics, not portfolio returns.",
        "DATA_GAP and END_OF_SAMPLE records remain in audit ledgers but are excluded from performance metrics.",
        "2021-2024 is development, 2025 validation, and 2026 retrospective audit only.",
    ]
    (out / "COST_STRESS_REPORT.md").write_text("\n".join(report) + "\n")
    print("\n".join(report), flush=True)


if __name__ == "__main__":
    main()

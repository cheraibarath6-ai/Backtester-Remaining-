from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from .data import acquire_klines, acquire_funding, quality_report
from .grid import make_grid_signals
from .backtest import run_backtest, summarize

# PFI stage 1: vary only the two leading factors per engine.
# All remaining factors are held at documented neutral baseline values.
FACTOR_VALUES = {
    "M1": {
        "factor_1": "max_sweep_depth_atr",
        "values_1": [0.35, 0.50, 0.65, 0.80, 1.00],
        "factor_2": "displacement_atr",
        "values_2": [0.80, 1.00, 1.20, 1.40, 1.60],
        "fixed": {"swing_lookback":20,"sweep_recency":6,"structure_lookback":5,
                  "adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,
                  "stop_lookback":5,"stop_buffer_atr":0.15}
    },
    "M2": {
        "factor_1": "ema_fast",
        "values_1": [8, 10, 15, 20, 30],
        "factor_2": "ema_slow",
        "values_2": [50, 75, 100, 150, 200],
        "fixed": {"rsi_trigger":55,"adx_min":18,"di_spread_min":2,
                  "htf_4h":False,"volume_ratio_min":1.0,
                  "stop_lookback":10,"stop_buffer_atr":0.15}
    },
    "M4": {
        "factor_1": "range_lookback",
        "values_1": [10, 15, 20, 25, 30],
        "factor_2": "retest_tolerance_atr",
        "values_2": [0.10, 0.20, 0.30, 0.40, 0.50],
        "fixed": {"max_retest_age":6,"breakout_buffer_atr":0.10,
                  "adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,
                  "stop_lookback":5,"stop_buffer_atr":0.15}
    },
    "M5": {
        "factor_1": "funding_percentile",
        "values_1": [0.05, 0.10, 0.15, 0.20, 0.25],
        "factor_2": "taker_imbalance",
        "values_2": [0.51, 0.53, 0.55, 0.57, 0.59],
        "fixed": {"funding_lookback":180,"adx_min":12,"htf_4h":False,
                  "volume_ratio_min":1.0,"max_ema_distance_atr":1.0,
                  "stop_lookback":8,"stop_buffer_atr":0.15}
    }
}

def configurations(model):
    spec=FACTOR_VALUES[model]
    for a in spec["values_1"]:
        for b in spec["values_2"]:
            p=dict(spec["fixed"])
            p[spec["factor_1"]]=a
            p[spec["factor_2"]]=b
            if model=="M2" and int(a)>=int(b):
                continue
            yield p

def metrics_for_period(trades, start_year, end_year):
    if trades.empty:
        return summarize(trades)
    years=pd.to_datetime(trades["exit_time"],utc=True).dt.year
    return summarize(trades[(years>=start_year)&(years<=end_year)])

def main():
    ap=argparse.ArgumentParser(description="PFI — Progressive Factor Isolation stage 1")
    ap.add_argument("--start",default="2021-01-01")
    ap.add_argument("--end",default="2026-11-13")
    ap.add_argument("--dev-end-year",type=int,default=2024)
    ap.add_argument("--symbols",nargs="+",default=["BTCUSDT","ETHUSDT"])
    ap.add_argument("--timeframes",nargs="+",choices=["5m","15m"],default=["5m","15m"])
    ap.add_argument("--models",nargs="+",choices=["M1","M2","M4","M5"],default=["M1","M2","M4","M5"])
    ap.add_argument("--fee-bps",type=float,default=5.0)
    ap.add_argument("--slippage-bps",type=float,default=2.0)
    ap.add_argument("--rr",type=float,default=2.0)
    ap.add_argument("--out",default="pfi_artifacts")
    a=ap.parse_args()
    if a.end<=a.start: ap.error("--end must be later than --start")
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    rows=[]; qualities=[]; funding_meta={}
    for symbol in a.symbols:
        print(f"PFI DATA START {symbol} {a.start}..{a.end}",flush=True)
        raw=acquire_klines(symbol,a.start,a.end)
        fund=acquire_funding(symbol,a.start,a.end)
        qualities.append(quality_report(raw,symbol))
        funding_meta[symbol]=fund.attrs.get("source","unknown")
        fund.to_csv(out/f"{symbol}_funding.csv")
        for tf in a.timeframes:
            for model in a.models:
                spec=FACTOR_VALUES[model]
                configs=list(configurations(model))
                print(f"PFI FACTOR TEST START {model} {symbol} {tf}: {len(configs)} combinations",flush=True)
                for i,params in enumerate(configs,1):
                    sig=make_grid_signals(raw,model,tf,fund if model=="M5" else None,params)
                    trades=run_backtest(sig,fund,symbol,model,tf,a.fee_bps,a.slippage_bps,a.rr)
                    dev=metrics_for_period(trades,2021,a.dev_end_year)
                    holdout_2025=metrics_for_period(trades,2025,2025)
                    holdout_2026=metrics_for_period(trades,2026,2026)
                    row={"model":model,"symbol":symbol,"timeframe":tf,
                         "factor_1":spec["factor_1"],"value_1":params[spec["factor_1"]],
                         "factor_2":spec["factor_2"],"value_2":params[spec["factor_2"]],
                         "parameters_json":json.dumps(params,sort_keys=True),
                         "development_years":f"2021-{a.dev_end_year}",
                         **{f"dev_{k}":v for k,v in dev.items()},
                         **{f"holdout_2025_{k}":v for k,v in holdout_2025.items()},
                         **{f"holdout_2026_{k}":v for k,v in holdout_2026.items()}}
                    rows.append(row)
                    if i%5==0:
                        pd.DataFrame(rows).to_csv(out/"pfi_stage1_partial.csv",index=False)
                        print(f"PFI PROGRESS {model} {symbol} {tf} {i}/{len(configs)}",flush=True)
                print(f"PFI FACTOR TEST COMPLETE {model} {symbol} {tf}",flush=True)
    result=pd.DataFrame(rows)
    result.to_csv(out/"pfi_stage1_results.csv",index=False)
    # Aggregate the same factor pair across both symbols and both execution timeframes.
    group_cols=["model","factor_1","value_1","factor_2","value_2"]
    agg=result.groupby(group_cols,dropna=False).agg(
        markets_tested=("symbol","count"),
        development_trades=("dev_trades","sum"),
        median_dev_profit_factor=("dev_profit_factor","median"),
        median_dev_win_rate_pct=("dev_win_rate_pct","median"),
        median_dev_net_R=("dev_net_R","median"),
        median_dev_drawdown_pct=("dev_max_drawdown_pct","median"),
        holdout_2025_median_pf=("holdout_2025_profit_factor","median"),
        holdout_2026_median_pf=("holdout_2026_profit_factor","median")
    ).reset_index()
    # Conservative descriptive score: reward profitable, repeated performance and penalize drawdown.
    agg["candidate_score"]=(
        agg["median_dev_net_R"].fillna(0)
        + agg["median_dev_profit_factor"].fillna(0)*0.25
        - agg["median_dev_drawdown_pct"].abs().fillna(0)*0.05
    )
    agg=agg.sort_values(["model","candidate_score"],ascending=[True,False])
    agg.to_csv(out/"pfi_stage1_pair_ranking.csv",index=False)
    top=agg.groupby("model",group_keys=False).head(5)
    top.to_csv(out/"pfi_stage1_top_candidates.csv",index=False)
    summary={"method":"PFI — Progressive Factor Isolation","stage":1,
      "period":{"start_inclusive":a.start,"end_exclusive":a.end},
      "development_period":f"2021-{a.dev_end_year}",
      "untouched_chronological_holdouts":["2025","2026 YTD"],
      "symbols":a.symbols,"timeframes":a.timeframes,"models":a.models,
      "combinations_per_model":25,"planned_rr":a.rr,
      "fee_bps_per_side":a.fee_bps,"slippage_bps_per_side":a.slippage_bps,
      "fixed_parameters":{m:FACTOR_VALUES[m]["fixed"] for m in a.models},
      "factor_values":{m:{k:v for k,v in FACTOR_VALUES[m].items() if k!="fixed"} for m in a.models},
      "rows_written":len(result),"data_quality":qualities,"funding_sources":funding_meta,
      "selection_warning":"Do not select solely by candidate_score. Inspect trade counts, yearly consistency, drawdown and both chronological holdouts before locking values. Holdouts must not be used to tune stage 1."}
    (out/"pfi_stage1_summary.json").write_text(json.dumps(summary,indent=2))
    print("PFI STAGE 1 COMPLETE",flush=True)
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__": main()

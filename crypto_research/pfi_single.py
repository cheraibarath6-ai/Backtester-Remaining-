from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from .data import acquire_klines, acquire_funding, quality_report
from .grid import make_grid_signals
from .pfi import fast_backtest
from .backtest import summarize

# Stage 2: one factor changes per model; all other parameters stay fixed.
# Broad exploratory values intentionally include weak/extreme settings.
SPECS = {
 "M1": {"factor":"max_sweep_depth_atr","values":[0.10,0.20,0.30,0.35,0.40,0.50,0.60,0.65,0.70,0.80,0.90,1.00,1.10,1.20,1.40,1.60,1.80,2.00],
        "fixed":{"swing_lookback":20,"sweep_recency":6,"displacement_atr":1.10,"structure_lookback":5,"adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":5,"stop_buffer_atr":0.15}},
 "M2": {"factor":"ema_fast","values":[5,8,10,12,15,18,20,25,30,35,40,45,50,60,70,80,90],
        "fixed":{"ema_slow":100,"rsi_trigger":55,"adx_min":18,"di_spread_min":2,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":10,"stop_buffer_atr":0.15}},
 "M4": {"factor":"range_lookback","values":[5,8,10,12,15,18,20,25,30,35,40,50,60,75,100],
        "fixed":{"retest_tolerance_atr":0.25,"max_retest_age":6,"breakout_buffer_atr":0.10,"adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":5,"stop_buffer_atr":0.15}},
 "M5": {"factor":"funding_percentile","values":[0.01,0.025,0.05,0.075,0.10,0.125,0.15,0.175,0.20,0.25,0.30,0.35,0.40,0.45],
        "fixed":{"funding_lookback":180,"taker_imbalance":0.55,"adx_min":12,"htf_4h":False,"volume_ratio_min":1.0,"max_ema_distance_atr":1.0,"stop_lookback":8,"stop_buffer_atr":0.15}}
}

def period_metrics(trades, start_year, end_year):
    if trades.empty: return summarize(trades)
    y=pd.to_datetime(trades["exit_time"],utc=True).dt.year
    return summarize(trades[(y>=start_year)&(y<=end_year)])

def main():
    ap=argparse.ArgumentParser(description="PFI Stage 2 — one-factor-at-a-time broad exploration")
    ap.add_argument("--start",default="2021-01-01")
    ap.add_argument("--end",default="2026-11-13")
    ap.add_argument("--symbols",nargs="+",default=["BTCUSDT","ETHUSDT"])
    ap.add_argument("--timeframes",nargs="+",choices=["5m","15m"],default=["5m","15m"])
    ap.add_argument("--models",nargs="+",choices=["M1","M2","M4","M5"],default=["M1","M2","M4","M5"])
    ap.add_argument("--fee-bps",type=float,default=5.0)
    ap.add_argument("--slippage-bps",type=float,default=2.0)
    ap.add_argument("--rr",type=float,default=2.0)
    ap.add_argument("--out",default="pfi_stage2_artifacts")
    a=ap.parse_args()
    if a.end<=a.start: ap.error("--end must be later than --start")
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    rows=[]; qualities=[]; funding_meta={}
    for symbol in a.symbols:
        print(f"PFI STAGE 2 DATA START {symbol} {a.start}..{a.end}",flush=True)
        raw=acquire_klines(symbol,a.start,a.end)
        fund=acquire_funding(symbol,a.start,a.end)
        qualities.append(quality_report(raw,symbol))
        funding_meta[symbol]=fund.attrs.get("source","unknown")
        fund.to_csv(out/f"{symbol}_funding.csv")
        for tf in a.timeframes:
            for model in a.models:
                spec=SPECS[model]; factor=spec["factor"]
                values=spec["values"]
                print(f"PFI STAGE 2 FACTOR START {model} {factor}: {len(values)} values | {symbol} {tf}",flush=True)
                for idx,value in enumerate(values,1):
                    params=dict(spec["fixed"]); params[factor]=value
                    signals=make_grid_signals(raw,model,tf,fund if model=="M5" else None,params)
                    trades=fast_backtest(signals,fund,symbol,model,tf,a.fee_bps,a.slippage_bps,a.rr)
                    base={"stage":2,"model":model,"factor":factor,"value":value,"symbol":symbol,"timeframe":tf,
                          "parameters_json":json.dumps(params,sort_keys=True)}
                    for label,lo,hi in [("development",2021,2024),("holdout_2025",2025,2025),("holdout_2026",2026,2026)]:
                        met=period_metrics(trades,lo,hi)
                        base.update({f"{label}_{k}":v for k,v in met.items()})
                    years=pd.to_datetime(trades["exit_time"],utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
                    for year in range(2021,2027):
                        met=summarize(trades[years==year]) if not trades.empty else summarize(trades)
                        base.update({f"y{year}_{k}":v for k,v in met.items()})
                    rows.append(base)
                    if idx%3==0 or idx==len(values):
                        pd.DataFrame(rows).to_csv(out/"pfi_stage2_partial.csv",index=False)
                        print(f"PFI STAGE 2 PROGRESS {model} {factor} {idx}/{len(values)} | {symbol} {tf}",flush=True)
                print(f"PFI STAGE 2 FACTOR COMPLETE {model} {factor} | {symbol} {tf}",flush=True)
    result=pd.DataFrame(rows)
    result.to_csv(out/"pfi_stage2_results.csv",index=False)
    group=["model","factor","value"]
    agg=result.groupby(group,dropna=False).agg(
      markets_tested=("symbol","count"),
      development_trades=("development_trades","sum"),
      development_pf_median=("development_profit_factor","median"),
      development_net_profit_pct_median=("development_net_return_pct","median"),
      development_net_R_median=("development_net_R","median"),
      development_win_rate_median=("development_win_rate_pct","median"),
      holdout_2025_pf_median=("holdout_2025_profit_factor","median"),
      holdout_2025_net_profit_pct_median=("holdout_2025_net_return_pct","median"),
      holdout_2026_pf_median=("holdout_2026_profit_factor","median"),
      holdout_2026_net_profit_pct_median=("holdout_2026_net_return_pct","median"),
      development_drawdown_median=("development_max_drawdown_pct","median")
    ).reset_index()
    agg.to_csv(out/"pfi_stage2_factor_ranking.csv",index=False)
    summary={"method":"PFI — one factor at a time","stage":2,"period":{"start_inclusive":a.start,"end_exclusive":a.end},
      "development_years":"2021-2024","chronological_holdouts":["2025","2026 YTD"],"symbols":a.symbols,"timeframes":a.timeframes,
      "models":a.models,"values_tested":{m:{"factor":SPECS[m]["factor"],"values":SPECS[m]["values"],"fixed_parameters":SPECS[m]["fixed"]} for m in a.models},
      "planned_rr":a.rr,"fee_bps_per_side":a.fee_bps,"slippage_bps_per_side":a.slippage_bps,
      "rows_written":len(result),"data_quality":qualities,"funding_sources":funding_meta,
      "selection_rule":"Retain statistically and economically similar candidates together; do not select on development PF alone. Require meaningful trade counts, year-by-year stability and both chronological holdouts. Funding source for M5 must be verified."}
    (out/"pfi_stage2_summary.json").write_text(json.dumps(summary,indent=2))
    print("PFI STAGE 2 COMPLETE",flush=True)
    print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__": main()

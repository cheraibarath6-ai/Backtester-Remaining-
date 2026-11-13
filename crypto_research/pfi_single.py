from __future__ import annotations
import argparse, json
from itertools import product
from pathlib import Path
import pandas as pd
from .data import acquire_klines, acquire_funding, quality_report
from .grid import make_grid_signals
from .pfi import fast_backtest
from .backtest import summarize

# Stage 2: test the next untouched factor while carrying forward Stage 1 zones.
# Each run varies ONE new factor; Stage 1 factor pairs are held at representative
# points across their retained zones. This preserves interactions without a full grid.
SPECS = {
 "M1": {"factor":"swing_lookback","values":[5,8,10,12,15,20,25,30,40,50,60],
        "anchors":{"max_sweep_depth_atr":[0.35,0.50,0.65,0.80,1.00],"displacement_atr":[1.20,1.40,1.60]},
        "fixed":{"sweep_recency":6,"structure_lookback":5,"adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":5,"stop_buffer_atr":0.15}},
 "M2": {"factor":"rsi_trigger","values":[45,48,50,52,55,58,60,62,65,68,70],
        "anchors":{"ema_fast":[8,10,15,20,30],"ema_slow":[50,75,150,200]},
        "fixed":{"adx_min":18,"di_spread_min":2,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":10,"stop_buffer_atr":0.15}},
 "M4": {"factor":"max_retest_age","values":[1,2,3,4,5,6,8,10,12,15],
        "anchors":{"range_lookback":[20,25,30],"retest_tolerance_atr":[0.10,0.20,0.30,0.40,0.50]},
        "fixed":{"breakout_buffer_atr":0.10,"adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":5,"stop_buffer_atr":0.15}},
 "M5": {"factor":"funding_lookback","values":[30,45,60,90,120,180,240,360,540,720],
        "anchors":{"funding_percentile":[0.05,0.15,0.20,0.25],"taker_imbalance":[0.51,0.53,0.55]},
        "fixed":{"adx_min":12,"htf_4h":False,"volume_ratio_min":1.0,"max_ema_distance_atr":1.0,"stop_lookback":8,"stop_buffer_atr":0.15}}
}

def configurations(model):
    spec=SPECS[model]
    anchor_names=list(spec["anchors"])
    for anchor_values in product(*(spec["anchors"][k] for k in anchor_names)):
        anchor=dict(zip(anchor_names,anchor_values))
        if model=="M2" and anchor["ema_fast"]>=anchor["ema_slow"]:
            continue
        for value in spec["values"]:
            p=dict(spec["fixed"]); p.update(anchor); p[spec["factor"]]=value
            yield p

def period_metrics(trades,start_year,end_year):
    if trades.empty: return summarize(trades)
    years=pd.to_datetime(trades["exit_time"],utc=True).dt.year
    return summarize(trades[(years>=start_year)&(years<=end_year)])

def main():
    ap=argparse.ArgumentParser(description="PFI Stage 2 — next-factor exploration conditioned on Stage 1 zones")
    ap.add_argument("--start",default="2021-01-01"); ap.add_argument("--end",default="2026-11-13")
    ap.add_argument("--symbols",nargs="+",default=["BTCUSDT","ETHUSDT"])
    ap.add_argument("--timeframes",nargs="+",choices=["5m","15m"],default=["5m","15m"])
    ap.add_argument("--models",nargs="+",choices=["M1","M2","M4","M5"],default=["M1","M2","M4","M5"])
    ap.add_argument("--fee-bps",type=float,default=5.0); ap.add_argument("--slippage-bps",type=float,default=2.0)
    ap.add_argument("--rr",type=float,default=2.0); ap.add_argument("--out",default="pfi_stage2_artifacts")
    a=ap.parse_args()
    if a.end<=a.start: ap.error("--end must be later than --start")
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    rows=[]; qualities=[]; funding_meta={}
    for symbol in a.symbols:
        print(f"PFI STAGE 2 DATA START {symbol} {a.start}..{a.end}",flush=True)
        raw=acquire_klines(symbol,a.start,a.end); fund=acquire_funding(symbol,a.start,a.end)
        qualities.append(quality_report(raw,symbol)); funding_meta[symbol]=fund.attrs.get("source","unknown")
        fund.to_csv(out/f"{symbol}_funding.csv")
        for tf in a.timeframes:
            for model in a.models:
                spec=SPECS[model]; configs=list(configurations(model))
                print(f"PFI STAGE 2 START {model}: {spec['factor']} across {len(configs)} anchored configurations | {symbol} {tf}",flush=True)
                for idx,params in enumerate(configs,1):
                    signals=make_grid_signals(raw,model,tf,fund if model=="M5" else None,params)
                    trades=fast_backtest(signals,fund,symbol,model,tf,a.fee_bps,a.slippage_bps,a.rr)
                    base={"stage":2,"model":model,"factor":spec["factor"],"value":params[spec["factor"]],
                          "symbol":symbol,"timeframe":tf,"parameters_json":json.dumps(params,sort_keys=True)}
                    for label,lo,hi in [("development",2021,2024),("holdout_2025",2025,2025),("holdout_2026",2026,2026)]:
                        base.update({f"{label}_{k}":v for k,v in period_metrics(trades,lo,hi).items()})
                    years=pd.to_datetime(trades["exit_time"],utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
                    for year in range(2021,2027):
                        met=summarize(trades[years==year]) if not trades.empty else summarize(trades)
                        base.update({f"y{year}_{k}":v for k,v in met.items()})
                    rows.append(base)
                    if idx%10==0 or idx==len(configs):
                        pd.DataFrame(rows).to_csv(out/"pfi_stage2_partial.csv",index=False)
                        print(f"PFI STAGE 2 PROGRESS {model} {symbol} {tf} {idx}/{len(configs)}",flush=True)
                print(f"PFI STAGE 2 COMPLETE {model} {symbol} {tf}",flush=True)
    result=pd.DataFrame(rows); result.to_csv(out/"pfi_stage2_results.csv",index=False)
    # Aggregate by new-factor value AND retained Stage 1 anchor values, not just factor alone.
    anchor_cols=[c for m in a.models for c in SPECS[m]["anchors"]]
    group=["model","factor","value","symbol","timeframe","parameters_json"]
    agg=result.groupby(["model","factor","value"],dropna=False).agg(
      markets_tested=("symbol","count"),development_trades=("development_trades","sum"),
      development_pf_median=("development_profit_factor","median"),
      development_net_R_median=("development_net_R","median"),
      development_win_rate_median=("development_win_rate_pct","median"),
      holdout_2025_pf_median=("holdout_2025_profit_factor","median"),
      holdout_2026_pf_median=("holdout_2026_profit_factor","median"),
      development_drawdown_median=("development_max_drawdown_pct","median")).reset_index()
    agg.to_csv(out/"pfi_stage2_factor_ranking.csv",index=False)
    # Also retain detailed rows so anchor-specific zones remain visible.
    summary={"method":"PFI — next-factor exploration conditioned on Stage 1 zones","stage":2,
      "period":{"start_inclusive":a.start,"end_exclusive":a.end},"development_years":"2021-2024",
      "chronological_holdouts":["2025","2026 YTD"],"symbols":a.symbols,"timeframes":a.timeframes,"models":a.models,
      "factor_specs":{m:{"factor":SPECS[m]["factor"],"values":SPECS[m]["values"],"stage1_anchor_zones":SPECS[m]["anchors"],"fixed":SPECS[m]["fixed"],"configurations":len(list(configurations(m)))} for m in a.models},
      "planned_rr":a.rr,"fee_bps_per_side":a.fee_bps,"slippage_bps_per_side":a.slippage_bps,
      "rows_written":len(result),"data_quality":qualities,"funding_sources":funding_meta,
      "selection_rule":"Retain notable contiguous or separated zones across anchored Stage 1 configurations; require meaningful trade counts, yearly stability, drawdown and both untouched holdouts. Do not select by development PF alone. Verify M5 funding source."}
    (out/"pfi_stage2_summary.json").write_text(json.dumps(summary,indent=2))
    print("PFI STAGE 2 ALL COMPLETE",flush=True); print(json.dumps(summary,indent=2),flush=True)

if __name__=="__main__": main()

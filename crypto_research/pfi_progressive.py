from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from .data import acquire_klines, acquire_funding, quality_report
from .grid import GRID, make_grid_signals
from .pfi import fast_backtest
from .backtest import summarize

# Stage 3 uses three rank-aligned candidate tracks. The three marginal top values
# from Stage 1 and Stage 2 seed the tracks. Each remaining factor is tested alone
# across those tracks; the top three values are then carried forward, one per track.
# This keeps factor isolation tractable while preserving three competing profiles.
SEEDS = {
 "M1": {
  "stage1": {"max_sweep_depth_atr":[0.80,0.35,0.65], "displacement_atr":[1.20,1.60,1.40]},
  "stage2": {"swing_lookback":[60,12,50]},
  "remaining": ["sweep_recency","structure_lookback","adx_min","htf_4h","volume_ratio_min","stop_lookback","stop_buffer_atr"],
  "base": {"swing_lookback":20,"sweep_recency":6,"max_sweep_depth_atr":0.65,"displacement_atr":1.10,
           "structure_lookback":5,"adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":5,"stop_buffer_atr":0.15}},
 "M2": {
  "stage1": {"ema_fast":[8,30,10], "ema_slow":[200,75,150]},
  "stage2": {"rsi_trigger":[70,68,55]},
  "remaining": ["adx_min","di_spread_min","htf_4h","volume_ratio_min","stop_lookback","stop_buffer_atr"],
  "base": {"ema_fast":10,"ema_slow":100,"rsi_trigger":55,"adx_min":18,"di_spread_min":2,
           "htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":10,"stop_buffer_atr":0.15}},
 "M4": {
  "stage1": {"range_lookback":[25,30,20], "retest_tolerance_atr":[0.10,0.20,0.50]},
  "stage2": {"max_retest_age":[1,3,4]},
  "remaining": ["breakout_buffer_atr","adx_min","htf_4h","volume_ratio_min","stop_lookback","stop_buffer_atr"],
  "base": {"range_lookback":20,"retest_tolerance_atr":0.25,"max_retest_age":6,"breakout_buffer_atr":0.10,
           "adx_min":18,"htf_4h":False,"volume_ratio_min":1.0,"stop_lookback":5,"stop_buffer_atr":0.15}},
 "M5": {
  "stage1": {"funding_percentile":[0.05,0.15,0.20], "taker_imbalance":[0.51,0.53,0.57]},
  "stage2": {"funding_lookback":[720,60,540]},
  "remaining": ["adx_min","htf_4h","volume_ratio_min","max_ema_distance_atr","stop_lookback","stop_buffer_atr"],
  "base": {"funding_lookback":180,"funding_percentile":0.20,"taker_imbalance":0.55,"adx_min":12,
           "htf_4h":False,"volume_ratio_min":1.0,"max_ema_distance_atr":1.0,"stop_lookback":8,"stop_buffer_atr":0.15}}
}

def initial_profiles(model):
    spec=SEEDS[model]
    profiles=[]
    for i in range(3):
        p=dict(spec["base"])
        for group in ("stage1","stage2"):
            for key,values in spec[group].items():
                p[key]=values[i]
        if model=="M2" and p["ema_fast"]>=p["ema_slow"]:
            raise ValueError(f"Invalid seeded EMA pair: {p}")
        profiles.append(p)
    return profiles

def metrics_for_period(trades, lo, hi):
    if trades.empty:
        return summarize(trades)
    years=pd.to_datetime(trades["exit_time"],utc=True).dt.year
    return summarize(trades[(years>=lo)&(years<=hi)])

def value_rank_table(rows, factor):
    d=pd.DataFrame(rows)
    agg=d.groupby("value",dropna=False).agg(
      market_slices=("symbol","count"),
      development_trades=("development_trades","sum"),
      development_pf_median=("development_profit_factor","median"),
      development_net_R_median=("development_net_R","median"),
      development_win_rate_median=("development_win_rate_pct","median"),
      holdout_2025_pf_median=("holdout_2025_profit_factor","median"),
      holdout_2026_pf_median=("holdout_2026_profit_factor","median"),
      development_drawdown_median=("development_max_drawdown_pct","median")
    ).reset_index()
    metrics=["development_profit_factor","development_net_R","holdout_2025_profit_factor",
             "holdout_2026_profit_factor","development_max_drawdown_pct"]
    agg["rank_pf"]=agg.development_pf_median.rank(ascending=False,method="average")
    agg["rank_net_R"]=agg.development_net_R_median.rank(ascending=False,method="average")
    agg["rank_2025"]=agg.holdout_2025_pf_median.rank(ascending=False,method="average")
    agg["rank_2026"]=agg.holdout_2026_pf_median.rank(ascending=False,method="average")
    agg["rank_drawdown"]=agg.development_drawdown_median.rank(ascending=False,method="average")
    agg["robust_average_rank"]=agg[["rank_pf","rank_net_R","rank_2025","rank_2026","rank_drawdown"]].mean(axis=1)
    agg=agg.sort_values(["robust_average_rank","development_pf_median","development_net_R_median"],
                        ascending=[True,False,False]).reset_index(drop=True)
    agg.insert(0,"factor",factor)
    return agg

def main():
    ap=argparse.ArgumentParser(description="PFI Stage 3 — sequential one-factor tests across three retained profiles")
    ap.add_argument("--start",default="2021-01-01"); ap.add_argument("--end",default="2026-11-13")
    ap.add_argument("--symbols",nargs="+",default=["BTCUSDT","ETHUSDT"])
    ap.add_argument("--timeframes",nargs="+",choices=["5m","15m"],default=["5m","15m"])
    ap.add_argument("--model",required=True,choices=["M1","M2","M4","M5"])
    ap.add_argument("--fee-bps",type=float,default=5.0); ap.add_argument("--slippage-bps",type=float,default=2.0)
    ap.add_argument("--rr",type=float,default=2.0); ap.add_argument("--out",default="pfi_stage3_artifacts")
    a=ap.parse_args()
    if a.end<=a.start: ap.error("--end must be later than --start")
    model=a.model; spec=SEEDS[model]
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    profiles=initial_profiles(model)
    all_rankings=[]; all_results=[]; qualities=[]; funding_meta={}
    market_data={}
    for symbol in a.symbols:
        print(f"PFI STAGE 3 DATA START {symbol} {a.start}..{a.end}",flush=True)
        raw=acquire_klines(symbol,a.start,a.end)
        fund=acquire_funding(symbol,a.start,a.end)
        qualities.append(quality_report(raw,symbol))
        funding_meta[symbol]=fund.attrs.get("source","unknown")
        fund.to_csv(out/f"{symbol}_funding.csv")
        market_data[symbol]=(raw,fund)
    print(f"PFI STAGE 3 {model}: seeded 3 profiles from Stage 1 + Stage 2 top-three values",flush=True)
    for factor_index,factor in enumerate(spec["remaining"],1):
        values=list(GRID[model][factor])
        factor_rows=[]
        print(f"PFI STAGE 3 FACTOR START {model} {factor} | variants={values} | profiles={len(profiles)}",flush=True)
        for profile_index,profile in enumerate(profiles,1):
            for value in values:
                params=dict(profile); params[factor]=value
                if model=="M2" and int(params["ema_fast"])>=int(params["ema_slow"]):
                    continue
                for symbol in a.symbols:
                    raw,fund=market_data[symbol]
                    for tf in a.timeframes:
                        signals=make_grid_signals(raw,model,tf,fund if model=="M5" else None,params)
                        trades=fast_backtest(signals,fund,symbol,model,tf,a.fee_bps,a.slippage_bps,a.rr)
                        base={"stage":3,"model":model,"factor":factor,"value":value,
                              "profile_track":profile_index,"symbol":symbol,"timeframe":tf,
                              "parameters_json":json.dumps(params,sort_keys=True)}
                        for label,lo,hi in [("development",2021,2024),("holdout_2025",2025,2025),("holdout_2026",2026,2026)]:
                            base.update({f"{label}_{k}":v for k,v in metrics_for_period(trades,lo,hi).items()})
                        years=pd.to_datetime(trades["exit_time"],utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
                        for year in range(2021,2027):
                            met=summarize(trades[years==year]) if not trades.empty else summarize(trades)
                            base.update({f"y{year}_{k}":v for k,v in met.items()})
                        factor_rows.append(base)
                        print(f"PFI STAGE 3 PROGRESS {model} {factor} track={profile_index} value={value} {symbol} {tf}",flush=True)
        ranking=value_rank_table(factor_rows,factor)
        ranking.to_csv(out/f"pfi_stage3_{model}_{factor}_ranking.csv",index=False)
        factor_frame=pd.DataFrame(factor_rows)
        factor_frame.to_csv(out/f"pfi_stage3_{model}_{factor}_results.csv",index=False)
        all_rankings.append(ranking)
        all_results.extend(factor_rows)
        # Carry the three best factor values forward, rank-aligned to the three tracks.
        selected=list(ranking["value"].head(3))
        while len(selected)<3:
            selected.append(selected[0])
        for i in range(3):
            profiles[i][factor]=selected[i]
        snapshot={"model":model,"factor_completed":factor,"factor_index":factor_index,
                  "selected_top3_values":selected,"profiles":profiles,
                  "ranking":ranking.to_dict(orient="records")}
        (out/f"pfi_stage3_{model}_progress.json").write_text(json.dumps(snapshot,indent=2,default=str))
        print(f"PFI STAGE 3 FACTOR COMPLETE {model} {factor}; retained top3={selected}",flush=True)
    pd.concat(all_rankings,ignore_index=True).to_csv(out/f"pfi_stage3_{model}_all_factor_rankings.csv",index=False)
    pd.DataFrame(all_results).to_csv(out/f"pfi_stage3_{model}_all_factor_results.csv",index=False)
    summary={"method":"Sequential one-factor PFI with three rank-aligned candidate profiles",
      "stage":3,"model":model,"period":{"start_inclusive":a.start,"end_exclusive":a.end},
      "development_years":"2021-2024","chronological_holdouts":["2025","2026 YTD"],
      "symbols":a.symbols,"timeframes":a.timeframes,"initial_stage1_top3":spec["stage1"],
      "stage2_top3":spec["stage2"],"remaining_factors_tested_in_order":spec["remaining"],
      "factor_variants":{f:GRID[model][f] for f in spec["remaining"]},
      "final_three_profiles":profiles,"planned_rr":a.rr,"fee_bps_per_side":a.fee_bps,
      "slippage_bps_per_side":a.slippage_bps,"data_quality":qualities,"funding_sources":funding_meta,
      "selection_method":"For each factor, test every listed variant independently across three retained profiles, two symbols and two timeframes. Rank values by average rank across development PF, development net-R, both chronological holdout PFs and development drawdown. Carry the top three values forward as three rank-aligned profiles. Binary factors have only two unique variants; the leading value is repeated only to preserve three profile tracks.",
      "warning":"This is a sequential screening stage, not final validation. Review trade counts, year-by-year stability and both holdouts; do not choose values on development PF alone. M5 remains provisional until funding data is independently verified."}
    (out/f"pfi_stage3_{model}_summary.json").write_text(json.dumps(summary,indent=2,default=str))
    print(f"PFI STAGE 3 ALL FACTORS COMPLETE {model}",flush=True)
    print(json.dumps(summary,indent=2,default=str),flush=True)

if __name__=="__main__": main()

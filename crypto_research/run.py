from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
import pandas as pd
from .data import acquire_klines, acquire_funding, quality_report
from .grid import make_grid_signals, parameter_count, shard_parameter_sets, invalid_reason
from .backtest import run_backtest, summarize

def _config_id(model,params):
    raw=json.dumps(params,sort_keys=True,separators=(",",":"))
    return hashlib.sha1((model+raw).encode()).hexdigest()[:12]

def main():
    p=argparse.ArgumentParser(description="Exhaustive crypto futures M1/M2/M4/M5 grid")
    p.add_argument("--start",default="2024-01-01"); p.add_argument("--end",default="2025-01-01")
    p.add_argument("--symbols",nargs="+",default=["BTCUSDT","ETHUSDT"])
    p.add_argument("--timeframes",nargs="+",choices=["5m","15m"],default=["5m","15m"])
    p.add_argument("--models",nargs="+",choices=["M1","M2","M4","M5"],default=["M1","M2","M4","M5"])
    p.add_argument("--fee-bps",type=float,default=5.0); p.add_argument("--slippage-bps",type=float,default=2.0)
    p.add_argument("--rr",type=float,default=2.0); p.add_argument("--out",default="artifacts")
    p.add_argument("--shard-index",type=int,default=0); p.add_argument("--shard-count",type=int,default=1)
    p.add_argument("--keep-trades",action="store_true")
    a=p.parse_args()
    if a.end<=a.start: p.error("--end must be later than --start")
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    quality=[]; funding_sources={}; summaries=[]; trade_parts=[]
    expected=sum((parameter_count(m)*(a.shard_index+1)//a.shard_count-
                  parameter_count(m)*a.shard_index//a.shard_count) for m in a.models)
    print(f"SHARD START index={a.shard_index}/{a.shard_count} expected_raw={expected}",flush=True)
    for sym in a.symbols:
        print(f"DATA {sym}: downloading 1m klines and funding",flush=True)
        raw=acquire_klines(sym,a.start,a.end); fund=acquire_funding(sym,a.start,a.end)
        quality.append(quality_report(raw,sym)); funding_sources[sym]=fund.attrs.get("source","unknown")
        fund.to_csv(out/f"{sym}_funding.csv")
        for tf in a.timeframes:
            for model in a.models:
                configs=list(shard_parameter_sets(model,a.shard_index,a.shard_count))
                print(f"MODEL START {sym} {tf} {model} shard={a.shard_index} raw_configs={len(configs)}",flush=True)
                for local_i,(global_i,params) in enumerate(configs,1):
                    cid=_config_id(model,params); invalid=invalid_reason(model,params)
                    base={"config_id":cid,"global_config_index":global_i,"model":model,
                          "symbol":sym,"timeframe":tf,"parameters_json":json.dumps(params,sort_keys=True)}
                    if invalid:
                        stats={"status":"SKIPPED_INVALID","skip_reason":invalid,"trades":0,"wins":0,
                               "losses":0,"win_rate_pct":0.0,"profit_factor":None,
                               "net_return_pct":0.0,"net_bps":0.0,"net_R":0.0,"max_drawdown_pct":0.0}
                    else:
                        sig=make_grid_signals(raw,model,tf,fund if model=="M5" else None,params)
                        trades=run_backtest(sig,fund,sym,model,tf,a.fee_bps,a.slippage_bps,a.rr)
                        stats=summarize(trades) if not trades.empty else summarize(pd.DataFrame())
                        stats["status"]="COMPLETED"; stats["skip_reason"]=""
                        if a.keep_trades and not trades.empty:
                            trades=trades.copy(); trades["config_id"]=cid
                            trades["parameters_json"]=json.dumps(params,sort_keys=True)
                            trade_parts.append(trades)
                    summaries.append({**base,**stats})
                    if local_i%100==0:
                        pd.DataFrame(summaries).to_csv(out/"grid_results_partial.csv",index=False)
                        print(f"PROGRESS {sym} {tf} {model} {local_i}/{len(configs)}",flush=True)
                print(f"MODEL COMPLETE {sym} {tf} {model}",flush=True)
    result=pd.DataFrame(summaries)
    result.to_csv(out/"grid_results.csv",index=False)
    if a.keep_trades and trade_parts:
        pd.concat(trade_parts,ignore_index=True).to_csv(out/"grid_trades.csv",index=False)
    valid=result[result.status=="COMPLETED"]
    if not valid.empty:
        ranked=valid.sort_values(["symbol","timeframe","model","profit_factor","net_return_pct"],
                                 ascending=[True,True,True,False,False],na_position="last")
        ranked.groupby(["symbol","timeframe","model"],as_index=False,group_keys=False).head(25).to_csv(out/"top25_per_model.csv",index=False)
    else: pd.DataFrame().to_csv(out/"top25_per_model.csv",index=False)
    report={"period":{"start_inclusive":a.start,"end_exclusive":a.end},"symbols":a.symbols,
      "timeframes":a.timeframes,"models":a.models,"planned_rr":a.rr,
      "fee_bps_per_side":a.fee_bps,"slippage_bps_per_side":a.slippage_bps,
      "shard":{"index":a.shard_index,"count":a.shard_count},
      "expected_raw_configurations_per_symbol_timeframe":{m:parameter_count(m) for m in a.models},
      "rows_written":len(result),"completed_valid_configurations":int((result.status=="COMPLETED").sum()),
      "skipped_invalid_configurations":int((result.status=="SKIPPED_INVALID").sum()),
      "data_quality":quality,"funding_sources":funding_sources,
      "warning":"In-sample ranking is descriptive only. Select candidates using a development period, then evaluate on an untouched chronological holdout. Third-party funding fallback is unverified until independently cross-checked."}
    (out/"grid_run_summary.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)

if __name__=="__main__": main()

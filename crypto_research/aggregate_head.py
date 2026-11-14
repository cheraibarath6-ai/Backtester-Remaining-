from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

def pf(values):
    x = pd.to_numeric(values, errors="coerce").dropna()
    gains = float(x[x > 0].sum()); losses = abs(float(x[x < 0].sum()))
    return gains / losses if losses else (None if gains == 0 else float("inf"))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="input-artifacts"); p.add_argument("--out",default="head_results")
    p.add_argument("--expected-symbols",nargs="+",default=["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","LINKUSDT","LTCUSDT","AVAXUSDT"])
    a=p.parse_args(); root=Path(a.input); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    summaries=[]; ledgers=[]; triggers=[]
    for path in root.rglob("*_summary.json"):
        row=json.loads(path.read_text()); summaries.append(row); sym=row.get("symbol")
        tf=path.parent/f"{sym}_trades.csv"; qf=path.parent/f"{sym}_trigger_audit.csv"
        if tf.exists():
            t=pd.read_csv(tf)
            if not t.empty: ledgers.append(t)
        if qf.exists():
            q=pd.read_csv(qf)
            if not q.empty: q["symbol"]=sym; triggers.append(q)
    sdf=pd.DataFrame(summaries)
    if sdf.empty: raise RuntimeError("No symbol summaries found")
    sdf.to_csv(out/"head_per_symbol_results.csv",index=False)
    all_t=pd.concat(ledgers,ignore_index=True) if ledgers else pd.DataFrame()
    if not all_t.empty:
        all_t.to_csv(out/"head_complete_trade_ledger.csv",index=False)
        valid=all_t.loc[~all_t.exit_reason.isin(["DATA_GAP","END_OF_SAMPLE"])].copy()
        valid["exit_time"]=pd.to_datetime(valid.exit_time,utc=True)
        valid["year"]=valid.exit_time.dt.year
        yearly=valid.groupby("year").agg(trades=("net_bps","size"),net_bps=("net_bps","sum"),net_R=("net_R","sum"),win_rate_pct=("net_bps",lambda s:float((s>0).mean()*100)),profit_factor=("net_bps",pf)).reset_index()
        yearly.to_csv(out/"head_yearly_trade_stream.csv",index=False)
        bysym=valid.groupby("symbol").agg(trades=("net_bps","size"),net_bps=("net_bps","sum"),net_R=("net_R","sum"),win_rate_pct=("net_bps",lambda s:float((s>0).mean()*100)),profit_factor=("net_bps",pf)).reset_index()
        bysym.to_csv(out/"head_symbol_trade_stream.csv",index=False)
        overall={"trades":int(len(valid)),"wins":int((valid.net_bps>0).sum()),"losses":int((valid.net_bps<=0).sum()),"win_rate_pct":float((valid.net_bps>0).mean()*100),"profit_factor":pf(valid.net_bps),"net_bps":float(valid.net_bps.sum()),"net_R":float(valid.net_R.sum()),"avg_net_bps":float(valid.net_bps.mean()),"data_gap_records":int(all_t.exit_reason.eq("DATA_GAP").sum()),"end_of_sample_records":int(all_t.exit_reason.eq("END_OF_SAMPLE").sum()),"same_bar_conflict_trades":int(valid.same_bar_conflict.sum())}
    else: overall={"trades":0,"profit_factor":None,"net_bps":0.0,"net_R":0.0}
    tr=pd.concat(triggers,ignore_index=True) if triggers else pd.DataFrame()
    if not tr.empty: tr.to_csv(out/"head_trigger_audit_all_symbols.csv",index=False)
    found=set(sdf.symbol.astype(str)); missing=sorted(set(a.expected_symbols)-found)
    dq=sdf[["symbol","start_inclusive","end_exclusive","funding_source","funding_rows","funding_max_gap_hours"]].copy()
    dq["candle_coverage_pct"]=sdf.candle_quality.map(lambda x:x.get("coverage_pct") if isinstance(x,dict) else None)
    dq["actual_data_start"]=sdf.candle_quality.map(lambda x:x.get("start") if isinstance(x,dict) else None)
    dq["actual_data_end"]=sdf.candle_quality.map(lambda x:x.get("end") if isinstance(x,dict) else None)
    dq.to_csv(out/"head_data_quality.csv",index=False)
    report={"engine":"HEAD","logic":"OR: any one of M6/M8/M14/M12/M15 triggers; no voting or confirmation","timeframe":"4h","requested_window":[sdf.start_inclusive.min(),sdf.end_exclusive.max()],"expected_symbols":a.expected_symbols,"completed_symbols":sorted(found),"missing_symbols":missing,"all_symbols_completed":not missing,"per_symbol_summaries":summaries,"aggregate_trade_stream_diagnostic_not_portfolio":overall,"caveat":"Cross-symbol trade-stream aggregation is not a capital-weighted portfolio return. Contract listing dates and candle coverage differ; inspect data-quality CSV."}
    (out/"HEAD_FIVE_YEAR_RESULTS.json").write_text(json.dumps(report,indent=2,default=str))
    lines=["# HEAD — five-model OR engine backtest","","A trigger from any one of M6, M8, M14, M12 or M15 is sufficient. No model voting or confirmation is used.","",f"Window: {report['requested_window'][0]} to {report['requested_window'][1]} (end exclusive)","Timeframe: 4h",f"Symbols completed: {len(found)}/{len(a.expected_symbols)}","","| Symbol | Trades | Net PF | Net bps | Net-R | Win rate | Candle coverage |","|---|---:|---:|---:|---:|---:|---:|"]
    for row in summaries:
        lines.append("| {0} | {1} | {2} | {3} | {4} | {5}% | {6}% |".format(row.get("symbol"),row.get("trades"),row.get("profit_factor"),row.get("net_bps"),row.get("net_R"),row.get("win_rate_pct"),(row.get("candle_quality") or {}).get("coverage_pct")))
    lines += ["","## Combined trade-stream diagnostic (not portfolio return)",f"- Valid trades: {overall.get('trades')}",f"- Net PF: {overall.get('profit_factor')}",f"- Net bps: {overall.get('net_bps')}",f"- Net-R: {overall.get('net_R')}",f"- Win rate: {overall.get('win_rate_pct')}%",f"- Same-bar conflict trades: {overall.get('same_bar_conflict_trades')}","","## Audit files","- head_complete_trade_ledger.csv","- head_trigger_audit_all_symbols.csv","- head_yearly_trade_stream.csv","- head_symbol_trade_stream.csv","- head_data_quality.csv","","Cross-symbol sums are not portfolio returns. DATA_GAP and END_OF_SAMPLE rows remain audited but are excluded from performance metrics."]
    (out/"HEAD_FIVE_YEAR_RESULTS.md").write_text("\n".join(lines)+"\n")
    print(f"HEAD AGGREGATE symbols={len(found)}/{len(a.expected_symbols)} trades={overall.get('trades')} PF={overall.get('profit_factor')} net_bps={overall.get('net_bps')}",flush=True)
    if missing: raise RuntimeError(f"Incomplete asset universe: {missing}")
if __name__=="__main__": main()

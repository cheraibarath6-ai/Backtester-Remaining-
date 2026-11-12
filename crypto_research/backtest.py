from __future__ import annotations
import pandas as pd

def run_backtest(bars,funding,symbol,model,timeframe,fee_bps=5.0,slippage_bps=2.0,rr=2.0,max_hold_bars=288):
    trades=[]; pos=None; ix=bars.index
    bar_minutes=5 if timeframe=="5m" else 15
    for i in range(1,len(bars)):
        row=bars.iloc[i]; ts=ix[i]; prev=bars.iloc[i-1]
        was_open=pos is not None
        if was_open:
            held=i-pos["entry_i"]; exit_px=None; reason=None
            if pos["side"]==1:
                stop_hit=row.low<=pos["stop"]; target_hit=row.high>=pos["target"]
            else:
                stop_hit=row.high>=pos["stop"]; target_hit=row.low<=pos["target"]
            # Conservative collision rule: stop wins if both barriers occur in one OHLC bar.
            if stop_hit: exit_px=pos["stop"]; reason="STOP"
            elif target_hit: exit_px=pos["target"]; reason="TARGET"
            elif held>=max_hold_bars: exit_px=float(row.close); reason="TIME"
            if exit_px is not None:
                exit_fill=exit_px*(1-pos["side"]*slippage_bps/10000)
                gross=pos["side"]*(exit_fill-pos["entry"])/pos["entry"]
                fees=2*fee_bps/10000
                fund_cost=0.0
                if funding is not None and not funding.empty:
                    ff=funding.loc[(funding.index>pos["entry_time"])&(funding.index<=ts)]
                    fund_cost=sum(pos["side"]*float(v) for v in ff.funding_rate)
                net=gross-fees-fund_cost
                risk=abs(pos["entry"]-pos["stop"])/pos["entry"]
                trades.append({"symbol":symbol,"model":model,"timeframe":timeframe,"side":"LONG" if pos["side"]==1 else "SHORT","entry_time":str(pos["entry_time"]),"exit_time":str(ts),"entry":pos["entry"],"exit":exit_fill,"stop":pos["stop"],"target":pos["target"],"exit_reason":reason,"gross_return_pct":gross*100,"fees_pct":fees*100,"funding_cost_pct":fund_cost*100,"net_return_pct":net*100,"net_bps":net*10000,"net_R":net/risk if risk else 0.0})
                pos=None
        # Do not re-enter at this bar's open after an intrabar exit. A new signal can enter next bar.
        if not was_open and pos is None and int(prev.get("signal",0))!=0:
            side=int(prev.signal); raw_entry=float(row.open)
            entry=raw_entry*(1+side*slippage_bps/10000)
            stop=float(prev.stop) if pd.notna(prev.stop) else float("nan")
            if not pd.notna(stop) or (side==1 and stop>=entry) or (side==-1 and stop<=entry): continue
            target=entry+side*rr*abs(entry-stop)
            entry_time=ts-pd.Timedelta(minutes=bar_minutes)
            pos={"side":side,"entry":entry,"stop":stop,"target":target,"entry_time":entry_time,"entry_i":i}
    if pos is not None:
        row=bars.iloc[-1]; ts=ix[-1]; px=float(row.close)*(1-pos["side"]*slippage_bps/10000)
        gross=pos["side"]*(px-pos["entry"])/pos["entry"]; fees=2*fee_bps/10000
        fund_cost=0.0
        if funding is not None and not funding.empty:
            ff=funding.loc[(funding.index>pos["entry_time"])&(funding.index<=ts)]
            fund_cost=sum(pos["side"]*float(v) for v in ff.funding_rate)
        net=gross-fees-fund_cost; risk=abs(pos["entry"]-pos["stop"])/pos["entry"]
        trades.append({"symbol":symbol,"model":model,"timeframe":timeframe,"side":"LONG" if pos["side"]==1 else "SHORT","entry_time":str(pos["entry_time"]),"exit_time":str(ts),"entry":pos["entry"],"exit":px,"stop":pos["stop"],"target":pos["target"],"exit_reason":"END_OF_SAMPLE","gross_return_pct":gross*100,"fees_pct":fees*100,"funding_cost_pct":fund_cost*100,"net_return_pct":net*100,"net_bps":net*10000,"net_R":net/risk if risk else 0.0})
    return pd.DataFrame(trades)

def summarize(t):
    if t.empty: return {"trades":0,"wins":0,"losses":0,"win_rate_pct":0.0,"profit_factor":0.0,"net_return_pct":0.0,"net_bps":0.0,"net_R":0.0,"max_drawdown_pct":0.0}
    t=t.sort_values("exit_time")
    w=t[t.net_bps>0]; l=t[t.net_bps<=0]; gp=float(w.net_bps.sum()); gl=abs(float(l.net_bps.sum()))
    eq=(1+t.net_return_pct/100).cumprod(); dd=(eq/eq.cummax()-1).min()*100
    return {"trades":int(len(t)),"wins":int(len(w)),"losses":int(len(l)),"win_rate_pct":round(100*len(w)/len(t),2),"profit_factor":round(gp/gl,4) if gl else None,"net_return_pct":round((eq.iloc[-1]-1)*100,4),"net_bps":round(float(t.net_bps.sum()),2),"net_R":round(float(t.net_R.sum()),3),"max_drawdown_pct":round(float(dd),3),"avg_trade_bps":round(float(t.net_bps.mean()),3),"funding_cost_pct":round(float(t.funding_cost_pct.sum()),4)}

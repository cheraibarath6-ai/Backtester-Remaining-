from __future__ import annotations
from itertools import product
import numpy as np
import pandas as pd

# Parameter values are deliberately explicit and kept in one auditable specification.
GRID = {
 "M1": {
  "swing_lookback":[10,20,30], "sweep_recency":[3,6,9],
  "max_sweep_depth_atr":[0.50,0.75,1.00], "displacement_atr":[0.90,1.10,1.30],
  "structure_lookback":[3,5,8], "adx_min":[12,18,24], "htf_4h":[False,True],
  "volume_ratio_min":[0.80,1.00,1.20], "stop_lookback":[3,5,7],
  "stop_buffer_atr":[0.05,0.15,0.25]},
 "M2": {
  "ema_fast":[10,20,30], "ema_slow":[50,100,200],
  "rsi_trigger":[50,55,60], "adx_min":[12,18,24],
  "di_spread_min":[0,2,5], "htf_4h":[False,True],
  "volume_ratio_min":[0.80,1.00,1.20], "stop_lookback":[5,10,15],
  "stop_buffer_atr":[0.05,0.15,0.25]},
 "M4": {
  "range_lookback":[10,20,30], "retest_tolerance_atr":[0.10,0.25,0.50],
  "max_retest_age":[3,6,10], "breakout_buffer_atr":[0.0,0.10,0.20],
  "adx_min":[12,18,24], "htf_4h":[False,True],
  "volume_ratio_min":[0.80,1.00,1.20], "stop_lookback":[3,5,8],
  "stop_buffer_atr":[0.05,0.15,0.25]},
 "M5": {
  "funding_lookback":[90,180,270], "funding_percentile":[0.10,0.20,0.30],
  "taker_imbalance":[0.52,0.55,0.58], "adx_min":[0,12,18],
  "htf_4h":[False,True], "volume_ratio_min":[0.80,1.00,1.20],
  "max_ema_distance_atr":[0.50,1.00,2.00], "stop_lookback":[5,8,12],
  "stop_buffer_atr":[0.05,0.15,0.25]}
}
RAW_COUNTS={"M1":39366,"M2":13122,"M4":13122,"M5":13122}

def parameter_sets(model):
    spec=GRID[model]
    keys=list(spec)
    return (dict(zip(keys,v)) for v in product(*(spec[k] for k in keys)))

def parameter_count(model):
    return RAW_COUNTS[model]

def invalid_reason(model,p):
    if model=="M2" and int(p["ema_fast"])>=int(p["ema_slow"]):
        return "INVALID_EMA_ORDER: fast EMA must be strictly below slow EMA"
    return None

_BAR_CACHE={}
_BIAS_CACHE={}
_FUND_CACHE={}

def _bars(raw,tf):
    key=(id(raw),tf)
    if key in _BAR_CACHE: return _BAR_CACHE[key].copy()
    rule={"5m":"5min","15m":"15min"}[tf]
    d=raw.resample(rule,label="right",closed="left").agg({
      "open":"first","high":"max","low":"min","close":"last","volume":"sum",
      "quote_volume":"sum","trades":"sum","taker_buy_base":"sum","taker_buy_quote":"sum"
    }).dropna(subset=["open","high","low","close"])
    c,h,l=d.close,d.high,d.low
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    d["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
    d["rsi"]=100-100/(1+gain/loss.replace(0,np.nan))
    up,down=h.diff(),-l.diff()
    pdm=up.where((up>down)&(up>0),0.0); mdm=down.where((down>up)&(down>0),0.0)
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/d.atr.replace(0,np.nan)
    mdi=100*mdm.ewm(alpha=1/14,adjust=False).mean()/d.atr.replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    d["adx"]=dx.ewm(alpha=1/14,adjust=False).mean(); d["pdi"]=pdi; d["mdi"]=mdi
    for n in (8,10,15,20,30,50,75,100,150,200): d[f"ema{n}"]=c.ewm(span=n,adjust=False).mean()
    d["taker_ratio"]=d.taker_buy_base/d.volume.replace(0,np.nan)
    d["volume_ratio"]=d.volume/d.volume.shift(1).rolling(20,min_periods=10).mean()
    _BAR_CACHE[key]=d
    return d.copy()

def _bias(raw,rule):
    key=(id(raw),rule)
    if key not in _BIAS_CACHE:
        h=raw.resample(rule,label="right",closed="left").agg({"close":"last"}).dropna()
        fast=h.close.ewm(span=50,adjust=False).mean()
        slow=h.close.ewm(span=200,adjust=False).mean()
        _BIAS_CACHE[key]=pd.Series(np.where(fast>slow,1,np.where(fast<slow,-1,0)),index=h.index)
    return _BIAS_CACHE[key]

def _htf(raw,d,side,on):
    one=_bias(raw,"1h").reindex(d.index,method="ffill").fillna(0).eq(side)
    if not on: return one
    four=_bias(raw,"4h").reindex(d.index,method="ffill").fillna(0).eq(side)
    return one & four

def _stop(d,side,n,b):
    return d.low.rolling(n,min_periods=n).min()-b*d.atr if side==1 else d.high.rolling(n,min_periods=n).max()+b*d.atr

def _penetration_ok(d,level,lag,side,cap_atr=0.25):
    ok=pd.Series(True,index=d.index)
    for step in range(lag):
        if side==1: ok &= d.low.shift(step)>=level-cap_atr*d.atr.shift(step)
        else: ok &= d.high.shift(step)<=level+cap_atr*d.atr.shift(step)
    return ok.fillna(False)

def _funding(f,lookback,pct):
    key=(id(f),lookback,pct,len(f))
    if key not in _FUND_CACHE:
        z=f[["funding_rate"]].sort_index().copy()
        z["lo"]=z.funding_rate.shift(1).rolling(lookback,min_periods=max(30,lookback//3)).quantile(pct)
        z["hi"]=z.funding_rate.shift(1).rolling(lookback,min_periods=max(30,lookback//3)).quantile(1-pct)
        _FUND_CACHE[key]=z
    return _FUND_CACHE[key]

def make_grid_signals(raw,model,tf,funding=None,params=None):
    p=params or {}
    reason=invalid_reason(model,p)
    if reason: raise ValueError(reason)
    d=_bars(raw,tf).copy(); d["signal"]=0; d["stop"]=np.nan
    a=d.atr.replace(0,np.nan)
    adx=float(p.get("adx_min",0)); vol=float(p.get("volume_ratio_min",0))
    if model=="M1":
        n=int(p["swing_lookback"]); rec=int(p["sweep_recency"])
        low=d.low.shift(1).rolling(n,min_periods=n).min()
        high=d.high.shift(1).rolling(n,min_periods=n).max()
        depth=float(p["max_sweep_depth_atr"])*a
        raw_l=(d.low<low)&(d.close>low)&((low-d.low)<=depth)
        raw_s=(d.high>high)&(d.close<high)&((d.high-high)<=depth)
        sweep_l=raw_l.shift(1).rolling(rec,min_periods=1).max().fillna(0).astype(bool)
        sweep_s=raw_s.shift(1).rolling(rec,min_periods=1).max().fillna(0).astype(bool)
        disp=(d.high-d.low)>=float(p["displacement_atr"])*a
        k=int(p["structure_lookback"])
        brk_l=d.close>d.high.shift(1).rolling(k,min_periods=k).max()
        brk_s=d.close<d.low.shift(1).rolling(k,min_periods=k).min()
        common=(d.adx>=adx)&(d.volume_ratio>=vol)
        long=sweep_l&brk_l&disp&common&_htf(raw,d,1,p["htf_4h"])
        short=sweep_s&brk_s&disp&common&_htf(raw,d,-1,p["htf_4h"])
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        n=int(p["stop_lookback"]); b=float(p["stop_buffer_atr"])
        d["stop"]=np.where(long,_stop(d,1,n,b),np.where(short,_stop(d,-1,n,b),np.nan))
    elif model=="M2":
        fast=int(p["ema_fast"]); slow=int(p["ema_slow"]); trigger=float(p["rsi_trigger"])
        short_trigger=100-trigger
        di=float(p["di_spread_min"])
        common=(d.adx>=adx)&(d.volume_ratio>=vol)
        long=(d[f"ema{fast}"]>d[f"ema{slow}"])&(d.close>d[f"ema{fast}"])&(d.rsi>trigger)&(d.rsi.shift(1)<=trigger)&((d.pdi-d.mdi)>=di)&common&_htf(raw,d,1,p["htf_4h"])
        short=(d[f"ema{fast}"]<d[f"ema{slow}"])&(d.close<d[f"ema{fast}"])&(d.rsi<short_trigger)&(d.rsi.shift(1)>=short_trigger)&((d.mdi-d.pdi)>=di)&common&_htf(raw,d,-1,p["htf_4h"])
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        n=int(p["stop_lookback"]); b=float(p["stop_buffer_atr"])
        d["stop"]=np.where(long,_stop(d,1,n,b),np.where(short,_stop(d,-1,n,b),np.nan))
    elif model=="M4":
        n=int(p["range_lookback"])
        top=d.high.shift(1).rolling(n,min_periods=n).max()
        bot=d.low.shift(1).rolling(n,min_periods=n).min()
        age=int(p["max_retest_age"]); tol=float(p["retest_tolerance_atr"])
        buf=float(p["breakout_buffer_atr"])
        up=d.close>(top+buf*a); dn=d.close<(bot-buf*a)
        lr=pd.Series(False,index=d.index); sr=lr.copy()
        for lag in range(1,age+1):
            lu,ld=top.shift(lag),bot.shift(lag)
            # Retest zone tolerance is optimized; penetration beyond 0.25 ATR remains a fixed failure cap.
            lr |= (up.shift(lag).fillna(False)&(d.low<=lu+tol*a)&(d.low>=lu-0.25*a)&(d.close>lu)&_penetration_ok(d,lu,lag,1))
            sr |= (dn.shift(lag).fillna(False)&(d.high>=ld-tol*a)&(d.high<=ld+0.25*a)&(d.close<ld)&_penetration_ok(d,ld,lag,-1))
        common=(d.adx>=adx)&(d.volume_ratio>=vol)
        long=lr&common&_htf(raw,d,1,p["htf_4h"])
        short=sr&common&_htf(raw,d,-1,p["htf_4h"])
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        n=int(p["stop_lookback"]); b=float(p["stop_buffer_atr"])
        d["stop"]=np.where(long,_stop(d,1,n,b),np.where(short,_stop(d,-1,n,b),np.nan))
    elif model=="M5":
        if funding is None or funding.empty: return d
        f=_funding(funding,int(p["funding_lookback"]),float(p["funding_percentile"]))
        d=pd.merge_asof(d.sort_index(),f,left_index=True,right_index=True,direction="backward")
        threshold=float(p["taker_imbalance"])
        distance=(d.close-d.ema20).abs()/a
        common=(d.adx>=adx)&(d.volume_ratio>=vol)&(distance<=float(p["max_ema_distance_atr"]))
        long=(d.funding_rate<=d.lo)&(d.taker_ratio>=threshold)&(d.close>d.ema20)&common&_htf(raw,d,1,p["htf_4h"])
        short=(d.funding_rate>=d.hi)&(d.taker_ratio<=(1-threshold))&(d.close<d.ema20)&common&_htf(raw,d,-1,p["htf_4h"])
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        n=int(p["stop_lookback"]); b=float(p["stop_buffer_atr"])
        d["stop"]=np.where(long,_stop(d,1,n,b),np.where(short,_stop(d,-1,n,b),np.nan))
    else: raise ValueError(model)
    d["signal"]=d.signal.fillna(0).astype(int)
    return d

def shard_parameter_sets(model,shard_index=0,shard_count=1):
    if shard_count<1 or not 0<=shard_index<shard_count: raise ValueError("Invalid shard")
    start=parameter_count(model)*shard_index//shard_count
    end=parameter_count(model)*(shard_index+1)//shard_count
    for i,p in enumerate(parameter_sets(model)):
        if start<=i<end: yield i,p

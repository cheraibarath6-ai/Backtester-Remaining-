from __future__ import annotations
import numpy as np
import pandas as pd

def add_indicators(d):
    x=d.copy(); c,h,l=x.close,x.high,x.low
    x["ema20"]=c.ewm(span=20,adjust=False).mean()
    x["ema50"]=c.ewm(span=50,adjust=False).mean()
    x["ema200"]=c.ewm(span=200,adjust=False).mean()
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean()
    loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    rs=gain/loss.replace(0,np.nan); x["rsi"]=100-100/(1+rs)
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    x["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
    up,down=h.diff(),-l.diff()
    pdm=up.where((up>down)&(up>0),0.0); mdm=down.where((down>up)&(down>0),0.0)
    pdi=100*pdm.ewm(alpha=1/14,adjust=False).mean()/x.atr.replace(0,np.nan)
    mdi=100*mdm.ewm(alpha=1/14,adjust=False).mean()/x.atr.replace(0,np.nan)
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    x["adx"]=dx.ewm(alpha=1/14,adjust=False).mean(); x["pdi"]=pdi; x["mdi"]=mdi
    x["taker_ratio"]=x.taker_buy_base/x.volume.replace(0,np.nan)
    return x

def higher_bias(raw):
    h=raw.resample("1h",label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last"}).dropna()
    fast=h.close.ewm(span=50,adjust=False).mean(); slow=h.close.ewm(span=200,adjust=False).mean()
    b=pd.Series(np.where(fast>slow,1,np.where(fast<slow,-1,0)),index=h.index)
    # A right-labelled 1h value is not visible until that hour has closed.
    return b

def make_signals(raw,model,tf,funding=None):
    rule={"5m":"5min","15m":"15min"}[tf]
    d=raw.resample(rule,label="right",closed="left").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum","quote_volume":"sum","trades":"sum","taker_buy_base":"sum","taker_buy_quote":"sum"}).dropna(subset=["open","high","low","close"])
    d=add_indicators(d)
    b=higher_bias(raw).reindex(d.index,method="ffill").fillna(0)
    d["bias"]=b; d["signal"]=0; d["stop"]=np.nan
    atr=d.atr.replace(0,np.nan); prior_hi=d.high.shift(1).rolling(20).max(); prior_lo=d.low.shift(1).rolling(20).min()
    if model=="M1":
        sweep_l=((d.low<prior_lo)&(d.close>prior_lo)).shift(1).rolling(6).max().fillna(0).astype(bool)
        sweep_s=((d.high>prior_hi)&(d.close<prior_hi)).shift(1).rolling(6).max().fillna(0).astype(bool)
        disp=(d.high-d.low)>=1.1*atr
        brk_l=d.close>d.high.shift(1).rolling(5).max()
        brk_s=d.close<d.low.shift(1).rolling(5).min()
        long=sweep_l&brk_l&disp&(b==1); short=sweep_s&brk_s&disp&(b==-1)
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        d["stop"]=np.where(long,d.low.rolling(6).min()-.15*atr,np.where(short,d.high.rolling(6).max()+.15*atr,np.nan))
    elif model=="M2":
        long=(d.ema50>d.ema200)&(d.close>d.ema20)&(d.rsi>55)&(d.rsi.shift(1)<=55)&(d.adx>20)&(d.pdi>d.mdi)&(b==1)
        short=(d.ema50<d.ema200)&(d.close<d.ema20)&(d.rsi<45)&(d.rsi.shift(1)>=45)&(d.adx>20)&(d.mdi>d.pdi)&(b==-1)
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        d["stop"]=np.where(long,d.low.rolling(10).min()-.1*atr,np.where(short,d.high.rolling(10).max()+.1*atr,np.nan))
    elif model=="M3":
        rng=d.high-d.low; body=(d.close-d.open).abs()/rng.replace(0,np.nan)
        imp_l=(rng>1.4*atr)&(body>.62)&(d.close>d.open)
        imp_s=(rng>1.4*atr)&(body>.62)&(d.close<d.open)
        for lag in range(1,7):
            ih,il=d.high.shift(lag),d.low.shift(lag); ir=ih-il
            long=(d.low<=ih-.382*ir)&(d.low>=ih-.786*ir)&(d.close>ih-.5*ir)&(d.close>d.open)&imp_l.shift(lag).fillna(False)&(b==1)
            short=(d.high>=il+.382*ir)&(d.high<=il+.786*ir)&(d.close<il+.5*ir)&(d.close<d.open)&imp_s.shift(lag).fillna(False)&(b==-1)
            d.loc[long&(d.signal==0),"signal"]=1; d.loc[short&(d.signal==0),"signal"]=-1
        d["stop"]=np.where(d.signal==1,d.low.rolling(5).min()-.1*atr,np.where(d.signal==-1,d.high.rolling(5).max()+.1*atr,np.nan))
    elif model=="M4":
        top=d.high.shift(2).rolling(20).max(); bot=d.low.shift(2).rolling(20).min()
        long=(d.close.shift(1)>top)&(d.low<=top*1.002)&(d.close>top)&(b==1)
        short=(d.close.shift(1)<bot)&(d.high>=bot*.998)&(d.close<bot)&(b==-1)
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        d["stop"]=np.where(long,d.low.rolling(8).min()-.1*atr,np.where(short,d.high.rolling(8).max()+.1*atr,np.nan))
    elif model=="M5":
        if funding is None or funding.empty: return d
        f=funding[["funding_rate"]].copy().sort_index()
        f["funding_low"]=f.funding_rate.rolling(270,min_periods=30).quantile(.10)
        f["funding_high"]=f.funding_rate.rolling(270,min_periods=30).quantile(.90)
        d=pd.merge_asof(d.sort_index(),f,left_index=True,right_index=True,direction="backward")
        long=(d.funding_rate<d.funding_low)&(d.taker_ratio>.58)&(d.close>d.ema20)&(b==1)
        short=(d.funding_rate>d.funding_high)&(d.taker_ratio<.42)&(d.close<d.ema20)&(b==-1)
        d.loc[long,"signal"]=1; d.loc[short,"signal"]=-1
        d["stop"]=np.where(long,d.low.rolling(8).min()-.1*atr,np.where(short,d.high.rolling(8).max()+.1*atr,np.nan))
    else: raise ValueError(model)
    d["signal"]=d.signal.fillna(0).astype(int)
    return d

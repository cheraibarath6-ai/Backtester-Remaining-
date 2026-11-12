from __future__ import annotations
import time, zipfile, io
from pathlib import Path
import requests
import pandas as pd

BASE = "https://data.binance.vision/data/futures/um/monthly"
COLS = ["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]

def months(start, end):
    return pd.date_range(pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC"), freq="MS", inclusive="left")

def get_zip(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 100:
        return dest
    for attempt in range(4):
        try:
            r=requests.get(url,timeout=90)
            if r.status_code==404: return None
            r.raise_for_status()
            if not r.content.startswith(b"PK"): raise ValueError("Archive response is not ZIP")
            dest.write_bytes(r.content)
            return dest
        except Exception:
            if attempt==3: raise
            time.sleep(2*(attempt+1))

def read_zip(path: Path):
    with zipfile.ZipFile(path) as z:
        csvs=[n for n in z.namelist() if n.endswith(".csv")]
        if not csvs: raise ValueError(f"No CSV in {path}")
        with z.open(csvs[0]) as f: d=pd.read_csv(f,header=None)
    d=d.iloc[:,:12]; d.columns=COLS
    # Binance archive CSVs may include a header row; discard non-numeric timestamps safely.
    open_ms=pd.to_numeric(d["open_time"],errors="coerce")
    d=d.loc[open_ms.notna()].copy()
    d["open_time"]=pd.to_datetime(open_ms.loc[d.index],unit="ms",utc=True)
    for c in ["open","high","low","close","volume","quote_volume","taker_buy_base","taker_buy_quote"]:
        d[c]=pd.to_numeric(d[c],errors="coerce")
    d["trades"]=pd.to_numeric(d.trades,errors="coerce").fillna(0)
    d=d.dropna(subset=["open","high","low","close","volume"])
    return d.sort_values("open_time").drop_duplicates("open_time").set_index("open_time")

def acquire_klines(symbol,start,end,root=Path("data")):
    parts=[]
    for m in months(start,end):
        ym=m.strftime("%Y-%m"); name=f"{symbol}-1m-{ym}.zip"
        url=f"{BASE}/klines/{symbol}/1m/{name}"
        p=get_zip(url,root/"raw"/"klines"/symbol/name)
        if p: parts.append(read_zip(p))
    if not parts: raise RuntimeError(f"No monthly kline archives found for {symbol}")
    d=pd.concat(parts).sort_index()
    d=d[~d.index.duplicated(keep="last")]
    return d.loc[(d.index>=pd.Timestamp(start,tz="UTC"))&(d.index<pd.Timestamp(end,tz="UTC"))]

def acquire_funding(symbol,start,end):
    # Prefer Binance's official historical endpoint. Some hosted CI regions receive HTTP 451;
    # in that case use the public third-party archive as a clearly labelled research fallback.
    url="https://fapi.binance.com/fapi/v1/fundingRate"
    cursor=int(pd.Timestamp(start,tz="UTC").timestamp()*1000)
    end_ms=int(pd.Timestamp(end,tz="UTC").timestamp()*1000)
    rows=[]; source="binance_official_api"
    try:
        while cursor<end_ms:
            r=requests.get(url,params={"symbol":symbol,"startTime":cursor,"endTime":end_ms,"limit":1000},timeout=30)
            r.raise_for_status(); batch=r.json()
            if not batch: break
            rows.extend(batch); nxt=int(batch[-1]["fundingTime"])+1
            if nxt<=cursor: break
            cursor=nxt; time.sleep(.12)
        d=pd.DataFrame(rows)
        if d.empty: raise RuntimeError("Official funding endpoint returned no rows")
        d["funding_time"]=pd.to_datetime(d.fundingTime.astype("int64"),unit="ms",utc=True)
        d["funding_rate"]=pd.to_numeric(d.fundingRate); d["mark_price"]=pd.to_numeric(d.markPrice)
        out=d.drop_duplicates("funding_time").set_index("funding_time")[["funding_rate","mark_price"]].sort_index()
    except Exception as official_error:
        fallback=f"https://huggingface.co/datasets/Crypt-dataset/Binance_Top40/resolve/main/funding/{symbol}.parquet"
        resp=requests.get(fallback,timeout=60); resp.raise_for_status()
        d=pd.read_parquet(io.BytesIO(resp.content))
        if not {"funding_time","funding_rate"}.issubset(d.columns):
            raise RuntimeError("Fallback funding dataset has an unexpected schema") from official_error
        d["funding_time"]=pd.to_datetime(pd.to_numeric(d.funding_time),unit="ms",utc=True)
        d["funding_rate"]=pd.to_numeric(d.funding_rate,errors="coerce")
        if "symbol" in d.columns: d=d[d.symbol==symbol]
        out=d.dropna(subset=["funding_rate"]).drop_duplicates("funding_time").set_index("funding_time")[["funding_rate"]].sort_index()
        out["mark_price"]=float("nan")
        source="third_party_huggingface_archive_unverified"
    out=out.loc[(out.index>=pd.Timestamp(start,tz="UTC"))&(out.index<pd.Timestamp(end,tz="UTC"))]
    out.attrs["source"]=source
    return out

def quality_report(d,symbol):
    expected=pd.date_range(d.index.min(),d.index.max(),freq="1min",tz="UTC")
    bad=((d.high<d[["open","close","low"]].max(axis=1))|(d.low>d[["open","close","high"]].min(axis=1))|(d.high<d.low)).sum()
    return {"symbol":symbol,"rows":len(d),"start":str(d.index.min()),"end":str(d.index.max()),"missing_minutes":len(expected.difference(d.index)),"duplicate_timestamps":int(d.index.duplicated().sum()),"bad_ohlc_rows":int(bad)}

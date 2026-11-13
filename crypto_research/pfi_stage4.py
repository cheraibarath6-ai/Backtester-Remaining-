from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from .data import acquire_klines, acquire_funding, quality_report
from .grid import make_grid_signals, invalid_reason
from .pfi import fast_backtest
from .backtest import summarize

# Stage 4: assemble complete profiles using the actual Stage 1 top-candidate
# rows, Stage 2 balanced top-three values, and Stage 3 factor shortlists.
# Each profile is evaluated as a complete configuration; no parameter is
# re-optimized during this validation stage.
PROFILES = {
  "M1": [
    {
      "profile": "P1",
      "parameters": {
        "swing_lookback": 60,
        "sweep_recency": 3,
        "max_sweep_depth_atr": 0.35,
        "displacement_atr": 1.6,
        "structure_lookback": 5,
        "adx_min": 24,
        "htf_4h": True,
        "volume_ratio_min": 1.2,
        "stop_lookback": 5,
        "stop_buffer_atr": 0.15
      }
    },
    {
      "profile": "P2",
      "parameters": {
        "swing_lookback": 12,
        "sweep_recency": 6,
        "max_sweep_depth_atr": 0.5,
        "displacement_atr": 1.6,
        "structure_lookback": 8,
        "adx_min": 18,
        "htf_4h": False,
        "volume_ratio_min": 1,
        "stop_lookback": 7,
        "stop_buffer_atr": 0.05
      }
    },
    {
      "profile": "P3",
      "parameters": {
        "swing_lookback": 50,
        "sweep_recency": 9,
        "max_sweep_depth_atr": 0.65,
        "displacement_atr": 1.6,
        "structure_lookback": 3,
        "adx_min": 12,
        "htf_4h": True,
        "volume_ratio_min": 0.8,
        "stop_lookback": 3,
        "stop_buffer_atr": 0.25
      }
    },
    {
      "profile": "BASELINE",
      "parameters": {
        "swing_lookback": 20,
        "sweep_recency": 6,
        "max_sweep_depth_atr": 0.65,
        "displacement_atr": 1.1,
        "structure_lookback": 5,
        "adx_min": 18,
        "htf_4h": False,
        "volume_ratio_min": 1,
        "stop_lookback": 5,
        "stop_buffer_atr": 0.15
      }
    }
  ],
  "M2": [
    {
      "profile": "P1",
      "parameters": {
        "ema_fast": 8,
        "ema_slow": 150,
        "rsi_trigger": 70,
        "adx_min": 18,
        "di_spread_min": 5,
        "htf_4h": True,
        "volume_ratio_min": 1,
        "stop_lookback": 15,
        "stop_buffer_atr": 0.15
      }
    },
    {
      "profile": "P2",
      "parameters": {
        "ema_fast": 8,
        "ema_slow": 200,
        "rsi_trigger": 68,
        "adx_min": 24,
        "di_spread_min": 0,
        "htf_4h": False,
        "volume_ratio_min": 0.8,
        "stop_lookback": 10,
        "stop_buffer_atr": 0.05
      }
    },
    {
      "profile": "P3",
      "parameters": {
        "ema_fast": 30,
        "ema_slow": 150,
        "rsi_trigger": 55,
        "adx_min": 12,
        "di_spread_min": 2,
        "htf_4h": True,
        "volume_ratio_min": 1.2,
        "stop_lookback": 5,
        "stop_buffer_atr": 0.25
      }
    },
    {
      "profile": "BASELINE",
      "parameters": {
        "ema_fast": 10,
        "ema_slow": 100,
        "rsi_trigger": 55,
        "adx_min": 18,
        "di_spread_min": 2,
        "htf_4h": False,
        "volume_ratio_min": 1,
        "stop_lookback": 10,
        "stop_buffer_atr": 0.15
      }
    }
  ],
  "M4": [
    {
      "profile": "P1",
      "parameters": {
        "range_lookback": 30,
        "retest_tolerance_atr": 0.1,
        "max_retest_age": 1,
        "breakout_buffer_atr": 0.2,
        "adx_min": 24,
        "htf_4h": True,
        "volume_ratio_min": 1.2,
        "stop_lookback": 5,
        "stop_buffer_atr": 0.25
      }
    },
    {
      "profile": "P2",
      "parameters": {
        "range_lookback": 25,
        "retest_tolerance_atr": 0.1,
        "max_retest_age": 3,
        "breakout_buffer_atr": 0.1,
        "adx_min": 18,
        "htf_4h": False,
        "volume_ratio_min": 0.8,
        "stop_lookback": 8,
        "stop_buffer_atr": 0.05
      }
    },
    {
      "profile": "P3",
      "parameters": {
        "range_lookback": 30,
        "retest_tolerance_atr": 0.2,
        "max_retest_age": 4,
        "breakout_buffer_atr": 0,
        "adx_min": 12,
        "htf_4h": True,
        "volume_ratio_min": 1,
        "stop_lookback": 3,
        "stop_buffer_atr": 0.15
      }
    },
    {
      "profile": "BASELINE",
      "parameters": {
        "range_lookback": 20,
        "retest_tolerance_atr": 0.25,
        "max_retest_age": 6,
        "breakout_buffer_atr": 0.1,
        "adx_min": 18,
        "htf_4h": False,
        "volume_ratio_min": 1,
        "stop_lookback": 5,
        "stop_buffer_atr": 0.15
      }
    }
  ],
  "M5": [
    {
      "profile": "P1",
      "parameters": {
        "funding_lookback": 720,
        "funding_percentile": 0.05,
        "taker_imbalance": 0.51,
        "adx_min": 18,
        "htf_4h": True,
        "volume_ratio_min": 1.2,
        "max_ema_distance_atr": 0.5,
        "stop_lookback": 12,
        "stop_buffer_atr": 0.05
      }
    },
    {
      "profile": "P2",
      "parameters": {
        "funding_lookback": 540,
        "funding_percentile": 0.05,
        "taker_imbalance": 0.53,
        "adx_min": 0,
        "htf_4h": False,
        "volume_ratio_min": 0.8,
        "max_ema_distance_atr": 1,
        "stop_lookback": 8,
        "stop_buffer_atr": 0.15
      }
    },
    {
      "profile": "P3",
      "parameters": {
        "funding_lookback": 60,
        "funding_percentile": 0.05,
        "taker_imbalance": 0.57,
        "adx_min": 12,
        "htf_4h": True,
        "volume_ratio_min": 1,
        "max_ema_distance_atr": 2,
        "stop_lookback": 5,
        "stop_buffer_atr": 0.25
      }
    },
    {
      "profile": "BASELINE",
      "parameters": {
        "funding_lookback": 180,
        "funding_percentile": 0.2,
        "taker_imbalance": 0.55,
        "adx_min": 12,
        "htf_4h": False,
        "volume_ratio_min": 1,
        "max_ema_distance_atr": 1,
        "stop_lookback": 8,
        "stop_buffer_atr": 0.15
      }
    }
  ]
}

def period_metrics(trades, lo, hi):
    if trades.empty:
        return summarize(trades)
    years=pd.to_datetime(trades["exit_time"],utc=True).dt.year
    return summarize(trades[(years>=lo)&(years<=hi)])

def main():
    ap=argparse.ArgumentParser(description="PFI Stage 4 — joint complete-profile validation")
    ap.add_argument("--start",default="2021-01-01")
    ap.add_argument("--end",default="2026-11-13")
    ap.add_argument("--symbols",nargs="+",default=["BTCUSDT","ETHUSDT"])
    ap.add_argument("--timeframes",nargs="+",choices=["5m","15m"],default=["5m","15m"])
    ap.add_argument("--model",required=True,choices=["M1","M2","M4","M5"])
    ap.add_argument("--fee-bps",type=float,default=5.0)
    ap.add_argument("--slippage-bps",type=float,default=2.0)
    ap.add_argument("--rr",type=float,default=2.0)
    ap.add_argument("--out",default="pfi_stage4_artifacts")
    a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    model=a.model
    profiles=PROFILES[model]
    rows=[]; qualities=[]; funding_meta={}
    market_data={}
    for symbol in a.symbols:
        print(f"PFI STAGE 4 DATA START {symbol} {a.start}..{a.end}",flush=True)
        raw=acquire_klines(symbol,a.start,a.end)
        fund=acquire_funding(symbol,a.start,a.end)
        qualities.append(quality_report(raw,symbol))
        funding_meta[symbol]=fund.attrs.get("source","unknown")
        fund.to_csv(out/f"{symbol}_funding.csv")
        market_data[symbol]=(raw,fund)
    (out/f"pfi_stage4_{model}_profiles.json").write_text(json.dumps(profiles,indent=2))
    for prof in profiles:
        pname=prof["profile"]; params=prof["parameters"]
        invalid=invalid_reason(model,params)
        if invalid: raise ValueError(f"{pname}: {invalid}")
        print(f"PFI STAGE 4 PROFILE START {model} {pname} {params}",flush=True)
        for symbol in a.symbols:
            raw,fund=market_data[symbol]
            for tf in a.timeframes:
                signals=make_grid_signals(raw,model,tf,fund if model=="M5" else None,params)
                trades=fast_backtest(signals,fund,symbol,model,tf,a.fee_bps,a.slippage_bps,a.rr)
                row={"stage":4,"model":model,"profile":pname,"symbol":symbol,"timeframe":tf,
                     "parameters_json":json.dumps(params,sort_keys=True)}
                for label,lo,hi in [("development",2021,2024),("holdout_2025",2025,2025),("holdout_2026",2026,2026)]:
                    row.update({f"{label}_{k}":v for k,v in period_metrics(trades,lo,hi).items()})
                years=pd.to_datetime(trades["exit_time"],utc=True).dt.year if not trades.empty else pd.Series(dtype=int)
                for year in range(2021,2027):
                    met=summarize(trades[years==year]) if not trades.empty else summarize(trades)
                    row.update({f"y{year}_{k}":v for k,v in met.items()})
                rows.append(row)
                print(f"PFI STAGE 4 PROGRESS {model} {pname} {symbol} {tf} trades={len(trades)}",flush=True)
    result=pd.DataFrame(rows)
    result.to_csv(out/f"pfi_stage4_{model}_profile_results.csv",index=False)
    metric_cols=["development_profit_factor","development_net_R","holdout_2025_profit_factor",
                 "holdout_2025_net_R","holdout_2026_profit_factor","holdout_2026_net_R",
                 "development_max_drawdown_pct"]
    summary=result.groupby("profile").agg(
      slices=("symbol","count"),
      development_trades=("development_trades","sum"),
      development_pf_median=("development_profit_factor","median"),
      development_net_R_median=("development_net_R","median"),
      development_win_rate_median=("development_win_rate_pct","median"),
      holdout_2025_trades=("holdout_2025_trades","sum"),
      holdout_2025_pf_median=("holdout_2025_profit_factor","median"),
      holdout_2025_net_R_median=("holdout_2025_net_R","median"),
      holdout_2026_trades=("holdout_2026_trades","sum"),
      holdout_2026_pf_median=("holdout_2026_profit_factor","median"),
      holdout_2026_net_R_median=("holdout_2026_net_R","median"),
      development_dd_median=("development_max_drawdown_pct","median")
    ).reset_index()
    ranks=[]
    for col,asc in [("development_profit_factor",False),("development_net_R",False),
                    ("holdout_2025_profit_factor",False),("holdout_2025_net_R",False),
                    ("holdout_2026_profit_factor",False),("holdout_2026_net_R",False),
                    ("development_max_drawdown_pct",False)]:
        ranks.append(result.groupby("profile")[col].median().rank(ascending=asc,method="average"))
    rank_frame=pd.concat(ranks,axis=1)
    summary["robust_average_rank"]=rank_frame.mean(axis=1).reindex(summary.profile).to_numpy()
    summary=summary.sort_values(["robust_average_rank","development_net_R_median"],ascending=[True,False])
    summary.to_csv(out/f"pfi_stage4_{model}_profile_ranking.csv",index=False)
    meta={"stage":4,"model":model,"method":"joint evaluation of three rank-aligned candidate profiles plus original baseline",
      "start_inclusive":a.start,"end_exclusive":a.end,"development":"2021-2024",
      "holdouts":["2025","2026 YTD"],"symbols":a.symbols,"timeframes":a.timeframes,
      "profiles":profiles,"planned_rr":a.rr,"fee_bps_per_side":a.fee_bps,
      "slippage_bps_per_side":a.slippage_bps,"data_quality":qualities,
      "funding_sources":funding_meta,
      "warning":"Stage 3 factor shortlists came from exploratory tests whose initial profiles were mis-seeded. Stage 4 rebuilds profiles using actual Stage 1 top_candidates and balanced Stage 2 top-three values, but Stage 3 marginal shortlists remain provisional. This is a candidate-profile comparison, not final out-of-sample validation. M5 funding source and coverage require independent verification."}
    (out/f"pfi_stage4_{model}_summary.json").write_text(json.dumps(meta,indent=2,default=str))
    print("PFI STAGE 4 COMPLETE "+model,flush=True)
    print(summary.to_string(index=False),flush=True)
    print(json.dumps(meta,indent=2,default=str),flush=True)

if __name__=="__main__": main()

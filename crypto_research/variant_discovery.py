from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import pandas as pd

from .backtest import completed_period_cohort, run_backtest, summarize
from .data import acquire_klines, quality_report
from .funding_patch import acquire_funding
from .independent_models import make_independent_signals

SYMBOLS = ("BTCUSDT", "ETHUSDT")
TIMEFRAME = "1h"
MODELS = ("M6", "M7", "M8", "M9", "M12", "M14", "M15")
TRAIN_START = "2024-01-01"
SPLIT = "2025-01-01"
END = "2026-01-01"


def variants():
    out = []
    def add(model, params, rr, hold, trail=None):
        out.append({
            "model": model, "parameters": params, "rr": rr,
            "hold_hours": hold, "trailing_atr_multiple": trail,
        })

    for n, vol, stop, rr, hold in itertools.product(
        (20, 35, 55), (0.8, 1.0), (1.5, 2.0), (1.5, 2.0, 2.5), (12, 24, 48)
    ):
        add("M6", {"donchian_period": n, "volume_ratio_min": vol, "stop_atr": stop}, rr, hold)

    for z, rsi, stop, hold in itertools.product(
        (1.5, 2.0), (30.0, 35.0), (1.0, 1.5), (6, 12, 24)
    ):
        add("M7", {"bb_z_entry": z, "rsi_long_max": rsi,
                   "rsi_short_min": 100.0-rsi, "stop_atr": stop}, None, hold)

    for lookback, breakout, expansion, stop, rr, hold in itertools.product(
        (50, 100), (20, 40), (1.0, 1.5), (1.5, 2.0), (1.5, 2.5), (12, 24)
    ):
        add("M8", {"squeeze_lookback": lookback, "squeeze_quantile": 0.20,
                   "breakout_period": breakout, "expansion_atr": expansion,
                   "volume_ratio_min": 0.8, "stop_atr": stop}, rr, hold)

    for taker, vol, adx, stop, rr, hold in itertools.product(
        (0.55, 0.60), (1.0, 1.2), (15.0, 20.0), (1.5, 2.0), (1.5, 2.5), (6, 12, 24)
    ):
        add("M9", {"taker_min": taker, "volume_ratio_min": vol,
                   "adx_min": adx, "stop_atr": stop}, rr, hold)

    for breakout, adx, stop, rr, hold in itertools.product(
        (20, 40), (18.0, 25.0), (1.5, 2.0), (1.5, 2.0, 2.5), (12, 24, 48)
    ):
        add("M12", {"breakout_period": breakout, "trend_adx_min": adx,
                    "range_adx_max": 18.0, "range_bb_z": 2.0,
                    "range_rsi": 35.0, "stop_atr": stop,
                    "range_stop_atr": 0.8}, rr, hold)

    for adx, di, mom, stop, rr, hold in itertools.product(
        (18.0, 24.0), (18.0, 25.0), (7, 14), (1.5, 2.0),
        (1.5, 2.0, 2.5), (12, 24, 48)
    ):
        add("M14", {"adx_min": adx, "di_min": di,
                    "momentum_lookback": mom, "stop_atr": stop}, rr, hold)

    for ao, macd, stop, trail, hold in itertools.product(
        (0.0, 0.03), (0.0, 0.03), (1.5, 2.0), (1.5, 2.0, 2.5), (12, 24, 48)
    ):
        add("M15", {"ao_cross_min_atr": ao, "macd_min_atr": macd,
                    "stop_atr": stop}, None, hold, trail)

    return out


def metrics_for(trades, start, end):
    cohort = completed_period_cohort(trades, start, end)
    return summarize(cohort), len(cohort)


def main():
    parser = argparse.ArgumentParser(description="BTC/ETH 1h frozen-grid discovery with 2025 holdout")
    parser.add_argument("--symbol", required=True, choices=SYMBOLS)
    parser.add_argument("--start", default=TRAIN_START)
    parser.add_argument("--split", default=SPLIT)
    parser.add_argument("--end", default=END)
    parser.add_argument("--warmup-hours", type=int, default=1200)
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--out", default="variant_discovery")
    args = parser.parse_args()

    start = pd.Timestamp(args.start, tz="UTC")
    split = pd.Timestamp(args.split, tz="UTC")
    end = pd.Timestamp(args.end, tz="UTC")
    if not start < split < end:
        parser.error("Require start < split < end")
    symbol = args.symbol
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    history_start = start - pd.Timedelta(hours=args.warmup_hours)
    print(f"DISCOVERY START {symbol}: {start} split={split} end={end} history={history_start}", flush=True)
    raw = acquire_klines(symbol, history_start, end)
    if raw.empty:
        raise RuntimeError(f"No official Binance 1m candles for {symbol}")
    funding = acquire_funding(symbol, raw.index.min(), end)
    source = funding.attrs.get("source", "unknown")
    gaps = funding.index.to_series().diff().dropna()
    max_gap = float(gaps.max().total_seconds()/3600) if not gaps.empty else None
    first_gap = float((funding.index.min()-raw.index.min()).total_seconds()/3600)
    last_gap = float((end-funding.index.max()).total_seconds()/3600)
    if (not source.startswith("binance_") or max_gap is None or max_gap > 8.5
            or first_gap > 8.5 or last_gap > 8.5):
        raise RuntimeError(
            f"Funding coverage failed closed: source={source}, max_gap={max_gap}, "
            f"first_gap={first_gap}, last_gap={last_gap}"
        )

    all_rows = []
    configs = variants()
    for number, cfg in enumerate(configs, 1):
        model = cfg["model"]
        bars = make_independent_signals(
            raw, model, TIMEFRAME, parameters=cfg["parameters"]
        )
        hold_bars = max(1, round(cfg["hold_hours"] * 60 / 60))
        trades = run_backtest(
            bars, funding, symbol, model, TIMEFRAME,
            fee_bps=args.fee_bps, slippage_bps=args.slippage_bps,
            rr=float(cfg["rr"]) if cfg["rr"] is not None else 2.0,
            max_hold_bars=hold_bars,
            trailing_atr_multiple=cfg["trailing_atr_multiple"],
            expected_end=args.end,
        )
        train, n_train = metrics_for(trades, start, split)
        test, n_test = metrics_for(trades, split, end)
        row = {
            "symbol": symbol, "timeframe": TIMEFRAME, "model": model,
            "variant_id": f"{model}_{number:04d}",
            "parameters": json.dumps(cfg["parameters"], sort_keys=True),
            "rr": cfg["rr"], "hold_hours": cfg["hold_hours"],
            "trailing_atr_multiple": cfg["trailing_atr_multiple"],
            "train_trades": n_train, "train_pf": train["profit_factor"],
            "train_pf_r": train["profit_factor_r"], "train_win_rate_pct": train["win_rate_pct"],
            "train_net_R": train["net_R"], "train_net_bps": train["net_bps"],
            "train_max_drawdown_R": train["max_drawdown_R"],
            "oos_trades": n_test, "oos_pf": test["profit_factor"],
            "oos_pf_r": test["profit_factor_r"], "oos_win_rate_pct": test["win_rate_pct"],
            "oos_net_R": test["net_R"], "oos_net_bps": test["net_bps"],
            "oos_max_drawdown_R": test["max_drawdown_R"],
            "fees_bps_per_side": args.fee_bps,
            "slippage_bps_per_side": args.slippage_bps,
            "funding_source": source, "funding_max_gap_hours": max_gap,
        }
        all_rows.append(row)
        if number % 50 == 0:
            print(f"{symbol}: completed {number}/{len(configs)} variants", flush=True)

    results = pd.DataFrame(all_rows)
    results.to_csv(outdir / f"{symbol}_all_variants.csv", index=False)

    # Select solely on 2024 training data. 2025 is not used for candidate selection.
    selected = []
    for model in MODELS:
        subset = results[(results.model == model) & (results.train_trades >= 20)].copy()
        subset = subset.sort_values(
            ["train_pf", "train_net_R", "train_trades"],
            ascending=[False, False, False], na_position="last",
        ).head(10)
        selected.append(subset)
    top = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame()
    if not top.empty:
        top["oos_screen_pass"] = (
            (top.oos_trades >= 20) & (top.oos_pf >= 1.10) & (top.oos_net_R > 0)
        )
        top["train_screen_pass"] = (
            (top.train_trades >= 20) & (top.train_pf >= 1.10) & (top.train_net_R > 0)
        )
    top.to_csv(outdir / f"{symbol}_training_selected_oos.csv", index=False)

    meta = {
        "symbol": symbol, "timeframe": TIMEFRAME,
        "train_window": [args.start, args.split],
        "untouched_oos_window": [args.split, args.end],
        "warmup_hours": args.warmup_hours,
        "raw_candle_rows": int(len(raw)),
        "raw_candle_quality": quality_report(raw.loc[(raw.index >= start) & (raw.index < end)], symbol, start, end),
        "funding_source": source, "funding_rows": int(len(funding)),
        "funding_first_gap_hours": first_gap, "funding_max_gap_hours": max_gap,
        "funding_last_gap_hours": last_gap,
        "fees_bps_per_side": args.fee_bps,
        "slippage_bps_per_side": args.slippage_bps,
        "variant_count": len(configs),
        "selection_rule": "Top 10 per model by 2024 PF among variants with >=20 completed training trades; 2025 held out from selection.",
        "oos_screen": "At least 20 completed OOS trades, PF >= 1.10, and net_R > 0; research screen only.",
        "execution": "1h completed-bar signal, next 1h open entry, stop-first OHLC, official funding, fee and slippage charged per side.",
        "models": list(MODELS),
    }
    (outdir / f"{symbol}_metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    print(f"DISCOVERY COMPLETE {symbol}: variants={len(results)} selected={len(top)}", flush=True)


if __name__ == "__main__":
    main()

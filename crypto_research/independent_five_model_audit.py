from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .backtest import run_backtest, summarize
from .data import acquire_klines, quality_report
from .funding_patch import acquire_funding
from .head_engine import HEAD_CONFIGS, OFFICIAL_FUNDING_SOURCES, TIMEFRAME, batch_history_start, _utc
from .independent_models import make_independent_signals

MODELS = ("M6", "M8", "M12", "M14", "M15")
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def main():
    parser = argparse.ArgumentParser(description="Independent frozen M6/M8/M12/M14/M15 audit on BTC and ETH")
    parser.add_argument("--start", default="2021-11-14")
    parser.add_argument("--end", default="2022-01-01")
    parser.add_argument("--symbol", required=True, choices=SYMBOLS)
    parser.add_argument("--warmup-bars", type=int, default=130)
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--out", default="independent_audit")
    args = parser.parse_args()

    start, end = _utc(args.start), _utc(args.end)
    if end <= start:
        parser.error("--end must be later than --start")
    history_start = batch_history_start(start, args.warmup_bars)
    symbol = args.symbol
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"INDEPENDENT AUDIT {symbol} {start}..{end} history={history_start}", flush=True)
    raw = acquire_klines(symbol, history_start, end)
    if raw.empty:
        raise RuntimeError(f"No official Binance candle data for {symbol} in requested period")
    funding = acquire_funding(symbol, raw.index.min(), end)
    source = funding.attrs.get("source", "unknown")
    gaps = funding.index.to_series().diff().dropna() if not funding.empty else pd.Series(dtype="timedelta64[ns]")
    max_gap = float(gaps.max().total_seconds() / 3600) if not gaps.empty else None
    first_gap = float((funding.index.min() - raw.index.min()).total_seconds() / 3600) if not funding.empty else None
    last_gap = float((end - funding.index.max()).total_seconds() / 3600) if not funding.empty else None
    if (funding.empty or source not in OFFICIAL_FUNDING_SOURCES or max_gap is None
            or max_gap > 8.5 or first_gap is None or first_gap < 0 or first_gap > 8.5
            or last_gap is None or last_gap < 0 or last_gap > 8.5):
        raise RuntimeError(
            f"Official funding failed closed: source={source}, rows={len(funding)}, "
            f"first_gap_hours={first_gap}, max_gap_hours={max_gap}, last_gap_hours={last_gap}"
        )

    results = []
    all_trades = []
    signal_audit = []
    for model in MODELS:
        cfg = HEAD_CONFIGS[model]
        bars = make_independent_signals(raw, model, TIMEFRAME, parameters=cfg["parameters"])
        signal_count = int((bars.signal.ne(0) & (bars.index >= start) & (bars.index < end)).sum())
        hold_bars = int(cfg["hold_hours"] / 4)
        trades = run_backtest(
            bars, funding, symbol, model, TIMEFRAME,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
            rr=float(cfg["rr"]) if cfg["rr"] is not None else 2.0,
            max_hold_bars=hold_bars,
            trailing_atr_multiple=cfg["trailing_atr_multiple"],
            expected_end=args.end,
        )
        if not trades.empty:
            exit_times = pd.to_datetime(trades.exit_time, utc=True)
            trades = trades.loc[(exit_times > start) & (exit_times <= end)].copy()
            trades["signal_count_in_window"] = signal_count
            all_trades.append(trades)
        else:
            trades = pd.DataFrame()
        metrics = summarize(trades)
        results.append({
            "symbol": symbol, "model": model, "timeframe": TIMEFRAME,
            "start_inclusive": args.start, "end_exclusive": args.end,
            "signal_bars": signal_count, **metrics,
            "rr": cfg["rr"], "hold_hours": cfg["hold_hours"],
            "trailing_atr_multiple": cfg["trailing_atr_multiple"],
            "fee_bps_per_side": args.fee_bps,
            "slippage_bps_per_side": args.slippage_bps,
            "funding_source": source, "funding_rows": int(len(funding)),
            "funding_max_gap_hours": max_gap,
        })
        signal_audit.append({"symbol": symbol, "model": model, "signal_bars": signal_count})
        print(
            f"{symbol} {model}: signals={signal_count} trades={metrics['trades']} "
            f"win_rate={metrics['win_rate_pct']} PF={metrics['profit_factor']} "
            f"net_R={metrics['net_R']} net_bps={metrics['net_bps']}",
            flush=True,
        )

    result_df = pd.DataFrame(results)
    result_df.to_csv(out / f"{symbol}_independent_model_results.csv", index=False)
    ledger = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    ledger.to_csv(out / f"{symbol}_independent_trade_ledger.csv", index=False)
    (out / f"{symbol}_audit_metadata.json").write_text(json.dumps({
        "symbol": symbol, "timeframe": TIMEFRAME,
        "start_inclusive": args.start, "end_exclusive": args.end,
        "history_start": str(history_start), "warmup_bars": args.warmup_bars,
        "candle_quality": quality_report(raw.loc[(raw.index >= start) & (raw.index < end)], symbol, start, end),
        "funding_source": source, "funding_rows": int(len(funding)),
        "funding_actual_start": str(funding.index.min()),
        "funding_actual_end": str(funding.index.max()),
        "funding_first_gap_hours": first_gap, "funding_max_gap_hours": max_gap,
        "funding_last_gap_hours": last_gap,
        "execution": "next 4h bar open; stop-first OHLC; same official funding; fee 5 bps and slippage 2 bps per side",
        "model_params": HEAD_CONFIGS,
    }, indent=2, default=str))
    print(f"COMPLETE {symbol}: {len(result_df)} standalone model rows, {len(ledger)} trade rows", flush=True)


if __name__ == "__main__":
    main()

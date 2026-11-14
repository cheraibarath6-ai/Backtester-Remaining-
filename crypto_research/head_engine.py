from __future__ import annotations

"""HEAD: OR-trigger crypto futures engine built from five frozen independent models.

A single model trigger is sufficient. Same-bar duplicate triggers are coalesced;
opposing same-bar triggers are resolved by documented deterministic priority.
Each accepted trigger retains that model's stop/target/holding/trailing rules.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import acquire_klines, quality_report
from .funding_patch import acquire_funding
from .independent_models import make_independent_signals
from .backtest import summarize

START_DEFAULT = "2021-11-14"
END_DEFAULT = "2026-11-14"
TIMEFRAME = "4h"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
           "DOGEUSDT", "ADAUSDT", "LINKUSDT", "LTCUSDT", "AVAXUSDT")
# Priority is used only if opposite directions fire on the same completed bar.
# It is not a confirmation rule; one trigger is sufficient.
MODEL_PRIORITY = ("M6", "M8", "M14", "M12", "M15")
HEAD_CONFIGS = {
    "M6": {
        "variant": "R2_DON55_VOL12_STOP30_RR30_H48",
        "parameters": {"donchian_period": 55, "volume_ratio_min": 1.2, "stop_atr": 3.0},
        "rr": 3.0, "hold_hours": 48, "trailing_atr_multiple": None,
    },
    "M8": {
        "variant": "R2_SQ20_BR40_EXP15_VOL10_STOP25_RR30_H48",
        "parameters": {"squeeze_lookback": 100, "squeeze_quantile": 0.20,
                       "breakout_period": 40, "expansion_atr": 1.5,
                       "volume_ratio_min": 1.0, "stop_atr": 2.5},
        "rr": 3.0, "hold_hours": 48, "trailing_atr_multiple": None,
    },
    "M12": {
        "variant": "R2_REGIME_BR40_STOP25_RANGE08_H72",
        "parameters": {"breakout_period": 40, "trend_adx_min": 25.0,
                       "range_adx_max": 18.0, "range_bb_z": 2.0,
                       "range_rsi": 35.0, "stop_atr": 2.5,
                       "range_stop_atr": 0.8},
        "rr": 2.5, "hold_hours": 72, "trailing_atr_multiple": None,
    },
    "M14": {
        "variant": "R2_ADX30_DI25_MOM21_STOP25_RR30_H48",
        "parameters": {"adx_min": 30.0, "di_min": 25.0,
                       "momentum_lookback": 21, "stop_atr": 2.5},
        "rr": 3.0, "hold_hours": 48, "trailing_atr_multiple": None,
    },
    "M15": {
        "variant": "R2_AO05_MACD05_STOP25_TRAIL25_H48",
        "parameters": {"ao_cross_min_atr": 0.05, "macd_min_atr": 0.05,
                       "stop_atr": 2.5},
        "rr": None, "hold_hours": 48, "trailing_atr_multiple": 2.5,
    },
}
OFFICIAL_FUNDING_SOURCES = {
    "binance_vision_official_monthly_archive",
    "binance_vision_archive_plus_official_api",
    "binance_official_api",
    "binance_vision_monthly_plus_daily_official_archive",
}


def combine_model_signals(model_frames: dict[str, pd.DataFrame], timeframe: str = TIMEFRAME):
    """Combine model signals using OR semantics; return bars plus trigger audit."""
    if not model_frames:
        raise ValueError("At least one model signal frame is required")
    if set(model_frames) - set(MODEL_PRIORITY):
        raise ValueError(f"Unexpected model(s): {sorted(set(model_frames) - set(MODEL_PRIORITY))}")
    first = next(iter(model_frames.values()))
    if not first.index.is_monotonic_increasing or first.index.has_duplicates:
        raise ValueError("Signal bars must have a unique increasing index")
    out = first.copy()
    out["signal"] = 0
    out["stop"] = np.nan
    out["target"] = np.nan
    out["head_source"] = ""
    out["trigger_sources"] = ""
    out["trigger_count"] = 0
    out["same_bar_conflict"] = False
    out["head_rr"] = np.nan
    out["head_hold_bars"] = np.nan
    out["head_trailing_atr_multiple"] = np.nan
    bars_per_hour = 60 / {"1m": 1, "3m": 3, "5m": 5, "15m": 15,
                          "30m": 30, "1h": 60, "2h": 120, "4h": 240}[timeframe]

    for model, frame in model_frames.items():
        if not frame.index.equals(out.index):
            raise ValueError(f"{model} bars do not align with the HEAD index")

    for ts in out.index:
        fired = []
        for model in MODEL_PRIORITY:
            frame = model_frames.get(model)
            if frame is None:
                continue
            direction = int(frame.at[ts, "signal"]) if pd.notna(frame.at[ts, "signal"]) else 0
            if direction:
                fired.append((model, direction))
        if not fired:
            continue
        # The priority only resolves a same-bar conflict or chooses the
        # parameter bundle when multiple same-direction models fire.
        chosen_model, chosen_side = fired[0]
        cfg = HEAD_CONFIGS[chosen_model]
        chosen_frame = model_frames[chosen_model]
        out.at[ts, "signal"] = chosen_side
        out.at[ts, "stop"] = float(chosen_frame.at[ts, "stop"])
        if "target" in chosen_frame and pd.notna(chosen_frame.at[ts, "target"]):
            out.at[ts, "target"] = float(chosen_frame.at[ts, "target"])
        out.at[ts, "head_source"] = chosen_model
        out.at[ts, "trigger_sources"] = ",".join(m for m, _ in fired)
        out.at[ts, "trigger_count"] = len(fired)
        out.at[ts, "same_bar_conflict"] = len({side for _, side in fired}) > 1
        out.at[ts, "head_rr"] = cfg["rr"] if cfg["rr"] is not None else np.nan
        out.at[ts, "head_hold_bars"] = max(1, int(round(cfg["hold_hours"] * bars_per_hour)))
        out.at[ts, "head_trailing_atr_multiple"] = (
            cfg["trailing_atr_multiple"]
            if cfg["trailing_atr_multiple"] is not None else np.nan
        )
    out["signal"] = out.signal.astype(int)
    return out


def run_head_backtest(bars, funding, symbol, timeframe="4h",
                      fee_bps=5.0, slippage_bps=2.0, expected_end=None):
    """Single-position next-bar-open executor with source-specific exit rules."""
    minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
               "1h": 60, "2h": 120, "4h": 240}[timeframe]
    delta = pd.Timedelta(minutes=minutes)
    if len(bars) < 2:
        return pd.DataFrame()
    if not bars.index.is_monotonic_increasing or bars.index.has_duplicates:
        raise ValueError("Bars must have a unique increasing index")

    opens = bars.open.to_numpy(float); highs = bars.high.to_numpy(float)
    lows = bars.low.to_numpy(float); closes = bars.close.to_numpy(float)
    signals = bars.signal.to_numpy(int); stops = bars.stop.to_numpy(float)
    targets = bars.target.to_numpy(float)
    rr_values = bars.head_rr.to_numpy(float)
    holds = bars.head_hold_bars.to_numpy(float)
    trails = bars.head_trailing_atr_multiple.to_numpy(float)
    index = bars.index
    f_index = funding.index if funding is not None and not funding.empty else None
    f_rates = pd.to_numeric(funding.funding_rate, errors="coerce").to_numpy(float) if f_index is not None else None
    f_marks = (pd.to_numeric(funding.mark_price, errors="coerce").to_numpy(float)
               if f_index is not None and "mark_price" in funding else
               np.full(len(funding), np.nan) if f_index is not None else None)
    trades = []
    pos = None

    def close_position(ts, raw_exit, reason, held):
        p = pos
        side = p["side"]; raw_entry = p["raw_entry"]; entry = p["entry"]
        exit_fill = raw_exit * (1 - side * slippage_bps / 10000)
        gross = side * (exit_fill - entry) / entry
        gross_move = side * (raw_exit - raw_entry) / raw_entry
        entry_slip = side * (entry - raw_entry) / raw_entry
        exit_slip = side * (raw_exit - exit_fill) / raw_entry
        fees = (fee_bps / 10000) * (1 + exit_fill / entry)
        funding_cost = 0.0
        if f_index is not None:
            first = f_index.searchsorted(p["entry_time"], side="left")
            last = f_index.searchsorted(ts, side="right")
            if last > first:
                rates = f_rates[first:last]
                marks = f_marks[first:last].copy()
                for j, event_time in enumerate(f_index[first:last]):
                    if not np.isfinite(marks[j]) or marks[j] <= 0:
                        bar_i = index.searchsorted(event_time, side="right") - 1
                        marks[j] = closes[bar_i] if bar_i >= 0 else entry
                valid = np.isfinite(rates) & np.isfinite(marks) & (marks > 0)
                if valid.any():
                    event_times = f_index[first:last][valid]
                    cashflows = side * rates[valid] * marks[valid] / entry
                    boundary = (event_times == p["entry_time"]) | (event_times == ts)
                    cashflows[boundary] = np.maximum(cashflows[boundary], 0.0)
                    funding_cost = float(cashflows.sum())
        net = gross - fees - funding_cost
        risk = abs(entry - p["initial_stop"]) / entry
        trades.append({
            "symbol": symbol, "model": "HEAD", "timeframe": timeframe,
            "side": "LONG" if side == 1 else "SHORT",
            "entry_time": str(p["entry_time"]), "exit_time": str(ts),
            "entry": entry, "exit": exit_fill, "raw_entry": raw_entry, "raw_exit": raw_exit,
            "gross_price_move_pct": gross_move * 100,
            "gross_price_move_bps": gross_move * 10000,
            "gross_return_pct": gross * 100,
            "fees_pct": fees * 100,
            "slippage_cost_pct": (entry_slip + exit_slip) * 100,
            "funding_cost_pct": funding_cost * 100,
            "net_return_pct": net * 100, "net_bps": net * 10000,
            "net_R": net / risk if risk else 0.0,
            "initial_stop": p["initial_stop"], "stop": p["stop"],
            "target": p["target"], "exit_reason": reason,
            "source_model": p["source_model"],
            "trigger_sources": p["trigger_sources"],
            "trigger_count": p["trigger_count"],
            "same_bar_conflict": p["same_bar_conflict"],
            "rr": p["rr"], "hold_bars_limit": p["hold_bars_limit"],
            "trailing_atr_multiple": p["trailing_atr_multiple"],
            "holding_bars": int(held), "holding_minutes": int(held * minutes),
        })

    for i in range(1, len(bars)):
        gap = index[i] - index[i - 1]
        if gap < delta:
            raise ValueError("Overlapping/sub-timeframe bars")
        if gap > delta:
            if pos is not None:
                close_position(index[i - 1], closes[i - 1], "DATA_GAP", i - 1 - pos["entry_i"] + 1)
                pos = None
            continue
        if pos is None and signals[i - 1] != 0:
            side = int(signals[i - 1]); raw_entry = opens[i]
            entry = raw_entry * (1 + side * slippage_bps / 10000)
            stop = stops[i - 1]
            if not np.isfinite(stop) or (side == 1 and stop >= entry) or (side == -1 and stop <= entry):
                continue
            target = targets[i - 1]
            rr = rr_values[i - 1]
            trail = trails[i - 1]
            if not np.isfinite(target) and np.isfinite(rr):
                target = entry + side * rr * abs(entry - stop)
            elif not np.isfinite(target) and np.isfinite(trail):
                target = np.nan
            elif not np.isfinite(target):
                continue
            if np.isfinite(target) and ((side == 1 and target <= entry) or (side == -1 and target >= entry)):
                continue
            hold = holds[i - 1]
            if not np.isfinite(hold):
                raise ValueError("A HEAD signal is missing its holding horizon")
            pos = {
                "side": side, "entry": entry, "raw_entry": float(raw_entry),
                "stop": float(stop), "initial_stop": float(stop),
                "target": float(target) if np.isfinite(target) else np.nan,
                "entry_time": index[i] - delta, "entry_i": i,
                "source_model": str(bars.head_source.iloc[i - 1]),
                "trigger_sources": str(bars.trigger_sources.iloc[i - 1]),
                "trigger_count": int(bars.trigger_count.iloc[i - 1]),
                "same_bar_conflict": bool(bars.same_bar_conflict.iloc[i - 1]),
                "rr": float(rr) if np.isfinite(rr) else None,
                "hold_bars_limit": int(hold),
                "trailing_atr_multiple": float(trail) if np.isfinite(trail) else None,
            }
        if pos is None:
            continue
        held = i - pos["entry_i"] + 1
        exit_px = None; reason = None
        if pos["side"] == 1:
            if opens[i] <= pos["stop"]: exit_px, reason = opens[i], "STOP_GAP"
            elif np.isfinite(pos["target"]) and opens[i] >= pos["target"]: exit_px, reason = pos["target"], "TARGET_GAP"
            else:
                stop_hit = lows[i] <= pos["stop"]
                target_hit = np.isfinite(pos["target"]) and highs[i] >= pos["target"]
        else:
            if opens[i] >= pos["stop"]: exit_px, reason = opens[i], "STOP_GAP"
            elif np.isfinite(pos["target"]) and opens[i] <= pos["target"]: exit_px, reason = pos["target"], "TARGET_GAP"
            else:
                stop_hit = highs[i] >= pos["stop"]
                target_hit = np.isfinite(pos["target"]) and lows[i] <= pos["target"]
        if exit_px is None:
            if stop_hit: exit_px, reason = pos["stop"], "STOP"
            elif target_hit: exit_px, reason = pos["target"], "TARGET"
            elif held >= pos["hold_bars_limit"]: exit_px, reason = closes[i], "TIME"
        trail = pos["trailing_atr_multiple"]
        if exit_px is None and trail is not None:
            atr = float(bars.atr.iloc[i]) if "atr" in bars else np.nan
            if np.isfinite(atr) and atr > 0:
                if pos["side"] == 1:
                    pos["stop"] = max(pos["stop"], highs[i] - trail * atr)
                else:
                    pos["stop"] = min(pos["stop"], lows[i] + trail * atr)
        if exit_px is not None:
            close_position(index[i], exit_px, reason, held)
            pos = None

    if pos is not None:
        reason = "END_OF_SAMPLE"
        if expected_end is not None:
            end_ts = pd.Timestamp(expected_end)
            end_ts = end_ts.tz_localize("UTC") if end_ts.tzinfo is None else end_ts.tz_convert("UTC")
            if index[-1] < end_ts:
                reason = "DATA_GAP"
        close_position(index[-1], closes[-1], reason, len(bars) - pos["entry_i"])
    return pd.DataFrame(trades)


def main():
    parser = argparse.ArgumentParser(description="HEAD OR-trigger engine, five-year crypto futures backtest")
    parser.add_argument("--start", default=START_DEFAULT)
    parser.add_argument("--end", default=END_DEFAULT)
    parser.add_argument("--symbol", required=True, choices=SYMBOLS)
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=2.0)
    parser.add_argument("--out", default="head_artifacts")
    args = parser.parse_args()
    if pd.Timestamp(args.end) <= pd.Timestamp(args.start):
        parser.error("--end must be later than --start")
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    symbol = args.symbol.upper()
    print(f"HEAD START {symbol} {args.start}..{args.end}", flush=True)
    raw = acquire_klines(symbol, args.start, args.end)
    funding = acquire_funding(symbol, raw.index.min(), args.end)
    source = funding.attrs.get("source", "unknown")
    gaps = funding.index.to_series().diff().dropna() if not funding.empty else pd.Series(dtype="timedelta64[ns]")
    max_gap = float(gaps.max().total_seconds() / 3600) if not gaps.empty else None
    if funding.empty or source not in OFFICIAL_FUNDING_SOURCES or max_gap is None or max_gap > 8.5:
        raise RuntimeError(f"Official funding failed closed: source={source}, rows={len(funding)}, max_gap_hours={max_gap}, attrs={dict(funding.attrs)}")
    quality = quality_report(raw, symbol, raw.index.min(), args.end)
    frames = {}
    for model in MODEL_PRIORITY:
        cfg = HEAD_CONFIGS[model]
        frames[model] = make_independent_signals(raw, model, TIMEFRAME, parameters=cfg["parameters"])
        print(f"MODEL SIGNALS {model}: {int(frames[model].signal.ne(0).sum())}", flush=True)
    combined = combine_model_signals(frames, TIMEFRAME)
    trades = run_head_backtest(combined, funding, symbol, TIMEFRAME,
                               args.fee_bps, args.slippage_bps, args.end)
    valid = trades.loc[~trades.exit_reason.isin(["DATA_GAP", "END_OF_SAMPLE"])].copy() if not trades.empty else trades.copy()
    summary = summarize(trades)
    summary.update({
        "symbol": symbol, "model": "HEAD", "timeframe": TIMEFRAME,
        "start_inclusive": args.start, "end_exclusive": args.end,
        "actual_candle_start": str(raw.index.min()),
        "actual_candle_end_exclusive": str(raw.index.max() + pd.Timedelta(minutes=1)),
        "listing_delay_days": round((raw.index.min() - pd.Timestamp(args.start, tz="UTC")).total_seconds() / 86400, 4),
        "fee_bps_per_side": args.fee_bps, "slippage_bps_per_side": args.slippage_bps,
        "funding_source": source, "funding_rows": int(len(funding)),
        "funding_max_gap_hours": max_gap, "candle_quality": quality,
        "model_trigger_bars": {m: int(frames[m].signal.ne(0).sum()) for m in MODEL_PRIORITY},
        "head_trigger_bars": int(combined.signal.ne(0).sum()),
        "conflict_bars": int(combined.same_bar_conflict.sum()),
        "multi_trigger_bars": int((combined.trigger_count > 1).sum()),
        "valid_trade_sources": valid.source_model.value_counts().to_dict() if not valid.empty else {},
    })
    (out / f"{symbol}_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    trades.to_csv(out / f"{symbol}_trades.csv", index=False)
    combined.loc[combined.signal.ne(0), [
        "signal", "head_source", "trigger_sources", "trigger_count",
        "same_bar_conflict", "stop", "target", "head_rr", "head_hold_bars",
        "head_trailing_atr_multiple"
    ]].to_csv(out / f"{symbol}_trigger_audit.csv")
    print(f"HEAD END {symbol}: trades={summary['trades']} PF={summary['profit_factor']} net_bps={summary['net_bps']}", flush=True)


if __name__ == "__main__":
    main()

from __future__ import annotations

import numpy as np
import pandas as pd


def run_backtest(
    bars,
    funding,
    symbol,
    model,
    timeframe,
    fee_bps=5.0,
    slippage_bps=2.0,
    rr=2.0,
    max_hold_bars=288,
):
    """
    Single-position, next-bar-open backtest.

    Signals on bar i-1 are filled at bar i open. The entry bar is included in
    barrier checks; if both stop and target are touched within one OHLC bar,
    the conservative stop-first rule is used. Funding cashflows apply to every
    USD-M perpetual position held across a funding timestamp, regardless of
    which model generated the signal.
    """
    bar_minutes = {
        "1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
        "1h": 60, "2h": 120, "4h": 240, "6h": 360,
        "12h": 720, "1d": 1440,
    }.get(timeframe)
    if bar_minutes is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if max_hold_bars is not None and max_hold_bars < 1:
        raise ValueError("max_hold_bars must be >= 1 or None")
    if len(bars) < 2:
        return pd.DataFrame()

    opens = bars["open"].to_numpy(dtype=float)
    highs = bars["high"].to_numpy(dtype=float)
    lows = bars["low"].to_numpy(dtype=float)
    closes = bars["close"].to_numpy(dtype=float)
    signals = bars["signal"].fillna(0).to_numpy(dtype=int)
    stops = bars["stop"].to_numpy(dtype=float)
    targets = (
        bars["target"].to_numpy(dtype=float)
        if "target" in bars.columns
        else np.full(len(bars), np.nan, dtype=float)
    )
    index = bars.index

    funding_index = None
    funding_rates = None
    if funding is not None and not funding.empty:
        funding = funding.sort_index()
        funding_index = funding.index
        funding_rates = pd.to_numeric(funding.funding_rate, errors="coerce").to_numpy(dtype=float)

    trades = []
    pos = None

    def finish_position(position, ts, exit_px, reason, held_bars):
        side = position["side"]
        exit_fill = float(exit_px) * (1 - side * slippage_bps / 10000)
        gross = side * (exit_fill - position["entry"]) / position["entry"]
        fees = 2 * fee_bps / 10000

        # Include an event exactly at entry conservatively because settlement
        # timestamps may deviate by seconds. Searchsorted avoids scanning all
        # funding rows for every trade.
        fund_cost = 0.0
        if funding_index is not None:
            first = funding_index.searchsorted(position["entry_time"], side="left")
            last = funding_index.searchsorted(ts, side="right")
            fund_cost = float(np.nansum(side * funding_rates[first:last]))

        net = gross - fees - fund_cost
        risk = abs(position["entry"] - position["stop"]) / position["entry"]
        trades.append({
            "symbol": symbol,
            "model": model,
            "timeframe": timeframe,
            "side": "LONG" if side == 1 else "SHORT",
            "entry_time": str(position["entry_time"]),
            "exit_time": str(ts),
            "entry": position["entry"],
            "exit": exit_fill,
            "stop": position["stop"],
            "target": position["target"],
            "exit_reason": reason,
            "gross_return_pct": gross * 100,
            "fees_pct": fees * 100,
            "funding_cost_pct": fund_cost * 100,
            "net_return_pct": net * 100,
            "net_bps": net * 10000,
            "net_R": net / risk if risk else 0.0,
            "holding_bars": int(held_bars),
            "holding_minutes": int(held_bars * bar_minutes),
        })

    for i in range(1, len(bars)):
        # A signal from the previous completed bar enters at this bar's open.
        if pos is None and signals[i - 1] != 0:
            side = int(signals[i - 1])
            raw_entry = opens[i]
            entry = raw_entry * (1 + side * slippage_bps / 10000)
            stop = stops[i - 1]
            if not np.isfinite(stop) or (side == 1 and stop >= entry) or (side == -1 and stop <= entry):
                continue

            target = targets[i - 1]
            if not np.isfinite(target):
                target = entry + side * rr * abs(entry - stop)
            if (side == 1 and target <= entry) or (side == -1 and target >= entry):
                continue

            pos = {
                "side": side,
                "entry": entry,
                "stop": float(stop),
                "target": float(target),
                "entry_time": index[i] - pd.Timedelta(minutes=bar_minutes),
                "entry_i": i,
            }

        if pos is None:
            continue

        # Check the entry bar as well as all later bars. Opening gaps are
        # filled at the open when they cross the stop (adverse); target gaps
        # receive only the target price (conservative). If both barriers are
        # touched intrabar, assume the adverse barrier first.
        held = i - pos["entry_i"] + 1
        exit_px = None
        reason = None
        stop_hit = False
        target_hit = False
        if pos["side"] == 1:
            if opens[i] <= pos["stop"]:
                exit_px, reason = opens[i], "STOP_GAP"
            elif opens[i] >= pos["target"]:
                exit_px, reason = pos["target"], "TARGET_GAP"
            else:
                stop_hit = lows[i] <= pos["stop"]
                target_hit = highs[i] >= pos["target"]
        else:
            if opens[i] >= pos["stop"]:
                exit_px, reason = opens[i], "STOP_GAP"
            elif opens[i] <= pos["target"]:
                exit_px, reason = pos["target"], "TARGET_GAP"
            else:
                stop_hit = highs[i] >= pos["stop"]
                target_hit = lows[i] <= pos["target"]

        if exit_px is None:
            if stop_hit:
                exit_px, reason = pos["stop"], "STOP"
            elif target_hit:
                exit_px, reason = pos["target"], "TARGET"
            elif max_hold_bars is not None and held >= max_hold_bars:
                exit_px, reason = closes[i], "TIME"

        if exit_px is not None:
            finish_position(pos, index[i], exit_px, reason, held)
            pos = None

    if pos is not None:
        held = len(bars) - pos["entry_i"]
        finish_position(pos, index[-1], closes[-1], "END_OF_SAMPLE", held)

    return pd.DataFrame(trades)


def summarize(t, risk_per_trade_pct=1.0):
    """
    Summarize one independent symbol/model/timeframe stream.

    net_return_pct is a fixed-initial-equity-risk return: net_R is multiplied
    by risk_per_trade_pct and summed without compounding. max_drawdown_pct is
    computed from that same fixed-risk equity curve. These are standardized
    research measures, not a portfolio return; no leverage or margin cap is
    assumed. Notional PnL is reported separately and is never compounded.
    """
    if risk_per_trade_pct <= 0:
        raise ValueError("risk_per_trade_pct must be > 0")
    if t.empty:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "profit_factor": 0.0, "profit_factor_r": 0.0,
            "net_return_pct": 0.0, "notional_net_return_pct": 0.0,
            "net_bps": 0.0, "net_R": 0.0, "max_drawdown_pct": 0.0,
            "max_drawdown_R": 0.0, "notional_max_drawdown_pct": 0.0,
            "risk_per_trade_pct": float(risk_per_trade_pct),
            "risk_equity_ruined": False,
            "avg_holding_minutes": 0.0, "median_holding_minutes": 0.0,
        }
    t = t.sort_values("exit_time")
    w = t[t.net_bps > 0]
    l = t[t.net_bps <= 0]
    gp = float(w.net_bps.sum())
    gl = abs(float(l.net_bps.sum()))

    net_r = pd.to_numeric(t.net_R, errors="coerce").fillna(0.0)
    gross_r = float(net_r[net_r > 0].sum())
    loss_r = abs(float(net_r[net_r < 0].sum()))
    cumulative_r = net_r.cumsum()
    r_peak = cumulative_r.cummax().clip(lower=0.0)
    drawdown_r = cumulative_r - r_peak
    max_drawdown_r = float(drawdown_r.min()) if len(drawdown_r) else 0.0

    # Fixed fraction of initial equity per R; no reinvestment/compounding.
    risk_equity = 1.0 + cumulative_r * (risk_per_trade_pct / 100.0)
    risk_peak = risk_equity.cummax().clip(lower=1.0)
    risk_dd = (risk_equity / risk_peak - 1.0).clip(lower=-1.0) * 100.0
    max_drawdown_pct = float(risk_dd.min()) if len(risk_dd) else 0.0

    # Also retain fixed 1x-notional cumulative PnL for transparent comparison.
    trade_notional_return = pd.to_numeric(t.net_return_pct, errors="coerce").fillna(0.0)
    notional_equity = 1.0 + trade_notional_return.cumsum() / 100.0
    notional_peak = notional_equity.cummax().clip(lower=1.0)
    notional_dd = (notional_equity / notional_peak - 1.0).clip(lower=-1.0) * 100.0
    notional_max_drawdown_pct = float(notional_dd.min()) if len(notional_dd) else 0.0

    if "holding_minutes" in t.columns:
        holding = pd.to_numeric(t.holding_minutes, errors="coerce")
    elif {"entry_time", "exit_time"}.issubset(t.columns):
        holding = (
            pd.to_datetime(t.exit_time, utc=True)
            - pd.to_datetime(t.entry_time, utc=True)
        ).dt.total_seconds() / 60
    else:
        holding = pd.Series([float("nan")] * len(t), index=t.index)
    return {
        "trades": int(len(t)),
        "wins": int(len(w)),
        "losses": int(len(l)),
        "win_rate_pct": round(100 * len(w) / len(t), 2),
        "profit_factor": round(gp / gl, 4) if gl else None,
        "profit_factor_r": round(gross_r / loss_r, 4) if loss_r else None,
        "net_return_pct": round(float(net_r.sum()) * risk_per_trade_pct, 4),
        "notional_net_return_pct": round(float(trade_notional_return.sum()), 4),
        "net_bps": round(float(t.net_bps.sum()), 2),
        "net_R": round(float(net_r.sum()), 3),
        "max_drawdown_pct": round(max_drawdown_pct, 3),
        "max_drawdown_R": round(max_drawdown_r, 3),
        "notional_max_drawdown_pct": round(notional_max_drawdown_pct, 3),
        "risk_per_trade_pct": float(risk_per_trade_pct),
        "risk_equity_ruined": bool((risk_equity <= 0).any()),
        "avg_trade_bps": round(float(t.net_bps.mean()), 3),
        "funding_cost_pct": round(float(t.funding_cost_pct.sum()), 4),
        "avg_holding_minutes": round(float(holding.mean()), 2) if holding.notna().any() else None,
        "median_holding_minutes": round(float(holding.median()), 2) if holding.notna().any() else None,
    }

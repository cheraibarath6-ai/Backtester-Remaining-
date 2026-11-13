from __future__ import annotations

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
    which model generated the signal. Funding may also be an M5 signal input,
    but it is not an M5-only carrying cost.
    """
    trades = []
    pos = None
    ix = bars.index
    bar_minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
                   "1h": 60, "2h": 120, "4h": 240, "6h": 360,
                   "12h": 720, "1d": 1440}.get(timeframe)
    if bar_minutes is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    if max_hold_bars is not None and max_hold_bars < 1:
        raise ValueError("max_hold_bars must be >= 1 or None")

    def finish_position(position, ts, exit_px, reason, held_bars):
        side = position["side"]
        exit_fill = float(exit_px) * (1 - side * slippage_bps / 10000)
        gross = side * (exit_fill - position["entry"]) / position["entry"]
        fees = 2 * fee_bps / 10000

        # Funding is a cashflow on the perpetual position, not an M5-only fee.
        # Include an event exactly at entry conservatively because Binance's
        # settlement timestamp can deviate by several seconds.
        fund_cost = 0.0
        if funding is not None and not funding.empty:
            ff = funding.loc[
                (funding.index >= position["entry_time"])
                & (funding.index <= ts)
            ]
            fund_cost = sum(side * float(v) for v in ff.funding_rate)

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
        row = bars.iloc[i]
        ts = ix[i]
        prev = bars.iloc[i - 1]

        # A prior completed-bar signal enters at this bar's open.
        if pos is None and int(prev.get("signal", 0)) != 0:
            side = int(prev.signal)
            raw_entry = float(row.open)
            entry = raw_entry * (1 + side * slippage_bps / 10000)
            stop = float(prev.stop) if pd.notna(prev.stop) else float("nan")
            if not pd.notna(stop) or (side == 1 and stop >= entry) or (side == -1 and stop <= entry):
                continue

            explicit_target = prev.get("target", float("nan"))
            if pd.notna(explicit_target):
                target = float(explicit_target)
            else:
                target = entry + side * rr * abs(entry - stop)

            if (side == 1 and target <= entry) or (side == -1 and target >= entry):
                continue

            pos = {
                "side": side,
                "entry": entry,
                "stop": stop,
                "target": target,
                "entry_time": ts - pd.Timedelta(minutes=bar_minutes),
                "entry_i": i,
            }

        if pos is None:
            continue

        # Check the entry bar as well as every subsequent bar. For an OHLC bar
        # where both barriers are touched, assume the adverse barrier happened first.
        held = i - pos["entry_i"] + 1
        if pos["side"] == 1:
            stop_hit = row.low <= pos["stop"]
            target_hit = row.high >= pos["target"]
        else:
            stop_hit = row.high >= pos["stop"]
            target_hit = row.low <= pos["target"]

        exit_px = None
        reason = None
        if stop_hit:
            exit_px, reason = pos["stop"], "STOP"
        elif target_hit:
            exit_px, reason = pos["target"], "TARGET"
        elif max_hold_bars is not None and held >= max_hold_bars:
            exit_px, reason = float(row.close), "TIME"

        if exit_px is not None:
            finish_position(pos, ts, exit_px, reason, held)
            pos = None

    if pos is not None:
        row = bars.iloc[-1]
        ts = ix[-1]
        held = len(bars) - pos["entry_i"]
        px = float(row.close)
        finish_position(pos, ts, px, "END_OF_SAMPLE", held)

    return pd.DataFrame(trades)


def summarize(t):
    if t.empty:
        return {
            "trades": 0, "wins": 0, "losses": 0, "win_rate_pct": 0.0,
            "profit_factor": 0.0, "net_return_pct": 0.0, "net_bps": 0.0,
            "net_R": 0.0, "max_drawdown_pct": 0.0,
            "avg_holding_minutes": 0.0, "median_holding_minutes": 0.0,
        }
    t = t.sort_values("exit_time")
    w = t[t.net_bps > 0]
    l = t[t.net_bps <= 0]
    gp = float(w.net_bps.sum())
    gl = abs(float(l.net_bps.sum()))
    eq = (1 + t.net_return_pct / 100).cumprod()
    dd = (eq / eq.cummax() - 1).min() * 100
    return {
        "trades": int(len(t)),
        "wins": int(len(w)),
        "losses": int(len(l)),
        "win_rate_pct": round(100 * len(w) / len(t), 2),
        "profit_factor": round(gp / gl, 4) if gl else None,
        "net_return_pct": round((eq.iloc[-1] - 1) * 100, 4),
        "net_bps": round(float(t.net_bps.sum()), 2),
        "net_R": round(float(t.net_R.sum()), 3),
        "max_drawdown_pct": round(float(dd), 3),
        "avg_trade_bps": round(float(t.net_bps.mean()), 3),
        "funding_cost_pct": round(float(t.funding_cost_pct.sum()), 4),
        "avg_holding_minutes": round(float(t.holding_minutes.mean()), 2),
        "median_holding_minutes": round(float(t.holding_minutes.median()), 2),
    }

from __future__ import annotations

import numpy as np
import pandas as pd

TIMEFRAME_RULES = {
    "1m": "1min",
    "3m": "3min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "12h": "12h",
    "1d": "1D",
}
INDEPENDENT_MODELS = ("M6", "M7", "M8", "M9", "M10", "M11", "M12", "M13", "M14", "M15")
_BAR_CACHE: dict[tuple, pd.DataFrame] = {}


def prepare_bars(raw: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Build completed UTC bars and causal indicators from Binance 1-minute OHLCV."""
    if timeframe not in TIMEFRAME_RULES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    cache_key = (id(raw), timeframe, len(raw), raw.index.min(), raw.index.max())
    cached = _BAR_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()
    if timeframe == "1m":
        d = raw.copy()
    else:
        d = raw.resample(TIMEFRAME_RULES[timeframe], label="right", closed="left").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
            "quote_volume": "sum",
            "trades": "sum",
            "taker_buy_base": "sum",
            "taker_buy_quote": "sum",
        }).dropna(subset=["open", "high", "low", "close"])

    d = d.sort_index().copy()
    close, high, low = d.close, d.high, d.low
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    d["rsi"] = 100 - 100 / (1 + rs)

    up, down = high.diff(), -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    d["plus_di"] = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False).mean() / d.atr.replace(0, np.nan)
    d["minus_di"] = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False).mean() / d.atr.replace(0, np.nan)
    dx = 100 * (d.plus_di - d.minus_di).abs() / (d.plus_di + d.minus_di).replace(0, np.nan)
    d["adx"] = dx.ewm(alpha=1 / 14, adjust=False).mean()

    for span in (5, 12, 20, 26, 34, 50, 100, 200):
        d[f"ema{span}"] = close.ewm(span=span, adjust=False).mean()

    d["mom14"] = close - close.shift(14)
    d["volume_ratio"] = d.volume / d.volume.shift(1).rolling(20, min_periods=10).mean()
    d["taker_ratio"] = d.taker_buy_base / d.volume.replace(0, np.nan)

    d["bb_mid"] = close.rolling(20, min_periods=20).mean()
    d["bb_std"] = close.rolling(20, min_periods=20).std(ddof=0)
    d["bb_upper"] = d.bb_mid + 2.0 * d.bb_std
    d["bb_lower"] = d.bb_mid - 2.0 * d.bb_std
    d["bb_z"] = (close - d.bb_mid) / d.bb_std.replace(0, np.nan)
    d["bb_width"] = (d.bb_upper - d.bb_lower) / d.bb_mid.replace(0, np.nan)

    typical = (high + low + close) / 3.0
    session = pd.Series(d.index.floor("D"), index=d.index)
    cum_pv = (typical * d.volume).groupby(session).cumsum()
    cum_vol = d.volume.groupby(session).cumsum()
    d["session_vwap"] = cum_pv / cum_vol.replace(0, np.nan)

    hl2 = (high + low) / 2.0
    d["awesome_oscillator"] = hl2.rolling(5).mean() - hl2.rolling(34).mean()
    macd_fast = close.ewm(span=12, adjust=False).mean()
    macd_slow = close.ewm(span=26, adjust=False).mean()
    d["macd"] = macd_fast - macd_slow
    d["macd_signal"] = d.macd.ewm(span=9, adjust=False).mean()
    d["macd_hist"] = d.macd - d.macd_signal

    _BAR_CACHE[cache_key] = d
    return d.copy()


def _set_atr_stops(d: pd.DataFrame, long: pd.Series, short: pd.Series, multiple: float):
    d.loc[long, "signal"] = 1
    d.loc[short, "signal"] = -1
    d["stop"] = np.where(
        long, d.close - multiple * d.atr,
        np.where(short, d.close + multiple * d.atr, np.nan),
    )


def make_independent_signals(
    raw: pd.DataFrame,
    model: str,
    timeframe: str,
    benchmark_raw: pd.DataFrame | None = None,
    open_interest: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Standalone candidate strategies M6-M15. No cross-model voting or filters.

    Signals are formed at the completed bar close; the shared executor enters
    at the next bar open. Any benchmark series is an explicit input to M10/M13,
    not another trading model's signal.
    """
    if model not in INDEPENDENT_MODELS:
        raise ValueError(f"Unsupported independent model: {model}")
    d = prepare_bars(raw, timeframe)
    d["signal"] = 0
    d["stop"] = np.nan
    d["target"] = np.nan
    atr = d.atr.replace(0, np.nan)

    if model == "M6":
        n = 55
        prior_high = d.high.shift(1).rolling(n, min_periods=n).max()
        prior_low = d.low.shift(1).rolling(n, min_periods=n).min()
        long = (d.close > prior_high) & (d.volume_ratio >= 1.0)
        short = (d.close < prior_low) & (d.volume_ratio >= 1.0)
        _set_atr_stops(d, long, short, 2.5)

    elif model == "M7":
        long = (d.bb_z <= -2.0) & (d.rsi <= 35)
        short = (d.bb_z >= 2.0) & (d.rsi >= 65)
        _set_atr_stops(d, long, short, 1.5)
        d.loc[long, "target"] = d.loc[long, "bb_mid"]
        d.loc[short, "target"] = d.loc[short, "bb_mid"]

    elif model == "M8":
        prior_squeeze_threshold = d.bb_width.shift(1).rolling(100, min_periods=50).quantile(0.20)
        squeeze = d.bb_width <= prior_squeeze_threshold
        recent_squeeze = squeeze.shift(1).rolling(6, min_periods=1).max().fillna(0).astype(bool)
        prior_high = d.high.shift(1).rolling(20, min_periods=20).max()
        prior_low = d.low.shift(1).rolling(20, min_periods=20).min()
        expansion = (d.high - d.low) >= 1.2 * atr
        long = recent_squeeze & (d.close > prior_high) & expansion & (d.volume_ratio >= 1.2)
        short = recent_squeeze & (d.close < prior_low) & expansion & (d.volume_ratio >= 1.2)
        _set_atr_stops(d, long, short, 2.0)

    elif model == "M9":
        crossed_up = (d.close > d.session_vwap) & (d.close.shift(1) <= d.session_vwap.shift(1))
        crossed_down = (d.close < d.session_vwap) & (d.close.shift(1) >= d.session_vwap.shift(1))
        long = crossed_up & (d.taker_ratio >= 0.58) & (d.volume_ratio >= 1.2) & (d.adx >= 18)
        short = crossed_down & (d.taker_ratio <= 0.42) & (d.volume_ratio >= 1.2) & (d.adx >= 18)
        _set_atr_stops(d, long, short, 1.75)

    elif model in ("M10", "M13"):
        if benchmark_raw is None:
            raise ValueError(f"{model} requires BTC benchmark candles")
        benchmark = prepare_bars(benchmark_raw, timeframe)
        btc_close = benchmark.close.reindex(d.index, method="ffill")
        if model == "M10":
            lookback = 20
            relative = d.close.pct_change(lookback) - btc_close.pct_change(lookback)
            long = (relative >= 0.01) & (d.close > d.ema50) & (d.ema50 > d.ema200)
            short = (relative <= -0.01) & (d.close < d.ema50) & (d.ema50 < d.ema200)
            _set_atr_stops(d, long, short, 2.0)
        else:
            lookback = 3
            btc_impulse = btc_close.pct_change(lookback)
            asset_move = d.close.pct_change(lookback)
            long = (btc_impulse >= 0.006) & ((btc_impulse - asset_move) >= 0.003) & (d.close > d.ema20)
            short = (btc_impulse <= -0.006) & ((asset_move - btc_impulse) >= 0.003) & (d.close < d.ema20)
            _set_atr_stops(d, long, short, 2.0)

    elif model == "M11":
        if open_interest is None or open_interest.empty:
            raise ValueError("M11 requires historical open-interest metrics; no price-only proxy is permitted")
        oi_candidates = (
            "open_interest_value", "sum_open_interest_value", "sumOpenInterestValue",
            "open_interest", "sum_open_interest", "sumOpenInterest",
        )
        oi_col = next((column for column in oi_candidates if column in open_interest.columns), None)
        if oi_col is None:
            raise ValueError("M11 open-interest data has no recognized OI field")
        oi = pd.to_numeric(open_interest[oi_col], errors="coerce").sort_index()
        tf_minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
                      "1h": 60, "2h": 120, "4h": 240, "6h": 360,
                      "12h": 720, "1d": 1440}[timeframe]
        # Only carry a source snapshot forward within one strategy bar.
        # Long gaps stay missing rather than creating synthetic OI signals.
        oi = oi.reindex(
            d.index, method="ffill",
            tolerance=pd.Timedelta(minutes=tf_minutes),
        )
        oi_change = oi.pct_change(12, fill_method=None)
        price_change = d.close.pct_change(12, fill_method=None)
        long = (oi_change >= 0.01) & (price_change >= 0.005) & (d.taker_ratio >= 0.55)
        short = (oi_change >= 0.01) & (price_change <= -0.005) & (d.taker_ratio <= 0.45)
        _set_atr_stops(d, long, short, 2.0)

    elif model == "M12":
        prior_high = d.high.shift(1).rolling(20, min_periods=20).max()
        prior_low = d.low.shift(1).rolling(20, min_periods=20).min()
        trend_long = (d.adx >= 25) & (d.close > prior_high)
        trend_short = (d.adx >= 25) & (d.close < prior_low)
        range_long = (d.adx <= 18) & (d.bb_z <= -2.0) & (d.rsi <= 35)
        range_short = (d.adx <= 18) & (d.bb_z >= 2.0) & (d.rsi >= 65)
        long = trend_long | range_long
        short = trend_short | range_short
        _set_atr_stops(d, long, short, 2.0)
        d.loc[range_long, "stop"] = d.loc[range_long, "low"] - 0.5 * atr.loc[range_long]
        d.loc[range_short, "stop"] = d.loc[range_short, "high"] + 0.5 * atr.loc[range_short]
        d.loc[range_long, "target"] = d.loc[range_long, "bb_mid"]
        d.loc[range_short, "target"] = d.loc[range_short, "bb_mid"]

    elif model == "M14":
        long = (d.adx > 25) & (d.mom14 > 0) & (d.plus_di > 25) & (d.plus_di > d.minus_di)
        short = (d.adx > 25) & (d.mom14 < 0) & (d.minus_di > 25) & (d.minus_di > d.plus_di)
        _set_atr_stops(d, long, short, 2.0)

    elif model == "M15":
        ao = d.awesome_oscillator
        ao_cross_up = (ao > 0) & (ao.shift(1) <= 0)
        ao_cross_down = (ao < 0) & (ao.shift(1) >= 0)
        long = (d.macd > 0) & ao_cross_up
        short = (d.macd < 0) & ao_cross_down
        _set_atr_stops(d, long, short, 2.0)

    d["signal"] = d.signal.fillna(0).astype(int)
    return d

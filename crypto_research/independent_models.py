# Backtest audit refresh: causal M13 lag and complete-bar resampling (2026-11-13)
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


def _add_segment_indicators(d: pd.DataFrame) -> pd.DataFrame:
    """Calculate indicators only within one uninterrupted run of complete bars."""
    d = d.copy()
    close, high, low = d.close, d.high, d.low
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    d["atr"] = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    d["rsi"] = 100 - 100 / (1 + rs)

    up, down = high.diff(), -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    d["plus_di"] = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / d.atr.replace(0, np.nan)
    d["minus_di"] = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / d.atr.replace(0, np.nan)
    dx = 100 * (d.plus_di - d.minus_di).abs() / (d.plus_di + d.minus_di).replace(0, np.nan)
    d["adx"] = dx.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()

    for span in (5, 12, 20, 26, 34, 50, 100, 200):
        d[f"ema{span}"] = close.ewm(span=span, adjust=False, min_periods=span).mean()

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
    session_key = pd.MultiIndex.from_arrays([d.index.floor("D"), d["data_segment"]])
    cum_pv = (typical * d.volume).groupby(session_key).cumsum()
    cum_vol = d.volume.groupby(session_key).cumsum()
    d["session_vwap"] = cum_pv / cum_vol.replace(0, np.nan)

    hl2 = (high + low) / 2.0
    d["awesome_oscillator"] = hl2.rolling(5).mean() - hl2.rolling(34).mean()
    macd_fast = close.ewm(span=12, adjust=False, min_periods=12).mean()
    macd_slow = close.ewm(span=26, adjust=False, min_periods=26).mean()
    d["macd"] = macd_fast - macd_slow
    d["macd_signal"] = d.macd.ewm(span=9, adjust=False, min_periods=9).mean()
    d["macd_hist"] = d.macd - d.macd_signal
    return d


def prepare_bars(raw: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Build complete UTC bars and reset all indicator history after data gaps."""
    if timeframe not in TIMEFRAME_RULES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    cache_key = (id(raw), timeframe, len(raw), raw.index.min(), raw.index.max())
    cached = _BAR_CACHE.get(cache_key)
    if cached is not None:
        return cached.copy()
    if timeframe == "1m":
        d = raw.copy()
    else:
        resampler = raw.resample(TIMEFRAME_RULES[timeframe], label="right", closed="left")
        minute_count = resampler["close"].count()
        d = resampler.agg({
            "open": "first", "high": "max", "low": "min", "close": "last",
            "volume": "sum", "quote_volume": "sum", "trades": "sum",
            "taker_buy_base": "sum", "taker_buy_quote": "sum",
        }).dropna(subset=["open", "high", "low", "close"])
        expected_minutes = {
            "3m": 3, "5m": 5, "15m": 15, "30m": 30, "1h": 60,
            "2h": 120, "4h": 240, "6h": 360, "12h": 720, "1d": 1440,
        }[timeframe]
        # Partial candles are invalid; their removal creates a visible segment break.
        d = d.loc[minute_count.reindex(d.index).fillna(0).eq(expected_minutes)]

    d = d.sort_index().copy()
    if d.empty:
        return d
    if not d.index.is_monotonic_increasing or d.index.has_duplicates:
        raise ValueError("Raw bars must have a strictly increasing, duplicate-free index")
    bar_delta = pd.Timedelta(TIMEFRAME_RULES[timeframe])
    segment_ids = d.index.to_series().diff().ne(bar_delta).cumsum()
    prepared_segments = []
    for segment_id, segment in d.groupby(segment_ids, sort=False):
        segment = segment.copy()
        segment["data_segment"] = int(segment_id)
        prepared_segments.append(_add_segment_indicators(segment))
    d = pd.concat(prepared_segments).sort_index()
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
    parameters: dict | None = None,
) -> pd.DataFrame:
    """
    Standalone candidate strategies M6-M15. No cross-model voting or filters.

    Signals are formed at the completed bar close; the shared executor enters
    at the next bar open. Any benchmark series is an explicit input to M10/M13,
    not another trading model's signal.
    """
    if model not in INDEPENDENT_MODELS:
        raise ValueError(f"Unsupported independent model: {model}")
    parameters = parameters or {}
    d = prepare_bars(raw, timeframe)
    # Compatibility for explicit synthetic fixtures and older cached frames.
    if "data_segment" not in d.columns:
        d["data_segment"] = 0
    d["signal"] = 0
    d["stop"] = np.nan
    d["target"] = np.nan
    atr = d.atr.replace(0, np.nan)

    if model == "M6":
        n = int(parameters.get("donchian_period", 55))
        volume_min = float(parameters.get("volume_ratio_min", 1.0))
        stop_multiple = float(parameters.get("stop_atr", 2.5))
        prior_high = d.high.shift(1).rolling(n, min_periods=n).max()
        prior_low = d.low.shift(1).rolling(n, min_periods=n).min()
        long = (d.close > prior_high) & (d.volume_ratio >= volume_min)
        short = (d.close < prior_low) & (d.volume_ratio >= volume_min)
        _set_atr_stops(d, long, short, stop_multiple)

    elif model == "M7":
        z_entry = float(parameters.get("bb_z_entry", 2.0))
        rsi_long_max = float(parameters.get("rsi_long_max", 35.0))
        rsi_short_min = float(parameters.get("rsi_short_min", 65.0))
        stop_multiple = float(parameters.get("stop_atr", 1.5))
        long = (d.bb_z <= -z_entry) & (d.rsi <= rsi_long_max)
        short = (d.bb_z >= z_entry) & (d.rsi >= rsi_short_min)
        _set_atr_stops(d, long, short, stop_multiple)
        d.loc[long, "target"] = d.loc[long, "bb_mid"]
        d.loc[short, "target"] = d.loc[short, "bb_mid"]

    elif model == "M8":
        squeeze_lookback = int(parameters.get("squeeze_lookback", 100))
        squeeze_quantile = float(parameters.get("squeeze_quantile", 0.20))
        breakout_period = int(parameters.get("breakout_period", 20))
        expansion_multiple = float(parameters.get("expansion_atr", 1.2))
        volume_min = float(parameters.get("volume_ratio_min", 1.2))
        stop_multiple = float(parameters.get("stop_atr", 2.0))
        prior_squeeze_threshold = d.bb_width.shift(1).rolling(
            squeeze_lookback, min_periods=max(20, squeeze_lookback // 2)
        ).quantile(squeeze_quantile)
        squeeze = d.bb_width <= prior_squeeze_threshold
        recent_squeeze = squeeze.shift(1).rolling(6, min_periods=1).max().fillna(0).astype(bool)
        prior_high = d.high.shift(1).rolling(breakout_period, min_periods=breakout_period).max()
        prior_low = d.low.shift(1).rolling(breakout_period, min_periods=breakout_period).min()
        expansion = (d.high - d.low) >= expansion_multiple * atr
        long = recent_squeeze & (d.close > prior_high) & expansion & (d.volume_ratio >= volume_min)
        short = recent_squeeze & (d.close < prior_low) & expansion & (d.volume_ratio >= volume_min)
        _set_atr_stops(d, long, short, stop_multiple)

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
        if "data_segment" not in benchmark.columns:
            benchmark["data_segment"] = 0
        bar_delta = pd.Timedelta(TIMEFRAME_RULES[timeframe])
        btc_close = benchmark.close.reindex(d.index, method="ffill", tolerance=bar_delta)
        btc_segment = benchmark.data_segment.reindex(
            d.index, method="ffill", tolerance=bar_delta
        )
        # Returns must stay inside uninterrupted altcoin and BTC data segments.
        group_key = (
            d["data_segment"].astype("string")
            + "|"
            + btc_segment.astype("Int64").astype("string")
        ).where(btc_close.notna() & btc_segment.notna())
        asset_return = d.close.groupby(group_key, dropna=True).pct_change(
            20 if model == "M10" else 3, fill_method=None
        )
        btc_return = btc_close.groupby(group_key, dropna=True).pct_change(
            20 if model == "M10" else 3, fill_method=None
        )
        if model == "M10":
            lookback = int(parameters.get("lookback", 20))
            relative = asset_return - btc_return
            threshold = float(parameters.get("relative_threshold", 0.01))
            ema_fast_period = int(parameters.get("ema_fast", 50))
            ema_slow_period = int(parameters.get("ema_slow", 200))
            ema_fast = d[f"ema{ema_fast_period}"]
            ema_slow = d[f"ema{ema_slow_period}"]
            long = (relative >= threshold) & (d.close > ema_fast) & (ema_fast > ema_slow)
            short = (relative <= -threshold) & (d.close < ema_fast) & (ema_fast < ema_slow)
            _set_atr_stops(d, long, short, float(parameters.get("stop_atr", 2.0)))
        else:
            lookback = int(parameters.get("btc_lookback", 3))
            # BTC impulse must precede the altcoin response window. Shift
            # by one full lookback so the two return windows do not overlap.
            btc_impulse = btc_return.groupby(group_key, dropna=True).shift(lookback)
            asset_move = asset_return
            impulse_threshold = float(parameters.get("impulse_threshold", 0.006))
            divergence_threshold = float(parameters.get("divergence_threshold", 0.003))
            ema_period = int(parameters.get("ema_period", 20))
            ema = d[f"ema{ema_period}"]
            long = (btc_impulse >= impulse_threshold) & ((btc_impulse - asset_move) >= divergence_threshold) & (d.close > ema)
            short = (btc_impulse <= -impulse_threshold) & ((asset_move - btc_impulse) >= divergence_threshold) & (d.close < ema)
            _set_atr_stops(d, long, short, float(parameters.get("stop_atr", 2.0)))

    elif model == "M11":
        if open_interest is None or open_interest.empty:
            raise ValueError("M11 requires historical open-interest metrics; no price-only proxy is permitted")
        # Use contract/base-denominated OI only. Quote-value OI embeds price
        # movement and can make an OI-pressure signal partly a price signal.
        oi_candidates = (
            "sum_open_interest", "sumOpenInterest",
            "open_interest_amount", "openInterest", "oi_contracts",
        )
        oi_col = next((column for column in oi_candidates if column in open_interest.columns), None)
        if oi_col is None:
            quote_columns = {
                "open_interest_value", "sum_open_interest_value", "sumOpenInterestValue",
            }
            if quote_columns.intersection(open_interest.columns):
                raise ValueError(
                    "M11 requires contract-denominated open interest; quote-value OI is not accepted"
                )
            raise ValueError("M11 open-interest data has no recognized contract-count OI field")
        oi = pd.to_numeric(open_interest[oi_col], errors="coerce").sort_index()
        # Binance USD-M metrics are 5-minute snapshots. A slow strategy
        # timeframe does not make a stale OI observation current: only carry
        # the latest snapshot by at most one source interval. In particular,
        # never forward-fill a missing 1h/4h OI interval for an entire bar.
        oi = oi.reindex(
            d.index, method="ffill",
            tolerance=pd.Timedelta(minutes=5),
        )
        lookback = int(parameters.get("oi_lookback", 12))
        oi_change_min = float(parameters.get("oi_change_min", 0.01))
        price_change_min = float(parameters.get("price_change_min", 0.005))
        taker_threshold = float(parameters.get("taker_threshold", 0.55))
        stop_multiple = float(parameters.get("stop_atr", 2.0))
        # Do not calculate OI or price changes across a missing-candle segment.
        oi_change = oi.groupby(d["data_segment"]).pct_change(lookback, fill_method=None)
        price_change = d.close.groupby(d["data_segment"]).pct_change(lookback, fill_method=None)
        long = (oi_change >= oi_change_min) & (price_change >= price_change_min) & (d.taker_ratio >= taker_threshold)
        short = (oi_change >= oi_change_min) & (price_change <= -price_change_min) & (d.taker_ratio <= 1.0 - taker_threshold)
        _set_atr_stops(d, long, short, stop_multiple)

    elif model == "M12":
        breakout_period = int(parameters.get("breakout_period", 20))
        trend_adx_min = float(parameters.get("trend_adx_min", 25.0))
        range_adx_max = float(parameters.get("range_adx_max", 18.0))
        range_bb_z = float(parameters.get("range_bb_z", 2.0))
        range_rsi = float(parameters.get("range_rsi", 35.0))
        stop_multiple = float(parameters.get("stop_atr", 2.0))
        range_stop_multiple = float(parameters.get("range_stop_atr", 0.5))
        prior_high = d.high.shift(1).rolling(breakout_period, min_periods=breakout_period).max()
        prior_low = d.low.shift(1).rolling(breakout_period, min_periods=breakout_period).min()
        trend_long = (d.adx >= trend_adx_min) & (d.close > prior_high)
        trend_short = (d.adx >= trend_adx_min) & (d.close < prior_low)
        range_long = (d.adx <= range_adx_max) & (d.bb_z <= -range_bb_z) & (d.rsi <= range_rsi)
        range_short = (d.adx <= range_adx_max) & (d.bb_z >= range_bb_z) & (d.rsi >= 100.0 - range_rsi)
        long = trend_long | range_long
        short = trend_short | range_short
        _set_atr_stops(d, long, short, stop_multiple)
        d.loc[range_long, "stop"] = d.loc[range_long, "low"] - range_stop_multiple * atr.loc[range_long]
        d.loc[range_short, "stop"] = d.loc[range_short, "high"] + range_stop_multiple * atr.loc[range_short]
        d.loc[range_long, "target"] = d.loc[range_long, "bb_mid"]
        d.loc[range_short, "target"] = d.loc[range_short, "bb_mid"]

    elif model == "M14":
        adx_min = float(parameters.get("adx_min", 25.0))
        di_min = float(parameters.get("di_min", 25.0))
        momentum_lookback = int(parameters.get("momentum_lookback", 14))
        momentum = d.close - d.close.shift(momentum_lookback)
        long = (d.adx > adx_min) & (momentum > 0) & (d.plus_di > di_min) & (d.plus_di > d.minus_di)
        short = (d.adx > adx_min) & (momentum < 0) & (d.minus_di > di_min) & (d.minus_di > d.plus_di)
        _set_atr_stops(d, long, short, float(parameters.get("stop_atr", 2.0)))

    elif model == "M15":
        ao = d.awesome_oscillator
        ao_min_atr = float(parameters.get("ao_cross_min_atr", 0.0))
        macd_min_atr = float(parameters.get("macd_min_atr", 0.0))
        ao_threshold = ao_min_atr * atr
        macd_threshold = macd_min_atr * atr
        ao_cross_up = (ao > ao_threshold) & (ao.shift(1) <= 0)
        ao_cross_down = (ao < -ao_threshold) & (ao.shift(1) >= 0)
        long = (d.macd > macd_threshold) & ao_cross_up
        short = (d.macd < -macd_threshold) & ao_cross_down
        _set_atr_stops(d, long, short, float(parameters.get("stop_atr", 2.0)))

    d["signal"] = d.signal.fillna(0).astype(int)
    return d

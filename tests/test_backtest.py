import pandas as pd

from crypto_research.backtest import run_backtest, summarize
from crypto_research.data import _timestamp_unit


def _bars(entry_high=105.0, entry_low=99.0):
    index = pd.date_range("2024-01-01 00:05:00", periods=3, freq="5min", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, entry_high, 105.0],
            "low": [99.0, entry_low, 99.0],
            "close": [100.0, 100.0, 100.0],
            "signal": [1, 0, 0],
            "stop": [95.0, float("nan"), float("nan")],
            "target": [float("nan"), float("nan"), float("nan")],
        },
        index=index,
    )


def test_entry_bar_target_is_not_missed():
    trades = run_backtest(
        _bars(entry_high=111.0), None, "BTCUSDT", "M6", "5m",
        fee_bps=0, slippage_bps=0, rr=2,
    )
    assert len(trades) == 1
    assert trades.iloc[0].exit_reason == "TARGET"
    assert trades.iloc[0].holding_bars == 1
    assert trades.iloc[0].holding_minutes == 5
    assert abs(trades.iloc[0].net_R - 2.0) < 1e-9


def test_stop_wins_when_both_barriers_touch_in_entry_bar():
    trades = run_backtest(
        _bars(entry_high=111.0, entry_low=94.0),
        None, "BTCUSDT", "M6", "5m",
        fee_bps=0, slippage_bps=0, rr=2,
    )
    assert len(trades) == 1
    assert trades.iloc[0].exit_reason == "STOP"
    assert trades.iloc[0].holding_bars == 1


def test_perpetual_funding_is_applied_to_non_m5_models():
    bars = _bars(entry_high=105.0, entry_low=99.0)
    funding = pd.DataFrame(
        {"funding_rate": [0.001]},
        index=pd.DatetimeIndex(["2024-01-01 00:05:00"], tz="UTC"),
    )
    trades = run_backtest(
        bars, funding, "BTCUSDT", "M2", "5m",
        fee_bps=0, slippage_bps=0, rr=2,
    )
    assert len(trades) == 1
    assert abs(trades.iloc[0].funding_cost_pct - 0.1) < 1e-9
    assert abs(trades.iloc[0].net_return_pct + 0.1) < 1e-9


def test_summary_reports_holding_time():
    trades = run_backtest(
        _bars(entry_high=105.0), None, "BTCUSDT", "M6", "5m",
        fee_bps=0, slippage_bps=0, rr=2,
    )
    stats = summarize(trades)
    assert stats["trades"] == 1
    assert stats["avg_holding_minutes"] == 10.0
    assert stats["median_holding_minutes"] == 10.0


def test_binance_archive_timestamp_unit_detection_handles_ms_and_us():
    assert _timestamp_unit(pd.Series([1_700_000_000_000])) == "ms"
    assert _timestamp_unit(pd.Series([1_700_000_000_000_000])) == "us"

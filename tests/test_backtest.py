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


def test_pfi_fast_backtest_checks_entry_bar_and_records_holding_time():
    from crypto_research.pfi import fast_backtest

    trades = fast_backtest(
        _bars(entry_high=111.0), None, "BTCUSDT", "M1", "5m",
        fee_bps=0, slippage_bps=0, rr=2,
    )
    assert len(trades) == 1
    assert trades.iloc[0].exit_reason == "TARGET"
    assert trades.iloc[0].holding_minutes == 5


def test_summary_supports_legacy_trade_ledger_without_holding_minutes():
    legacy = pd.DataFrame({
        "exit_time": ["2024-01-01 00:10:00+00:00"],
        "entry_time": ["2024-01-01 00:05:00+00:00"],
        "net_bps": [10.0],
        "net_return_pct": [0.1],
        "net_R": [0.2],
        "funding_cost_pct": [0.0],
    })
    stats = summarize(legacy)
    assert stats["avg_holding_minutes"] == 5.0
    assert stats["median_holding_minutes"] == 5.0


def test_stop_gap_fills_at_the_open_not_the_stale_stop_price():
    index = pd.date_range("2024-01-01 00:05:00", periods=3, freq="5min", tz="UTC")
    bars = pd.DataFrame(
        {
            "open": [100.0, 100.0, 90.0],
            "high": [101.0, 101.0, 92.0],
            "low": [99.0, 96.0, 89.0],
            "close": [100.0, 100.0, 91.0],
            "signal": [1, 0, 0],
            "stop": [95.0, float("nan"), float("nan")],
            "target": [float("nan"), float("nan"), float("nan")],
        },
        index=index,
    )
    trades = run_backtest(
        bars, None, "BTCUSDT", "M6", "5m",
        fee_bps=0, slippage_bps=0, rr=2,
    )
    assert len(trades) == 1
    assert trades.iloc[0].exit_reason == "STOP_GAP"
    assert trades.iloc[0].exit == 90.0
    assert abs(trades.iloc[0].net_R + 2.0) < 1e-9


def test_summary_uses_fixed_risk_not_full_notional_compounding():
    trades = pd.DataFrame({
        "exit_time": ["2024-01-01 00:10:00+00:00", "2024-01-01 00:15:00+00:00"],
        "entry_time": ["2024-01-01 00:05:00+00:00", "2024-01-01 00:10:00+00:00"],
        "net_bps": [200.0, -300.0],
        "net_return_pct": [2.0, -3.0],
        "net_R": [2.0, -3.0],
        "funding_cost_pct": [0.0, 0.0],
        "holding_minutes": [5, 5],
    })
    stats = summarize(trades, risk_per_trade_pct=1.0)
    assert stats["net_return_pct"] == -1.0
    assert stats["notional_net_return_pct"] == -1.0
    assert abs(stats["max_drawdown_pct"] - (-2.941)) < 0.01
    assert stats["max_drawdown_R"] == -3.0
    assert stats["risk_per_trade_pct"] == 1.0

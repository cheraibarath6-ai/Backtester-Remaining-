import pandas as pd

from crypto_research.aggregate_independent import (
    _aggregate_trade_rows,
    _aggregate_yearly_trade_rows,
)


def _trades():
    return pd.DataFrame({
        "model": ["M6", "M6", "M6", "M6"],
        "variant": ["BASELINE"] * 4,
        "timeframe": ["4h"] * 4,
        "symbol": ["BTCUSDT", "BTCUSDT", "ETHUSDT", "ETHUSDT"],
        "exit_time": [
            "2025-01-01T04:00:00Z",
            "2025-01-02T04:00:00Z",
            "2026-01-01T04:00:00Z",
            "2026-01-02T04:00:00Z",
        ],
        "net_bps": [100.0, -50.0, 200.0, -100.0],
        "net_R": [2.0, -1.0, 1.0, -2.0],
        "holding_minutes": [240, 480, 240, 720],
    })


def test_cross_symbol_aggregate_reports_both_notional_and_r_pf():
    result = _aggregate_trade_rows(_trades()).iloc[0]
    assert result.trades == 4
    assert result.symbol_streams == 2
    assert result.aggregate_trade_pf_bps == 2.0
    assert result.aggregate_profit_factor_R == 1.0
    assert result.net_R_sum == 0.0
    assert result.fixed_initial_equity_risk_return_pct_at_1pct == 0.0
    assert result.avg_holding_minutes == 420.0
    assert "not a capital-weighted portfolio" in result.note


def test_cross_symbol_yearly_summary_is_separate_by_calendar_year():
    result = _aggregate_yearly_trade_rows(_trades()).sort_values("year")
    assert result.year.tolist() == [2025, 2026]
    assert result.trades.tolist() == [2, 2]
    assert result.net_R_sum.tolist() == [1.0, -1.0]


def test_data_gap_trade_rows_are_audited_but_excluded_from_metrics():
    trades = _trades()
    trades["exit_reason"] = ["TARGET", "STOP", "TARGET", "DATA_GAP"]

    aggregate = _aggregate_trade_rows(trades).iloc[0]
    assert aggregate.trades == 3
    assert aggregate.total_trade_records == 4
    assert aggregate.data_gap_trades == 1
    assert aggregate.net_R_sum == 2.0
    assert aggregate.aggregate_profit_factor_R == 3.0

    yearly = _aggregate_yearly_trade_rows(trades).sort_values("year")
    assert yearly.year.tolist() == [2025, 2026]
    assert yearly.trades.tolist() == [2, 1]
    assert yearly.data_gap_trades.tolist() == [0, 1]
    assert yearly.net_R_sum.tolist() == [1.0, 1.0]

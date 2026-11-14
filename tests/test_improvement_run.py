import pandas as pd

from crypto_research.improvement_run import (
    ACTIVE_MODELS,
    _retention_band,
    cost_diagnostics,
    improvement_profiles,
)


def test_improvement_scope_contains_only_the_eight_selected_independent_models():
    profiles = improvement_profiles()
    assert tuple(profiles) == ACTIVE_MODELS
    assert set(ACTIVE_MODELS) == {"M6", "M7", "M8", "M10", "M12", "M13", "M14", "M15"}
    assert "M9" not in profiles and "M11" not in profiles
    assert all(items[0]["variant"] == "BASELINE" for items in profiles.values())
    assert all(len({p["variant"] for p in items}) == len(items) for items in profiles.values())


def test_cost_diagnostics_separates_gross_move_fees_slippage_and_funding():
    trades = pd.DataFrame([
        {
            "side": "LONG", "raw_entry": 100.0, "raw_exit": 102.0,
            "gross_price_move_bps": 200.0, "gross_return_pct": 1.9,
            "fees_pct": 0.1, "slippage_cost_pct": 0.02,
            "funding_cost_pct": 0.01, "net_bps": 187.0,
            "exit_reason": "TARGET",
        },
        {
            "side": "SHORT", "raw_entry": 100.0, "raw_exit": 101.0,
            "gross_price_move_bps": -100.0, "gross_return_pct": -1.1,
            "fees_pct": 0.1, "slippage_cost_pct": 0.02,
            "funding_cost_pct": 0.0, "net_bps": -112.0,
            "exit_reason": "STOP",
        },
        {
            "side": "LONG", "raw_entry": 100.0, "raw_exit": 90.0,
            "gross_price_move_bps": -1000.0, "gross_return_pct": -10.0,
            "fees_pct": 0.1, "slippage_cost_pct": 0.02,
            "funding_cost_pct": 0.0, "net_bps": -1012.0,
            "exit_reason": "DATA_GAP",
        },
    ])

    result = cost_diagnostics(trades)

    assert result["gross_price_move_bps"] == 100.0
    assert result["gross_price_points"] == 1.0
    assert result["gross_executed_bps"] == 80.0
    assert result["fees_bps"] == 20.0
    assert result["slippage_bps"] == 4.0
    assert result["funding_bps"] == 1.0
    assert result["total_cost_bps"] == 25.0
    assert result["net_pnl_bps"] == 75.0
    assert result["gross_positive_move_bps"] == 200.0
    assert result["cost_share_of_gross_positive_pct"] == 12.5


def test_retention_band_reports_trade_count_tradeoff_explicitly():
    assert _retention_band(100.0) == ">=100%"
    assert _retention_band(97.0) == ">=95%"
    assert _retention_band(92.0) == ">=90%"
    assert _retention_band(87.0) == ">=85%"
    assert _retention_band(82.0) == ">=80%"
    assert _retention_band(74.0) == "<80%"
    assert _retention_band(None) == "NO_BASELINE"

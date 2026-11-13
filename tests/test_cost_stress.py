import pandas as pd

from crypto_research.cost_stress_run import (
    COST_SCENARIOS,
    SELECTED_VARIANTS,
    block_bootstrap_metrics,
    selected_profiles,
)


def test_cost_scenarios_reexecute_with_increasing_costs():
    assert [(x["fee_bps"], x["slippage_bps"]) for x in COST_SCENARIOS] == [
        (5.0, 2.0), (7.5, 3.0), (10.0, 5.0), (15.0, 10.0)
    ]


def test_selected_stress_profiles_are_independent_and_exclude_m3():
    profiles = selected_profiles()
    assert set(profiles) == {"M6", "M11"}
    assert {p["variant"] for p in profiles["M6"]} == SELECTED_VARIANTS["M6"]
    assert {p["variant"] for p in profiles["M11"]} == SELECTED_VARIANTS["M11"]
    assert not any("M3" in name for group in profiles.values() for name in [p["variant"] for p in group])


def test_block_bootstrap_is_reproducible_and_keeps_trade_clusters():
    index = pd.date_range("2025-01-01", periods=80, freq="4h", tz="UTC")
    trades = pd.DataFrame({
        "exit_time": index,
        "net_R": [0.8 if i % 3 else -0.7 for i in range(80)],
        "exit_reason": ["TIME"] * 80,
    })
    first = block_bootstrap_metrics(trades, seed=1234, resamples=50, block_size=10)
    second = block_bootstrap_metrics(trades, seed=1234, resamples=50, block_size=10)
    assert first == second
    assert first["trades"] == 80
    assert first["resamples"] == 50
    assert 0 <= first["prob_net_R_positive_pct"] <= 100



def test_cost_stress_grid_does_not_define_any_ensemble_or_m3_profile():
    profiles = selected_profiles()
    assert all(model in {"M6", "M11"} for model in profiles)
    assert "M3" not in profiles

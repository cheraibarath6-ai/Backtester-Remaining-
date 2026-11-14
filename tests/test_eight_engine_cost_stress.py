import pandas as pd

from crypto_research.eight_engine_cost_stress_run import (
    ACTIVE_MODELS,
    COST_SCENARIOS,
    attach_excursions,
    cost_stress_profiles,
)


def test_cost_stress_profiles_are_exactly_the_eight_approved_independent_models():
    profiles = cost_stress_profiles()
    assert set(profiles) == set(ACTIVE_MODELS)
    assert len(ACTIVE_MODELS) == 8
    for model, variants in profiles.items():
        names = [item["variant"] for item in variants]
        assert names[0] == "BASELINE"
        assert len(names) == len(set(names))
    assert not ({"M1", "M2", "M3", "M4", "M5", "M9", "M11"} & set(profiles))


def test_cost_scenarios_increase_fees_and_slippage_without_changing_model_scope():
    assert [item["fee_bps"] for item in COST_SCENARIOS] == [5.0, 7.5, 10.0, 15.0]
    assert [item["slippage_bps"] for item in COST_SCENARIOS] == [2.0, 3.0, 5.0, 10.0]


def test_excursions_are_directional_and_use_complete_one_minute_path():
    index = pd.date_range("2024-01-01 00:00:00", periods=3, freq="1min", tz="UTC")
    raw = pd.DataFrame(
        {
            "high": [101.0, 111.0, 105.0],
            "low": [99.0, 94.0, 98.0],
        },
        index=index,
    )
    trades = pd.DataFrame(
        {
            "entry_time": ["2024-01-01T00:00:00Z", "2024-01-01T00:00:00Z"],
            "exit_time": ["2024-01-01T00:03:00Z", "2024-01-01T00:03:00Z"],
            "side": ["LONG", "SHORT"],
            "raw_entry": [100.0, 100.0],
            "entry": [100.0, 100.0],
            "initial_stop": [95.0, 105.0],
        }
    )

    result = attach_excursions(trades, raw)
    assert result.excursion_complete.tolist() == [True, True]
    assert result.mae_bps.tolist() == [600.0, 1100.0]
    assert result.mfe_bps.tolist() == [1100.0, 600.0]
    assert result.mae_R.iloc[0] == 1.2
    assert result.mfe_R.iloc[0] == 2.2


def test_incomplete_one_minute_path_is_not_used_for_mae_mfe():
    index = pd.DatetimeIndex([
        "2024-01-01 00:00:00+00:00",
        "2024-01-01 00:02:00+00:00",
    ])
    raw = pd.DataFrame({"high": [101.0, 105.0], "low": [99.0, 98.0]}, index=index)
    trades = pd.DataFrame(
        {
            "entry_time": ["2024-01-01T00:00:00Z"],
            "exit_time": ["2024-01-01T00:03:00Z"],
            "side": ["LONG"],
            "raw_entry": [100.0],
            "entry": [100.0],
            "initial_stop": [95.0],
        }
    )

    result = attach_excursions(trades, raw)
    assert result.excursion_complete.iloc[0] == False
    assert pd.isna(result.mae_bps.iloc[0])
    assert pd.isna(result.mfe_bps.iloc[0])

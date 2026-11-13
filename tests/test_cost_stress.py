import zipfile

import pandas as pd

from crypto_research.metrics import read_metrics_zip

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
    assert "BASELINE_H24" in {p["variant"] for p in profiles["M6"]}
    assert "HOLD_48H" in {p["variant"] for p in profiles["M6"]}
    assert next(p for p in profiles["M6"] if p["variant"] == "HOLD_48H")["hold_hours"] == 48.0
    assert {"STOP2_H24", "RR3_H24", "VOLUME12_H24"} <= {p["variant"] for p in profiles["M6"]}
    assert "OI05_PRICE025_H36" in {p["variant"] for p in profiles["M11"]}
    assert "BASELINE_H24" in {p["variant"] for p in profiles["M11"]}
    assert next(p for p in profiles["M6"] if p["variant"] == "BASELINE_H24")["hold_hours"] == 24.0
    assert next(p for p in profiles["M11"] if p["variant"] == "BASELINE_H24")["hold_hours"] == 24.0



def test_historical_oi_loader_shifts_post_june_2026_rows_to_available_time(tmp_path):
    csv = (
        "create_time,symbol,sum_open_interest,sum_open_interest_value\n"
        "2026-06-24 23:55:00,BTCUSDT,10,1000\n"
        "2026-06-25 00:00:00,BTCUSDT,11,1100\n"
        "2026-06-25 00:05:00,BTCUSDT,12,1200\n"
    )
    path = tmp_path / "BTCUSDT-metrics-2026-06-25.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("BTCUSDT-metrics-2026-06-25.csv", csv)

    oi = read_metrics_zip(path, "BTCUSDT")

    assert pd.Timestamp("2026-06-24 23:55:00", tz="UTC") in oi.index
    assert pd.Timestamp("2026-06-25 00:05:00", tz="UTC") in oi.index
    assert pd.Timestamp("2026-06-25 00:10:00", tz="UTC") in oi.index
    assert pd.Timestamp("2026-06-25 00:00:00", tz="UTC") not in oi.index
    assert oi.loc[pd.Timestamp("2026-06-25 00:05:00", tz="UTC"), "sum_open_interest_value"] == 1100
    assert "shifted +5m" in oi.attrs["timestamp_alignment"]

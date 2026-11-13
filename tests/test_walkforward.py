import pandas as pd

from crypto_research.walkforward_run import (
    completed_training_cohort,
    select_candidate,
    build_test_year_window,
)


def _trades(values, start="2021-01-01"):
    entries = pd.date_range(start, periods=len(values), freq="1D", tz="UTC")
    exits = entries + pd.Timedelta(hours=1)
    return pd.DataFrame({
        "entry_time": entries.astype(str),
        "exit_time": exits.astype(str),
        "net_bps": [value * 100 for value in values],
        "net_R": values,
        "net_return_pct": [value for value in values],
        "funding_cost_pct": [0.0] * len(values),
        "holding_minutes": [60] * len(values),
        "exit_reason": ["TARGET" if value > 0 else "STOP" for value in values],
    })


def test_training_cohort_excludes_boundary_and_censored_trades_but_keeps_gap_audit_rows():
    trades = _trades([1.0, -0.5, 0.2, 0.3])
    trades.loc[2, "exit_time"] = "2023-01-01T00:00:00+00:00"
    trades.loc[3, "exit_reason"] = "END_OF_SAMPLE"
    trades.loc[1, "exit_reason"] = "DATA_GAP"

    cohort = completed_training_cohort(trades, "2021-01-01", "2023-01-01")

    assert len(cohort) == 2
    assert "DATA_GAP" in set(cohort.exit_reason)
    assert "END_OF_SAMPLE" not in set(cohort.exit_reason)
    assert pd.to_datetime(cohort.exit_time, utc=True).max() < pd.Timestamp("2023-01-01", tz="UTC")


def test_selector_uses_net_r_as_primary_rank_not_highest_pf_alone():
    high_pf_low_net = _trades([0.1] * 19 + [-0.1])
    lower_pf_higher_net = _trades([1.0] * 15 + [-0.5] * 5)
    candidates = [
        {"profile": {"model": "M6", "variant": "HIGH_PF", "parameters": {}}, "trades": high_pf_low_net},
        {"profile": {"model": "M6", "variant": "HIGHER_NET_R", "parameters": {}}, "trades": lower_pf_higher_net},
    ]

    selected, scores = select_candidate(
        candidates, "2021-01-01", "2022-01-01", min_train_trades=10
    )

    assert selected is not None
    assert selected["profile"]["variant"] == "HIGHER_NET_R"
    assert len(scores) == 2


def test_year_window_disables_entries_at_and_after_exclusive_end():
    index = pd.date_range("2022-12-31 20:00", periods=10, freq="4h", tz="UTC")
    signals = pd.DataFrame({"signal": [1, 1, -1, -1, 1, 1, 1, -1, 1, 1]}, index=index)

    window = build_test_year_window(signals, "2023-01-01", "2023-01-02")

    assert window.index[0] == pd.Timestamp("2023-01-01 00:00", tz="UTC")
    assert window.signal.iloc[0] == 1
    assert window.loc[pd.Timestamp("2023-01-02", tz="UTC"), "signal"] == 0
    assert (window.loc[window.index >= pd.Timestamp("2023-01-02", tz="UTC"), "signal"] == 0).all()


def test_walkforward_profile_universe_is_independent_and_contains_no_m3():
    from crypto_research.combination_run import combination_profiles

    assert {p["variant"] for p in combination_profiles("M6")}
    assert {p["variant"] for p in combination_profiles("M11")}
    assert all("M3" not in p["variant"] for model in ("M6", "M11") for p in combination_profiles(model))

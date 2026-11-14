import pandas as pd

from crypto_research.eight_engine_walkforward_run import (
    ACTIVE_MODELS,
    build_test_window,
    retention_metrics,
    select_candidate,
)
from crypto_research.eight_engine_cost_stress_run import cost_stress_profiles


def _trades(entries, outcomes):
    entries = pd.to_datetime(entries, utc=True)
    values = list(outcomes)
    frame = pd.DataFrame({
        "entry_time": entries.astype(str),
        "exit_time": (entries + pd.Timedelta(hours=1)).astype(str),
        "side": ["LONG"] * len(entries),
        "net_bps": [value * 10 for value in values],
        "net_R": values,
        "net_return_pct": [value / 100 for value in values],
        "funding_cost_pct": [0.0] * len(entries),
        "fees_pct": [0.0] * len(entries),
        "slippage_cost_pct": [0.0] * len(entries),
        "gross_return_pct": [value / 100 for value in values],
        "gross_price_move_bps": [value * 10 for value in values],
        "raw_entry": [100.0] * len(entries),
        "raw_exit": [100.0 + value for value in values],
        "entry": [100.0] * len(entries),
        "holding_minutes": [60] * len(entries),
        "exit_reason": ["TARGET" if value > 0 else "STOP" for value in values],
    })
    return frame


def test_active_model_and_cost_profile_scope_is_exactly_eight_independent_models():
    expected = {"M6", "M7", "M8", "M10", "M12", "M13", "M14", "M15"}
    assert set(ACTIVE_MODELS) == expected
    assert set(cost_stress_profiles()) == expected


def test_retention_metrics_separate_count_overlap_and_rejected_counterfactuals():
    entries = pd.date_range("2021-01-01", periods=10, freq="D", tz="UTC")
    baseline = _trades(entries, [1, 1, 1, 1, 1, -1, -1, -1, -1, -1])
    candidate = _trades(entries[:8], [1, 1, 1, 1, 1, -1, -1, -1])

    metrics = retention_metrics(baseline, candidate)

    assert metrics["baseline_trades"] == 10
    assert metrics["candidate_trades"] == 8
    assert metrics["trade_count_retention_pct"] == 80.0
    assert metrics["baseline_entry_retention_pct"] == 80.0
    assert metrics["rejected_baseline_entries"] == 2
    assert metrics["rejected_baseline_net_bps"] == -20.0
    assert metrics["new_entries"] == 0


def test_selector_rejects_high_net_r_candidate_that_discards_most_baseline_entries():
    entries = pd.date_range("2021-01-01", periods=100, freq="D", tz="UTC")
    baseline = _trades(entries, [1] * 50 + [-1] * 50)
    low_retention = _trades(entries[:40], [2] * 40)
    high_retention = _trades(entries[:90], [1] * 60 + [-1] * 30)
    candidates = [
        {"profile": {"model": "M6", "variant": "BASELINE", "parameters": {}, "rr": 2.0, "hold_hours": 24.0}, "trades": baseline, "signals": None},
        {"profile": {"model": "M6", "variant": "LOW_RETENTION", "parameters": {}, "rr": 2.0, "hold_hours": 24.0}, "trades": low_retention, "signals": None},
        {"profile": {"model": "M6", "variant": "HIGH_RETENTION", "parameters": {}, "rr": 2.0, "hold_hours": 24.0}, "trades": high_retention, "signals": None},
    ]

    selected, scores = select_candidate(
        candidates,
        "2021-01-01",
        "2022-01-01",
        min_train_trades=30,
        min_entry_retention_pct=80.0,
        min_count_retention_pct=80.0,
    )

    assert selected is not None
    assert selected["profile"]["variant"] == "HIGH_RETENTION"
    assert next(row for row in scores if row["variant"] == "LOW_RETENTION")["eligible"] is False
    assert next(row for row in scores if row["variant"] == "HIGH_RETENTION")["eligible"] is True


def test_test_window_disables_entries_at_exclusive_year_end():
    index = pd.date_range("2023-01-01", periods=4, freq="4h", tz="UTC")
    signals = pd.DataFrame({"signal": [1, -1, 1, -1]}, index=index)

    window = build_test_window(signals, "2023-01-01", "2023-01-01 08:00:00")

    assert window.signal.tolist() == [1, -1, 0, 0]

import pandas as pd

from crypto_research.forward_run import (
    mask_pre_evaluation_signals,
    parse_kline_rows,
    parse_open_interest_rows,
    selected_forward_profiles,
)


def test_forward_mask_preserves_warmup_but_disables_pre_evaluation_entries():
    index = pd.date_range("2026-10-31 16:00:00", periods=4, freq="4h", tz="UTC")
    signals = pd.DataFrame(
        {"signal": [1, -1, 1, -1], "close": [100.0, 101.0, 102.0, 103.0]},
        index=index,
    )

    masked = mask_pre_evaluation_signals(signals, "2026-11-01 00:00:00")

    assert masked.signal.tolist() == [0, -1, 1, -1]
    assert masked.close.equals(signals.close)
    assert signals.signal.tolist() == [1, -1, 1, -1]


def test_recent_kline_parser_uses_official_api_timestamp_and_columns():
    open_ms = int(pd.Timestamp("2026-11-01 00:00:00", tz="UTC").timestamp() * 1000)
    rows = [[
        open_ms, "100", "102", "99", "101", "12",
        open_ms + 59_999, "1212", 25, "7", "707", "0",
    ]]

    bars = parse_kline_rows(rows)

    assert len(bars) == 1
    assert bars.index[0] == pd.Timestamp("2026-11-01 00:00:00", tz="UTC")
    assert bars.iloc[0].close == 101.0
    assert bars.iloc[0].taker_buy_base == 7.0
    assert bars.iloc[0].trades == 25


def test_recent_open_interest_parser_keeps_official_value_field():
    timestamp = int(pd.Timestamp("2026-11-01 00:05:00", tz="UTC").timestamp() * 1000)
    rows = [{
        "symbol": "BTCUSDT",
        "sumOpenInterest": "1234.5",
        "sumOpenInterestValue": "987654.3",
        "timestamp": timestamp,
    }]

    oi = parse_open_interest_rows(rows, "BTCUSDT")

    assert len(oi) == 1
    assert oi.index[0] == pd.Timestamp("2026-11-01 00:05:00", tz="UTC")
    assert oi.iloc[0].sum_open_interest_value == 987654.3


def test_forward_profiles_are_predeclared_and_keep_models_independent():
    profiles = selected_forward_profiles()

    assert set(profiles) == {"M6", "M11"}
    assert {p["variant"] for p in profiles["M6"]} == {
        "D100_STOP2_H168", "RR3_H168", "STOP2_H168"
    }
    assert {p["variant"] for p in profiles["M11"]} == {
        "OI05_H48", "PRICE025_RR3_H48", "OI05_PRICE025_H36"
    }
    assert not any("M3" in p["variant"] for group in profiles.values() for p in group)

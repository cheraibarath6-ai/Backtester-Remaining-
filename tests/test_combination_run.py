from crypto_research.eight_engine_combination_run import combination_profiles


def test_combination_research_is_limited_to_evidence_led_models():
    profiles = combination_profiles()
    assert set(profiles) == {"M6", "M8", "M15"}
    assert all(items[0]["variant"] == "BASELINE" for items in profiles.values())
    assert "M9" not in profiles and "M11" not in profiles
    assert all(len({p["variant"] for p in items}) == len(items) for items in profiles.values())


def test_m6_combinations_change_only_model_specific_donchian_parameters():
    profiles = {p["variant"]: p for p in combination_profiles()["M6"]}
    assert profiles["RR3_STOP3"]["rr"] == 3.0
    assert profiles["RR3_STOP3"]["parameters"]["stop_atr"] == 3.0
    assert profiles["RR3_VOL12"]["rr"] == 3.0
    assert profiles["RR3_VOL12"]["parameters"]["volume_ratio_min"] == 1.2
    assert profiles["RR3_HOLD48"]["rr"] == 3.0
    assert profiles["RR3_HOLD48"]["hold_hours"] == 48.0


def test_m8_combinations_keep_volatility_expansion_model_independent():
    profiles = {p["variant"]: p for p in combination_profiles()["M8"]}
    assert profiles["HOLD48_VOL10"]["hold_hours"] == 48.0
    assert profiles["HOLD48_VOL10"]["parameters"]["volume_ratio_min"] == 1.0
    assert profiles["HOLD48_RR3"]["hold_hours"] == 48.0
    assert profiles["HOLD48_RR3"]["rr"] == 3.0
    assert profiles["HOLD48_EXP15"]["parameters"]["expansion_atr"] == 1.5
    assert profiles["VOL10_RR3"]["parameters"]["volume_ratio_min"] == 1.0
    assert profiles["VOL10_RR3"]["rr"] == 3.0


def test_m15_trailing_variant_is_a_single_model_exit_combination():
    profiles = {p["variant"]: p for p in combination_profiles()["M15"]}
    assert profiles["ATR_TRAIL_2_5"]["trailing_atr_multiple"] == 2.5
    assert profiles["ATR_TRAIL_2_5_H48"]["trailing_atr_multiple"] == 2.5
    assert profiles["ATR_TRAIL_2_5_H48"]["hold_hours"] == 48.0

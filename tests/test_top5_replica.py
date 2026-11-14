from crypto_research.top5_replica_run import TOP5_MODELS, replica_profiles


def test_replica_scope_is_exactly_the_five_selected_4h_models():
    profiles = replica_profiles()
    assert tuple(profiles) == TOP5_MODELS
    assert set(TOP5_MODELS) == {"M6", "M8", "M12", "M14", "M15"}
    assert not ({"M1", "M2", "M3", "M4", "M5", "M9", "M10", "M11", "M13"} & set(profiles))


def test_each_model_has_one_distinct_multi_factor_replica_and_baseline():
    profiles = replica_profiles()
    expected = {
        "M6": "R2_DON55_VOL12_STOP30_RR30_H48",
        "M8": "R2_SQ20_BR40_EXP15_VOL10_STOP25_RR30_H48",
        "M12": "R2_REGIME_BR40_STOP25_RANGE08_H72",
        "M14": "R2_ADX30_DI25_MOM21_STOP25_RR30_H48",
        "M15": "R2_AO05_MACD05_STOP25_TRAIL25_H48",
    }
    for model, variant in expected.items():
        by_name = {item["variant"]: item for item in profiles[model]}
        assert "BASELINE" in by_name
        assert variant in by_name
        assert len(by_name) == len(profiles[model])
        assert by_name[variant]["model"] == model


def test_replicas_change_multiple_model_specific_and_exit_factors():
    profiles = replica_profiles()
    for model, items in profiles.items():
        baseline = next(x for x in items if x["variant"] == "BASELINE")
        replica = next(x for x in items if x["variant"].startswith("R2_"))
        changed_parameters = {
            key for key in set(baseline["parameters"]) | set(replica["parameters"])
            if baseline["parameters"].get(key) != replica["parameters"].get(key)
        }
        changed_exit = sum([
            baseline["rr"] != replica["rr"],
            baseline["hold_hours"] != replica["hold_hours"],
            baseline.get("trailing_atr_multiple") != replica.get("trailing_atr_multiple"),
        ])
        assert len(changed_parameters) + changed_exit >= 3, model


def test_m12_range_stop_is_explicitly_widened_not_confused_with_trend_stop():
    replica = next(x for x in replica_profiles()["M12"] if x["variant"].startswith("R2_"))
    assert replica["parameters"]["range_stop_atr"] == 0.8
    assert replica["parameters"]["stop_atr"] == 2.5


def test_m15_replica_keeps_the_walkforward_supported_trailing_exit():
    replica = next(x for x in replica_profiles()["M15"] if x["variant"].startswith("R2_"))
    assert replica["trailing_atr_multiple"] == 2.5
    assert replica["hold_hours"] == 48

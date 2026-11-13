from crypto_research.sensitivity_run import sensitivity_profiles


def _changed_fields(left, right):
    keys = set(left) | set(right)
    return {key for key in keys if left.get(key) != right.get(key)}


def test_m6_sensitivity_profiles_are_independent_one_factor_variants():
    profiles = sensitivity_profiles("M6")
    assert profiles[0]["variant"] == "BASELINE"
    assert "ATR_TRAIL_2.5" in {p["variant"] for p in profiles}
    assert "HOLD_168H" in {p["variant"] for p in profiles}
    base = profiles[0]
    for profile in profiles[1:]:
        parameter_changes = _changed_fields(base["parameters"], profile["parameters"])
        execution_changes = _changed_fields(
            {k: base.get(k) for k in ("rr", "hold_hours", "trailing_atr_multiple")},
            {k: profile.get(k) for k in ("rr", "hold_hours", "trailing_atr_multiple")},
        )
        assert len(parameter_changes) + len(execution_changes) == 1


def test_m11_sensitivity_profiles_change_one_parameter_or_exit_rule():
    profiles = sensitivity_profiles("M11")
    assert profiles[0]["variant"] == "BASELINE"
    base = profiles[0]
    for profile in profiles[1:]:
        parameter_changes = _changed_fields(base["parameters"], profile["parameters"])
        execution_changes = _changed_fields(
            {k: base.get(k) for k in ("rr", "hold_hours", "trailing_atr_multiple")},
            {k: profile.get(k) for k in ("rr", "hold_hours", "trailing_atr_multiple")},
        )
        assert len(parameter_changes) + len(execution_changes) == 1


def test_sensitivity_suite_excludes_m3_and_keeps_models_separate():
    assert {p["variant"] for p in sensitivity_profiles("M6")} != {
        p["variant"] for p in sensitivity_profiles("M11")
    }
    assert all(p["variant"] for model in ("M6", "M11") for p in sensitivity_profiles(model))

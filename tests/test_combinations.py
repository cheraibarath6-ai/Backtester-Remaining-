from crypto_research.combination_run import combination_profiles


def test_m6_combinations_keep_model_independent_and_include_long_holds():
    profiles = combination_profiles("M6")
    names = {p["variant"] for p in profiles}
    assert "ANCHOR_H168" in names
    assert "D100_STOP2_RR3_H168" in names
    assert "TRAIL25_H168" in names
    assert "BASELINE_H24" in names
    assert next(p for p in profiles if p["variant"] == "BASELINE_H24")["hold_hours"] == 24.0
    assert all(p["hold_hours"] >= 120 for p in profiles if p["variant"] != "BASELINE_H24")


def test_m11_combinations_keep_oi_and_price_thresholds_explicit():
    profiles = combination_profiles("M11")
    names = {p["variant"] for p in profiles}
    assert "OI05_PRICE025_H48" in names
    assert "OI05_PRICE025_RR3_H48" in names
    assert "OI05_PRICE025_H72" in names
    assert "BASELINE_H24" in names
    assert next(p for p in profiles if p["variant"] == "BASELINE_H24")["hold_hours"] == 24.0
    assert all("oi_change_min" in p["parameters"] for p in profiles)


def test_combination_runner_has_no_cross_model_or_ensemble_profile():
    m6 = combination_profiles("M6")
    m11 = combination_profiles("M11")
    assert all(p["variant"] for p in m6 + m11)
    assert len({p["variant"] for p in m6}) == len(m6)
    assert len({p["variant"] for p in m11}) == len(m11)

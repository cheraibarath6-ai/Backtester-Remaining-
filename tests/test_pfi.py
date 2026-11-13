from crypto_research.pfi import FACTOR_VALUES, configurations

def test_pfi_stage_one_has_twenty_five_pairs_per_model():
    for model in ("M1","M2","M4","M5"):
        rows=list(configurations(model))
        assert len(rows)==25
        spec=FACTOR_VALUES[model]
        assert len(spec["values_1"])==5
        assert len(spec["values_2"])==5

def test_pfi_m2_ema_pairs_are_valid_and_supported():
    rows=list(configurations("M2"))
    assert len(rows)==25
    assert all(p["ema_fast"] < p["ema_slow"] for p in rows)
    assert set(p["ema_fast"] for p in rows)=={8,10,15,20,30}
    assert set(p["ema_slow"] for p in rows)=={50,75,100,150,200}

def test_pfi_only_varies_two_declared_factors():
    for model,spec in FACTOR_VALUES.items():
        rows=list(configurations(model))
        varying=set().union(*(set(p) for p in rows))
        assert spec["factor_1"] in varying
        assert spec["factor_2"] in varying
        for p in rows:
            assert p[spec["factor_1"]] in spec["values_1"]
            assert p[spec["factor_2"]] in spec["values_2"]
            for k,v in spec["fixed"].items():
                assert p[k]==v

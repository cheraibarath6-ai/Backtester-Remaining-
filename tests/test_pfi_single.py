from crypto_research.pfi_single import SPECS, configurations

def test_stage2_uses_only_factors_not_tested_in_stage1():
    expected={"M1":"swing_lookback","M2":"rsi_trigger","M4":"max_retest_age","M5":"funding_lookback"}
    for model,factor in expected.items():
        assert SPECS[model]["factor"]==factor

def test_stage2_preserves_stage1_anchor_zones():
    expected={
      "M1":{"max_sweep_depth_atr":[0.35,0.50,0.65,0.80,1.00],"displacement_atr":[1.20,1.40,1.60]},
      "M2":{"ema_fast":[8,10,15,20,30],"ema_slow":[50,75,150,200]},
      "M4":{"range_lookback":[20,25,30],"retest_tolerance_atr":[0.10,0.20,0.30,0.40,0.50]},
      "M5":{"funding_percentile":[0.05,0.15,0.20,0.25],"taker_imbalance":[0.51,0.53,0.55]}
    }
    for model,anchors in expected.items():
        assert SPECS[model]["anchors"]==anchors

def test_stage2_configuration_counts_and_validity():
    expected={"M1":165,"M2":220,"M4":150,"M5":120}
    for model,count in expected.items():
        rows=list(configurations(model))
        assert len(rows)==count
        factor=SPECS[model]["factor"]
        assert {p[factor] for p in rows}==set(SPECS[model]["values"])
        for p in rows:
            for key,values in SPECS[model]["anchors"].items():
                assert p[key] in values
            for key,value in SPECS[model]["fixed"].items():
                assert p[key]==value
    assert all(p["ema_fast"]<p["ema_slow"] for p in configurations("M2"))

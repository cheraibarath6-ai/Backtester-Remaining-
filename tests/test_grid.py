import pandas as pd
from crypto_research.grid import GRID, RAW_COUNTS, parameter_count, parameter_sets, invalid_reason, _penetration_ok

def test_exact_raw_grid_counts_and_unique_rows():
    assert RAW_COUNTS == {"M1":39366,"M2":13122,"M4":13122,"M5":13122}
    for model in RAW_COUNTS:
        rows=list(parameter_sets(model))
        assert len(rows)==parameter_count(model)
        assert len({tuple(sorted(x.items())) for x in rows})==len(rows)

def test_m2_invalid_ema_pairs_are_explicit_not_silently_removed():
    rows=list(parameter_sets("M2"))
    invalid=[p for p in rows if invalid_reason("M2",p)]
    assert len(invalid)==3*(3**6)*2
    assert len(rows)-len(invalid)==8748

def test_parameter_values_match_requested_ranges():
    assert GRID["M1"]["swing_lookback"]==[10,20,30]
    assert GRID["M1"]["sweep_recency"]==[3,6,9]
    assert GRID["M2"]["ema_fast"]==[10,20,30]
    assert GRID["M2"]["ema_slow"]==[50,100,200]
    assert GRID["M4"]["retest_tolerance_atr"]==[0.10,0.25,0.50]
    assert GRID["M5"]["funding_lookback"]==[90,180,270]

def test_m4_retest_rejects_deep_intermediate_long_penetration():
    idx=pd.RangeIndex(5)
    d=pd.DataFrame({"low":[9.9,9.9,9.7,9.9,9.9],"high":[10.1]*5,"atr":[1.0]*5},index=idx)
    level=pd.Series([10.0]*5,index=idx)
    assert bool(_penetration_ok(d,level,3,1).iloc[4]) is False

def test_m4_retest_rejects_deep_intermediate_short_penetration():
    idx=pd.RangeIndex(5)
    d=pd.DataFrame({"high":[10.1,10.1,10.3,10.1,10.1],"low":[9.9]*5,"atr":[1.0]*5},index=idx)
    level=pd.Series([10.0]*5,index=idx)
    assert bool(_penetration_ok(d,level,3,-1).iloc[4]) is False

def test_m4_retest_accepts_shallow_path():
    idx=pd.RangeIndex(5)
    d=pd.DataFrame({"low":[9.9]*5,"high":[10.1]*5,"atr":[1.0]*5},index=idx)
    level=pd.Series([10.0]*5,index=idx)
    assert bool(_penetration_ok(d,level,3,1).iloc[4])
    assert bool(_penetration_ok(d,level,3,-1).iloc[4])

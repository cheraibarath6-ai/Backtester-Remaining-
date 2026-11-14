import numpy as np
import pandas as pd
from crypto_research.head_engine import HEAD_CONFIGS, MODEL_PRIORITY, combine_model_signals

def frame(index, signals, stops):
    return pd.DataFrame({"open":[100.0]*len(index),"high":[101.0]*len(index),"low":[99.0]*len(index),"close":[100.0]*len(index),"atr":[1.0]*len(index),"signal":signals,"stop":stops,"target":[np.nan]*len(index)},index=index)

def test_single_model_trigger_is_sufficient():
    idx=pd.date_range("2025-01-01",periods=3,freq="4h",tz="UTC")
    out=combine_model_signals({"M8":frame(idx,[0,1,0],[np.nan,97.0,np.nan])})
    assert out.signal.tolist()==[0,1,0] and out.head_source.iloc[1]=="M8"
    assert out.trigger_count.iloc[1]==1

def test_same_direction_triggers_are_coalesced_not_voted():
    idx=pd.date_range("2025-01-01",periods=2,freq="4h",tz="UTC")
    out=combine_model_signals({"M6":frame(idx,[1,0],[97.0,np.nan]),"M8":frame(idx,[1,0],[98.0,np.nan])})
    assert out.signal.iloc[0]==1 and out.trigger_count.iloc[0]==2
    assert out.trigger_sources.iloc[0]=="M6,M8" and out.head_source.iloc[0]=="M6"

def test_opposing_same_bar_triggers_use_priority_and_audit_conflict():
    idx=pd.date_range("2025-01-01",periods=2,freq="4h",tz="UTC")
    out=combine_model_signals({"M15":frame(idx,[-1,0],[103.0,np.nan]),"M6":frame(idx,[1,0],[97.0,np.nan])})
    assert out.signal.iloc[0]==1 and out.head_source.iloc[0]=="M6"
    assert bool(out.same_bar_conflict.iloc[0]) and out.trigger_count.iloc[0]==2

def test_five_frozen_models_and_exit_profiles():
    assert set(HEAD_CONFIGS)==set(MODEL_PRIORITY)
    assert HEAD_CONFIGS["M6"]["rr"]==3.0
    assert HEAD_CONFIGS["M12"]["hold_hours"]==72
    assert HEAD_CONFIGS["M15"]["trailing_atr_multiple"]==2.5

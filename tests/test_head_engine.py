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


def test_entry_timestamp_is_next_completed_bar_open():
    from crypto_research.head_engine import run_head_backtest

    idx = pd.date_range("2025-01-01", periods=3, freq="4h", tz="UTC")
    bars = pd.DataFrame({
        "open": [100.0, 100.0, 101.0],
        "high": [101.0, 102.0, 102.0],
        "low": [99.0, 99.0, 100.0],
        "close": [100.0, 101.0, 101.0],
        "atr": [1.0, 1.0, 1.0],
        "signal": [1, 0, 0],
        "stop": [95.0, np.nan, np.nan],
        "target": [110.0, np.nan, np.nan],
        "head_rr": [2.0, np.nan, np.nan],
        "head_hold_bars": [1.0, np.nan, np.nan],
        "head_trailing_atr_multiple": [np.nan, np.nan, np.nan],
        "head_source": ["M6", "", ""],
        "trigger_sources": ["M6", "", ""],
        "trigger_count": [1, 0, 0],
        "same_bar_conflict": [False, False, False],
    }, index=idx)
    funding = pd.DataFrame(columns=["funding_rate", "mark_price"])
    trades = run_head_backtest(bars, funding, "BTCUSDT")
    assert len(trades) == 1
    assert trades.iloc[0].entry_time == str(idx[1] - pd.Timedelta(hours=4))
    assert trades.iloc[0].exit_reason == "TIME"



def test_batch_history_start_has_130_complete_4h_warmup_bars():
    from crypto_research.head_engine import batch_history_start

    assert batch_history_start("2022-01-01") == pd.Timestamp("2021-12-10 08:00:00", tz="UTC")
    assert batch_history_start("2021-11-14") == pd.Timestamp("2021-10-23 08:00:00", tz="UTC")


def test_batch_trade_scoping_assigns_boundary_exit_once_and_keeps_cross_boundary_trade():
    from crypto_research.head_engine import scope_batch_trades

    rows = pd.DataFrame({
        "entry_time": [
            "2021-12-31 20:00:00+00:00",
            "2022-01-01 00:00:00+00:00",
            "2022-01-01 04:00:00+00:00",
        ],
        "exit_time": [
            "2022-01-01 00:00:00+00:00",
            "2022-01-01 08:00:00+00:00",
            "2022-01-01 12:00:00+00:00",
        ],
        "exit_reason": ["TARGET", "STOP", "END_OF_SAMPLE"],
    })
    first = scope_batch_trades(rows, "2021-11-14", "2022-01-01")
    second = scope_batch_trades(rows, "2022-01-01", "2023-01-01")

    assert first.index.tolist() == [0]
    assert second.index.tolist() == [1, 2]
    assert set(first.index).isdisjoint(set(second.index))


def test_batch_scoping_retains_pre_window_data_gap_audit():
    from crypto_research.head_engine import scope_batch_trades

    rows = pd.DataFrame({
        "entry_time": ["2021-12-31 12:00:00+00:00"],
        "exit_time": ["2021-12-31 20:00:00+00:00"],
        "exit_reason": ["DATA_GAP"],
    })
    scoped = scope_batch_trades(rows, "2022-01-01", "2023-01-01")
    assert len(scoped) == 1
    assert scoped.iloc[0].exit_reason == "DATA_GAP"

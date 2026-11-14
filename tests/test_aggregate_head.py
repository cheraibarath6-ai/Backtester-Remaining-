import pandas as pd

from crypto_research.aggregate_head import _dedupe_trigger_audit, _model_attribution


def test_trigger_audit_dedup_keeps_same_model_combination_at_distinct_bars():
    audit = pd.DataFrame({
        "symbol": ["BTCUSDT", "BTCUSDT", "BTCUSDT"],
        "open_time": [
            "2022-01-01 00:00:00+00:00",
            "2022-01-01 04:00:00+00:00",
            "2022-01-01 04:00:00+00:00",
        ],
        "head_source": ["M6", "M6", "M6"],
        "trigger_sources": ["M6,M8", "M6,M8", "M6,M8"],
    })

    deduped = _dedupe_trigger_audit(audit)
    assert len(deduped) == 2

    attribution = _model_attribution(pd.DataFrame(), deduped, ["BTCUSDT"])
    m6 = attribution.loc[attribution.model == "M6"].iloc[0]
    m8 = attribution.loc[attribution.model == "M8"].iloc[0]
    assert m6.trigger_bars == 2
    assert m8.trigger_bars == 2
    assert m6.selected_bars == 2

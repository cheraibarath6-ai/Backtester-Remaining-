from __future__ import annotations

"""One additional, evidence-led multi-factor replicate for the top five 4h engines.

Each model has its own candidate profile and is backtested independently.
No cross-model signal, ranking, voting, or portfolio combination is used.
"""

from . import improvement_run as runner
from .improvement_run import _profile

TOP5_MODELS = ("M6", "M8", "M12", "M14", "M15")
_BASE_FACTORY = runner.improvement_profiles


def replica_profiles():
    original = _BASE_FACTORY()
    selected = {
        "M6": [
            item for item in original["M6"]
            if item["variant"] in {"BASELINE", "RR_3_0", "VOLUME_1_2", "STOP_ATR_3_0"}
        ],
        "M8": [
            item for item in original["M8"]
            if item["variant"] in {"BASELINE", "HOLD_48H", "VOLUME_1_0", "EXPANSION_1_5"}
        ],
        "M12": [
            item for item in original["M12"]
            if item["variant"] in {"BASELINE", "BREAKOUT_40", "HOLD_72H", "STOP_ATR_2_5"}
        ],
        "M14": [
            item for item in original["M14"]
            if item["variant"] in {"BASELINE", "MOMENTUM_21", "ADX_30", "STOP_ATR_2_5"}
        ],
        "M15": [
            item for item in original["M15"]
            if item["variant"] in {"BASELINE", "AO_MIN_0_05_ATR", "MACD_MIN_0_05_ATR", "STOP_ATR_2_5"}
        ],
    }

    # M6: combine the already supported 3R and volume confirmation with the
    # wider 3-ATR stop and 48h horizon. This directly tests whether the
    # longer breakout follow-through offsets the wider stop's added risk.
    m6 = {"donchian_period": 55, "volume_ratio_min": 1.2, "stop_atr": 3.0}
    selected["M6"].append(
        _profile("M6", "R2_DON55_VOL12_STOP30_RR30_H48", m6, rr=3.0, hold_hours=48)
    )

    # M8: keep the squeeze definition fixed, require a longer 40-bar breakout
    # and 1.5-ATR expansion, but relax volume to 1.0 to protect opportunity
    # count. Wider stop + 3R + 48h aim to let confirmed expansion pay for costs.
    m8 = {
        "squeeze_lookback": 100,
        "squeeze_quantile": 0.20,
        "breakout_period": 40,
        "expansion_atr": 1.5,
        "volume_ratio_min": 1.0,
        "stop_atr": 2.5,
    }
    selected["M8"].append(
        _profile("M8", "R2_SQ20_BR40_EXP15_VOL10_STOP25_RR30_H48",
                 m8, rr=3.0, hold_hours=48)
    )

    # M12: its range branch's 0.5-ATR stop and trend branch's 20-bar
    # breakout are plausible sources of premature exits/noisy breaks.
    # Widen the range stop to 0.8 ATR, use a 40-bar trend breakout and a
    # 2.5-ATR trend stop; keep the 72h horizon supported by prior selection.
    m12 = {
        "breakout_period": 40,
        "trend_adx_min": 25.0,
        "range_adx_max": 18.0,
        "range_bb_z": 2.0,
        "range_rsi": 35.0,
        "stop_atr": 2.5,
        "range_stop_atr": 0.8,
    }
    selected["M12"].append(
        _profile("M12", "R2_REGIME_BR40_STOP25_RANGE08_H72",
                 m12, rr=2.5, hold_hours=72)
    )

    # M14: MOMENTUM_21 was selected most often by the expanding walk-forward.
    # Add ADX>=30 confirmation, a 2.5-ATR stop, 3R objective and 48h horizon
    # to test stronger trend persistence without changing the model family.
    m14 = {
        "adx_min": 30.0,
        "di_min": 25.0,
        "momentum_lookback": 21,
        "stop_atr": 2.5,
    }
    selected["M14"].append(
        _profile("M14", "R2_ADX30_DI25_MOM21_STOP25_RR30_H48",
                 m14, rr=3.0, hold_hours=48)
    )

    # M15: the 2.5-ATR trailing exit was the most frequently selected
    # walk-forward profile. Add modest AO and MACD strength floors to reduce
    # weak zero-line crosses, retaining the same trailing exit architecture.
    m15 = {
        "ao_cross_min_atr": 0.05,
        "macd_min_atr": 0.05,
        "stop_atr": 2.5,
    }
    selected["M15"].append(
        _profile("M15", "R2_AO05_MACD05_STOP25_TRAIL25_H48",
                 m15, hold_hours=48, trailing=2.5)
    )

    expected = set(TOP5_MODELS)
    if set(selected) != expected:
        raise ValueError(f"Replica scope mismatch: {sorted(selected)}")
    for model, items in selected.items():
        names = [item["variant"] for item in items]
        if not names or names[0] != "BASELINE" or len(names) != len(set(names)):
            raise ValueError(f"{model} profiles must be unique and start with BASELINE")
    return selected


def main():
    original_factory = runner.improvement_profiles
    original_models = runner.ACTIVE_MODELS
    runner.improvement_profiles = replica_profiles
    runner.ACTIVE_MODELS = TOP5_MODELS
    try:
        runner.main()
    finally:
        runner.improvement_profiles = original_factory
        runner.ACTIVE_MODELS = original_models


if __name__ == "__main__":
    main()

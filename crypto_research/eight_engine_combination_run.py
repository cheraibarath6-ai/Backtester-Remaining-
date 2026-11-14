from __future__ import annotations

from . import improvement_run as runner
from .improvement_run import _profile

_BASE_PROFILE_FACTORY = runner.improvement_profiles


def combination_profiles():
    """Small, predeclared within-model combinations from positive 4h evidence.

    The regular one-factor runner is not modified. This runner carries only
    M6, M8 and M15 forward, with each model evaluated independently.
    """
    original = _BASE_PROFILE_FACTORY()
    profiles = {
        "M6": [
            item for item in original["M6"]
            if item["variant"] in {"BASELINE", "RR_3_0", "STOP_ATR_3_0", "VOLUME_1_2", "HOLD_48H"}
        ],
        "M8": [
            item for item in original["M8"]
            if item["variant"] in {"BASELINE", "HOLD_48H", "VOLUME_1_0", "EXPANSION_1_5", "RR_3_0"}
        ],
        "M15": [
            item for item in original["M15"]
            if item["variant"] in {"BASELINE", "ATR_TRAIL_2_5"}
        ],
    }

    m6_base = {"donchian_period": 55, "volume_ratio_min": 1.0, "stop_atr": 2.5}
    profiles["M6"].extend([
        _profile("M6", "RR3_STOP3", {**m6_base, "stop_atr": 3.0}, rr=3.0),
        _profile("M6", "RR3_VOL12", {**m6_base, "volume_ratio_min": 1.2}, rr=3.0),
        _profile("M6", "RR3_HOLD48", m6_base.copy(), rr=3.0, hold_hours=48),
        _profile("M6", "HOLD48_STOP3", {**m6_base, "stop_atr": 3.0}, hold_hours=48),
    ])

    m8_base = {
        "squeeze_lookback": 100,
        "squeeze_quantile": 0.20,
        "breakout_period": 20,
        "expansion_atr": 1.2,
        "volume_ratio_min": 1.2,
        "stop_atr": 2.0,
    }
    profiles["M8"].extend([
        _profile("M8", "HOLD48_VOL10", {**m8_base, "volume_ratio_min": 1.0}, hold_hours=48),
        _profile("M8", "HOLD48_RR3", m8_base.copy(), rr=3.0, hold_hours=48),
        _profile("M8", "HOLD48_EXP15", {**m8_base, "expansion_atr": 1.5}, hold_hours=48),
        _profile("M8", "VOL10_RR3", {**m8_base, "volume_ratio_min": 1.0}, rr=3.0),
    ])

    m15_base = {"ao_cross_min_atr": 0.0, "macd_min_atr": 0.0, "stop_atr": 2.0}
    profiles["M15"].append(
        _profile("M15", "ATR_TRAIL_2_5_H48", m15_base.copy(), hold_hours=48, trailing=2.5)
    )

    for model, items in profiles.items():
        names = [item["variant"] for item in items]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate combination profile for {model}")
        if not names or names[0] != "BASELINE":
            raise ValueError(f"{model} combination set must start with BASELINE")

    return profiles


def main():
    # Patch only during this CLI invocation; importing this module in tests
    # never changes the regular one-factor runner.
    original_factory = runner.improvement_profiles
    runner.improvement_profiles = combination_profiles
    try:
        runner.main()
    finally:
        runner.improvement_profiles = original_factory


if __name__ == "__main__":
    main()

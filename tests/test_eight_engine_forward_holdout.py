from crypto_research.eight_engine_forward_holdout_run import (
    FROZEN_VARIANTS,
    HOLDOUT_START,
    MINIMUM_HOLDOUT_DAYS,
    _profile_lookup,
    daily_archive_url,
    expected_daily_dates,
)
from crypto_research.improvement_run import ACTIVE_MODELS


def test_forward_holdout_scope_is_exactly_eight_models():
    expected = {"M6", "M7", "M8", "M10", "M12", "M13", "M14", "M15"}
    assert set(ACTIVE_MODELS) == expected
    assert set(FROZEN_VARIANTS) == expected
    assert "M1" not in FROZEN_VARIANTS
    assert "M5" not in FROZEN_VARIANTS
    assert "M9" not in FROZEN_VARIANTS
    assert "M11" not in FROZEN_VARIANTS


def test_frozen_candidates_are_predeclared_and_exist_in_the_eight_model_profiles():
    profiles = _profile_lookup()
    for model, variant in FROZEN_VARIANTS.items():
        assert "BASELINE" in profiles[model]
        if variant is not None:
            assert variant in profiles[model]


def test_holdout_starts_after_freeze_date_and_requires_a_full_month():
    assert HOLDOUT_START == "2026-11-01"
    assert MINIMUM_HOLDOUT_DAYS == 30
    dates = expected_daily_dates("2026-11-01", "2026-12-01")
    assert len(dates) == 30
    assert dates[0].strftime("%Y-%m-%d") == "2026-11-01"
    assert dates[-1].strftime("%Y-%m-%d") == "2026-11-30"


def test_daily_archive_url_uses_official_binance_vision_usdm_path():
    url = daily_archive_url("BTCUSDT", "2026-11-01")
    assert url == (
        "https://data.binance.vision/data/futures/um/daily/klines/"
        "BTCUSDT/1m/BTCUSDT-1m-2026-11-01.zip"
    )

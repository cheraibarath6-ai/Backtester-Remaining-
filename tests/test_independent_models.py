import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from crypto_research.independent_models import (
    INDEPENDENT_MODELS,
    make_independent_signals,
    prepare_bars,
)
from crypto_research.metrics import read_metrics_zip


def _synthetic_raw(n=5000):
    rng = np.random.default_rng(17)
    index = pd.date_range("2024-01-01", periods=n, freq="1min", tz="UTC")
    returns = rng.normal(0.0, 0.0015, n)
    close = 100 * np.exp(np.cumsum(returns))
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.0015, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.0015, n))
    volume = rng.uniform(50, 250, n)
    taker_ratio = rng.uniform(0.25, 0.75, n)
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "quote_volume": volume * close,
        "trades": rng.integers(5, 100, n),
        "taker_buy_base": volume * taker_ratio,
        "taker_buy_quote": volume * taker_ratio * close,
    }, index=index)


def test_independent_model_list_excludes_m3():
    assert "M3" not in INDEPENDENT_MODELS
    assert set(INDEPENDENT_MODELS) == {
        "M6", "M7", "M8", "M9", "M10", "M11", "M12", "M13", "M14", "M15"
    }


def test_prepare_bars_uses_completed_right_labelled_bars():
    raw = _synthetic_raw(30)
    bars = prepare_bars(raw, "5m")
    assert bars.index[0] == pd.Timestamp("2024-01-01 00:05:00", tz="UTC")
    assert len(bars) == 6


@pytest.mark.parametrize("model", ["M6", "M7", "M8", "M9", "M12", "M14", "M15"])
def test_price_only_independent_models_build_valid_signals(model):
    raw = _synthetic_raw()
    signals = make_independent_signals(raw, model, "15m")
    assert {"signal", "stop", "target", "atr", "adx"}.issubset(signals.columns)
    assert set(signals.signal.unique()).issubset({-1, 0, 1})


@pytest.mark.parametrize("model", ["M10", "M13"])
def test_cross_asset_models_require_and_use_btc_benchmark(model):
    raw = _synthetic_raw()
    with pytest.raises(ValueError, match="requires BTC benchmark"):
        make_independent_signals(raw, model, "1h")
    signals = make_independent_signals(raw, model, "1h", benchmark_raw=raw)
    assert set(signals.signal.unique()).issubset({-1, 0, 1})


def test_m11_requires_real_open_interest_and_accepts_binance_field_names():
    raw = _synthetic_raw()
    with pytest.raises(ValueError, match="requires historical open-interest"):
        make_independent_signals(raw, "M11", "5m")
    bars = prepare_bars(raw, "5m")
    oi = pd.DataFrame(
        {"sum_open_interest_value": np.linspace(1_000_000, 1_100_000, len(bars))},
        index=bars.index,
    )
    signals = make_independent_signals(raw, "M11", "5m", open_interest=oi)
    assert set(signals.signal.unique()).issubset({-1, 0, 1})


def test_metrics_archive_parser_reads_official_snake_case_fields(tmp_path):
    columns = [
        "create_time", "symbol", "sum_open_interest", "sum_open_interest_value",
        "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
        "count_long_short_ratio", "sum_taker_long_short_vol_ratio",
    ]
    rows = [
        [1704067500000, "BTCUSDT", 100.0, 4_200_000.0, 1.1, 1.2, 0.9, 1.05],
        [1704067800000, "BTCUSDT", 101.0, 4_250_000.0, 1.2, 1.3, 0.8, 1.08],
    ]
    csv_bytes = pd.DataFrame(rows, columns=columns).to_csv(index=False).encode()
    archive_path = tmp_path / "BTCUSDT-metrics-2024-01-01.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("BTCUSDT-metrics-2024-01-01.csv", csv_bytes)

    metrics = read_metrics_zip(archive_path, "BTCUSDT")
    assert len(metrics) == 2
    assert "sum_open_interest_value" in metrics.columns
    assert metrics.iloc[-1].sum_open_interest_value == 4_250_000.0
    assert metrics.index.tz is not None

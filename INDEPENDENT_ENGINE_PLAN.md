# Independent Core Engine Discovery Plan

## Scope

Every strategy is an independent system. A model is evaluated on its own trades and is never required to agree with, or be filtered by, another model. There is no ensemble or master-model voting. M3 remains in the separate Backtester repository and is not touched here.

## Existing baselines

M1, M2, M4 and M5 are included as independent reference strategies using their prior Stage 4 P1 and P2 parameter profiles. These are baselines, not pre-approved winners. M5 alone uses funding as an entry feature; all four models still incur actual perpetual funding cashflows when a position crosses a funding timestamp.

## New independent candidates

| Model | Independent thesis | First-pass baseline |
|---|---|---|
| M6 Donchian | Trend continuation after a prior N-bar high/low break | 55-bar channel, 2.5 ATR stop, 2R planned target |
| M7 Bollinger mean reversion | Extreme deviation from rolling mean reverts toward the mean | 20-bar bands, 2 standard deviations, RSI 35/65, 1.5 ATR stop, mean target |
| M8 Volatility expansion | A prior squeeze followed by range expansion and channel break can start a directional move | 100-bar squeeze percentile, 20-bar breakout, 1.2 ATR expansion, 2 ATR stop |
| M9 VWAP/flow | Daily session VWAP cross with taker imbalance and volume confirmation | Taker ratio 0.58/0.42, volume ratio 1.2, ADX 18, 1.75 ATR stop |
| M10 Relative momentum | An altcoin with sustained relative strength/weakness versus BTC may continue to outperform/underperform | 20-bar relative return, 1% threshold, EMA50/200 trend, 2 ATR stop |
| M11 Open-interest pressure | Rising notional OI plus directional price/market-buy pressure may indicate position build-up | 12-bar OI/price changes, 1% OI and 0.5% price thresholds, 2 ATR stop |
| M12 Regime-specific standalone | One strategy changes its own entry rule by measured regime: breakout in strong trend, mean reversion in low ADX | ADX 25/18, 20-bar channel, 2σ bands |
| M13 BTC lead-lag | After a BTC impulse, an altcoin that has lagged may catch up in the same direction | 3-bar BTC impulse 0.6%, relative lag 0.3%, EMA20 direction, 2 ATR stop |
| M14 ADX momentum | Directional movement, ADX and momentum identify persistent directional pressure | ADX 25, DI 25, 14-bar momentum, 2 ATR stop |
| M15 Awesome MACD | MACD trend state plus zero-crossing of Awesome Oscillator identifies momentum transition | MACD 12/26/9, Awesome Oscillator 5/34, 2 ATR stop |

M11 is not allowed to substitute price-only proxies for missing open-interest history. If official OI metrics are unavailable, that symbol/model stream is marked DATA_GATED.

M10 and M13 use BTC only as a reference series; BTC is not traded by those two models. All other model decisions remain independent.

## First-pass screen

- Symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT and DOGEUSDT, subject to actual contract and data-history availability.
- Timeframes: 5m, 15m, 1h and 4h for M6-M15. Existing M1/M2/M4/M5 baselines remain on 5m/15m and BTC/ETH to preserve the Stage 4 comparison scope.
- Period: 2021-01-01 through 2026-10-31 (exclusive end 2026-11-01), subject to listing and source coverage.
- Execution: completed-bar signal, next-bar-open entry, entry-bar stop/target check, stop-first when both barriers are touched in one OHLC bar.
- Costs: 5 bps taker fee and 2 bps slippage per side, plus actual USD-M funding cashflows on every perpetual position.
- Risk: 2R planned target where the model does not specify an explicit mean target; 24-hour maximum holding horizon across timeframes.
- Reporting: per-stream trade count, PF, net-R, net return, win rate, drawdown, average holding time, yearly breakdown and source coverage.

## Chronological evaluation

- 2021-2024: development period.
- 2025: validation period.
- 2026 through October: retrospective audit evidence because it was included in broad parameter sweeps; it is not a pristine untouched holdout and must not be used to select parameters.
- First-pass positive candidates require at least 100 development trades, development PF > 1 and positive development net-R. Stronger candidates also need at least 50 trades in 2025 with PF > 1 and positive net-R.
- A candidate still needs factor sensitivity, cost stress, yearly consistency and further untouched validation before it can be considered a surviving engine. A positive single stream is not enough to establish robustness.

## Known limitations

- 1-minute OHLCV cannot reconstruct order-book queue position or exact intrabar path. Stop-first collision handling is intentionally conservative.
- The first-pass strategy parameters are research baselines, not optimized settings.
- M11 currently tests open-interest pressure. A separately validated liquidation-event feed is not yet integrated.
- Binance Vision's published data terms restrict its use to non-commercial research and personal non-production historical backtesting. Do not use these datasets for live proprietary execution or commercial signal distribution without separate rights.


## Second phase: M6/M11 one-factor sensitivity

The first corrected screen showed that M6 and M11 deserve diagnosis, not selection. Both 4h strategies exited predominantly at the 24-hour time cap (roughly 77-81% for M6 and 70-77% for M11 in the first completed BTC/ETH/SOL samples). A separate sweep runner now varies one factor at a time, with each configuration remaining an independent strategy stream.

### M6 factors

- Donchian lookback: 20, 55, 100 bars.
- Initial ATR stop: 2.0, 2.5, 3.0 ATR.
- Volume ratio threshold: 0.8, 1.0, 1.2.
- Planned reward/risk: 1.5R, 2R, 3R.
- Maximum holding horizon: 24, 48, 72, 168 hours.
- Separate 2.5 ATR trailing-stop exit variant; trailing levels are updated only after a completed bar and can trigger from the next bar. Initial risk is retained for R-multiple calculation.

### M11 factors

- OI lookback: 6, 12, 24 bars.
- OI increase threshold: 0.5%, 1.0%, 1.5%.
- Directional price threshold: 0.25%, 0.5%, 1.0%.
- Symmetric taker-imbalance threshold: 0.52, 0.55, 0.60.
- Initial ATR stop: 1.5, 2.0, 2.5 ATR.
- Planned reward/risk: 1.5R, 2R, 3R.
- Maximum holding horizon: 24, 48, 72, 168 hours.

The sweep uses 1h and 4h, both long and short, seven liquid USD-M symbols, 5 bps taker fees per side, 2 bps slippage per side, and actual funding cashflows. It reports development (2021-2024), 2025 validation and 2026 YTD separately. The 2026 figures have already been viewed in the first-pass report, so they are treated as a retrospective holdout and are not used to tune or select parameters.

### Accounting audit update

- Entry and exit fees are charged on their respective executed notionals.
- Funding cashflows use the settlement mark price when available; otherwise the latest completed strategy-bar close at or before the funding timestamp is used, converted to entry-notional terms.
- Cross-symbol reports now distinguish notional-based PF from R-based PF and report per-symbol drawdown ranges. They explicitly do not claim a capital-weighted portfolio return or portfolio drawdown.

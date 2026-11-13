# Independent Crypto-Futures Engine Screening — 13 November 2026

## Status

The first-pass independent screen completed successfully for all seven Binance USD-M symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT and DOGEUSDT. The workflow ran from 2021-01-01 through 2026-10-31. All strategy rows are separate; no ensemble or cross-model confirmation was used. M3 was excluded and untouched.

- Workflow: https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43410791826
- Combined artifact: https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43410791826/artifacts/14034181470
- Source/licensing register: https://github.com/cheraibarath6-ai/Backtester-Remaining-/blob/main/RESEARCH_SOURCES.md

The combined artifact contains 504 screen-result rows, 1,824 yearly rows and 1,136,327 individual trades. It includes all per-symbol model/timeframe results and the full trade ledger.

## Method and costs

- Binance USD-M perpetual 1-minute OHLCV, resampled to 5m, 15m, 1h and 4h for M6-M15.
- M1, M2, M4 and M5 retained as the user's independent P1/P2 baselines on BTC and ETH at 5m and 15m.
- Both long and short for the new symmetric models; M10/M13 use BTC as a benchmark and do not open a BTC trade.
- Entry at the next bar open after a completed signal bar.
- 5 bps fee and 2 bps slippage per side; actual Binance funding cashflows charged to every perpetual position held across a settlement timestamp.
- Planned fallback target 2R; maximum holding period 24 hours.
- Development: 2021-2024. Validation: 2025. Later holdout: January-October 2026.

## Best tested timeframe per new model

PF is calculated from net trade returns in bps after fees, slippage and funding. Net-R is summed across the separate symbol streams; it is not a capital-weighted portfolio return. The DD columns are the median and worst per-symbol peak-to-trough drawdown in R, calculated from cumulative net-R. For an indicative fixed-risk translation, multiply R by 1% if each trade risks 1% of initial equity, without compounding; no leverage/margin cap is applied. Account-level return still requires a position-sizing and concurrent-exposure model.

| Model | TF | Trades | Symbols | PF | Net-R | Win % | Avg hold (h) | Median per-symbol net-R | Median / worst DD (R) | 2021-24 Dev (N/PF/R) | 2025 (N/PF/R) | 2026 holdout (N/PF/R) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 Donchian | 4h | 2,373 | 7 | 1.10 | +99.74 | 45.85 | 22.08 | +11.56 | -11.84 / -13.02 | 1,585 / 1.12 / +77.54 | 425 / 1.05 / +25.24 | 363 / 0.98 / -3.03 |
| M7 Bollinger mean reversion | 4h | 4,410 | 7 | 0.79 | -567.71 | 43.54 | 16.87 | -75.50 | -89.29 / -132.11 | 3,040 / 0.78 / -426.82 | 751 / 0.84 / -97.05 | 619 / 0.82 / -43.85 |
| M8 Volatility expansion | 4h | 1,747 | 7 | 1.06 | +64.09 | 45.51 | 21.09 | +3.56 | -13.97 / -18.59 | 1,140 / 1.04 / +40.89 | 333 / 1.39 / +40.81 | 274 / 0.80 / -17.62 |
| M9 VWAP/volume | 1h | 1,015 | 7 | 1.01 | -12.14 | 40.30 | 11.94 | -0.50 | -15.87 / -43.23 | 535 / 1.09 / +16.66 | 199 / 0.76 / -31.35 | 281 / 1.05 / +2.55 |
| M10 Relative momentum | 4h | 6,482 | 6 | 1.04 | +69.93 | 46.25 | 21.87 | +14.87 | -28.33 / -47.61 | 4,433 / 1.07 / +87.79 | 1,169 / 0.98 / +27.63 | 880 / 0.87 / -45.50 |
| M11 Open-interest pressure | 4h | 670 | 7 | 1.27 | +48.95 | 49.10 | 21.58 | +4.53 | -5.89 / -13.50 | 314 / 1.33 / +33.48 | 156 / 1.28 / +11.34 | 200 / 1.16 / +4.14 |
| M12 Regime-switching | 4h | 3,167 | 7 | 0.91 | -144.07 | 39.91 | 19.18 | -25.25 | -31.25 / -50.49 | 2,137 / 0.92 / -79.02 | 578 / 0.81 / -38.28 | 452 / 1.00 / -26.77 |
| M13 BTC lead-lag | 4h | 4,968 | 6 | 0.90 | -103.42 | 44.10 | 22.13 | -12.16 | -27.14 / -57.66 | 3,671 / 0.90 / -65.79 | 669 / 1.00 / +17.32 | 628 / 0.77 / -54.96 |
| M14 ADX momentum | 4h | 6,702 | 7 | 1.00 | +77.69 | 44.66 | 21.73 | +19.05 | -21.05 / -50.47 | 4,629 / 1.02 / +62.33 | 1,133 / 0.94 / +26.08 | 940 / 0.97 / -10.72 |
| M15 Awesome MACD | 1h | 7,217 | 7 | 1.05 | -29.07 | 40.74 | 14.57 | -24.40 | -67.26 / -95.05 | 4,970 / 1.14 / +197.60 | 1,268 / 0.80 / -140.28 | 979 / 0.83 / -86.38 |

## Interpretation

- **M11 4h is the strongest candidate for further independent research, not a selected/live model.** Aggregate PF remained above 1 in development, 2025 and 2026. It produced 670 trades across seven symbols. However, only 199 trades were in the 2026 holdout, and symbol-level holdout results were mixed: DOGE, ETH and XRP were positive, while ADA, BNB, BTC and SOL were negative. The full-period per-symbol net-R was positive for all seven, but the 2026 result is not uniformly distributed.
- M11's 4h exits were 71.8% time exits at the 24-hour cap. Its signal uses OI change over 12 bars, price change and taker-buy ratio. This is **open-interest pressure only**; reliable historical liquidation-pressure data has not yet been sourced.
- **M6 4h is the second candidate to explore.** It had 2,373 trades and positive net-R in development and 2025, but 2026 was effectively flat/slightly negative (PF 1.00, -0.97R). About 76.4% of M6 4h exits were time exits, so the 24-hour cap may be truncating trend runs.
- M8 and M10 were positive in development/earlier periods but deteriorated in 2026. M14 is close to flat in PF and negative in the 2026 holdout. M9 is near breakeven overall but failed 2025 and has only 25 trades on 4h.
- M7 and M12 are materially negative across periods. M15's attractive development result did not survive 2025 or 2026.
- M13's current implementation compares BTC and altcoin returns over the same completed interval. That is not a genuine lead-lag test. Its results are **invalid for selection** until the BTC impulse is shifted into an earlier, non-overlapping window and the model is rerun.
- No model is approved. No positive in-sample PF is sufficient by itself.

## Year-by-year results for the best tested timeframe

Each cell is trade count / PF / net-R. PF is net of costs. M11's six trades in 2021 are too few to interpret.

| Model / TF | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD |
|---|---:|---:|---:|---:|---:|---:|
| M6 4h | 405 / 1.14 / +15.9 | 407 / 1.09 / +20.8 | 362 / 1.05 / +20.1 | 411 / 1.19 / +20.7 | 425 / 1.05 / +25.2 | 363 / 0.98 / -3.0 |
| M7 4h | 742 / 0.81 / -93.7 | 746 / 0.70 / -128.4 | 757 / 0.92 / -53.5 | 795 / 0.71 / -151.2 | 751 / 0.84 / -97.1 | 619 / 0.82 / -43.8 |
| M8 4h | 300 / 1.07 / +20.4 | 278 / 1.04 / +8.4 | 286 / 0.82 / -11.6 | 276 / 1.24 / +23.8 | 333 / 1.39 / +40.8 | 274 / 0.80 / -17.6 |
| M9 1h | 130 / 1.11 / +17.3 | 111 / 1.24 / +13.0 | 127 / 0.85 / -18.8 | 167 / 1.11 / +5.1 | 199 / 0.76 / -31.4 | 281 / 1.05 / +2.6 |
| M10 4h | 1,254 / 1.23 / +101.9 | 1,108 / 1.03 / +26.6 | 1,021 / 0.86 / -31.5 | 1,050 / 0.99 / -9.2 | 1,169 / 0.98 / +27.6 | 880 / 0.87 / -45.5 |
| M11 4h | 6 / 5.05 / +3.7 | 108 / 1.53 / +15.9 | 110 / 1.17 / +9.8 | 90 / 1.13 / +4.1 | 156 / 1.28 / +11.3 | 200 / 1.16 / +4.1 |
| M12 4h | 550 / 0.87 / -54.7 | 535 / 0.89 / -28.6 | 485 / 1.02 / +29.0 | 567 / 0.99 / -24.8 | 578 / 0.81 / -38.3 | 452 / 1.00 / -26.8 |
| M13 4h* | 1,074 / 0.88 / -1.8 | 869 / 0.91 / -14.9 | 773 / 0.79 / -52.6 | 955 / 1.05 / +3.5 | 669 / 1.00 / +17.3 | 628 / 0.77 / -55.0 |
| M14 4h | 1,114 / 1.06 / +20.1 | 1,201 / 1.01 / +15.7 | 1,139 / 0.95 / +1.6 | 1,175 / 1.00 / +24.8 | 1,133 / 0.94 / +26.1 | 940 / 0.97 / -10.7 |
| M15 1h | 1,197 / 1.41 / +171.6 | 1,246 / 1.06 / +53.2 | 1,311 / 0.83 / -118.9 | 1,211 / 1.12 / +95.2 | 1,271 / 0.80 / -141.6 | 981 / 0.83 / -88.6 |

* M13 yearly numbers are retained for audit only and must not be interpreted as valid lead-lag performance.

## Existing baseline profiles (BTC/ETH only)

| Profile | TF | Trades | PF | Net-R | Win % | Dev (N/PF/R) | 2025 (N/PF/R) | 2026 (N/PF/R) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1-P1 | 5m | 175 | 0.63 | -74.7 | 26.3 | 111 / 0.78 / -37.7 | 39 / 0.21 / -28.0 | 25 / 0.65 / -9.0 |
| M1-P1 | 15m | 55 | 0.72 | -5.0 | 36.4 | 27 / 0.49 / -8.5 | 15 / 0.98 / -1.1 | 13 / 1.58 / +4.5 |
| M1-P2 | 5m | 2,205 | 0.89 | -411.7 | 35.0 | 1,457 / 0.94 / -262.7 | 375 / 0.73 / -94.2 | 373 / 0.81 / -54.8 |
| M1-P2 | 15m | 828 | 0.83 | -102.2 | 36.1 | 508 / 0.89 / -37.8 | 160 / 0.65 / -43.6 | 160 / 0.85 / -20.8 |
| M2-P1 | 5m | 3,411 | 0.93 | -264.9 | 36.9 | 2,385 / 0.88 / -244.0 | 558 / 1.08 / +2.1 | 468 / 1.01 / -23.0 |
| M2-P1 | 15m | 1,524 | 0.91 | -38.6 | 40.0 | 1,056 / 0.89 / -36.3 | 257 / 0.96 / -1.4 | 211 / 1.01 / -0.9 |
| M2-P2 | 5m | 4,869 | 0.86 | -725.9 | 34.9 | 3,346 / 0.85 / -510.6 | 832 / 0.88 / -118.6 | 691 / 0.90 / -96.7 |
| M2-P2 | 15m | 2,089 | 0.96 | -70.6 | 39.1 | 1,425 / 0.93 / -71.4 | 344 / 1.01 / -8.0 | 320 / 1.09 / +8.8 |
| M4-P1 | 5m | 1,630 | 0.77 | -318.1 | 33.9 | 1,133 / 0.78 / -204.4 | 271 / 0.77 / -55.6 | 226 / 0.74 / -58.1 |
| M4-P1 | 15m | 616 | 0.90 | -48.7 | 37.0 | 413 / 0.87 / -32.2 | 118 / 0.80 / -19.4 | 85 / 1.31 / +2.9 |
| M4-P2 | 5m | 5,916 | 0.77 | -1,450.7 | 32.6 | 4,032 / 0.77 / -983.6 | 1,053 / 0.74 / -260.5 | 831 / 0.78 / -206.6 |
| M4-P2 | 15m | 2,137 | 0.88 | -220.1 | 37.0 | 1,433 / 0.88 / -142.1 | 410 / 0.83 / -51.8 | 294 / 0.98 / -26.1 |
| M5-P1 | 5m | 121 | 0.51 | -67.2 | 28.9 | 74 / 0.40 / -46.2 | 27 / 0.88 / -8.6 | 20 / 0.51 / -12.4 |
| M5-P1 | 15m | 69 | 1.18 | -0.4 | 44.9 | 45 / 0.80 / -5.8 | 12 / 2.86 / +5.2 | 12 / 1.60 / +0.2 |
| M5-P2 | 5m | 1,458 | 0.70 | -536.7 | 32.8 | 1,071 / 0.66 / -397.7 | 222 / 0.87 / -73.0 | 165 / 0.75 / -66.0 |
| M5-P2 | 15m | 576 | 0.84 | -116.0 | 34.5 | 414 / 0.70 / -126.2 | 84 / 1.12 / -1.7 | 78 / 1.73 / +11.9 |

None of the baseline profiles has positive aggregate net-R across the full test period. M5-P1 15m is only 69 trades and still slightly negative in net-R.

## Data quality

- Candle source: Binance Vision official USD-M 1m archives.
- BTC, ETH, BNB, ADA and DOGE: 100% minute coverage; no duplicate timestamps or invalid OHLC rows.
- SOL and XRP: 99.7653% coverage, each missing 7,200 minutes; no duplicate timestamps or invalid OHLC rows. These gaps need interval-level inspection before a final rerun.
- Funding: official Binance monthly archives, no missing archive months, maximum observed gap approximately 8 hours.
- Open interest: official Binance daily metrics. BTC coverage is 99.902% from 2021-01-01. Other symbols begin 2021-12-01, so full-range coverage is approximately 84.3%; all expected archive days from their available start were downloaded. This is a listing/history boundary, not 15.7% random missing data.
- M11 does not have historical liquidation-event data. It must not be described as a liquidation-pressure engine yet.

## Backtest audit items before parameter search

The first screen verified next-bar entry, entry-bar stop/target checking, conservative stop-first handling when both barriers touch, fees/slippage, and funding settlement charges across all perpetual models. The following issues remain and will be fixed before the next full run:

1. M13 BTC impulse must be shifted to a prior, non-overlapping window; current same-window results are invalid.
2. Stop exits must account for an opening gap through the stop rather than always filling at the stop price.
3. Higher-timeframe resampling should reject incomplete bars when underlying 1-minute candles are missing.
4. The current summary's compounded net_return_pct/max_drawdown_pct assumes 100% notional is reinvested on every trade. It is not an account-equity curve. We will replace it with clearly labelled fixed-risk and fixed-notional measures and keep portfolio returns separate.
5. The 24-hour max-hold cap dominates exits for M6/M11. Test 12h/24h/48h/72h, and separately test the public MIT Donchian H1/H4 trailing-stop variant.
6. Stress costs above the baseline, test one-bar-late entries, and inspect top-trade concentration before considering a candidate robust.

## Public-source leads

- The MIT Donchian implementation in [vivchar2002-cyber/crypto-backtest-engine](https://github.com/vivchar2002-cyber/crypto-backtest-engine) provides an H1/H4 trend-following variant to test independently; no performance claim is imported.
- The GPL-3.0 [official Freqtrade strategies](https://github.com/freqtrade/freqtrade-strategies) repository provides ADXMomentum and AwesomeMacd rule references. Its ReinforcedAverage source explicitly describes itself as a proof of concept that does not perform especially well, so a third-party high-return claim is not accepted without reproduction.
- The MIT [Crypto-Statistical-Arbitrage](https://github.com/abailey81/Crypto-Statistical-Arbitrage) README claims 44,652 trades and PF 28.53 for BTC futures-curve trading. The result aggregates four allocated strategies across multiple venues; it is not an independent model result. A standalone funding-carry candidate is queued for separate reconstruction after historical multi-venue data and costs can be verified.

## Decision

No model passes the current selection bar. M11 4h merits the next independent parameter/time-hold study; M6 4h merits a separate stop/trailing/holding-period study. Neither is approved for deployment. M8/M10/M14 remain diagnostic candidates, not selected models. M3 remains untouched.

# Asset-Oriented Independent Crypto Futures Engine

## Objective

One engine process, with independently evaluated strategy modules per asset. A module is never required to agree with another module. There is no ensemble voting, confirmation filter, shared signal score, or priority-based signal selection. Each asset/strategy pair has its own signals, parameters, position state, fills, funding attribution, trade ledger, and performance report.

A separate portfolio risk allocator may cap total notional, leverage, and correlated exposure after signals are generated. It must not modify the underlying strategy signal or merge strategy trade histories.

## Asset assignments carried forward

The following are research leads from earlier asset-specific Model 3 work, not newly revalidated results:

| Asset | Existing best asset-oriented model | Reported PF | Trades | Period |
|---|---|---:|---:|---|
| BTCUSDT | Model 3 Rank 7 | 1.515 | 175 | 2024-2026 |
| ETHUSDT | M6 4h | 1.7288 | 93 | 2024-2025 |
| SOLUSDT | Model 3B | 2.03 | 1,164 | 2024 |
| DOGEUSDT | Model 3C | 2.66 | 385 | 2026 YTD |
| ADAUSDT | Model 3A | 2.35 | 564 | 2024 |
| LINKUSDT | Model 3C | 2.35 | 461 | 2025 |
| XRPUSDT | Model 3X | 1.58 | 345 | 2026 YTD |

The periods are not comparable. DOGE's reported 2026 YTD result is retrospective evidence, not a clean holdout. It must be re-tested on a full chronological history before selection.

## Two additional independent strategy families

M6 Donchian trend continuation and M8 volatility expansion are added as separate candidate modules. They are not blended with Model 3 or each other.

- M6: Donchian breakout with ATR risk, volume confirmation and independently optimized holding/RR profiles.
- M8: volatility squeeze followed by expansion and breakout, with its own stop, target and holding profiles.

The completed eight-engine research indicates M6 4h is a stronger broad candidate than M8 4h, but neither is approved globally. DOGE-specific 1h/4h expanding-window research is started in the dedicated DOGE workflow.

## DOGE research protocol

- Asset: DOGEUSDT USD-M perpetual.
- Strategy families: M6 and M8, run separately.
- Timeframes: 1h and 4h.
- Historical window: 2021-01-01 inclusive to 2026-11-01 exclusive, subject to source coverage and funding gate.
- Annual tests: 2023, 2024, 2025, and 2026 retrospective.
- Training-only selection for each model and timeframe; minimum 30 completed training trades; non-baseline variants require at least 80% baseline-entry overlap and 80% trade-count retention.
- 5 bps taker fee and 2 bps slippage per side, plus actual Binance USD-M funding cashflows.
- Completed-bar signal, next-bar-open execution, stop-first OHLC collision handling, adverse gap fills, and gap-safe indicators.
- DATA_GAP and END_OF_SAMPLE records remain in audit ledgers and are excluded from performance metrics.
- 2026 is not a pristine holdout because it was previously inspected during research.

The earlier DOGE full-screen job was cancelled before producing a complete result. The dedicated run must be inspected from its actual per-model artifacts; no result is assumed in advance.

## Engine interfaces and execution

1. Asset registry resolves each symbol to one primary historical strategy candidate plus M6 and M8 independent candidates.
2. Strategy adapters generate completed-bar signals and strategy-specific stops/targets.
3. The executor runs one independent position stream per asset/strategy/timeframe.
4. Every stream reports trade count, net-bps PF, R-PF, net-R, win rate, drawdown, average hold, funding, fees, slippage, yearwise cohorts and data-quality counts.
5. Training selects parameters only within the same asset and same model. Validation is chronological and out of sample.
6. A portfolio layer may limit combined exposure but cannot filter or vote on model entries.
7. Model 3 adapters remain external until their exact source and configuration are imported from the separate Model 3 research repository. This repository must not fabricate or silently substitute Model 3 logic.

## Data rights

The repository's Binance Vision source audit records CC BY-NC-SA 4.0 terms and non-commercial research/personal non-production backtesting restrictions. This research engine is for historical research only. Do not use these datasets for live proprietary execution or commercial signal distribution without separately obtaining appropriate data rights.

## Current implementation status

- Asset registry added at `crypto_research/asset_engine_registry.py`.
- DOGE M6/M8 1h/4h expanding-window workflow added at `.github/workflows/doge-asset-research.yml`.
- The DOGE workflow must complete and its artifacts must be inspected before choosing DOGE's additional strategy.
- Model 3 adapter implementation is intentionally marked as an external dependency pending its exact source.

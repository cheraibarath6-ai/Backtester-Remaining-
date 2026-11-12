# Crypto Futures Remaining Models — Exhaustive Research

Independent research repository for M1, M2, M4 and M5 only. Model 3 remains in the separate, existing Backtester repository and is not included here.

## Canonical grid (per symbol/timeframe)

| Model | Definition | Raw combinations |
|---|---|---:|
| M1 | Liquidity sweep + structural confirmation | 39,366 |
| M2 | Trend momentum | 13,122 |
| M4 | Breakout + retest | 13,122 |
| M5 | Funding + taker flow | 13,122 |
| **Total** | | **78,732** |

BTCUSDT + ETHUSDT, each on 5m + 15m = **314,928 raw combinations**. M2's raw grid includes all nine fast/slow EMA pairings; pairs where fast EMA >= slow EMA are retained in the audit ledger as explicitly skipped invalid configurations. Valid EMA pairings = 6, yielding 8,748 executable M2 configurations per symbol/timeframe.

## Research design
- Binance USD-M perpetual historical 1-minute klines aggregated to 5m/15m.
- Funding rates sourced from Binance official endpoint when accessible; fallback source is labelled and must be independently verified.
- Completed signal bar, next-bar-open entry; long and short.
- 2R planned target, 5 bps taker fee and 2 bps slippage per side by default.
- Conservative stop-first rule when stop and target are both touched in one OHLC bar.
- Funding, fees and slippage deducted.
- One position per model/symbol/timeframe.
- M1/M2/M4/M5 all keep the original 1H directional bias; optional 4H confirmation is a grid dimension.
- M4 retest must touch its configured tolerance zone, close back on the breakout side, and never penetrate more than 0.25 ATR beyond the breakout level. That 0.25 ATR failure cap is fixed, not tuned.

## Execution
GitHub Actions is manual-dispatch only. Four deterministic shards per model/symbol/timeframe reduce individual job size. Results include every valid/invalid config row, shard progress, data quality, funding source and ranking tables. The full 2024 baseline is the first run; subsequent chronological holdout periods should be run separately (e.g. 2025 and 2026 YTD where data is complete). Never select or report a profitable configuration based only on in-sample ranking.

## Output
- `grid_results.csv`: per-configuration metrics and parameter JSON
- `top25_per_model.csv`: descriptive ranking only
- `grid_run_summary.json`: expected/completed/skipped counts, period, costs, data quality, funding source
- funding CSV and partial checkpoint CSV

## Important
This is historical research, not a promise of returns or a live trading system. 1m OHLCV cannot reconstruct order-book queue position or exact intrabar paths. Third-party funding fallback is explicitly unverified until cross-checked.

# Forward holdout data audit — 13 November 2026

## Run status

- Workflow: [Forward Holdout M6/M11 — run 43474084425](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425)
- Branch: research/funding-notional-audit-v2
- Evaluation start: 2026-11-01 00:00 UTC
- Last complete archive day: 2026-11-12 UTC
- All seven symbol jobs completed successfully. This is a successful data-collection and integrity run, **not a scored trading holdout**.

## Candle and OI coverage

| Symbol | 1m rows | Candle coverage | Missing 1m bars | OI rows | OI 5m coverage | Missing OI buckets |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 46,080 | 100.0000% | 0 | 4,896 | 99.9796% | 1 |
| ETHUSDT | 46,080 | 100.0000% | 0 | 4,896 | 99.9796% | 1 |
| SOLUSDT | 46,080 | 100.0000% | 0 | 4,896 | 99.9796% | 1 |
| BNBUSDT | 46,080 | 100.0000% | 0 | 4,896 | 99.9796% | 1 |
| XRPUSDT | 46,080 | 100.0000% | 0 | 4,896 | 99.9796% | 1 |
| ADAUSDT | 46,080 | 100.0000% | 0 | 4,896 | 99.9796% | 1 |
| DOGEUSDT | 46,080 | 100.0000% | 0 | 4,896 | 99.9796% | 1 |

- Candle period including warm-up: 2026-10-12 00:00 through 2026-11-12 23:59 UTC.
- Candle source: official Binance Vision USD-M daily 1m archives.
- OI period: 2026-10-27 00:05 through 2026-11-13 00:00 UTC.
- OI source: official Binance Vision daily USD-M metrics archives.
- Post-2026-06-25 OI metric timestamps are shifted +5 minutes to the actual snapshot availability time. This prevents using a metric snapshot before it is available.
- The single missing 5m OI bucket per symbol is recorded in each quality file; no future snapshot is forward-filled to conceal it.

## Funding blocker — no forward PnL was calculated

The official daily fundingRate archive paths for 2026-11-01 through 2026-11-12 returned 404 for all seven symbols. The futures funding REST endpoint previously returned HTTP 451 from the GitHub Actions runner region. The official source available to the historical pipeline is the monthly funding archive; the November 2026 monthly archive has not yet been published.

Therefore every selected M6/M11 profile is marked DATA_GATED_FUNDING_ARCHIVE_PENDING. No trades were scored, no net-R/PF/win rate/drawdown is reported for November, and no zero-funding assumption was used. This is not a zero-trade result; it is a funding-data gate. Re-run scoring after the official November monthly funding archive appears and verify its checksum/coverage first.

## Symbol artifacts

- [BTCUSDT artifact 14062400557](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425/artifacts/14062400557)
- [ETHUSDT artifact 14062995012](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425/artifacts/14062995012)
- [SOLUSDT artifact 14062321300](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425/artifacts/14062321300)
- [BNBUSDT artifact 14062910321](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425/artifacts/14062910321)
- [XRPUSDT artifact 14062855522](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425/artifacts/14062855522)
- [ADAUSDT artifact 14062550535](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425/artifacts/14062550535)
- [DOGEUSDT artifact 14062138408](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425/artifacts/14062138408)

Each artifact contains a run_summary.json, the raw 1m candle file, the forward OI metrics file, and a screen_results.csv showing the funding-data gate. Trade and yearly ledgers are empty by design because no funding-complete forward scoring was possible.

## Licence and use

Binance's Vision Dataset Terms version 1.0, last updated 26 August 2026, grants CC BY-NC-SA 4.0 except where otherwise designated. Permitted uses include purely personal, non-production historical backtesting. The terms expressly exclude live proprietary trading execution and commercial automated order generation; commercial use requires a separate written enterprise data licence. See the [official Binance Vision Dataset Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md).

## Decision

- This forward run verifies that recent candles and OI are available with high coverage.
- It does not validate or invalidate M6/M11 trading performance because official funding data is missing.
- M6 and M11 remain independent; M11 is OI-only, not liquidation-pressure.
- No engine is approved for live deployment.
- M3 remains untouched.

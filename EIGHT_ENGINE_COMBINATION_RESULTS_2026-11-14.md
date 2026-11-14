# Eight-engine within-model combination results — 14 November 2026

## Scope and provenance

This completed combination pass covers only the evidence-led 4h candidates from M6, M8 and M15. Each engine is evaluated as its own strategy. No cross-model combination, voting, or confirmation is used. M1-M5, M9 and M11 are not run, tuned, aggregated or compared. M3 remains untouched.

- Branch: `research/funding-notional-audit-v2`
- Draft PR #2: https://github.com/cheraibarath6-ai/Backtester-Remaining-/pull/2
- Fresh baseline screen: [run 43554579139](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43554579139)
- Eight-engine one-factor sweep: [run 43554593008](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43554593008)
- Within-model combination sweep: [run 43561784934](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43561784934)
- Combination aggregate artifact: [artifact 14101380428](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43561784934/artifacts/14101380428)
- Scoped regression suite: [run 43561724757](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43561724757), 87 passed.

All seven symbol jobs and the aggregate job in the combination run completed successfully. The artifact contains 147 symbol/variant rows and 40,840 ledger records. There are 15 `DATA_GAP` and 4 `END_OF_SAMPLE` records; both remain in the audit ledger and are excluded from performance metrics.

## Method

- Binance USD-M 1m candles, resampled to 4h; symbols: BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, SOLUSDT, XRPUSDT.
- Completed-bar signals; next-bar-open entries; stop-first OHLC collision handling; adverse gap fills.
- Base costs: 5 bps taker fee per side, 2 bps slippage per side, plus official Binance funding cashflows.
- Funding is sourced from Binance Vision's official monthly archive; maximum observed settlement gap is 8h. No zero-funding fallback is used.
- `DATA_GAP` and `END_OF_SAMPLE` are excluded from metrics.
- Development is 2021-2024; 2025 is the validation cohort; 2026 through 31 October is retrospective audit evidence, not a pristine holdout.
- Yearwise rows below group trades by exit year. The development/validation/audit cohort rows group by entry year and require exit before the cohort boundary. These are different views.
- Cross-symbol sums are trade-stream diagnostics, not a capital-weighted portfolio return or drawdown. Net bps are summed per-trade entry-notional returns.
- Crypto has no universal pip size; net bps and net-R are used for comparison.

## Combination results

The strongest combination candidates are:

| Model / variant | Trades | Trade-count retention | Baseline entries retained | Net PF | PF (R) | Net bps | Net-R |
|---|---:|---:|---:|---:|---:|---:|---:|
| M6 RR3_VOL12 | 2,209 | 93.09% | 89.21% | 1.1790 | 1.1960 | +78,280 | +128.188 |
| M6 HOLD48_STOP3 | 2,036 | 85.80% | 81.42% | 1.2176 | 1.2470 | +110,628 | +160.020 |
| M8 VOLUME_1_0 | 1,803 | 103.32% | 97.71% | 1.0619 | 1.1081 | +16,847 | +68.020 |
| M8 HOLD48_VOL10 | 1,753 | 100.46% | 94.67% | 1.0698 | 1.1053 | +24,550 | +85.770 |
| M8 HOLD48_EXP15 | 1,467 | 84.07% | 80.11% | 1.1072 | 1.1405 | +31,541 | +95.787 |
| M15 ATR_TRAIL_2_5_H48 | 1,941 | 95.15% | 94.61% | 1.0597 | 1.0893 | +19,802 | +65.005 |

The 100%+ count-retention results include new entry timestamps; they do not mean every baseline entry was retained. The separate baseline-entry-retention column measures the retained original entry timestamps.

### Cohort validation and retrospective audit

| Model / variant | 2025 trades | 2025 PF | 2025 net bps | 2025 net-R | 2026 audit trades | 2026 PF | 2026 net bps | 2026 net-R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 RR3_VOL12 | 396 | 1.160 | +11,315 | +33.184 | 332 | 1.056 | +2,610 | +3.439 |
| M6 HOLD48_STOP3 | 348 | 1.141 | +11,911 | +34.489 | 300 | 0.982 | -1,110 | -1.328 |
| M8 VOLUME_1_0 | 345 | 1.372 | +15,277 | +41.691 | 278 | 0.843 | -5,501 | -12.960 |
| M8 HOLD48_VOL10 | 332 | 1.548 | +29,059 | +71.354 | 269 | 0.740 | -12,522 | -28.832 |
| M8 HOLD48_EXP15 | 276 | 1.548 | +25,147 | +58.434 | 225 | 0.800 | -8,047 | -14.243 |
| M15 ATR_TRAIL_2_5_H48 | 351 | 1.077 | +4,798 | +29.552 | 298 | 0.740 | -12,271 | -21.365 |

**Interpretation:** M6 RR3_VOL12 is the best balanced candidate so far: it keeps 93.1% of baseline trade count, retains 89.2% of baseline entry timestamps, and remains positive in each exit-year row from 2021 through the 2026 retrospective cohort. M6 HOLD48_STOP3 has the highest PF/net result, but gives up 14.2% of trades and is negative in the 2026 audit. It should remain a comparison candidate, not the default selection.

M8 variants improve 2025 substantially, but all listed 48h variants weaken in the 2026 audit. M8 VOLUME_1_0 preserves more trades and is less fragile than the 48h alternatives, but its 2026 cohort remains negative. M15's trailing variants improve the baseline, but the 2026 cohort remains negative. None is ready for live use.

## Cost consumption

The following are summed across the seven independent symbol streams. Cost share is total fees + slippage + funding divided by gross positive directional price movement; it is not a percentage of net profits.

| Variant | Gross positive move / trade | Fees / trade | Slippage / trade | Funding / trade | Total cost / trade | Cost share |
|---|---:|---:|---:|---:|---:|---:|
| M6 RR3_VOL12 | 242.63 bps | 10.03 | 4.01 | 4.18 | 18.23 | 7.51% |
| M6 HOLD48_STOP3 | 314.69 bps | 10.03 | 4.01 | 6.46 | 20.50 | 6.52% |
| M8 VOLUME_1_0 | 168.04 bps | 10.01 | 4.00 | 2.15 | 16.15 | 9.61% |
| M8 HOLD48_VOL10 | 222.39 bps | 10.00 | 4.00 | 2.91 | 16.92 | 7.61% |
| M8 HOLD48_EXP15 | 230.00 bps | 10.00 | 4.00 | 3.03 | 17.04 | 7.41% |
| M15 ATR_TRAIL_2_5_H48 | 188.76 bps | 10.00 | 4.00 | 2.70 | 16.71 | 8.85% |

The fixed fee/slippage schedule contributes about 14 bps per round trip before funding. M6's longer-hold variant earns a larger gross move but also pays more funding. M8's 48h variants reduce cost share by capturing larger moves, but their 2026 weakness is a separate signal-regime issue.

## Yearwise exit-year results

### M6

| Variant | Year | Trades | Net bps | PF |
|---|---:|---:|---:|---:|
| RR3_VOL12 | 2021 | 381 | +32,622 | 1.278 |
| RR3_VOL12 | 2022 | 369 | +10,002 | 1.132 |
| RR3_VOL12 | 2023 | 344 | +8,236 | 1.137 |
| RR3_VOL12 | 2024 | 385 | +14,517 | 1.221 |
| RR3_VOL12 | 2025 | 396 | +11,315 | 1.160 |
| RR3_VOL12 | 2026 | 334 | +1,589 | 1.034 |
| HOLD48_STOP3 | 2021 | 351 | +44,574 | 1.341 |
| HOLD48_STOP3 | 2022 | 348 | +20,064 | 1.227 |
| HOLD48_STOP3 | 2023 | 328 | +11,603 | 1.181 |
| HOLD48_STOP3 | 2024 | 352 | +25,427 | 1.329 |
| HOLD48_STOP3 | 2025 | 350 | +11,492 | 1.135 |
| HOLD48_STOP3 | 2026 | 307 | -2,532 | 0.960 |

### M8 and M15

| Variant | Year | Trades | Net bps | PF |
|---|---:|---:|---:|---:|
| VOLUME_1_0 | 2021 | 310 | +6,186 | 1.094 |
| VOLUME_1_0 | 2022 | 289 | +2,546 | 1.053 |
| VOLUME_1_0 | 2023 | 293 | -9,589 | 0.778 |
| VOLUME_1_0 | 2024 | 286 | +8,467 | 1.219 |
| VOLUME_1_0 | 2025 | 345 | +15,277 | 1.372 |
| VOLUME_1_0 | 2026 | 280 | -6,041 | 0.830 |
| HOLD48_VOL10 | 2021 | 298 | -1,940 | 0.978 |
| HOLD48_VOL10 | 2022 | 280 | +6,791 | 1.115 |
| HOLD48_VOL10 | 2023 | 288 | -9,247 | 0.817 |
| HOLD48_VOL10 | 2024 | 279 | +13,530 | 1.263 |
| HOLD48_VOL10 | 2025 | 334 | +28,641 | 1.536 |
| HOLD48_VOL10 | 2026 | 274 | -13,225 | 0.730 |
| ATR_TRAIL_2_5_H48 | 2021 | 313 | +18,255 | 1.244 |
| ATR_TRAIL_2_5_H48 | 2022 | 320 | +4,665 | 1.088 |
| ATR_TRAIL_2_5_H48 | 2023 | 342 | -4,965 | 0.890 |
| ATR_TRAIL_2_5_H48 | 2024 | 308 | +7,976 | 1.163 |
| ATR_TRAIL_2_5_H48 | 2025 | 353 | +5,052 | 1.081 |
| ATR_TRAIL_2_5_H48 | 2026 | 305 | -11,182 | 0.763 |

### Counterfactual retention audit

The combination artifact records the baseline outcome of every rejected baseline entry:

- M6 RR3_VOL12 rejected 256 baseline entries whose baseline counterfactual net was -1,770 bps and +2.20R; it added 92 new entries.
- M6 HOLD48_STOP3 rejected 441 baseline entries whose counterfactual net was -21,317 bps and +0.98R; it added 104 new entries.
- M8 VOLUME_1_0 rejected 40 baseline entries whose counterfactual net was +3,356 bps and +6.39R; it added 98 new entries.
- M8 HOLD48_VOL10 rejected 93 baseline entries whose counterfactual net was +2,341 bps and +9.20R; it added 101 new entries.
- M8 HOLD48_EXP15 rejected 347 baseline entries whose counterfactual net was -9,040 bps and -16.29R; it added 69 new entries.
- M15 ATR_TRAIL_2_5_H48 rejected 110 baseline entries whose counterfactual net was +1,743 bps and -2.72R; it added 11 new entries.

This is important: not every rejected trade was a loser. For M8 and M15 some rejected baseline trades were profitable; the improved net result comes from a different exit/entry path, not simply removing all losers.

## Remaining models and next stage

The one-factor sweep did not produce a candidate for M7, M10, M12, M13 or M14 that simultaneously had positive development PF/net-R, positive 2025 validation PF/net bps, and at least 80% baseline-entry retention. M10 and M14 have interesting but low-retention or weak-validation leads; M7, M12 and M13 remain negative and need structural diagnosis before more filters.

Next: run a separate four-level fee/slippage stress on baselines and evidence-led variants, with block-bootstrap uncertainty checks and bar-path MAE/MFE diagnostics. The cost-stress pass will retain each model as an independent strategy. After that, use only surviving variants for expanding walk-forward testing. No engine is approved for live trading.

## Data and licensing

The source audit and Binance Vision restrictions are documented in [RESEARCH_SOURCES.md](https://github.com/cheraibarath6-ai/Backtester-Remaining-/blob/research/funding-notional-audit-v2/RESEARCH_SOURCES.md). Binance Vision data is restricted to non-commercial research/personal non-production historical backtesting under its published terms. These results do not authorize live or commercial automated execution.

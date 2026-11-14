# Eight-engine crypto-futures cost-aware sweep — 14 November 2026

## Scope and run provenance

This report covers only the independent engines M6, M7, M8, M10, M12, M13, M14 and M15. M1-M5, M9 and M11 were not run, tuned, aggregated or selected. No model voting, ensemble or cross-model confirmation was used.

- Branch: `research/funding-notional-audit-v2`
- Draft PR #2: https://github.com/cheraibarath6-ai/Backtester-Remaining-/pull/2
- Fresh baseline screen (5m/15m/1h/4h, seven symbols): [GitHub Actions run 43554579139](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43554579139), aggregate artifact 14098162339.
- One-factor cost-aware improvement sweep (15m/1h/4h, seven symbols): [GitHub Actions run 43554593008](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43554593008), aggregate artifact 14099395184.
- Full regression suite after the new scoped combination runner: [run 43561724757](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43561724757), **87 passed**.
- Evidence-led within-model combination run: [run 43561784934](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43561784934) — queued/running when this report was written; no combination results are claimed yet.

The PR remains open and in draft. Its current changed-file list contains 39 paths and no M3 path.

## Method and accounting

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, SOLUSDT and XRPUSDT.
- Binance USD-M 1-minute historical candles, resampled to the tested strategy timeframes. Signals use completed bars and entries fill at the next bar open.
- Base costs: 5 bps taker fee per side and 2 bps slippage per side, plus actual funding cashflows at settlement.
- Entry and exit fees use their respective executed notionals. Funding uses settlement mark-price notional. Funding is fail-closed to official Binance sources; no zero-funding fallback is scored.
- Stop/target collision handling is stop-first; adverse opening gaps are modelled. Indicator histories reset at missing-data boundaries. `DATA_GAP` and `END_OF_SAMPLE` records remain in audit ledgers but are excluded from metrics.
- Development cohort: entries during 2021-2024 that close before 2025-01-01. Validation cohort: entries during 2025 that close before 2026-01-01. 2026 is retrospective audit only, not a pristine holdout.
- The yearwise table below groups realized trades by **exit year**. Cohort validation above uses **entry year**; these are intentionally different views.
- Cross-symbol sums are trade-stream diagnostics, not a capital-weighted portfolio return or portfolio drawdown. `net_bps` is the sum of per-trade basis-point returns on entry notional, not a portfolio return.
- Crypto has no universal pip size. This report uses comparable net bps and net-R rather than inventing a common pip. Raw price points remain symbol-specific.

## Data quality and funding

| Symbol | 1m candles | Coverage | Funding rows | Funding max gap |
|---|---:|---:|---:|---:|
| BTCUSDT | 3,067,200 | 100.0000% | 6,390 | 8.0000h |
| ETHUSDT | 3,067,200 | 100.0000% | 6,390 | 8.0000h |
| BNBUSDT | 3,067,200 | 100.0000% | 6,390 | 8.0000h |
| ADAUSDT | 3,067,200 | 100.0000% | 6,390 | 8.0000h |
| DOGEUSDT | 3,067,200 | 100.0000% | 6,390 | 8.0000h |
| SOLUSDT | 3,060,000 | 99.7653% | 6,465 | 8.0000h |
| XRPUSDT | 3,060,000 | 99.7653% | 6,390 | 8.0000h |

Funding source was the official Binance Vision monthly archive with no missing archive months. SOL and XRP each have 7,200 missing 1-minute candles across two intervals; the gap-safe executor invalidates any affected open position and skips stale signals. M10 and M13 use BTC as a benchmark, not as a traded leg; their traded universe therefore contains six symbols.

**Licensing:** the public data source and restrictions are documented in [RESEARCH_SOURCES.md](https://github.com/cheraibarath6-ai/Backtester-Remaining-/blob/research/funding-notional-audit-v2/RESEARCH_SOURCES.md). Binance Vision terms identify the dataset as CC BY-NC-SA 4.0 except where otherwise specified and restrict it to non-commercial research/personal non-production backtesting. These results do not license live or commercial automated execution.

## Fresh baseline — 4h comparison

This is the strongest common timeframe in the initial screen. Costs are already deducted.

| Model | Trades | Net PF (bps) | PF (R) | Net bps | Net-R | 2025 cohort trades | 2025 PF | 2025 net bps | Cost / gross positive move | Cost / trade |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 Donchian | 2,373 | 1.095 | 1.138 | +46,272 | +98.864 | 425 | 1.053 | +4,034 | 8.02% | 18.76 bps |
| M7 mean reversion | 4,410 | 0.787 | 0.745 | -191,284 | -575.422 | 751 | 0.840 | -21,422 | 7.30% | 12.04 bps |
| M8 volatility expansion | 1,745 | 1.059 | 1.104 | +15,531 | +63.844 | 333 | 1.386 | +15,364 | 9.62% | 16.19 bps |
| M10 relative momentum | 6,296 | 1.016 | 1.022 | +18,104 | +42.390 | 1,167 | 0.980 | -3,634 | 9.26% | 17.47 bps |
| M12 regime-specific | 3,164 | 0.910 | 0.896 | -58,048 | -146.312 | 578 | 0.813 | -20,128 | 8.64% | 16.68 bps |
| M13 BTC lead-lag | 7,954 | 0.877 | 0.931 | -166,850 | -167.028 | 1,303 | 0.898 | -20,515 | 10.16% | 15.88 bps |
| M14 ADX momentum | 6,669 | 0.999 | 1.034 | -1,014 | +71.964 | 1,133 | 0.936 | -11,855 | 8.70% | 16.62 bps |
| M15 Awesome MACD | 2,040 | 0.929 | 0.934 | -20,366 | -42.623 | 374 | 0.786 | -11,698 | 11.51% | 15.79 bps |

The 5m baseline was negative on all eight engines. The 15m baseline was also negative on all eight. At 1h, only M15 showed a positive notional PF/net-bps result (+40,525 bps, PF 1.046), but its net-R was -27.96 and its 2025 validation was negative (PF 0.805, -29,908 bps). It is not a robust pass.

## 4h yearwise baseline — trades / net bps / PF

Net bps are comparable trade-stream diagnostics; they are not universal pips or portfolio returns. Years are assigned by exit year. 2026 covers only the retrospective period through 31 October.

| Model | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 retrospective |
|---|---|---|---|---|---|---|
| M6 | 405 / +18,241 / 1.14 | 407 / +8,205 / 1.09 | 362 / +3,269 / 1.05 | 411 / +13,761 / 1.19 | 425 / +4,034 / 1.05 | 363 / -1,238 / 0.98 |
| M7 | 742 / -46,892 / 0.80 | 746 / -50,505 / 0.70 | 757 / -8,905 / 0.92 | 795 / -47,918 / 0.70 | 751 / -21,422 / 0.84 | 619 / -15,642 / 0.82 |
| M8 | 300 / +4,292 / 1.07 | 276 / +1,958 / 1.04 | 286 / -7,641 / 0.81 | 276 / +8,745 / 1.24 | 333 / +15,364 / 1.39 | 274 / -7,187 / 0.80 |
| M10 | 1,139 / +57,909 / 1.19 | 1,041 / +2,460 / 1.01 | 1,021 / -20,657 / 0.86 | 1,050 / -2,623 / 0.99 | 1,169 / -4,228 / 0.98 | 876 / -14,757 / 0.87 |
| M12 | 549 / -24,417 / 0.87 | 533 / -13,542 / 0.89 | 485 / +1,355 / 1.02 | 567 / -1,373 / 0.99 | 578 / -20,128 / 0.81 | 452 / +56 / 1.00 |
| M13 | 1,473 / -43,663 / 0.89 | 1,420 / -36,274 / 0.86 | 1,234 / -33,572 / 0.79 | 1,363 / -8,328 / 0.96 | 1,309 / -21,164 / 0.90 | 1,155 / -23,850 / 0.83 |
| M14 | 1,098 / +22,112 / 1.06 | 1,188 / +557 / 1.00 | 1,139 / -7,788 / 0.95 | 1,175 / -448 / 1.00 | 1,133 / -11,855 / 0.94 | 936 / -3,592 / 0.97 |
| M15 | 330 / +17,758 / 1.29 | 332 / -1,665 / 0.96 | 358 / -4,516 / 0.88 | 327 / -1,588 / 0.96 | 376 / -11,788 / 0.78 | 317 / -18,567 / 0.58 |

## One-factor improvement findings — 4h

The table shows variants that improved net expectancy without destroying most baseline entries. Trade-count change is versus the baseline total count; baseline-entry retention measures how many baseline entry timestamps remain.

| Model / variant | Trades | Count change | Baseline entries retained | Net PF | Net bps | Net-R | 2025 trades | 2025 PF | 2025 net bps | 2025 net-R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 baseline | 2,373 | — | 100.0% | 1.095 | +46,272 | +98.864 | 425 | 1.053 | +4,034 | +25.122 |
| M6 RR 3.0 | 2,314 | -2.5% | 96.6% | 1.172 | +79,315 | +125.625 | 415 | 1.147 | +10,817 | +31.908 |
| M6 stop 3.0 ATR | 2,338 | -1.5% | 98.0% | 1.118 | +56,939 | +92.861 | 418 | 1.072 | +5,531 | +24.289 |
| M6 hold 48h | 2,107 | -11.2% | 84.7% | 1.189 | +98,154 | +166.586 | 362 | 1.104 | +8,813 | +34.203 |
| M8 baseline | 1,745 | — | 100.0% | 1.059 | +15,531 | +63.844 | 333 | 1.386 | +15,364 | +40.730 |
| M8 hold 48h | 1,700 | -2.6% | 97.1% | 1.067 | +22,932 | +83.201 | 322 | 1.576 | +29,650 | +71.451 |
| M8 volume min 1.0 | 1,803 | +3.3% | 97.7% | 1.062 | +16,847 | +68.020 | 345 | 1.372 | +15,277 | +41.692 |
| M8 expansion 1.5 ATR | 1,491 | -14.6% | 81.6% | 1.103 | +23,263 | +77.473 | 284 | 1.427 | +15,062 | +36.981 |
| M15 baseline | 2,040 | — | 100.0% | 0.929 | -20,366 | -42.623 | 374 | 0.786 | -11,698 | -18.024 |
| M15 ATR trail 2.5 | 1,880 | -7.8% | 91.8% | 1.046 | +16,690 | +91.215 | 339 | 1.021 | +1,408 | +23.997 |

### Does cost eat the move?

The following figures are from the full valid trade ledgers, across the seven symbol streams. “Cost share” means total fees + slippage + funding divided by the sum of positive raw directional price moves. It is not cost as a percentage of net profits.

| Model / variant | Gross positive move per trade | Fees / trade | Slippage / trade | Funding / trade | Total cost / trade | Cost share |
|---|---:|---:|---:|---:|---:|---:|
| M6 baseline | 233.98 bps | 10.03 | 4.01 | 4.72 | 18.76 | 8.02% |
| M6 RR 3.0 | 242.25 bps | 10.03 | 4.01 | 4.17 | 18.22 | 7.52% |
| M6 hold 48h | 303.41 bps | 10.03 | 4.01 | 6.10 | 20.14 | 6.64% |
| M8 baseline | 168.34 bps | 10.01 | 4.00 | 2.19 | 16.19 | 9.62% |
| M8 hold 48h | 222.47 bps | 10.00 | 4.00 | 3.00 | 17.00 | 7.64% |
| M8 expansion 1.5 ATR | 175.57 bps | 10.00 | 4.00 | 2.23 | 16.24 | 9.25% |
| M15 baseline | 137.22 bps | 10.00 | 4.00 | 1.79 | 15.79 | 11.51% |
| M15 ATR trail 2.5 | 211.46 bps | 10.00 | 4.00 | 3.31 | 17.32 | 8.19% |

The 5/2 bps per-side fee/slippage schedule contributes about 14 bps per round trip before funding. The main improvement in the strongest variants is not a reduction in fixed fees: it is capturing a larger move per trade, so those fixed costs consume a smaller fraction of the move. M6 RR 3.0 also slightly reduces average funding per trade relative to baseline. M8 48h increases funding per trade, but gross positive movement grows faster.

## Interpretation and next stage

- **Best balanced M6 candidate so far:** RR 3.0. It retains 96.6% of baseline entries, loses only 2.5% of total trades, and improves both full-period and 2025 validation PF/net bps. The 48h M6 version produces more total net bps and the highest PF, but gives up 11.2% of trades and has a weaker 2026 retrospective.
- **Best balanced M8 candidate so far:** 48h hold. It retains 97.1% of baseline entries and improves full-period and 2025 validation net bps/PF. Its 2025 validation is strong, but 2026 retrospective is negative. M8 is therefore promising but not robustly selected.
- **M15 ATR trailing 2.5** changes a negative baseline into a modest positive result with 91.8% entry retention. The 2025 PF is only 1.021 and the 2026 retrospective is weak; this is a tentative candidate, not a pass.
- M10 and M14 have some positive full-period 4h variants, but their 2025 notional net-bps/PF validation is negative. M12's isolated 1h BREAKOUT_10 result has only PF 1.009 in validation while net-R remains negative and the full-period result is poor. M7 and M13 did not establish a profitable 4h baseline or a convincing one-factor improvement.
- The M8 4h one-factor candidates and M6 4h RR/stop variants are the strongest candidates for controlled within-model combinations. The next run tests only M6, M8 and M15 at 4h; it does not combine different engines. The 2025 validation and 2026 retrospective remain separate from development selection.
- No engine is approved for live execution. The future forward holdout after 1 November 2026 is still required, along with cost stress, walk-forward and Monte Carlo checks on surviving candidates.


## Exit-reason diagnosis — 4h baseline

These counts and net bps exclude `DATA_GAP` and `END_OF_SAMPLE` records. The large negative contribution from stop exits is the main issue in several weak models; fees are not the dominant cause of their negative expectancy.

| Model | Stop exits (count / net bps) | Target exits (count / net bps) | Time exits (count / net bps) |
|---|---:|---:|---:|
| M6 | 373 / -257,228 | 186 / +239,734 | 1,814 / +63,766 |
| M7 | 2,043 / -848,188 | 556 / +288,775 | 1,811 / +368,129 |
| M8 | 389 / -168,441 | 186 / +143,925 | 1,170 / +40,047 |
| M10 | 1,151 / -664,033 | 409 / +444,942 | 4,736 / +237,195 |
| M12 | 1,027 / -447,910 | 363 / +342,327 | 1,774 / +47,534 |
| M13 | 1,377 / -752,968 | 390 / +376,207 | 6,187 / +209,911 |
| M14 | 1,235 / -713,038 | 497 / +541,540 | 4,937 / +170,485 |
| M15 | 371 / -155,064 | 113 / +92,627 | 1,556 / +42,071 |

M6 RR 3.0 is consistent with this diagnosis: it reduces target exits from 186 to 78, but raises the time-exit contribution from about +63.8k to +150.2k bps while retaining 96.6% of baseline entry timestamps. M8 hold 48h increases target exits from 186 to 317 and raises the time-exit contribution from about +40.0k to +66.9k bps, while retaining 97.1% of baseline entries. These are model-specific exit effects, not cross-engine combinations.

M7, M12 and M13 are not primarily failing because of the fixed 14 bps round-trip fee/slippage schedule: their stop-exit losses overwhelm the positive target/time exits. They need entry/stop logic diagnosis before more restrictive filters are considered. The current ledger does not yet record bar-by-bar MAE/MFE, so exact adverse/favourable excursion and stop-distance efficiency remain a diagnostic gap.

## 2026 retrospective audit for the leading one-factor candidates

These are completed entry cohorts from 1 January through 31 October 2026. They are retrospective audit evidence, not a pristine holdout.

| Model / variant | Trades | Net PF | Net bps | Net-R |
|---|---:|---:|---:|---:|
| M6 baseline | 361 | 0.996 | -217 | -1.036 |
| M6 RR 3.0 | 350 | 1.007 | +353 | -1.678 |
| M6 hold 48h | 316 | 0.936 | -4,141 | -4.163 |
| M6 stop 3.0 ATR | 352 | 1.007 | +335 | -0.820 |
| M8 baseline | 272 | 0.811 | -6,647 | -15.590 |
| M8 hold 48h | 263 | 0.753 | -11,585 | -24.913 |
| M8 volume min 1.0 | 278 | 0.843 | -5,501 | -12.960 |
| M8 expansion 1.5 ATR | 232 | 0.865 | -4,005 | -8.805 |
| M15 baseline | 316 | 0.580 | -18,456 | -49.288 |
| M15 ATR trail 2.5 | 289 | 0.725 | -14,129 | -23.054 |

This weak 2026 cohort is why M8 is only a promising validation candidate, not a final selection. M6 RR 3.0 and stop 3.0 are close to flat in net bps but still negative in net-R. The future untouched forward holdout remains essential.

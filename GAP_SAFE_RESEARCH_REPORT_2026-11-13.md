# Gap-safe independent crypto-futures research — 13 November 2026

## Scope and run provenance

This report supersedes the earlier pre-gap screen and preliminary sensitivity figures.

- Branch: `research/funding-notional-audit-v2`
- Commit screened: `eb4ef5be676475c0aed241a54355f0260ec596c1`
- Draft PR: [#2](https://github.com/cheraibarath6-ai/Backtester-Remaining-/pull/2) (kept open and in draft)
- Full gap-safe independent screen: [workflow 43447250532](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250532)
- One-factor sensitivity: [workflow 43447250657](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250657)
- Within-model combinations: [workflow 43447250545](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250545)
- Funding/accounting and regression tests: [workflow 43447250668](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250668)
- Full screen artifact: [14056895727](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250532/artifacts/14056895727)
- Sensitivity artifact: [14056180913](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250657/artifacts/14056180913)
- Combination artifact: [14054857991](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250545/artifacts/14054857991)

All seven symbol jobs completed successfully in each research stream. The aggregate screen produced 504 result rows, 1,824 yearly rows and 1,179,360 trade-ledger records. There were 304 completed streams, 112 expected unsupported baseline-timeframe rows, 80 expected baseline-symbol-not-in-Stage-4 rows, and 8 not-applicable BTC benchmark rows for M10/M13. The ledger retained 54 `DATA_GAP` exits; they are excluded from all performance metrics.

The test workflow completed successfully. The current PR changed-file list has no M3 file. M3 remains untouched.

## Execution and data audit

The gap-safe executor now:

- enters at the next bar open after a completed-bar signal;
- checks the entry bar for stop/target hits and uses conservative stop-first handling if both are touched;
- models adverse opening gaps;
- charges entry and exit fees on their respective executed notionals;
- applies funding to mark-price settlement notional (or the last completed bar close when no mark is available) for every perpetual position, irrespective of model;
- resets indicator, VWAP, OI-change and benchmark-return histories at every complete-bar data segment;
- does not carry positions or stale signals across missing-bar intervals;
- retains affected trades as `DATA_GAP` audit records but excludes them from performance;
- reports fixed-initial-equity-risk return separately from fixed-notional PnL.

### Data quality

| Symbol | 1m candle coverage | Missing minutes | OI coverage | OI history start |
|---|---:|---:|---:|---|
| BTCUSDT | 100.0000% | 0 | 99.9020% | 2021-01-01 |
| ETHUSDT | 100.0000% | 0 | 84.2964% | 2021-12-01 |
| BNBUSDT | 100.0000% | 0 | 84.2964% | 2021-12-01 |
| ADAUSDT | 100.0000% | 0 | 84.2964% | 2021-12-01 |
| DOGEUSDT | 100.0000% | 0 | 84.2964% | 2021-12-01 |
| SOLUSDT | 99.7653% | 7,200 (2 intervals) | 84.2937% | 2021-12-01 |
| XRPUSDT | 99.7653% | 7,200 (2 intervals) | 84.2963% | 2021-12-01 |

Candle source: official Binance Vision USD-M 1m archives. Funding source: official Binance Vision monthly funding archives; no missing archive months, 6,390 funding rows per symbol (6,465 SOL), maximum observed settlement interval about 8 hours. OI source: official Binance Vision daily futures metrics; no missing archive days after each symbol's available start. The six non-BTC symbols have no OI history before 1 December 2021, so M11's 2021 sample is BTC-dominated and must not be interpreted as seven-symbol coverage.

SOL/XRP's two missing-minute intervals each are visible in quality metadata. Positions affected by unobserved intervals were invalidated rather than scored. This correction materially supersedes all pre-gap performance figures.

## Full baseline screen

All results below use 5 bps taker fee and 2 bps slippage per side, plus actual funding. PF is shown both on net bps and net R. The cross-symbol sums are trade-stream aggregates for the same independent model, **not a capital-weighted portfolio return or portfolio drawdown**. The drawdown shown is the worst individual-symbol drawdown at the 1% initial-equity-risk convention.

### M1/M2/M4/M5 Stage-4 baselines

No P1/P2 baseline passed both 2021–2024 development and 2025 validation. The best isolated validation exceptions were too small or had negative development.

| Model/profile | TF | Trades | Full PF bps / PF R | Full net-R | Dev net-R | 2025 net-R | 2026 audit net-R |
|---|---:|---:|---:|---:|---:|---:|---:|
| M1 P1 | 5m | 175 | 0.628 / 0.518 | -74.73 | -37.69 | -28.01 | -9.03 |
| M1 P2 | 5m | 2,205 | 0.886 / 0.760 | -411.71 | -262.68 | -94.24 | -54.79 |
| M1 P1 | 15m | 55 | 0.724 / 0.856 | -5.04 | -8.46 | -1.06 | +4.48 |
| M1 P2 | 15m | 828 | 0.835 / 0.814 | -102.20 | -37.78 | -43.62 | -20.79 |
| M2 P1 | 5m | 3,411 | 0.925 / 0.887 | -265.05 | -244.19 | +2.07 | -22.93 |
| M2 P2 | 5m | 4,869 | 0.859 / 0.800 | -726.03 | -510.74 | -118.60 | -96.69 |
| M2 P1 | 15m | 1,524 | 0.912 / 0.953 | -38.67 | -36.35 | -1.44 | -0.89 |
| M2 P2 | 15m | 2,089 | 0.959 / 0.944 | -70.66 | -71.46 | -7.98 | +8.79 |
| M4 P1 | 5m | 1,630 | 0.772 / 0.748 | -318.19 | -204.48 | -55.59 | -58.12 |
| M4 P2 | 5m | 5,916 | 0.766 / 0.694 | -1,450.69 | -983.61 | -260.51 | -206.57 |
| M4 P1 | 15m | 616 | 0.901 / 0.877 | -48.67 | -32.15 | -19.41 | +2.90 |
| M4 P2 | 15m | 2,137 | 0.883 / 0.842 | -220.15 | -142.22 | -51.80 | -26.13 |
| M5 P1 | 5m | 121 | 0.513 / 0.432 | -67.22 | -46.17 | -8.60 | -12.44 |
| M5 P2 | 5m | 1,458 | 0.698 / 0.592 | -536.68 | -397.71 | -73.04 | -65.93 |
| M5 P1 | 15m | 69 | 1.182 / 0.991 | -0.42 | -5.80 | +5.22 (12 trades) | +0.16 |
| M5 P2 | 15m | 576 | 0.843 / 0.741 | -116.04 | -126.26 | -1.66 | +11.88 |

### New-model baseline comparison — 4h

| Model | Trades | PF bps / PF R | Net-R | Win % | Avg hold | Worst symbol DD at 1% risk | Dev net-R (PF R) | 2025 net-R (PF R) | 2026 audit net-R (PF R) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 Donchian | 2,373 | 1.096 / 1.139 | +99.56 | 45.9 | 22.1h | -11.3% | +77.38 (1.163) | +25.22 (1.204) | -3.03 (0.974) |
| M7 mean reversion | 4,410 | 0.790 / 0.748 | -567.69 | 43.6 | 16.9h | -100.0% | -426.78 (0.726) | -97.08 (0.755) | -43.84 (0.851) |
| M8 volatility expansion | 1,745 | 1.060 / 1.106 | +64.59 | 45.6 | 21.1h | -18.4% | +41.40 (1.104) | +40.81 (1.403) | -17.62 (0.841) |
| M9 VWAP/flow | 25 | 0.622 / 0.580 | -5.72 | 32.0 | 19.2h | -2.7% | -1.61 (0.306) | -0.43 (0.000; 1 trade) | -3.68 (0.543) |
| M10 relative momentum | 6,300 | 1.017 / 1.023 | +44.88 | 46.0 | 21.9h | -38.7% | +62.75 (1.049) | +27.62 (1.079) | -45.49 (0.841) |
| M11 OI pressure | 670 | 1.268 / 1.235 | +48.96 | 49.1 | 21.6h | -12.4% | +33.49 (1.352) | +11.33 (1.245) | +4.13 (1.062) |
| M12 regime-specific | 3,164 | 0.912 / 0.899 | -142.75 | 40.0 | 19.2h | -43.7% | -77.69 (0.916) | -38.30 (0.861) | -26.76 (0.871) |
| M13 BTC lead-lag | 7,954 | 0.878 / 0.932 | -163.26 | 44.5 | 22.1h | -57.8% | -91.93 (0.944) | -8.35 (0.979) | -62.98 (0.830) |
| M14 ADX momentum | 6,673 | 1.001 / 1.036 | +75.07 | 44.6 | 21.7h | -42.3% | +59.73 (1.041) | +26.06 (1.074) | -10.72 (0.965) |
| M15 Awesome MACD | 2,040 | 0.930 / 0.935 | -41.51 | 43.1 | 22.0h | -24.0% | +26.24 (1.068) | -18.03 (0.860) | -49.73 (0.613) |

Interpretation across other timeframes:

- M6: 5m/15m negative; 1h near breakeven but development negative; 4h is the only positive baseline timeframe.
- M7: negative on all four timeframes.
- M8: 4h alone has positive development and 2025 validation; its 2026 retrospective audit turned negative. 5m/15m/1h negative.
- M9: 5m/15m negative; 1h near breakeven overall but 2025 negative; 4h has only 25 trades and is not decision-grade.
- M10: 4h alone has positive development/2025, but 2026 is materially negative; other timeframes negative.
- M11: 4h alone is positive across the reported periods; 5m/15m/1h are negative.
- M12: negative on all timeframes.
- M13: negative on all timeframes despite the corrected non-overlapping BTC impulse/alt response windows. This agrees with the cited negative prior evidence; retain only as a falsifiable research hypothesis, not an assumed edge.
- M14: 4h development/2025 positive but 2026 negative; other timeframes negative.
- M15: 1h development positive but 2025 and 2026 negative; other timeframes negative.

## M6/M11 one-factor and within-model combination findings

All sensitivity and combination jobs completed for seven symbols. M6 and M11 remained separate strategies. The 2026 values below are retrospective audit evidence only: 2026 had already been exposed in broad sweeps and is **not** a pristine untouched holdout.

The within-model combinations below were retained for deeper robustness work based on development and 2025 validation evidence. All trade metrics pool independent symbol streams; they are not portfolio returns. Drawdown is the worst individual-symbol drawdown.

### M6 Donchian candidates — development plus 2025

| Variant | Trades | PF bps / PF R | Net-R | Win % | Avg hold | Worst symbol DD at 1% risk | 2026 audit trades / PF R / net-R |
|---|---:|---:|---:|---:|---:|---:|---:|
| D100_STOP2_H168 | 1,237 | 1.169 / 1.234 | +170.97 | 41.2 | 55.7h | -16.78% | 215 / 1.269 / +31.95 |
| RR3_H168 | 1,354 | 1.194 / 1.222 | +171.26 | 39.7 | 95.4h | -20.66% | 242 / 1.153 / +21.21 |
| STOP2_H168 | 1,742 | 1.113 / 1.173 | +181.65 | 40.1 | 59.1h | -26.72% | 313 / 1.008 / +1.62 |

All seven symbols were positive in 2021–2025 for D100_STOP2_H168 and RR3_H168. STOP2_H168 was positive in six of seven; XRP was slightly negative. D100_STOP2_H168 had the lower worst-symbol drawdown of these three. RR3_H168 has the longest capital lock-up, averaging about 95 hours.

### M11 open-interest pressure candidates — development plus 2025

| Variant | Trades | PF bps / PF R | Net-R | Win % | Avg hold | Worst symbol DD at 1% risk | 2026 audit trades / PF R / net-R |
|---|---:|---:|---:|---:|---:|---:|---:|
| OI05_PRICE025_H36 | 534 | 1.317 / 1.351 | +66.17 | 48.3 | 29.7h | -6.91% | 224 / 1.029 / +2.53 |
| OI05_H48 | 484 | 1.283 / 1.315 | +61.35 | 46.1 | 36.4h | -7.74% | 207 / 1.094 / +8.51 |
| PRICE025_RR3_H48 | 456 | 1.353 / 1.390 | +72.57 | 46.1 | 38.6h | -9.43% | 189 / 1.059 / +5.16 |

All seven symbols were positive in 2021–2025 for these three variants. OI05_H48 and PRICE025_RR3_H48 had positive net-R in each 2022–2025 calendar year; the 2021 segment has only six trades because most altcoin OI history starts in December 2021. M11 remains an **OI-pressure** model only. It does not use a historical liquidation-event tape.

## Cost-stress and Monte Carlo diagnostics

A ledger repricing diagnostic was run on the selected M6/M11 variants, using only trades exiting through 2025:

- Base: 5 bps fee / 2 bps slippage per side.
- Stress 1: 7.5 bps fee / 4 bps slippage per side.
- Stress 2: 10 bps fee / 5 bps slippage per side.

This reprices entry/exit fills and fees from recorded trades while retaining their recorded stop/target path and funding cashflows. It is **not yet a full OHLC re-execution under stressed costs**.

| Model/variant | Base PF R / net-R | 7.5/4 PF R / net-R | 10/5 PF R / net-R | Median per-symbol block-bootstrap P(net-R > 0) |
|---|---:|---:|---:|---:|
| M6 D100_STOP2_H168 | 1.234 / +170.97 | 1.197 / +145.97 | 1.169 / +126.91 | 0.894 |
| M6 RR3_H168 | 1.222 / +171.26 | 1.189 / +147.85 | 1.164 / +129.96 | 0.872 |
| M6 STOP2_H168 | 1.173 / +181.65 | 1.136 / +145.12 | 1.109 / +117.20 | 0.916 |
| M11 OI05_PRICE025_H36 | 1.351 / +66.17 | 1.248 / +48.66 | 1.175 / +35.33 | 0.932 |
| M11 OI05_H48 | 1.315 / +61.35 | 1.227 / +45.70 | 1.163 / +33.79 | 0.952 |
| M11 PRICE025_RR3_H48 | 1.390 / +72.57 | 1.299 / +57.59 | 1.234 / +46.23 | 0.970 |

Bootstrap diagnostic: 500 moving-block resamples per symbol, 20-trade blocks, 2021–2025 trades only. The displayed probability is the median across symbol streams, not a portfolio probability. This resampling does not replace walk-forward or forward data.

## Decision

- **No model is approved for live deployment.**
- M6 4h and M11 4h are the two candidates that justify deeper work. M11 currently has the cleaner drawdown profile; M6 has more trades but greater drawdown and much longer holding periods in its long-hold variants.
- M8/M10/M14 4h had positive development and 2025 results but failed or weakened in the retrospective 2026 audit; do not promote them.
- M7/M9/M12/M13/M15 and the M1/M2/M4/M5 baselines did not establish a robust edge in this screen.
- Complete full OHLC cost re-execution, chronological walk-forward/Monte Carlo checks, symbol/regime stability diagnostics and a genuinely forward holdout after 2026-11-01 before selection.
- The current data screen ends at 2026-11-01 exclusive. A forward period after that date has not yet been scored in this report.
- Binance Vision published data terms restrict these datasets to non-commercial research and personal non-production historical backtesting; separate rights are needed before commercial or live proprietary use.

See [RESEARCH_SOURCES.md](RESEARCH_SOURCES.md) for implementation references and licence notes.

---

## Follow-on gap-safe combination and forward-data audit — 13 November 2026

The completed one-factor and within-model combination artifacts were re-opened and recalculated from the actual trade ledgers. The following six combinations are shown because they are the strongest independent M6/M11 candidates under the predeclared 2021–2024 development and 2025 validation windows. The 2026 column remains retrospective audit evidence because 2026 was exposed in the broad sweeps.

### Selected M6 combinations — 4h

| Variant | Period | Trades | Net-bps PF | R PF | Net-R | Win % | Avg hold | Worst symbol DD at 1% risk |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| D100_RR3_H168 | 2021–24 dev | 768 | 1.462 | 1.471 | +198.40 | 41.7 | 91.5h | -11.03% |
|  | 2025 validation | 187 | 0.917 | 1.076 | +8.28 | 38.0 | 88.5h | -9.22% |
|  | 2026 retrospective | 163 | 1.489 | 1.452 | +37.07 | 43.6 | 100.6h | -7.62% |
| D100_STOP2_H168 | 2021–24 dev | 994 | 1.216 | 1.268 | +155.45 | 42.0 | 56.3h | -16.78% |
|  | 2025 validation | 243 | 0.950 | 1.103 | +15.52 | 38.3 | 53.2h | -9.63% |
|  | 2026 retrospective | 215 | 1.301 | 1.268 | +31.95 | 43.3 | 60.8h | -8.31% |
| D100_VOL12_RR3_H168 | 2021–24 dev | 753 | 1.458 | 1.475 | +196.71 | 41.7 | 90.7h | -11.35% |
|  | 2025 validation | 185 | 0.922 | 1.092 | +9.92 | 38.4 | 88.8h | -8.97% |
|  | 2026 retrospective | 158 | 1.551 | 1.505 | +39.88 | 43.7 | 100.8h | -9.56% |

M6 caution: all three selected combinations have a 2025 net-bps PF below 1.0 even though R-based PF and net-R are positive. This divergence means the combinations are not a clean validation pass. The 168h variants also tie up positions for roughly 90–100 hours on average. They remain research candidates, not selections. The simpler D100_RR3_H168 variant has the highest development net-R, while D100_STOP2_H168 has shorter holding time but a worse historical worst-symbol drawdown.

### Selected M11 combinations — 4h

| Variant | Period | Trades | Net-bps PF | R PF | Net-R | Win % | Avg hold | Worst symbol DD at 1% risk |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| OI05_RR3_H48 | 2021–24 dev | 321 | 1.337 | 1.396 | +51.39 | 44.5 | 38.6h | -6.55% |
|  | 2025 validation | 158 | 1.245 | 1.232 | +15.35 | 45.6 | 39.1h | -8.58% |
|  | 2026 retrospective | 200 | 1.197 | 1.117 | +10.40 | 42.5 | 38.2h | -8.82% |
| OI05_PRICE025_RR3_H48 | 2021–24 dev | 346 | 1.349 | 1.392 | +54.99 | 45.1 | 38.5h | -7.24% |
|  | 2025 validation | 162 | 1.258 | 1.233 | +15.91 | 45.7 | 39.0h | -7.99% |
|  | 2026 retrospective | 211 | 1.164 | 1.069 | +6.60 | 41.7 | 38.2h | -9.42% |
| OI05_PRICE025_RR3_H72 | 2021–24 dev | 332 | 1.413 | 1.445 | +70.05 | 44.0 | 51.0h | -7.44% |
|  | 2025 validation | 153 | 1.247 | 1.264 | +20.82 | 43.8 | 51.5h | -7.59% |
|  | 2026 retrospective | 199 | 1.010 | 0.972 | -3.16 | 37.7 | 49.9h | -13.04% |

M11's two 48h variants are the cleaner validation candidates because both development and 2025 have net-bps PF and R PF above 1.0, with positive net-R. The OI05_PRICE025_RR3_H72 variant is not retained as a leading candidate: its 2026 retrospective R PF fell below 1.0 and net-R was negative. The 48h OI-only version has slightly better 2026 audit performance; the price-threshold version has a lower worst-symbol drawdown through 2025 but slightly weaker 2026 audit performance. Do not choose between them from the retrospective 2026 values.

### Full OHLC cost re-execution and block bootstrap

A new full cost-stress workflow has been added. Unlike the earlier ledger repricing diagnostic, it re-runs the same OHLC path with four per-side cost settings:

- 5 bps fee / 2 bps slippage (baseline);
- 7.5 bps fee / 3 bps slippage;
- 10 bps fee / 5 bps slippage;
- 15 bps fee / 10 bps slippage.

It tests three predeclared variants per model, keeps M6 and M11 separate, and runs a 500-resample moving-block bootstrap with 20-trade blocks per symbol stream. Annual fixed-parameter results are also exported for chronological stability review. This workflow is currently running: [Independent M6–M11 Full Cost Stress Research](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43473850295). The regression suite passed on its two active symbol jobs; the full cost results are not yet available.

### Forward holdout data availability

The forward-only workflow completed successfully for all seven symbols: [Forward Holdout M6/M11 — run 43474084425](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425). Each symbol has 46,080 recent 1m candles with 100% coverage and 4,896 5m OI rows with 99.9796% coverage (one missing 5m bucket). The daily candle parser uses the actual USD-M archive headers (count, taker_buy_volume, taker_buy_quote_volume); post-2026-06-25 OI labels are shifted +5 minutes to their actual availability time to avoid lookahead. See [FORWARD_HOLDOUT_STATUS_2026-11-13.md](FORWARD_HOLDOUT_STATUS_2026-11-13.md) for per-symbol artifacts and exact quality details.

The attempted official daily funding-rate archive paths for 2026-11-01 through 2026-11-12 returned 404 for all seven symbols. The public REST funding endpoint had previously returned HTTP 451 from the runner region. The official monthly funding archive for November is not yet published, so the November forward holdout cannot currently be scored with funding costs. The runner fails closed: it records candle/OI data and marks every M6/M11 profile DATA_GATED_FUNDING_ARCHIVE_PENDING instead of silently treating funding as zero or producing misleading PnL. No forward trades or performance metrics were scored. Re-run after Binance publishes the November monthly funding archive.

### Current research decision

- M11 4h 48h OI-pressure candidates are the strongest current research leads; both have positive development and 2025 results on both net-bps PF and R PF. They still need full cost stress, walk-forward diagnostics, Monte Carlo review and a properly funded forward holdout.
- M6 4h remains promising, but the within-model combinations have weaker 2025 net-bps PF than their R-based PF suggests and hold positions for long periods. They need careful cost, capital-utilization and risk-geometry scrutiny.
- No model is approved for live trading. M3 remains untouched.


## Additional historical OI timestamp correction — 13 November 2026

A final data-timing audit found that Binance USD-M metrics rows from 2026-06-25 onward carry an OI snapshot at T+5 minutes while the original historical metrics loader treated the row label T as the availability time. This creates up to five minutes of lookahead for M11 in the 2026 retrospective period. The forward-only loader had already applied the +5m availability shift; the historical loader is now corrected and regression-tested. The full regression suite passed 66 tests in [Funding Notional Audit Tests run 43475126673](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475126673). The 2021–2024 development and 2025 validation M11 figures in this report are unaffected, but **all M11 2026 retrospective figures and the earlier cost-stress 2026 outputs are provisional and must not be used**. M6 and all non-OI models are unaffected by this specific correction.

Corrected reruns are underway: [core screen 43475018639](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475018639), [M6/M11 sensitivity 43475105074](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475105074), [M6/M11 combinations 43475114006](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475114006), [funding/OI regression tests 43475126673](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475126673), and corrected [full cost stress 43475120490](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475120490). The older cost-stress run using the unshifted loader is not accepted for 2026 M11 conclusions.

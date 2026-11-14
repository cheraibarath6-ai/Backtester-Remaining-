# Gap-safe M6/M11 One-Factor Sensitivity — 13 November 2026

## Provenance

- Branch: research/funding-notional-audit-v2
- Gap-safe sensitivity workflow: [43447250657](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250657)
- Aggregate artifact: [14056180913](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43447250657/artifacts/14056180913)
- Seven Binance USD-M symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT, DOGEUSDT
- Period: 2021-01-01 through 2026-11-01 exclusive
- Timeframes: 1h and 4h; both directions
- Baseline costs: 5 bps fee and 2 bps slippage per side, plus official Binance funding cashflows at settlement
- 406 one-factor result rows and 228,889 trade-ledger rows; all seven symbol jobs and aggregation completed successfully

This report supersedes the earlier pre-gap sensitivity figures. The executor now invalidates positions crossing missing-bar intervals as DATA_GAP, keeps those records in audit ledgers, excludes them from metrics, skips stale signals after gaps and resets indicator/VWAP/OI/benchmark histories at segment boundaries. The full screen ledger retained 54 DATA_GAP records across the seven symbols; these are excluded from performance metrics. M3 remains untouched.



> **Additional timestamp audit discovered after this report:** Binance USD-M daily metrics rows from 2026-06-25 onward label OI snapshots five minutes earlier than their actual availability. The historical loader originally did not apply this +5m shift. Development (2021–2024) and 2025 validation figures below are unaffected; all M11 2026 retrospective values in this report are provisional and must not be used for selection. The forward-only loader already applied the shift. The historical loader is now corrected and the full screen, one-factor sweep, combinations, and tests are being rerun: [core screen 43475018639](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475018639), [sensitivity 43475105074](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475105074), [combinations 43475114006](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475114006), [audit tests 43475126673](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475126673). A corrected full cost-stress run is queued at [43475120490](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475120490). Earlier 2026 M11 audit metrics are superseded once those runs finish.

## Metrics interpretation

- Net-bps PF = sum of positive trade net-bps divided by the absolute sum of negative trade net-bps.
- R PF = the same calculation using initial-risk-normalized net-R.
- Net-R sums and the corresponding 1%-risk fixed-initial-equity return are sums across independent symbol streams, not portfolio returns.
- Worst drawdown is the worst individual-symbol drawdown under 1% initial-equity risk per R. It is not a combined portfolio drawdown.
- Average holding time is shown in hours.

## M6 Donchian — 4h one-factor results

| Variant | Trades | Net-bps PF | R PF | Net-R | Win % | Avg hold | Worst symbol DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 2,373 | 1.096 | 1.139 | +99.56 | 45.85 | 22.1h | -11.31% |
| Donchian 20 | 4,203 | 0.977 | 1.044 | +53.43 | 43.94 | 22.4h | -18.85% |
| Donchian 100 | 1,649 | 1.143 | 1.181 | +92.45 | 45.91 | 21.9h | -11.61% |
| ATR stop 2.0 | 2,466 | 1.080 | 1.128 | +117.08 | 44.77 | 20.6h | -12.85% |
| ATR stop 3.0 | 2,338 | 1.118 | 1.158 | +93.43 | 46.49 | 22.8h | -11.38% |
| Volume floor 0.8 | 2,439 | 1.077 | 1.120 | +88.59 | 45.43 | 22.1h | -12.21% |
| Volume floor 1.2 | 2,264 | 1.100 | 1.152 | +102.76 | 45.72 | 22.1h | -11.18% |
| RR 1.5 | 2,477 | 1.061 | 1.106 | +79.70 | 45.78 | 21.4h | -13.06% |
| RR 3.0 | 2,314 | 1.174 | 1.183 | +126.32 | 46.20 | 22.5h | -11.48% |
| Hold 48h | 2,107 | 1.190 | 1.211 | +167.33 | 45.56 | 38.5h | -11.81% |
| Hold 72h | 1,993 | 1.147 | 1.145 | +128.49 | 43.95 | 51.2h | -16.66% |
| Hold 168h | 1,811 | 1.146 | 1.161 | +161.43 | 41.74 | 80.3h | -18.57% |
| ATR trail 2.5 | 2,288 | 1.068 | 1.104 | +67.61 | 44.27 | 21.2h | -10.58% |

### M6 chronological breakdown

| Variant | Period | Trades | Net-bps PF | R PF | Net-R |
|---|---|---:|---:|---:|---:|
| Baseline | 2021–24 development | 1,585 | 1.122 | 1.163 | +77.38 |
|  | 2025 validation | 425 | 1.054 | 1.204 | +25.22 |
|  | 2026 retrospective | 363 | 0.978 | 0.974 | -3.03 |
| Hold 48h | 2021–24 development | 1,421 | 1.259 | 1.271 | +140.07 |
|  | 2025 validation | 364 | 1.099 | 1.241 | +33.76 |
|  | 2026 retrospective | 323 | 0.919 | 0.953 | -6.51 |
| Hold 168h | 2021–24 development | 1,216 | 1.172 | 1.172 | +115.37 |
|  | 2025 validation | 319 | 1.075 | 1.186 | +32.64 |
|  | 2026 retrospective | 277 | 1.075 | 1.086 | +13.41 |
| RR 3.0 | 2021–24 development | 1,547 | 1.207 | 1.214 | +97.99 |
|  | 2025 validation | 415 | 1.148 | 1.266 | +32.00 |
|  | 2026 retrospective | 352 | 0.987 | 0.967 | -3.67 |

The 48h hold variant is the strongest development/2025 one-factor result, with more trades and better net-R than the baseline. Its 2026 retrospective result is negative, so it cannot be promoted using that period. The 168h variant had a positive 2026 retrospective result but requires about 80 hours average holding and has a materially worse historical worst-symbol drawdown. Do not choose between them using 2026; the broad sweep included that period.

M6 at 1h is not robust: the best R PF is only about 1.007 (hold 168h), net-bps PF is below 1, and the worst-symbol drawdown is about -60.6%. The 4h horizon is the only credible M6 research timeframe in this screen.

## M11 open-interest pressure — 4h one-factor results

| Variant | Trades | Net-bps PF | R PF | Net-R | Win % | Avg hold | Worst symbol DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 670 | 1.268 | 1.235 | +48.96 | 49.10 | 21.6h | -12.38% |
| OI lookback 6 | 631 | 1.185 | 1.155 | +30.45 | 49.13 | 21.7h | -12.22% |
| OI lookback 24 | 682 | 1.191 | 1.220 | +46.50 | 48.24 | 21.4h | -9.04% |
| OI threshold 0.5% | 747 | 1.270 | 1.235 | +53.95 | 49.26 | 21.6h | -11.67% |
| OI threshold 1.5% | 617 | 1.224 | 1.206 | +40.79 | 48.78 | 21.4h | -10.72% |
| Price threshold 0.25% | 710 | 1.281 | 1.244 | +53.70 | 49.44 | 21.6h | -10.77% |
| Price threshold 1.0% | 571 | 1.209 | 1.168 | +31.09 | 47.64 | 21.5h | -12.48% |
| Taker threshold 0.52 | 3,598 | 0.972 | 0.976 | -28.41 | 40.02 | 21.8h | -92.69% |
| Taker threshold 0.60 | 17 | 0.186 | 0.257 | -5.71 | 35.29 | 21.4h | -2.42% |
| ATR stop 1.5 | 687 | 1.175 | 1.161 | +44.09 | 47.16 | 19.7h | -14.94% |
| ATR stop 2.5 | 662 | 1.303 | 1.267 | +44.76 | 49.55 | 22.7h | -11.39% |
| RR 1.5 | 678 | 1.194 | 1.173 | +36.05 | 49.41 | 20.9h | -12.80% |
| RR 3.0 | 665 | 1.292 | 1.281 | +58.15 | 49.17 | 22.1h | -14.83% |
| Hold 48h | 622 | 1.240 | 1.237 | +61.73 | 45.66 | 36.1h | -14.57% |
| Hold 72h | 597 | 1.176 | 1.182 | +54.78 | 43.22 | 45.7h | -11.49% |
| Hold 168h | 566 | 1.172 | 1.163 | +56.42 | 40.46 | 61.3h | -12.74% |

### M11 chronological breakdown

| Variant | Period | Trades | Net-bps PF | R PF | Net-R |
|---|---|---:|---:|---:|---:|
| Baseline | 2021–24 development | 314 | 1.335 | 1.352 | +33.49 |
|  | 2025 validation | 156 | 1.280 | 1.245 | +11.33 |
|  | 2026 retrospective | 200 | 1.159 | 1.062 | +4.13 |
| Hold 48h | 2021–24 development | 292 | 1.323 | 1.349 | +40.93 |
|  | 2025 validation | 145 | 1.203 | 1.234 | +13.89 |
|  | 2026 retrospective | 185 | 1.145 | 1.083 | +6.90 |
| RR 3.0 | 2021–24 development | 312 | 1.387 | 1.447 | +42.13 |
|  | 2025 validation | 155 | 1.330 | 1.290 | +13.38 |
|  | 2026 retrospective | 198 | 1.125 | 1.039 | +2.63 |
| OI threshold 0.5% | 2021–24 development | 352 | 1.336 | 1.353 | +37.08 |
|  | 2025 validation | 172 | 1.295 | 1.276 | +13.71 |
|  | 2026 retrospective | 223 | 1.156 | 1.042 | +3.17 |
| Price threshold 0.25% | 2021–24 development | 336 | 1.329 | 1.353 | +35.79 |
|  | 2025 validation | 162 | 1.275 | 1.231 | +11.19 |
|  | 2026 retrospective | 212 | 1.214 | 1.095 | +6.72 |

M11 at 4h is the strongest current standalone research candidate. Its baseline and the OI-threshold, price-threshold, RR3 and 48h variants all have positive development and 2025 net-bps PF and R PF. The 48h and RR3 variants increase net-R but worsen the worst-symbol drawdown versus some threshold variants. M11 at 1h is weak: only RR3 is marginally positive (PF about 1.005 net-bps / 1.004 R) with a worst-symbol drawdown around -45%; other tested 1h variants are negative.

M11 is strictly OI-pressure-only. It uses official open-interest metrics and taker-buy ratio, not a historical liquidation-event tape. Do not label it a liquidation-pressure engine.

## Data quality and cost assumptions

- 1m candles: official Binance Vision USD-M archives.
- BTC: 100% minute coverage; official OI history from 2021-01-01, about 99.902% coverage.
- ETH, BNB, ADA, DOGE: 100% minute coverage; OI metrics begin 2021-12-01, about 84.3% coverage over the full 2021–2026 range.
- SOL and XRP: each has two 1-hour missing-minute intervals (7,200 minutes total); the gap-safe executor invalidates affected positions and excludes DATA_GAP records from metrics.
- Funding: official Binance Vision monthly funding archives, no missing archive months in the scored historical screen. Funding is applied to every open perpetual position, regardless of strategy.
- Costs: 5 bps taker fee and 2 bps slippage per side.

## Next research steps

1. Finish the within-model M6/M11 combinations; do not combine M6 and M11.
2. Complete the new full OHLC cost-stress workflow at 5/2, 7.5/3, 10/5 and 15/10 bps per side, with moving-block bootstrap diagnostics. The prior ledger-repricing table is only indicative and is superseded by this full re-execution.
3. Continue annual chronological diagnostics and a properly funded forward holdout after 2026-11-01. Binance's November monthly funding archive is not yet available; the REST endpoint is region-restricted and attempted daily funding archives returned 404, so the forward runner currently gates scoring instead of assuming zero funding.
4. Require positive net-bps PF and R PF on 2021–2024 development and 2025 validation, adequate trade count, reasonable drawdown and robustness under stressed costs before promoting any candidate.

No model is approved for live trading. Cross-symbol aggregates are not portfolio returns. M3 remains untouched.

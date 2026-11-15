# DOGEUSDT M6/M8 independent walk-forward results — 2026-11-15

## Executive result

The final DOGE workflow (run 43679567927) completed successfully. All four matrix jobs completed, all four artifacts were inspected, and the Python suite passed (125 tests in each job checked). The earlier run exposed a pandas boolean-mask bug in the funding archive coverage annotation; the code was fixed to reduce the mask with `.any()`, and the final run passed.

**Data and funding gates passed** for all four runs:
- Binance Vision USD-M 1-minute candles: 3,067,200 rows, 2021-01-01 00:00 UTC through 2026-10-31 23:59 UTC.
- 100.00% expected-minute coverage; zero missing minutes/intervals, duplicate timestamps, or bad OHLC rows.
- Funding: official Binance Vision monthly archive, 6,390 rows, no missing archive months, maximum observed gap 8.000013 hours; funding gate passed.
- Costs: 5 bps fee per side and 2 bps slippage per side; funding cashflows applied.
- Execution: completed-bar signal, next-bar-open fill, conservative stop-first collision rule.
- Training selection: at least 30 trades, at least 80% baseline-entry overlap and 80% trade-count retention for eligible non-baseline variants.

## Combined annual walk-forward OOS ledger

The aggregate PF values below are recomputed from every selected OOS trade in the four annual test windows: net PF is the ratio of summed positive to absolute summed negative net bps; R-PF is the same ratio using net-R. Net-R is the sum of per-trade R. Combined max drawdown is computed on the chronological cumulative net-R curve, including zero as the initial equity peak. These are independent strategy-stream diagnostics, not portfolio returns.

| Model | TF | Trades | Wins | Losses | Win rate | Net PF | R-PF | Net-R | Combined max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 | 4h | 191 | 80 | 111 | 41.88% | 1.170 | 1.233 | +16.50R | -7.45R |
| M8 | 4h | 155 | 66 | 89 | 42.58% | 1.209 | 1.238 | +16.80R | -10.27R |
| M6 | 1h | 622 | 238 | 384 | 38.26% | 0.929 | 0.954 | -16.53R | -51.09R |
| M8 | 1h | 574 | 210 | 364 | 36.59% | 0.852 | 0.883 | -42.37R | -58.16R |

## Year-by-year selected OOS results

Values are: selected variant; trades; net PF / R-PF; net-R; annual max drawdown in R.

### M6 — 4h
| Year | Selected variant | Trades | Net PF | R-PF | Net-R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| 2023 | RR_3_0 | 43 | 0.686 | 0.876 | -1.80R | -3.80R |
| 2024 | RR_3_0 | 52 | 1.539 | 1.461 | +7.13R | -3.66R |
| 2025 | HOLD_48H | 56 | 1.205 | 1.367 | +8.48R | -3.18R |
| 2026* | HOLD_48H | 40 | 1.041 | 1.152 | +2.69R | -7.45R |

### M8 — 4h
| Year | Selected variant | Trades | Net PF | R-PF | Net-R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| 2023 | HOLD48_VOL10 | 38 | 0.626 | 0.861 | -2.53R | -5.25R |
| 2024 | HOLD48_VOL10 | 34 | 1.405 | 1.342 | +4.68R | -4.16R |
| 2025 | HOLD48_VOL10 | 46 | 1.981 | 2.212 | +20.10R | -4.61R |
| 2026* | HOLD48_VOL10 | 37 | 0.759 | 0.754 | -5.44R | -7.79R |

### M6 — 1h
| Year | Selected variant | Trades | Net PF | R-PF | Net-R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| 2023 | HOLD_48H | 150 | 0.494 | 0.569 | -46.32R | -46.32R |
| 2024 | HOLD_48H | 165 | 1.082 | 1.124 | +12.09R | -12.44R |
| 2025 | RR3_VOL12 | 183 | 1.080 | 1.203 | +18.21R | -13.05R |
| 2026* | RR3_VOL12 | 124 | 1.066 | 0.992 | -0.51R | -28.33R |

### M8 — 1h
| Year | Selected variant | Trades | Net PF | R-PF | Net-R | Max DD |
|---|---|---:|---:|---:|---:|---:|
| 2023 | BASELINE | 163 | 0.837 | 0.824 | -17.87R | -31.80R |
| 2024 | BASELINE | 150 | 0.880 | 0.997 | -0.23R | -11.72R |
| 2025 | HOLD_48H | 147 | 0.983 | 1.060 | +5.59R | -12.93R |
| 2026* | HOLD_48H | 114 | 0.635 | 0.644 | -29.87R | -38.41R |

*2026 is retrospective, not a pristine holdout. Earlier broad sweeps had already inspected these strategy families and periods; the complete walk-forward is therefore a retrospective diagnostic, not an unbiased final validation.

## Interpretation

1. **Do not promote either 1h DOGE module.** Both lose over the combined OOS ledger. M8 1h is especially weak (-42.37R, PF 0.852, -58.16R max drawdown). M6 1h has more trades but remains negative (-16.53R, PF 0.929).
2. **4h is the only viable direction from this experiment.** Both 4h modules are positive in aggregate and have much smaller drawdowns.
3. **M6 4h is the more stable provisional candidate.** It has 191 trades versus M8's 155, positive results in 2024, 2025 and 2026, and lower combined R drawdown (-7.45R versus -10.27R). Its net PF is 1.170 and R-PF 1.233.
4. **M8 4h has higher aggregate PF but less stable year-to-year behaviour.** It produces +20.10R in 2025, but loses in 2023 and 2026. Its overall PF/R-PF are 1.209/1.238, based on only 155 trades.
5. M6 4h selected RR_3_0 in 2023/2024 and HOLD_48H in 2025/2026; M8 4h selected HOLD48_VOL10 in all four annual windows. Training candidate selection respected the configured eligibility gates. The OOS test retention values were also above 80% for all 4h years.

## Decision

- Data and funding integrity: **passed**.
- Research workflow and tests: **passed**.
- DOGE 1h M6/M8: **reject for now**.
- DOGE 4h M6: **provisional research candidate; not production-approved**.
- DOGE 4h M8: **provisional research candidate; not production-approved**.

No explicit statistical deployment acceptance rule was configured, and there is no pristine untouched holdout. A positive retrospective PF is not sufficient to declare a strategy passed. Next validation should freeze the 4h profiles, keep M6 and M8 completely separate, and evaluate forward-only paper signals from 2026-11-01 onward with live-observed funding and realistic fills. Do not combine the two strategies or let one confirm/veto the other.

## Artifact provenance

Final workflow run: https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43679567927

Artifacts inspected:
- `doge-independent-M6-1h`
- `doge-independent-M8-1h`
- `doge-independent-M6-4h`
- `doge-independent-M8-4h`

Source ledger fields and the original annual metrics are preserved in those artifacts.

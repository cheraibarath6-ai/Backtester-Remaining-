# M6 / M11 One-Factor Sensitivity Results — 13 November 2026

## Scope and reproducibility

- Workflow: https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43429571954
- Aggregate artifact: [independent-m6-m11-sensitivity-results](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43429571954/artifacts/14046160714)
- Commit: `1a2d02c856992807ec04126f1689e33722f1d954`
- Seven Binance USD-M symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT, DOGEUSDT.
- Period: 2021-01-01 through 2026-10-31.
- Timeframes: 1h and 4h.
- Costs: 5 bps fee and 2 bps slippage per side; official Binance funding cashflows charged to every open perpetual position at settlement.
- One-factor-at-a-time variants: 406 result rows and 228,889 trade-ledger rows. All seven symbol jobs and the aggregate job completed successfully.
- M6 and M11 are evaluated independently. No ensemble or cross-model agreement is used. M3 was not included or modified.

PF below is shown both as net-bps PF and R-based PF. Net-R sums are trade-level sums across separate symbol streams, not a capital-weighted portfolio return. Drawdown is the worst individual-symbol drawdown at a fixed 1% of initial equity risk per R; it is not a combined portfolio drawdown.

## M6 Donchian — 4h

| Variant | Trades | PF (net bps) | PF (R) | Net-R | Win % | Avg hold | Worst per-symbol DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 24h baseline | 2,373 | 1.1438 | 1.1392 | +99.543 | 45.85 | 22.08h | -11.31% |
| 48h hold | 2,108 | 1.1920 | 1.2122 | +168.471 | 45.59 | 38.49h | -11.81% |
| 72h hold | 1,994 | 1.1454 | 1.1454 | +129.047 | 43.98 | 51.19h | -16.66% |
| 168h hold | 1,812 | 1.1438 | 1.1594 | +160.396 | 41.72 | 80.34h | -18.57% |
| Donchian 100 | 1,649 | 1.1425 | 1.1807 | +92.431 | 45.91 | 21.90h | -11.61% |
| RR 3 | 2,314 | 1.1735 | 1.1833 | +126.301 | 46.20 | 22.54h | -11.48% |

### M6 period breakdown

The 168h variant was positive in every reported year:

| Year | Trades | PF (R) | Net-R |
|---|---:|---:|---:|
| 2021 | 298 | 1.3260 | +51.979 |
| 2022 | 310 | 1.1968 | +32.279 |
| 2023 | 299 | 1.0529 | +9.341 |
| 2024 | 309 | 1.1195 | +20.742 |
| 2025 | 319 | 1.1857 | +32.643 |
| 2026 YTD | 277 | 1.0856 | +13.413 |

The 48h variant had stronger development plus 2025 results (+172.919R versus +144.926R for 168h), but its 2026 result was -4.449R. The 168h variant's 2026 result was +15.470R. Therefore the 48h variant is the in-period development/validation leader, while 168h is the more stable-looking later-period candidate. Do not select between them using 2026: the full sensitivity sweep included all periods, so 2026 is now a retrospective audit period, not a pristine untouched holdout.

The 168h variant's average holding time is about 80 hours. Its longer duration is a material capital-utilization and funding-exposure trade-off. Its 2026 per-symbol results were mixed, not uniformly positive. The 48h variant had a materially worse 2026 aggregate despite better earlier-period metrics.

## M11 open-interest pressure — 4h

| Variant | Trades | PF (net bps) | PF (R) | Net-R | Win % | Avg hold | Worst per-symbol DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| 24h baseline | 670 | 1.2678 | 1.2348 | +48.956 | 49.10 | 21.58h | -12.38% |
| 48h hold | 622 | 1.2404 | 1.2374 | +61.733 | 45.66 | 36.07h | -14.57% |
| 72h hold | 597 | 1.1760 | 1.1818 | +54.779 | 43.22 | 45.69h | -11.49% |
| 168h hold | 566 | 1.1721 | 1.1634 | +56.422 | 40.46 | 61.27h | -12.74% |
| RR 3 | 665 | 1.2918 | 1.2807 | +58.147 | 49.17 | 22.14h | -14.83% |
| OI threshold 0.5% | 747 | 1.2703 | 1.2351 | +53.948 | 49.26 | 21.58h | -11.67% |
| Price threshold 0.25% | 710 | 1.2814 | 1.2435 | +53.700 | 49.44 | 21.64h | -10.77% |

### M11 period breakdown

The 48h variant was positive in all six calendar-year groups, but 2021 has only six trades and is not meaningful:

| Year | Trades | PF (R) | Net-R |
|---|---:|---:|---:|
| 2021 | 6 | 4.6716 | +4.502 |
| 2022 | 98 | 1.3845 | +14.168 |
| 2023 | 103 | 1.3843 | +16.799 |
| 2024 | 85 | 1.1543 | +5.465 |
| 2025 | 145 | 1.2335 | +13.894 |
| 2026 YTD | 185 | 1.0829 | +6.904 |

The 48h hold increased net-R versus the 24h baseline, but also increased worst individual-symbol drawdown from -12.38% to -14.57% at the fixed 1% risk convention. The 2026 per-symbol distribution was mixed: five of seven symbols were positive; BNB and ETH were negative. The baseline had only three positive symbols in 2026.

M11 uses OI change, price change and taker-buy ratio. It is an **open-interest pressure** model, not a liquidation-pressure model. No complete historical Binance liquidation-event tape was used.

## Cost sensitivity (indicative only)

A ledger-based additional-cost haircut was applied to the completed trades; this is not a second full OHLC execution rerun. It estimates the effect of increasing fees from 5 to 7.5 bps per side and slippage from 2 to 4 bps per side, then to 10/5 bps per side.

| Variant | Base PF-R / Net-R | Approx. 7.5/4 PF-R / Net-R | Approx. 10/5 PF-R / Net-R |
|---|---:|---:|---:|
| M6 168h | 1.159 / +160.40R | 1.126 / +129.15R | 1.101 / +104.84R |
| M11 48h | 1.237 / +61.73R | 1.156 / +42.11R | 1.096 / +26.86R |
| M11 24h baseline | 1.235 / +48.96R | 1.126 / +27.56R | 1.048 / +10.91R |

This haircut uses recorded entry/exit prices and initial stops to estimate incremental cost in R. It does not replace a full re-execution with stressed slippage and fees. Full cost-stress runs remain required before selection.

## Data quality

- Candles: official Binance Vision USD-M 1m archives. BTC, ETH, BNB, ADA and DOGE had 100% minute coverage. SOL and XRP each had 99.7653% coverage (7,200 missing minutes) and need gap-interval inspection before final selection.
- Funding: official Binance Vision monthly archive; no missing archive months; maximum observed interval approximately 8 hours. Funding is applied to all perpetual positions, independent of model.
- OI: official Binance daily metrics. BTC coverage was 99.902% from 2021-01-01. The other six symbols began 2021-12-01, yielding about 84.3% coverage across the full 2021-2026 window; there were no missing archive days after each symbol's available start.
- No historical liquidation-event series was available. Do not substitute OI change for liquidations.

## Decision and next tests

No model is approved for deployment.

- M6 4h: keep 48h and 168h as separate candidates. Test the predeclared within-M6 combinations and additional 120h/144h/192h hold variants. Do not choose using the retrospective 2026 result.
- M11 4h: keep the 24h baseline and 48h hold as separate candidates; test predeclared combinations of OI threshold, price threshold, RR and holding horizon. 48h improves net-R but worsens worst-symbol drawdown.
- Next workflow: [M6/M11 combination research](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43444627475).
- Corrected all-model screen: [Independent Core Engine Discovery](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43444488687). It must finish and its artifacts must be inspected before any full model comparison.
- A genuinely untouched forward holdout must begin after 2026-11-01; the already-screened 2026 data must not be reused as if it were unseen.

M3 remains untouched.

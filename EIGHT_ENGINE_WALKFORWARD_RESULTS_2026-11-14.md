# Eight-engine expanding walk-forward results — 14 November 2026

## Scope and execution

This report records the completed run [43570153457](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43570153457), branch `research/funding-notional-audit-v2`, code revision `0ca06944c63b6aff869553d88ec83ac0cd5821ac`.

- Models run independently: M6, M7, M8, M10, M12, M13, M14, M15 only.
- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, SOLUSDT, XRPUSDT.
- Timeframes: 1h and 4h. This walk-forward batch does not cover 5m/15m.
- Test years: 2023, 2024, 2025 and 2026 through 31 October.
- Results: 448 model/symbol/timeframe/year rows; 432 completed and 16 not applicable. The 16 N/A rows are M10 and M13 on BTC, because BTC is the benchmark, not a traded leg. There are 1,632 training-score rows and 75,756 selected test-trade ledger rows.
- 5 bps taker fee and 2 bps slippage per side, plus official Binance USD-M funding. Signals use completed bars and entries execute on the next bar.
- Selection is per model and per symbol stream. It maximizes training net-R, then R-PF and drawdown, with at least 80% training baseline-entry overlap and 80% trade-count retention for non-baseline candidates.
- DATA_GAP and END_OF_SAMPLE records remain in the ledger but are excluded from scored metrics. Cross-symbol summaries are symbol-stream diagnostics, not portfolio returns.

## Important interpretation

The candidate profiles in this run were discovered after broad historical sweeps. Although each annual test window uses only earlier training observations for its per-stream profile selection, the candidate universe itself was informed by later historical research. Treat this as a retrospective expanding-window diagnostic, **not a pristine untouched holdout**. 2026 is retrospective audit evidence only.

The reported medians below are medians across completed symbol streams for each model/timeframe/year. They are not pooled cross-symbol returns. M10 and M13 have six traded symbol streams because BTC is used as a benchmark.

## All-period summary by model and timeframe

The medians cover the 2023–2026 annual test streams. "Entry retention" is overlap with baseline entry timestamps; "count retention" is candidate valid trade count divided by baseline valid trade count.

| Model | TF | Median trades / symbol-year | Median selected PF | Median selected net bps | Median selected net-R | Median baseline PF | Median baseline net bps | Median entry retention | Median count retention | Selected streams PF > 1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 | 1h | 165.5 | 0.910 | -2,221 | -5.71 | 0.962 | -1,119 | 89.2% | 93.0% | 11/28 |
| M6 | 4h | 50.0 | 1.108 | +742 | +2.64 | 1.047 | +240 | 85.8% | 91.5% | 18/28 |
| M7 | 1h | 376.5 | 0.848 | -6,203 | -52.48 | 0.845 | -5,520 | 97.0% | 100.0% | 2/28 |
| M7 | 4h | 113.0 | 0.820 | -3,561 | -11.38 | 0.830 | -3,108 | 98.2% | 104.4% | 7/28 |
| M8 | 1h | 138.5 | 0.923 | -1,269 | -4.62 | 0.898 | -1,230 | 91.5% | 94.2% | 7/28 |
| M8 | 4h | 38.0 | 1.006 | +26 | +0.55 | 0.966 | -134 | 97.2% | 100.0% | 14/28 |
| M10 | 1h | 269.5 | 0.917 | -2,999 | -5.53 | 0.917 | -2,999 | 100.0% | 100.0% | 5/24 |
| M10 | 4h | 174.0 | 0.896 | -1,858 | -3.71 | 0.896 | -1,858 | 100.0% | 100.0% | 8/24 |
| M12 | 1h | 227.5 | 0.913 | -3,158 | -24.48 | 0.925 | -2,099 | 88.9% | 91.8% | 10/28 |
| M12 | 4h | 70.0 | 0.948 | -567 | -1.28 | 0.957 | -411 | 91.4% | 92.9% | 13/28 |
| M13 | 1h | 347.5 | 0.916 | -4,206 | -7.88 | 0.916 | -4,206 | 100.0% | 100.0% | 5/24 |
| M13 | 4h | 214.0 | 0.886 | -2,885 | -5.43 | 0.886 | -2,885 | 100.0% | 100.0% | 3/24 |
| M14 | 1h | 296.0 | 0.938 | -3,166 | -4.14 | 0.938 | -2,844 | 100.0% | 100.0% | 7/28 |
| M14 | 4h | 159.5 | 0.975 | -499 | +2.43 | 0.962 | -1,102 | 91.4% | 100.7% | 12/28 |
| M15 | 1h | 177.5 | 0.841 | -2,471 | -12.42 | 0.841 | -2,220 | 100.0% | 100.0% | 9/28 |
| M15 | 4h | 43.5 | 0.925 | -319 | -0.50 | 0.757 | -1,484 | 93.3% | 94.1% | 12/28 |

## Yearwise 4h results

Each cell is the median across seven symbol streams (six for M10/M13). Trade count is median trades per symbol, not the total across symbols.

| Year | Model | Median trades | Selected PF | Selected net bps | Selected net-R | Baseline PF | Baseline net bps | Entry retention | Count retention |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | M6 | 47 | 1.143 | +875 | +3.21 | 0.974 | -178 | 90.0% | 94.0% |
| 2023 | M7 | 113 | 1.099 | +1,037 | -1.44 | 1.099 | +1,449 | 98.3% | 109.6% |
| 2023 | M8 | 38 | 0.626 | -1,788 | -2.93 | 0.678 | -1,479 | 97.3% | 100.0% |
| 2023 | M10 | 171 | 0.775 | -2,794 | -6.90 | 0.775 | -2,794 | 100.0% | 100.0% |
| 2023 | M12 | 62 | 1.213 | +2,216 | +10.10 | 0.946 | -378 | 91.5% | 92.7% |
| 2023 | M13 | 203 | 0.744 | -5,683 | -13.15 | 0.744 | -5,683 | 100.0% | 100.0% |
| 2023 | M14 | 158 | 0.815 | -3,080 | -2.95 | 0.815 | -3,080 | 91.8% | 101.6% |
| 2023 | M15 | 48 | 0.939 | -233 | -3.26 | 0.939 | -233 | 94.4% | 95.3% |
| 2024 | M6 | 52 | 1.141 | +1,322 | +2.57 | 1.135 | +1,256 | 87.9% | 91.4% |
| 2024 | M7 | 117 | 0.750 | -5,105 | -22.49 | 0.712 | -5,766 | 99.1% | 110.3% |
| 2024 | M8 | 37 | 1.163 | +1,398 | +2.87 | 1.366 | +1,717 | 97.8% | 100.0% |
| 2024 | M10 | 176 | 0.980 | -316 | -1.58 | 0.980 | -316 | 100.0% | 100.0% |
| 2024 | M12 | 76 | 0.972 | -346 | -0.04 | 0.923 | -1,059 | 87.9% | 91.2% |
| 2024 | M13 | 225 | 0.992 | -284 | +3.72 | 0.992 | -284 | 100.0% | 100.0% |
| 2024 | M14 | 169 | 1.020 | +457 | +1.99 | 1.020 | +457 | 94.0% | 101.8% |
| 2024 | M15 | 43 | 1.159 | +997 | +3.51 | 1.117 | +549 | 93.8% | 93.8% |
| 2025 | M6 | 51 | 1.175 | +2,902 | +8.01 | 1.009 | +108 | 82.1% | 87.5% |
| 2025 | M7 | 116 | 0.820 | -3,546 | -15.96 | 0.840 | -2,315 | 98.1% | 100.0% |
| 2025 | M8 | 46 | 1.165 | +799 | +3.15 | 1.236 | +1,066 | 95.5% | 96.0% |
| 2025 | M10 | 199 | 0.957 | -880 | +4.02 | 0.957 | -880 | 100.0% | 100.0% |
| 2025 | M12 | 78 | 0.904 | -1,772 | -0.94 | 0.838 | -1,709 | 98.7% | 100.0% |
| 2025 | M13 | 217 | 0.925 | -2,610 | -1.53 | 0.925 | -2,610 | 100.0% | 100.0% |
| 2025 | M14 | 162 | 0.998 | -60 | +4.32 | 0.923 | -2,069 | 85.9% | 100.0% |
| 2025 | M15 | 52 | 1.036 | +244 | +4.32 | 0.856 | -1,236 | 92.7% | 93.2% |
| 2026* | M6 | 47 | 1.000 | +2 | +2.23 | 1.018 | +134 | 86.0% | 89.5% |
| 2026* | M7 | 92 | 0.819 | -3,443 | -7.15 | 0.888 | -1,495 | 97.8% | 100.0% |
| 2026* | M8 | 37 | 0.607 | -2,189 | -5.44 | 0.708 | -1,669 | 97.1% | 97.5% |
| 2026* | M10 | 151 | 0.851 | -2,975 | -7.90 | 0.851 | -2,975 | 100.0% | 100.0% |
| 2026* | M12 | 63 | 1.046 | +486 | -3.49 | 1.041 | +489 | 93.7% | 93.7% |
| 2026* | M13 | 191 | 0.870 | -2,922 | -9.17 | 0.870 | -2,922 | 100.0% | 100.0% |
| 2026* | M14 | 136 | 0.966 | -674 | -0.28 | 0.995 | -113 | 85.8% | 100.7% |
| 2026* | M15 | 43 | 0.689 | -1,997 | -4.68 | 0.668 | -2,211 | 95.3% | 95.3% |

*2026 results are retrospective through 31 October, not a pristine holdout.

## Selected-profile frequency across annual symbol streams

| Model / timeframe | Most frequently selected profiles |
|---|---|
| M6 4h | HOLD_48H 18; RR_3_0 5; HOLD48_STOP3 3; RR3_VOL12 1; BASELINE 1 |
| M8 4h | HOLD48_VOL10 9; EXPANSION_1_5 7; HOLD_48H 5; VOLUME_1_0 4; HOLD48_EXP15 2; BASELINE 1 |
| M14 4h | MOMENTUM_21 16; BASELINE 12 |
| M15 4h | ATR_TRAIL_2_5 19; ATR_TRAIL_2_5_H48 4; BASELINE 5 |
| M12 4h | HOLD_72H 16; BASELINE 7; STOP_ATR_1_5 4; BREAKOUT_40 1 |
| M7 4h | BB_Z_1_8 14; BASELINE 10; HOLD_72H 4 |
| M10 4h | BASELINE 23; EMA_FAST_100 1 |
| M13 4h | BASELINE 24 |

## Data-quality audit

Official Binance Vision USD-M 1m candles cover 1 January 2021 through 31 October 2026. BTC, ETH, BNB, ADA and DOGE have 100% coverage in the recorded audit. SOL and XRP each have 7,200 missing minutes in two historical intervals (99.7653% coverage); missing intervals are explicitly gap-handled and affected trades are not scored. No duplicate timestamps or malformed OHLC rows were recorded in the quality manifest.

Funding came from the official Binance Vision monthly archive. The recorded maximum settlement gap was approximately 8.000013 hours, with no missing archive months; the funding gate passed. No zero-funding fallback was used.

The Binance Vision data licensing terms in the repository's source audit must be respected; this dataset is marked CC BY-NC-SA 4.0 for non-commercial research. This research does not establish permission for commercial or live automated execution.

## Decision

- **M6 4h is the clearest walk-forward candidate:** median selected PF 1.108 and median net +742 bps per symbol-year, with median 91.5% trade-count retention. Its 2025 median is strong, but 2026 is essentially flat on net bps. Continue as a research candidate only.
- **M8 4h is regime-sensitive:** near breakeven across all streams; 2024/2025 are positive, but 2023 and 2026 are negative. It is not robust enough for promotion.
- **M14 4h is mixed:** the median R result is positive, but median net bps remains negative and 2026 weakens. Investigate symbol-level dispersion before another sweep.
- **M15 4h improves on its baseline in several years but remains negative across the full median; 2026 is weak.**
- M7, M10, M12 and M13 do not show a sufficiently consistent positive net edge in this walk-forward diagnostic. Avoid adding more filters merely to improve PF.

The next defensible step is not another broad parameter search on the same historical window. Freeze the best M6 4h definition and retain M8/M14/M15 only as secondary research candidates. Continue paper observation and wait for the predeclared forward holdout to accumulate at least 30 complete UTC days with verified official funding and checksums. As of 14 November 2026, that window is not complete. The forward-holdout workflow remains dormant while PR #2 is an unmerged draft; do not merge or run it without an explicit merge decision.

## Reproducibility

- Workflow: [Independent Eight-Engine Retention-Gated Walk-Forward — run 43570153457](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43570153457)
- Full per-symbol/year result CSV, training candidate scores, selected trade ledger, and data-quality JSON are in the run's `eight-engine-walkforward-results` artifact.
- Cost-stress and 500-block-bootstrap report: [EIGHT_ENGINE_COST_STRESS_RESULTS_2026-11-14.md](EIGHT_ENGINE_COST_STRESS_RESULTS_2026-11-14.md)
- Forward holdout protocol: [FORWARD_HOLDOUT_PROTOCOL_2026-11-14.md](FORWARD_HOLDOUT_PROTOCOL_2026-11-14.md)
- PR #2 remains open and draft. This report adds no model code and does not touch M3.

# Corrected independent crypto-futures research — 14 November 2026


## Follow-up audit: period attribution and censored trades

A subsequent audit on 14 November found that the earlier screen, sensitivity, combination and cost-stress helpers assigned development/validation trades by **exit year** rather than by **entry cohort**, and the shared summary counted unresolved `END_OF_SAMPLE` records as completed trades. This could place a pre-validation entry into the 2025 validation bucket and score positions that had not actually closed by the data boundary.

The corrected code now:
- defines development/validation cohorts by entry time within the requested period and requires the trade to exit before that period's exclusive end;
- excludes both `DATA_GAP` and `END_OF_SAMPLE` records from performance metrics while retaining both in audit ledgers with separate counts;
- applies the same exclusion to cross-symbol aggregators and the cost-stress bootstrap;
- keeps yearly realized summaries grouped by exit year, but excludes censored records from their metrics.

**Important:** the development, 2025 validation and 2026 retrospective cohort metrics shown in the earlier sections below come from the superseded runs listed above. They are not final selection evidence. The corrected reruns are:

- [Funding/accounting and cohort regression tests — 43520168387](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43520168387)
- [Full independent screen — 43520160545](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43520160545)
- [M6/M11 one-factor sensitivity — 43520160442](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43520160442)
- [M6/M11 combinations and expanding walk-forward — 43520168355](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43520168355)
- [M6/M11 full OHLC cost stress — 43520168394](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43520168394)

The combination and cost-stress grids also now include the previously omitted M6 48h holding-horizon anchor, M6 24h stop/RR/volume one-factor anchors, and M11 OI05/price025 36h candidate. No candidate is approved until these corrected runs and the expanding-window checks complete. 2026 remains retrospective audit evidence, not a pristine holdout.


## Scope and provenance

- Research branch: `research/funding-notional-audit-v2`
- Draft PR: [#2](https://github.com/cheraibarath6-ai/Backtester-Remaining-/pull/2), preserved open and in draft.
- Full corrected independent screen: [run 43475018639](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475018639), aggregate artifact [14067668167](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475018639/artifacts/14067668167).
- M6/M11 one-factor sensitivity: [run 43475105074](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475105074), aggregate artifact [14067097910](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475105074/artifacts/14067097910).
- Within-model combinations: [run 43475114006](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475114006), aggregate artifact [14066914237](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475114006/artifacts/14066914237).
- Full OHLC cost stress and 500-resample block bootstrap: [run 43475120490](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475120490), aggregate artifact [14067828401](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475120490/artifacts/14067828401).
- Funding/accounting regression tests: [run 43475126673](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43475126673); the inspected log reports **66 passed**.
- Forward data-collection audit: [run 43474084425](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425); all seven symbol jobs completed, but no forward trades were scored because funding was unavailable.

The corrected full screen produced 504 symbol/model/timeframe result rows, 1,824 yearly rows and 1,179,360 trade-ledger records. The ledger retains 54 `DATA_GAP` exits; those records are excluded from performance metrics. Cross-symbol trade-stream sums below are not capital-weighted portfolio returns or portfolio drawdowns.

## Execution and accounting audit

The current gap-safe executor:

- generates signals on completed bars and fills at the next bar open;
- checks the entry bar for stop/target hits and applies conservative stop-first handling if both barriers are touched;
- models adverse opening gaps;
- charges entry and exit fees on their respective executed notionals;
- applies funding at settlement on mark-price notional (or the last completed bar close when no mark price is available) to every open USD-M perpetual position, independent of signal model;
- resets rolling indicators, VWAP, OI changes and benchmark-return histories at data-segment boundaries;
- invalidates positions crossing unobserved candle intervals with `DATA_GAP`, skips stale signals and preserves exact missing intervals;
- shifts Binance OI metric rows dated 25 June 2026 onward by +5 minutes to their actual snapshot availability time, preventing M11 from consuming a future snapshot;
- reports fixed-initial-equity-risk return separately from fixed-notional PnL.

## Data quality

| Symbol | 1m rows | Candle coverage | Missing minutes | Funding rows | Funding max gap | OI coverage |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 3,067,200 | 100.0000% | 0 | 6,390 | 8.0000h | 99.9019% |
| ETHUSDT | 3,067,200 | 100.0000% | 0 | 6,390 | 8.0000h | 84.2963% |
| BNBUSDT | 3,067,200 | 100.0000% | 0 | 6,390 | 8.0000h | 84.2963% |
| ADAUSDT | 3,067,200 | 100.0000% | 0 | 6,390 | 8.0000h | 84.2963% |
| DOGEUSDT | 3,067,200 | 100.0000% | 0 | 6,390 | 8.0000h | 84.2963% |
| SOLUSDT | 3,060,000 | 99.7653% | 7,200 (2 intervals) | 6,465 | 8.0000h | 84.2935% |
| XRPUSDT | 3,060,000 | 99.7653% | 7,200 (2 intervals) | 6,390 | 8.0000h | 84.2961% |

Candle source: official Binance Vision USD-M 1m monthly archives, with SHA256 companion checks when available. Funding source: official Binance Vision monthly funding archives; no missing archive months. OI source: official Binance Vision daily metrics. The six non-BTC symbols' OI history begins 1 December 2021, explaining most of their full-period coverage shortfall; no missing archive days were reported after the available start. M11 remains OI-only; no historical liquidation feed is used.

## M1/M2/M4/M5 retained baselines

All tested baseline streams were negative in aggregate net-R. P1/P2 5m/15m results:

| Model/profile | TF | Trades | PF bps | PF R | Net-R |
|---|---:|---:|---:|---:|---:|
| M1 P1 | 5m | 175 | 0.6277 | 0.5176 | -74.733 |
| M1 P2 | 5m | 2,205 | 0.8864 | 0.7597 | -411.712 |
| M1 P1 | 15m | 55 | 0.7240 | 0.8560 | -5.036 |
| M1 P2 | 15m | 828 | 0.8345 | 0.8139 | -102.200 |
| M2 P1 | 5m | 3,411 | 0.9254 | 0.8869 | -265.054 |
| M2 P2 | 5m | 4,869 | 0.8589 | 0.8005 | -726.026 |
| M2 P1 | 15m | 1,524 | 0.9123 | 0.9530 | -38.675 |
| M2 P2 | 15m | 2,089 | 0.9590 | 0.9442 | -70.655 |
| M4 P1 | 5m | 1,630 | 0.7722 | 0.7480 | -318.191 |
| M4 P2 | 5m | 5,916 | 0.7656 | 0.6939 | -1,450.694 |
| M4 P1 | 15m | 616 | 0.9014 | 0.8771 | -48.666 |
| M4 P2 | 15m | 2,137 | 0.8832 | 0.8418 | -220.154 |
| M5 P1 | 5m | 121 | 0.5134 | 0.4316 | -67.216 |
| M5 P2 | 5m | 1,458 | 0.6980 | 0.5924 | -536.677 |
| M5 P1 | 15m | 69 | 1.1819 | 0.9912 | -0.419 |
| M5 P2 | 15m | 576 | 0.8428 | 0.7405 | -116.038 |

M5 P1 15m is a small-sample near-breakeven exception: 69 trades overall and only 12 trades in 2025. Its net-R remains slightly negative.

## Independent M6-M15 baseline comparison — 4h

Costs: 5 bps taker fee and 2 bps slippage per side, plus actual funding. Return is fixed-initial-equity risk at 1% per R; the cross-symbol sum is only a trade-stream diagnostic. Drawdown is the worst individual-symbol drawdown at the same 1% risk convention.

| Model | Trades | PF bps | PF R | Net-R | Win % | Avg hold | Worst symbol DD | Dev 2021-24 net-R | 2025 net-R | 2026 retrospective net-R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 Donchian | 2,373 | 1.0957 | 1.1392 | +99.558 | 45.85 | 22.1h | -11.312% | +77.375 | +25.216 | -3.032 |
| M7 mean reversion | 4,410 | 0.7898 | 0.7476 | -567.694 | 43.56 | 16.9h | -100.000% | -426.779 | -97.076 | -43.838 |
| M8 volatility expansion | 1,745 | 1.0599 | 1.1058 | +64.588 | 45.56 | 21.1h | -18.358% | +41.403 | +40.808 | -17.623 |
| M9 VWAP/flow | 25 | 0.6221 | 0.5803 | -5.719 | 32.00 | 19.2h | -2.699% | -1.608 | -0.433 | -3.679 |
| M10 relative momentum | 6,300 | 1.0172 | 1.0234 | +44.879 | 46.03 | 21.9h | -38.745% | +62.750 | +27.620 | -45.489 |
| M11 OI pressure | 669 | 1.2661 | 1.2346 | +48.916 | 49.03 | 21.6h | -12.376% | +33.493 | +11.333 | +4.091 |
| M12 regime-specific | 3,164 | 0.9119 | 0.8988 | -142.752 | 39.95 | 19.2h | -43.738% | -77.693 | -38.296 | -26.763 |
| M13 BTC lead-lag | 7,954 | 0.8779 | 0.9320 | -163.263 | 44.51 | 22.1h | -57.794% | -91.934 | -8.348 | -62.982 |
| M14 ADX momentum | 6,673 | 1.0005 | 1.0356 | +75.071 | 44.63 | 21.7h | -42.343% | +59.734 | +26.058 | -10.722 |
| M15 Awesome MACD | 2,040 | 0.9302 | 0.9352 | -41.514 | 43.14 | 22.0h | -24.017% | +26.243 | -18.026 | -49.728 |

Yearly 4h net-R by model (cross-symbol trade-stream sums; not portfolio returns):

| Model | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 audit |
|---|---:|---:|---:|---:|---:|---:|
| M6 | +15.778 | +20.826 | +20.082 | +20.689 | +25.216 | -3.032 |
| M7 | -93.743 | -128.219 | -53.536 | -151.281 | -97.076 | -43.838 |
| M8 | +20.336 | +8.935 | -11.638 | +23.770 | +40.808 | -17.623 |
| M9 | -1.059 | +1.961 | -0.704 | -1.804 | -0.433 | -3.679 |
| M10 | +83.553 | +19.958 | -31.455 | -9.309 | +27.620 | -45.489 |
| M11 | +3.676* | +15.930 | +9.829 | +4.058 | +11.333 | +4.091 |
| M12 | -54.375 | -27.501 | +29.004 | -24.821 | -38.296 | -26.763 |
| M13 | -6.750 | -28.634 | -66.416 | +9.866 | -8.348 | -62.982 |
| M14 | +19.234 | +14.112 | +1.639 | +24.749 | +26.058 | -10.722 |
| M15 | +34.717 | -1.622 | -4.579 | -2.277 | -18.026 | -49.728 |

* M11 2021 contains only six trades across three symbols; non-BTC OI archives begin in December 2021.

Additional timeframe diagnostics: M9 1h has 1,012 trades, PF bps 1.0013, PF R 0.9753 and net-R -15.084; it is near breakeven on bps but negative on R. M15 1h has PF bps 1.0465 but PF R 0.9933 and net-R -26.314. Neither is a pass. M7 is negative on all tested timeframes. M13 is negative on all four tested timeframes.

## M6/M11 full cost stress and bootstrap

The completed cost-stress run re-executed OHLC paths at four per-side cost levels: 5/2, 7.5/3, 10/5 and 15/10 bps (fee/slippage). It covered three selected within-model variants per model, not the original 24h screen baseline.

| Model/variant | Cost | Trades | PF bps | PF R | Net-R | Worst symbol DD |
|---|---|---:|---:|---:|---:|---:|
| M6 D100_RR3_H168 | base 5/2 | 1,118 | 1.3750 | 1.3984 | +243.748 | -11.076% |
| M6 D100_RR3_H168 | severe 15/10 | 1,114 | 1.2520 | 1.2464 | +159.598 | -17.864% |
| M6 D100_VOL12_RR3_H168 | base 5/2 | 1,096 | 1.3779 | 1.4106 | +246.499 | -11.345% |
| M6 D100_VOL12_RR3_H168 | severe 15/10 | 1,091 | 1.2624 | 1.2618 | +165.995 | -17.262% |
| M6 D100_STOP2_H168 | base 5/2 | 1,452 | 1.1815 | 1.2387 | +202.926 | -16.776% |
| M6 D100_STOP2_H168 | severe 15/10 | 1,440 | 1.0833 | 1.1044 | +93.863 | -23.559% |
| M11 OI05_RR3_H48 | base 5/2 | 681 | 1.2623 | 1.2643 | +75.538 | -15.187% |
| M11 OI05_RR3_H48 | severe 15/10 | 680 | 1.0066 | 0.9856 | -4.690 | -22.947% |
| M11 OI05_PRICE025_RR3_H48 | base 5/2 | 721 | 1.2623 | 1.2485 | +75.898 | -13.984% |
| M11 OI05_PRICE025_RR3_H48 | severe 15/10 | 720 | 1.0055 | 0.9716 | -9.856 | -24.247% |
| M11 OI05_PRICE025_RR3_H72 | base 5/2 | 686 | 1.2403 | 1.2470 | +86.443 | -12.386% |
| M11 OI05_PRICE025_RR3_H72 | severe 15/10 | 685 | 1.0317 | 1.0129 | +5.013 | -23.361% |

Interpretation by chronological validation:

- The three selected M6 168h variants are positive in 2021-2024 development, but all three have negative 2025 net-R at severe costs (approximately -5.5R, -3.2R and -5.0R respectively). Their attractive full-period severe-cost totals are therefore not sufficient for selection.
- M11 H48 variants also fail severe-cost 2025 validation (approximately -1.3R and -1.4R; R-PF below 1). M11 OI05_PRICE025_RR3_H72 is the only selected M11 combination with positive 2025 severe-cost net-R (+3.117R, PF bps 1.0528, PF R 1.0359), but it is negative in 2024 (-6.549R) and its 2026 retrospective audit is sharply negative (-29.342R, PF bps 0.8013, PF R 0.7691). It is not a robust pass.
- The cost-stress bootstrap used 500 moving-block resamples of 20 consecutive trades per symbol stream. At severe costs, M6 D100_VOL12_RR3_H168 had median symbol-stream probability of positive net-R 87.4%, but its weakest symbol was 34.6%. M11 H72 had median 73.8%, but its weakest symbol was 2.8%. This is a diagnostic, not a forecast or portfolio probability.

## M13 falsification evidence and public source/licensing audit

[nateemma/strategies — btc_corr/FINAL_REPORT.md](https://github.com/nateemma/strategies/blob/master/btc_corr/FINAL_REPORT.md) studies BTC plus 12 alts on 1h data (with a 4h cross-check, roughly 2024-04 to 2026-07). It reports lag-0 correlation as the peak for all pairs/timeframes and lag-1h correlation collapsing near zero (e.g. SOL 0.747 to -0.016; ETH 0.791 to 0.004). This is negative prior evidence for return-based M13, not a proof about every sub-hourly mechanism. The report also attributes a small predictive lift to volatility/trend-regime features rather than lagged BTC returns. M13 remains a falsifiable standalone test, not an assumed edge. No GPL source code was copied.

Other public strategy references and their licences are recorded in [RESEARCH_SOURCES.md](RESEARCH_SOURCES.md). The project independently implements the concepts; GPL-3.0 strategy source is not copied. MIT references are used as implementation/research leads, not as evidence of performance.

**Binance Vision restriction:** The current Dataset Terms version 1.0 (updated 26 August 2026) grants CC BY-NC-SA 4.0 except where specifically designated otherwise, limits permitted use to non-commercial/personal non-production research and expressly prohibits live proprietary execution or commercial automated order generation without a separate written enterprise licence. See [official terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md). This research data must not be assumed licensed for live or commercial deployment.

## Forward data gate

[Forward data audit run 43474084425](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43474084425) collected 46,080 recent 1m candles per symbol with 100% coverage and 4,896 OI rows per symbol with 99.9796% 5m coverage. The official daily funding archive paths for 1-12 November returned 404 and the official funding REST endpoint returned HTTP 451 from the runner region. The November monthly archive was not yet published. All forward M6/M11 scoring was correctly marked `DATA_GATED_FUNDING_ARCHIVE_PENDING`; no trades were scored and no zero-funding assumption was made. This is not a zero-trade outcome.

## New robustness work added to the branch

- Added an independent expanding-window M6/M11 walk-forward runner and workflow. For each symbol/model/year, it selects among that model's predeclared parameter profiles using only completed trades before the test-year boundary; net-R is the primary ranking key and R-PF only a tie-breaker. Annual tests start flat, disable new signals at the exclusive year end, and allow entered trades their declared holding horizon to exit. 2026 remains retrospective audit evidence, not a pristine holdout.
- Added the original 24h M6 and M11 screen baselines to the within-model profile grid and the next full cost-stress selection. The earlier completed cost-stress run above predates this baseline inclusion; a baseline-inclusive cost-stress rerun is required before treating it as the final stress comparison.
- Updated the public-source register with the M13 falsification evidence.
- These new workflow/code changes were pushed after the completed runs listed above. Their latest run IDs/status are not yet verified in this report; do not treat the walk-forward or baseline-inclusive cost-stress as completed.

## Current decision

- **Research leads:** M11 4h original baseline and M6 4h original baseline; M8 4h is a weaker secondary candidate; M14 4h is borderline with excessive drawdown.
- **Not proven:** none has passed the complete sequence of independent walk-forward, baseline-inclusive full cost stress, Monte Carlo, and a funding-complete forward holdout.
- **Not selected:** M7, M9, M10, M12, M13 and M15 have not demonstrated robust net expectancy under the tested settings; M10/M14 positive full-period sums are undermined by drawdown and/or 2026 deterioration.
- No engine is approved for live trading. M3 remains untouched.


## Latest baseline-inclusive reruns — 14 November

The original 24h M6/M11 screen profiles were added to the within-model profile universe after the completed cost-stress run above. The earlier run 43475120490 is therefore not the final stress comparison for those original baselines.

- [Baseline-inclusive full cost stress PR run 43503121592](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43503121592): pending at the last inspection; BTC and ETH jobs were in progress, with the other five symbol jobs queued. Each symbol job compiles the research package and runs the complete pytest suite before re-execution.
- [Updated within-model combination PR run 43503121351](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43503121351): pending at the last inspection; job creation had not yet completed.
- The new [expanding-window walk-forward workflow](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/workflows/m6-m11-walkforward.yml) is on the branch. Its execution/artifacts are not yet verified here.

The latest branch comparison against `main` is 101 commits ahead across 33 changed files. The compare response contains **no M3 path**. All research changes remain confined to the independent-engine research, data/accounting, tests, reports and workflow files.


## Latest Actions verification after baseline inclusion

- [Funding Notional Audit Tests run 43503837843](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43503837843) completed successfully. Its job log confirms **70 passed in 1.21s**, including the walk-forward helper tests and the corrected 24h baseline-profile assertions.
- [Updated M6/M11 combination + walk-forward run 43503837399](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43503837399) is queued with seven symbol jobs. The walk-forward matrix and aggregator are dependent jobs and will be created after the combination matrix completes.
- [Baseline-inclusive full cost stress run 43503837360](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43503837360) is pending; its jobs have not yet been created at the latest status check.
- Earlier run 43503121592 failed because the old long-hold test rejected the intentional 24h baseline; run 43503320576 passed the full test step (70 passed) but was cancelled during workflow replacement. The current run IDs above supersede those attempts.

The original 24h M6/M11 profiles are now included in both the combination and cost-stress grids. No cost-stress or walk-forward performance result is claimed until their current artifacts finish and are inspected.

## Latest audit update — 14 November 2026

### Funding settlement boundary treatment

The shared executor now distinguishes settlements strictly inside a position's holding interval from settlements exactly coincident with its entry or exit timestamp. With OHLC data, ordering at an exact boundary cannot be resolved. The conservative rule is therefore:
- charge an adverse boundary funding cashflow;
- do not assume a favorable funding credit at an ambiguous entry/exit boundary;
- apply the signed funding cashflow normally for settlements strictly inside the holding interval.

This applies to all perpetual strategies, not just M5 or M11. Two dedicated regression tests cover the boundary and interior cases.

### 2026 period naming

The independent screen, M6/M11 sensitivity and combination outputs now use `retrospective_2026_*` fields. The plan and aggregate report explicitly describe 2026 through October as retrospective audit evidence because it was included in broad parameter sweeps; it is not a pristine untouched holdout and is excluded from parameter selection. A future forward-only holdout remains reserved for dates after 1 November 2026, subject to complete official funding data.

### Latest regression and reruns

- [Funding/accounting regression run 43525320832](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525320832): successful; inspected log confirms **77 passed in 1.44s**.
- Latest corrected branch head: `83474438af4e569db5edd45b49b94d9cd4558362`.
- [Independent screen 43525314007](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314007), [M6/M11 sensitivity 43525314000](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314000), [M6/M11 combinations/walk-forward 43525320939](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525320939), and [full OHLC cost stress 43525320823](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525320823) are the current corrected run set. Their result artifacts must be inspected after completion; prior runs with the less conservative funding-boundary rule are superseded for final selection.

No model is approved for live trading. M3 remains untouched.


## Verified baseline-inclusive cost stress and combination reruns — 14 November 2026, 00:35 UTC

This section supersedes the earlier cost-stress status above. The new runs are on the same research code revision as the corrected cohort logic; the one commit between the earlier screen SHA and the current branch head changed only this report.

### Latest verified workflows and artifacts

- [Funding/accounting regression tests — run 43525481806](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525481806): completed successfully. The inspected job log confirms **77 passed in 1.10s**.
- [Baseline-inclusive full OHLC cost stress — run 43525481794](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525481794): all seven symbol jobs and the aggregate job completed successfully. [Aggregate artifact 14087983532](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525481794/artifacts/14087983532).
- [Within-model combinations plus expanding walk-forward — run 43525482018](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525482018): all seven M6/M11 combination symbol jobs and the combination aggregator completed successfully. [Combination aggregate artifact 14089187276](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525482018/artifacts/14089187276). The separate walk-forward matrix has started: BTC and ETH were in progress, and the other five symbols were queued at the last inspection. No walk-forward performance result is claimed yet.
- [M6/M11 one-factor sensitivity — run 43525314000](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314000): all seven symbols and aggregation completed. [Aggregate artifact 14088008286](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314000/artifacts/14088008286).
- [Independent full screen — run 43525314007](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314007): six symbol jobs completed; DOGE was still executing at the last inspection, so its final aggregate is pending. The only commit between this run's code SHA and the current branch head changed this report, not research code.

### Baseline-inclusive full OHLC cost stress

The completed stress run re-executed each selected profile's OHLC path at four per-side fee/slippage levels: **5/2, 7.5/3, 10/5 and 15/10 bps**. It covered 13 independent profiles (eight M6 and five M11), seven symbols, and 4h bars. It produced 364 symbol/profile/cost rows, 52 cross-symbol profile/cost summaries and 74,779 trade-ledger records. The ledger retains 28 DATA_GAP and 44 END_OF_SAMPLE records; both are excluded from performance metrics.

The table compares the 5/2 base and 15/10 severe-cost cases. PF columns are net-bps PF and R-based PF. Net-R and the 1%-per-R fixed-initial-risk arithmetic are shown as cross-symbol trade-stream sums, not portfolio returns. Drawdown is the worst individual-symbol drawdown at 1% fixed risk.

| Independent profile | Trades base / severe | PF-bps base / severe | PF-R base / severe | Net-R base / severe | Win % base / severe | Worst symbol DD base / severe | Avg hold |
|---|---:|---:|---:|---:|---:|---:|---:|
| M6 BASELINE_H24 | 2,373 / 2,370 | 1.0948 / 0.9265 | 1.1382 / 0.9188 | +98.864 / -64.559 | 45.85 / 41.65 | -11.33 / -29.22 | 22.1h |
| M6 HOLD_48H | 2,107 / 2,101 | 1.1889 / 1.0428 | 1.2098 / 1.0283 | +166.586 / +24.376 | 45.56 / 42.79 | -11.87 / -27.10 | 38.5h |
| M6 RR3_H24 | 2,314 / 2,312 | 1.1725 / 0.9912 | 1.1823 / 0.9559 | +125.625 / -33.811 | 46.20 / 41.91 | -11.52 / -26.18 | 22.5h |
| M6 STOP2_H24 | 2,466 / 2,462 | 1.0791 / 0.9141 | 1.1273 / 0.9133 | +116.236 / -87.888 | 44.77 / 40.66 | -12.94 / -36.92 | 20.6h |
| M6 VOLUME12_H24 | 2,264 / 2,261 | 1.0990 / 0.9274 | 1.1505 / 0.9259 | +102.083 / -55.929 | 45.72 / 41.49 | -11.20 / -30.56 | 22.1h |
| M6 D100_RR3_H168 | 1,115 / 1,111 | 1.3749 / 1.2521 | 1.3985 / 1.2468 | +243.696 / +159.790 | 41.35 / 40.32 | -11.10 / -17.89 | 92.5h |
| M6 D100_STOP2_H168 | 1,447 / 1,435 | 1.1813 / 1.0835 | 1.2387 / 1.1049 | +202.833 / +94.241 | 41.53 / 40.84 | -16.79 / -23.57 | 56.5h |
| M6 D100_VOL12_RR3_H168 | 1,093 / 1,088 | 1.3777 / 1.2625 | 1.4107 / 1.2623 | +246.455 / +166.194 | 41.45 / 40.53 | -11.35 / -17.29 | 92.0h |
| M11 BASELINE_H24 | 669 / 668 | 1.2640 / 0.9361 | 1.2325 / 0.8801 | +48.510 / -29.603 | 49.03 / 42.37 | -12.40 / -20.31 | 21.6h |
| M11 OI05_PRICE025_H36 | 760 / 758 | 1.2537 / 0.9642 | 1.2375 / 0.9245 | +66.016 / -24.288 | 46.84 / 41.69 | -10.98 / -22.22 | 29.6h |
| M11 OI05_PRICE025_RR3_H48 | 721 / 720 | 1.2605 / 1.0042 | 1.2466 / 0.9703 | +75.402 / -10.334 | 44.11 / 40.97 | -14.00 / -24.36 | 38.5h |
| M11 OI05_PRICE025_RR3_H72 | 686 / 685 | 1.2389 / 1.0306 | 1.2455 / 1.0117 | +85.986 / +4.574 | 41.98 / 38.83 | -12.41 / -23.41 | 50.8h |
| M11 OI05_RR3_H48 | 681 / 680 | 1.2605 / 1.0053 | 1.2624 / 0.9842 | +75.073 / -5.139 | 44.05 / 41.03 | -15.21 / -23.06 | 38.6h |

The severe-cost aggregate alone is not a selection test. The entry-cohort results below show why the apparently strong full-period profiles remain unproven.

### Severe-cost chronological entry cohorts

Cohorts are assigned by entry timestamp, require exit before the exclusive cohort end, and exclude DATA_GAP and END_OF_SAMPLE. Development is 2021–2024; 2025 is the parameter-validation period; 2026 is retrospective audit evidence only. PF values are aggregated from the valid trade ledger, not averaged from symbol PFs.

| Profile | Dev trades / net-R | 2025 trades | 2025 PF-bps / PF-R / net-R | 2026 trades / net-R |
|---|---:|---:|---:|---:|
| M6 BASELINE_H24 | 1,584 / -23.26 | 427 | 0.863 / 0.944 / -7.89 | 359 / -33.41 |
| M6 HOLD_48H | 1,418 / +49.80 | 364 | 0.950 / 1.037 / +5.68 | 319 / -31.11 |
| M6 RR3_H24 | 1,545 / -1.32 | 417 | 0.936 / 0.988 / -1.67 | 350 / -30.81 |
| M6 STOP2_H24 | 1,643 / -39.32 | 444 | 0.892 / 0.991 / -1.66 | 375 / -46.92 |
| M6 VOLUME12_H24 | 1,514 / -22.93 | 407 | 0.868 / 0.953 / -6.29 | 340 / -26.71 |
| M6 D100_RR3_H168 | 765 / +142.70 | 189 | 0.812 / 0.935 / -7.71 | 157 / +24.80 |
| M6 D100_STOP2_H168 | 986 / +84.57 | 243 | 0.848 / 0.955 / -7.28 | 206 / +16.95 |
| M6 D100_VOL12_RR3_H168 | 749 / +143.65 | 187 | 0.822 / 0.953 / -5.47 | 152 / +28.02 |
| M11 BASELINE_H24 | 313 / -2.43 | 157 | 0.908 / 0.840 / -9.02 | 198 / -18.16 |
| M11 OI05_PRICE025_H36 | 364 / -2.39 | 170 | 1.068 / 1.054 / +3.73 | 224 / -25.63 |
| M11 OI05_PRICE025_RR3_H48 | 346 / +13.04 | 162 | 1.012 / 0.967 / -2.55 | 212 / -20.82 |
| M11 OI05_PRICE025_RR3_H72 | 333 / +30.25 | 153 | 1.046 / 1.025 / +2.23 | 199 / -27.90 |
| M11 OI05_RR3_H48 | 321 / +12.55 | 158 | 1.002 / 0.967 / -2.51 | 201 / -15.18 |

Interpretation:
- M6's 168h variants retain positive full-period severe-cost net-R because development and 2026 retrospective gains are large, but each fails the 2025 severe-cost PF-bps and PF-R validation. They are not selected.
- M6 HOLD_48H is the best of the added 48h anchors in development and 2025 net-R, but 2025 PF-bps is below 1 and its 2026 retrospective result is sharply negative.
- M11 H36 and H72 are the only listed M11 severe-cost profiles with positive 2025 net-R and both PFs above 1. Their 2026 retrospective results are strongly negative; H36 development is also below 1 PF. Neither is robust.
- M11 remains open-interest-only. No liquidation-event proxy or unlicensed liquidation feed was introduced.

### Combination and sensitivity findings

The completed M6/M11 combination artifact contains 238 symbol/profile/timeframe result rows, 43,099 trade-ledger records, 21 DATA_GAP records and 54 END_OF_SAMPLE records. The strict development-plus-2025 positive-candidate file contains **25 rows, all M6; no M11 candidate passed that per-symbol filter**. The 4h M6 HOLD_48H candidate passed on four symbols (not all seven), with 208 validation trades and +39.182 aggregate symbol-stream net-R at base costs; its 2026 retrospective sum is only +0.656R. The candidate is not approved, especially given its severe-cost deterioration above.

The completed one-factor sensitivity artifact contains 406 result rows, 228,753 ledger records, 57 DATA_GAP exits and 79 END_OF_SAMPLE records. Its 37 development-plus-2025 positive candidate rows comprise 34 M6 and three M11 candidates across timeframes; the strongest 4h M6 one-factor lead is HOLD_48H across four symbols. The M11 4h sensitivity candidate passed on only one symbol. These are screening results, not holdout validation.

### Data quality and remaining validation

The combination artifact confirms:
- BTC, ETH, BNB, ADA and DOGE have 100% 1m candle coverage.
- SOL and XRP each retain 7,200 missing minutes across two intervals (99.7653% coverage); the executor's DATA_GAP invalidation remains active.
- Funding is from official Binance Vision USD-M monthly archives; the maximum observed settlement gap is approximately eight hours and no archive months are missing in this historical dataset.
- BTC OI coverage is 99.9019%; the other six symbols are approximately 84.3%, with their available OI history beginning 1 December 2021.
- The forward November data collection remains unscored because verified official funding data was unavailable; the forward runner correctly failed closed rather than assuming zero funding.

The walk-forward jobs in run 43525482018 are still running/queued and have not produced a verified aggregate artifact. The full independent screen run 43525314007 also still awaits the DOGE symbol job and final aggregate. The 2026 results remain retrospective, not an untouched holdout. No model is approved for live trading.

PR #2 remains open and in draft. The current PR comparison contains 34 files and no M3 path; M3 remains untouched.


## Latest-head verification — 14 November 2026, 02:25 UTC

This section supersedes the older workflow-status notes above. The current branch head at this check is `3883267657897c9cded7b17b1d109a175890918b`. Comparing it with the code SHA used by the completed independent screen/sensitivity shows that the two intervening commits changed only this report; no research code changed after those seven-symbol results.

### Verified current workflows

- [Funding/accounting regression tests — run 43535470971](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43535470971): success. The actual test log confirms **77 passed in 0.93s**.
- [Baseline-inclusive full OHLC cost stress — run 43535470919](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43535470919): all seven symbol jobs and the aggregate job succeeded. [Latest aggregate artifact 14092771731](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43535470919/artifacts/14092771731). It contains 364 symbol/profile/cost rows, 74,779 ledger rows, 28 DATA_GAP and 44 END_OF_SAMPLE records; the latter two classes remain in audit ledgers and are excluded from performance statistics. The four cost scenarios and 13 independent M6/M11 profiles reproduce the baseline-inclusive results already tabulated above.
- [M6/M11 combinations and expanding walk-forward — run 43535470944](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43535470944): all seven combination symbol jobs and the combination aggregate succeeded. [Latest combination aggregate artifact 14092662142](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43535470944/artifacts/14092662142). It contains 238 result rows, 43,099 ledger rows, 21 DATA_GAP and 54 END_OF_SAMPLE records. The strict development-plus-2025 candidate file has 25 rows, all M6; no M11 profile passed that per-symbol filter. M6 HOLD_48H passed on four symbols, not seven; its 208 validation trades total +39.182R across symbol streams at base costs, while its 2026 retrospective sum is only +0.656R. Cross-symbol sums are not portfolio returns.
- [Independent full screen — run 43525314007](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314007): all seven symbol jobs and the aggregate succeeded. [Artifact 14088604613](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314007/artifacts/14088604613).
- [M6/M11 one-factor sensitivity — run 43525314000](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314000): all seven symbol jobs and the aggregate succeeded. [Artifact 14088008286](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43525314000/artifacts/14088008286).

### Expanding walk-forward: partial verified results only

The walk-forward matrix is part of run 43535470944. At this check, BTC and ETH were completed, BNB and SOL were in progress, and ADA, XRP and DOGE were queued. The aggregate walk-forward job has not completed; therefore the two-symbol results below are partial diagnostics, not a seven-symbol conclusion.

For each symbol/model/year, the runner selected a parameter profile using only that same model's prior completed training trades (net-R primary rank, R-PF tie-breaker), then started the test year flat. M6 and M11 were selected and scored independently; there is no cross-model input.

| Symbol | Model | Test year | Selected profile | Test trades | PF-bps | PF-R | Net-R | Avg hold |
|---|---|---:|---|---:|---:|---:|---:|---:|
| BTCUSDT | M6 | 2023 | D100_H168 | 34 | 0.9943 | 1.1271 | +2.330 | 77.1h |
| BTCUSDT | M6 | 2024 | D100_STOP2_H168 | 42 | 0.9822 | 1.0996 | +2.582 | 56.0h |
| BTCUSDT | M6 | 2025 | D100_RR3_H168 | 32 | 0.5619 | 0.6765 | -7.248 | 77.4h |
| BTCUSDT | M6 | 2026 retrospective | STOP2_H168 | 40 | 1.0708 | 0.9994 | -0.014 | 65.1h |
| BTCUSDT | M11 | 2023 | OI05_PRICE025_STOP25_H48 | 19 | 1.4618 | 1.9021 | +5.230 | 34.7h |
| BTCUSDT | M11 | 2024 | PRICE025_RR3_H48 | 15 | 0.7123 | 0.9529 | -0.383 | 38.7h |
| BTCUSDT | M11 | 2025 | PRICE025_RR3_H48 | 40 | 1.1597 | 1.1075 | +1.985 | 36.3h |
| BTCUSDT | M11 | 2026 retrospective | OI05_PRICE025_H36 | 44 | 0.6576 | 0.6139 | -7.754 | 30.0h |
| ETHUSDT | M6 | 2023 | RR3_H168 | 36 | 0.9060 | 0.9989 | -0.025 | 93.3h |
| ETHUSDT | M6 | 2024 | D100_VOL12_H168 | 32 | 0.9228 | 1.0021 | +0.039 | 80.9h |
| ETHUSDT | M6 | 2025 | RR3_H168 | 40 | 1.1391 | 1.3225 | +6.877 | 97.5h |
| ETHUSDT | M6 | 2026 retrospective | RR3_H168 | 31 | 1.2751 | 1.2471 | +3.799 | 107.2h |
| ETHUSDT | M11 | 2023 | OI05_PRICE025_STOP25_H48 | 21 | 1.5271 | 1.4759 | +3.370 | 36.6h |
| ETHUSDT | M11 | 2024 | RR3_H48 | 15 | 1.3184 | 1.6915 | +2.969 | 41.1h |
| ETHUSDT | M11 | 2025 | RR3_H48 | 20 | 2.1654 | 2.3815 | +10.933 | 38.4h |
| ETHUSDT | M11 | 2026 retrospective | RR3_H48 | 28 | 0.8429 | 0.9327 | -0.941 | 36.9h |

The 2025 walk-forward is encouraging for M11 on these two symbols, but BTC/ETH sample counts remain modest and the 2026 retrospective results are negative for M11 on both symbols. M6's 2025 walk-forward is split sharply between BTC and ETH. These partial results do not establish cross-symbol robustness. BTC and ETH walk-forward artifacts are [14093772947](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43535470944/artifacts/14093772947) and [14092819744](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43535470944/artifacts/14092819744).

### Current interpretation

- Baseline-inclusive full OHLC stress is now complete; no M6/M11 candidate passes the complete chronological robustness test. M6 long-horizon profiles look strong in aggregate but fail 2025 validation at severe costs. M11 H36/H72 profiles have some positive severe-cost 2025 results but turn sharply negative in 2026 retrospective evidence; the original M11 baseline also fails severe-cost validation.
- The completed combination matrix produces M6-only per-symbol candidates under the strict development-plus-2025 filter. The best H48 candidate is not consistent across all seven symbols and loses its apparent advantage in the retrospective 2026 audit.
- The walk-forward matrix remains incomplete. Its remaining five symbol jobs must finish and the aggregate artifact must be inspected before any full walk-forward conclusion.
- The November forward holdout remains unscored until official funding data is verified. No zero-funding assumption is permitted.
- No engine is approved for live trading. M3 remains untouched.

PR #2 remains open and in draft. Its changed-file list contains no M3 path.

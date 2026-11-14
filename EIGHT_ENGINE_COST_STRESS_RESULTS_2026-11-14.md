# Eight-engine cost-stress results and exit diagnosis — 14 November 2026

Verified from [GitHub Actions run 43565198508](https://github.com/cheraibarath6-ai/Backtester-Remaining-/actions/runs/43565198508), branch `research/funding-notional-audit-v2`, commit `a619c4628bd11546893b228c132bc9d92dce78f3`.

## Run integrity and data quality

- Scope: M6, M7, M8, M10, M12, M13, M14 and M15 only. No M1–M5, M9 or M11 backtests were run in this batch. No cross-model voting or combinations.
- Seven symbol jobs and the aggregate job completed successfully: 840 result rows, 438,941 trade-ledger rows and 816 symbol-stream bootstrap rows.
- The ledger retains 88 DATA_GAP and 144 END_OF_SAMPLE records for audit; both are excluded from scored metrics.
- Cost scenarios re-execute fills: BASE 5/2, MODERATE 7.5/3, HIGH 10/5 and SEVERE 15/10 bps per side (fee/slippage). Funding is separately charged using official Binance USD-M settlement data.
- MAE/MFE is measured on complete 1m paths only. Monte Carlo uses 500 contiguous-block resamples of 20 trades per symbol stream; it is diagnostic, not predictive.
- This cost-stress run is 4h. M10 and M13 use BTC as a benchmark, so they trade six altcoin streams.

| Symbol | 1m coverage | Missing minutes | Missing intervals | Funding rows | Max funding gap |
|---|---:|---:|---:|---:|---:|
| BTCUSDT | 100.0000% | 0 | 0 | 6,390 | 8.0000h |
| ETHUSDT | 100.0000% | 0 | 0 | 6,390 | 8.0000h |
| BNBUSDT | 100.0000% | 0 | 0 | 6,390 | 8.0000h |
| ADAUSDT | 100.0000% | 0 | 0 | 6,390 | 8.0000h |
| DOGEUSDT | 100.0000% | 0 | 0 | 6,390 | 8.0000h |
| SOLUSDT | 99.7653% | 7,200 | 2 | 6,465 | 8.0000h |
| XRPUSDT | 99.7653% | 7,200 | 2 | 6,390 | 8.0000h |

SOL and XRP missing intervals are handled by the gap-aware executor. Funding came from official Binance Vision monthly archives with no missing months; maximum gap is about 8 hours.

## Retention-aware comparison

Total trade-count retention and baseline-entry overlap are separate metrics. Baseline-entry overlap counts matching symbol, side and entry timestamp. New entries can increase total count without preserving the original opportunity set.

| Model | Comparison variant | Trades | Count vs baseline | Baseline-entry overlap | Net PF | R-PF | Net bps | Net-R |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| M6 | RR3_VOL12 | 2,209 | 93.1% | 89.2% | 1.179 | 1.196 | +78,280 | +128.2 |
| M7 | BB_Z_1_8 | 5,013 | 113.7% | 97.1% | 0.816 | 0.752 | -183,250 | -624.9 |
| M8 | HOLD48_VOL10 | 1,753 | 100.5% | 94.7% | 1.070 | 1.105 | +24,550 | +85.8 |
| M10 | BASELINE (no qualifying improvement) | 6,296 | 100.0% | 100.0% | 1.016 | 1.022 | +18,104 | +42.4 |
| M12 | HOLD_72H | 2,855 | 90.2% | 87.1% | 0.953 | 0.954 | -35,725 | -75.2 |
| M13 | BASELINE (no qualifying improvement) | 7,954 | 100.0% | 100.0% | 0.877 | 0.931 | -166,850 | -167.0 |
| M14 | MOMENTUM_21 | 6,774 | 101.6% | 85.9% | 1.014 | 1.045 | +16,988 | +95.9 |
| M15 | ATR_TRAIL_2_5_H48 | 1,941 | 95.1% | 94.6% | 1.060 | 1.089 | +19,802 | +65.0 |

M10 EMA_FAST_100 has 98.1% total count retention but only 74.2% baseline-entry overlap; LOOKBACK_10 has 91.0% count retention but only 35.5% overlap. Neither clears the 80% overlap gate. M13 BTC_LOOKBACK_4 has 94.7% count retention but only 32.2% baseline-entry overlap; HOLD_48H has 69.9% count retention and 58.9% overlap. Neither is a retention-compliant improvement.

M12 HOLD_72H is the least-bad retention-friendly variant but remains negative. M7 BB_Z_1_8 preserves the original entries and adds trades, but remains substantially negative. They are not profitable candidates.

## Higher-PF alternatives and their trade-retention cost

| Model | Variant | Trades | Count vs baseline | Entry overlap | Net PF | Net bps | 2025 PF / net bps | 2026 retrospective PF / net bps | Severe PF / net bps |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 | HOLD48_STOP3 | 2,036 | 85.8% | 81.4% | 1.218 | +110,628 | 1.141 / +11,911 | 0.982 / -1,110 | 1.058 / +31,990 |
| M8 | HOLD48_EXP15 | 1,467 | 84.1% | 80.1% | 1.107 | +31,541 | 1.548 / +25,147 | 0.800 / -8,047 | 0.942 / -18,957 |
| M14 | HOLD_48H | 4,502 | 67.5% | 57.4% | 1.039 | +42,636 | 0.973 / -4,268 | 1.024 / +2,637 | 0.893 / -125,353 |

M6 HOLD48_STOP3 survives even severe costs but loses 14.2% of total trades. M8 HOLD48_EXP15 survives 10/5 costs but falls below 85% trade-count retention and fails severe costs. M14 HOLD_48H loses too much of the baseline opportunity set.

## Cost stress for the retention-aware comparison variants

| Model | Variant | Cost case | Trades | Net PF | R-PF | Net bps | Net-R | Cost / gross positive move |
|---|---|---|---:|---:|---:|---:|---:|---:|
| M6 | RR3_VOL12 | BASE | 2,209 | 1.179 | 1.196 | +78,280 | +128.2 | 7.51% |
| M6 | RR3_VOL12 | MODERATE | 2,209 | 1.142 | 1.148 | +63,063 | +98.7 | 10.40% |
| M6 | RR3_VOL12 | HIGH | 2,209 | 1.096 | 1.089 | +43,671 | +61.1 | 14.11% |
| M6 | RR3_VOL12 | SEVERE | 2,207 | 0.997 | 0.967 | -1,702 | -24.2 | 22.42% |
| M7 | BB_Z_1_8 | BASE | 5,013 | 0.816 | 0.752 | -183,250 | -624.9 | 7.28% |
| M7 | BB_Z_1_8 | MODERATE | 5,013 | 0.784 | 0.715 | -218,385 | -734.4 | 11.67% |
| M7 | BB_Z_1_8 | HIGH | 5,013 | 0.746 | 0.670 | -263,566 | -871.6 | 17.36% |
| M7 | BB_Z_1_8 | SEVERE | 5,013 | 0.668 | 0.581 | -363,978 | -1,166.6 | 30.54% |
| M8 | HOLD48_VOL10 | BASE | 1,753 | 1.070 | 1.105 | +24,550 | +85.8 | 7.61% |
| M8 | HOLD48_VOL10 | MODERATE | 1,753 | 1.033 | 1.058 | +11,837 | +47.9 | 10.76% |
| M8 | HOLD48_VOL10 | HIGH | 1,752 | 0.993 | 1.009 | -2,722 | +7.4 | 14.75% |
| M8 | HOLD48_VOL10 | SEVERE | 1,750 | 0.908 | 0.910 | -35,621 | -80.7 | 23.59% |
| M10 | BASELINE | BASE | 6,296 | 1.016 | 1.022 | +18,104 | +42.4 | 9.36% |
| M10 | BASELINE | MODERATE | 6,296 | 0.978 | 0.981 | -25,449 | -50.8 | 13.16% |
| M10 | BASELINE | HIGH | 6,295 | 0.931 | 0.929 | -80,741 | -168.3 | 18.17% |
| M10 | BASELINE | SEVERE | 6,291 | 0.833 | 0.828 | -208,299 | -430.3 | 29.76% |
| M12 | HOLD_72H | BASE | 2,855 | 0.953 | 0.954 | -35,725 | -75.2 | 6.94% |
| M12 | HOLD_72H | MODERATE | 2,854 | 0.928 | 0.929 | -55,289 | -140.4 | 9.68% |
| M12 | HOLD_72H | HIGH | 2,853 | 0.897 | 0.895 | -81,004 | -220.2 | 13.25% |
| M12 | HOLD_72H | SEVERE | 2,845 | 0.835 | 0.831 | -134,995 | -383.4 | 21.30% |
| M13 | BASELINE | BASE | 7,954 | 0.877 | 0.931 | -166,850 | -167.0 | 10.28% |
| M13 | BASELINE | MODERATE | 7,954 | 0.840 | 0.862 | -221,973 | -290.2 | 14.89% |
| M13 | BASELINE | HIGH | 7,954 | 0.795 | 0.801 | -292,324 | -445.2 | 20.98% |
| M13 | BASELINE | SEVERE | 7,954 | 0.704 | 0.705 | -448,950 | -782.5 | 35.10% |
| M14 | MOMENTUM_21 | BASE | 6,774 | 1.014 | 1.045 | +16,988 | +95.9 | 8.73% |
| M14 | MOMENTUM_21 | MODERATE | 6,772 | 0.976 | 0.988 | -30,238 | -11.8 | 12.47% |
| M14 | MOMENTUM_21 | HIGH | 6,767 | 0.930 | 0.932 | -90,277 | -148.2 | 17.39% |
| M14 | MOMENTUM_21 | SEVERE | 6,759 | 0.831 | 0.832 | -230,488 | -456.1 | 28.91% |
| M15 | ATR_TRAIL_2_5_H48 | BASE | 1,941 | 1.060 | 1.089 | +19,802 | +65.0 | 8.85% |
| M15 | ATR_TRAIL_2_5_H48 | MODERATE | 1,941 | 1.018 | 1.039 | +6,211 | +28.8 | 12.56% |
| M15 | ATR_TRAIL_2_5_H48 | HIGH | 1,941 | 0.968 | 0.977 | -11,263 | -17.4 | 17.33% |
| M15 | ATR_TRAIL_2_5_H48 | SEVERE | 1,941 | 0.866 | 0.856 | -50,097 | -117.9 | 27.93% |

## Cost decomposition

The base 5/2 bps per-side schedule contributes approximately 14 bps per round trip before funding (10 bps fees + 4 bps slippage). Cost share is total fees + slippage + funding divided by the sum of positive raw directional price moves, not a percentage of net profits.

| Model / variant | Trades | Gross positive move bps | Fees bps | Slippage bps | Funding bps | Total cost bps | Cost share | Cost / trade |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 RR3_VOL12 | 2,209 | 535,964 | 22,165 | 8,866 | 9,239 | 40,270 | 7.51% | 18.23 |
| M7 BB_Z_1_8 | 5,013 | 835,265 | 50,179 | 20,071 | -9,484 | 60,766 | 7.28% | 12.12 |
| M8 HOLD48_VOL10 | 1,753 | 389,843 | 17,531 | 7,013 | 5,109 | 29,653 | 7.61% | 16.92 |
| M10 baseline | 6,296 | 1,187,900 | 63,027 | 25,210 | 21,782 | 110,019 | 9.26% | 17.47 |
| M12 HOLD_72H | 2,855 | 741,098 | 28,614 | 11,446 | 11,092 | 51,152 | 6.90% | 17.92 |
| M13 baseline | 7,954 | 1,243,508 | 79,588 | 31,835 | 14,874 | 126,297 | 10.16% | 15.88 |
| M14 MOMENTUM_21 | 6,774 | 1,299,692 | 67,832 | 27,132 | 17,394 | 112,358 | 8.65% | 16.59 |
| M15 ATR_TRAIL_2_5_H48 | 1,941 | 366,393 | 19,415 | 7,766 | 5,245 | 32,426 | 8.85% | 16.71 |

## Exit diagnosis from baseline

The weak engines are not primarily losing because of the fixed 14 bps round-trip fee/slippage schedule. Their stop-exit losses overwhelm target and time-exit gains:

| Model | Stop trades / net bps | Target trades / net bps | Time trades / net bps | Stop MAE / MFE |
|---|---:|---:|---:|---:|
| M6 | 373 / -257,228 | 186 / +239,734 | 1,814 / +63,766 | 1.29R / 0.29R |
| M7 | 2,043 / -848,188 | 556 / +288,775 | 1,811 / +368,129 | 1.67R / 0.40R |
| M8 | 389 / -168,441 | 186 / +143,925 | 1,170 / +40,047 | 1.32R / 0.33R |
| M10 | 1,151 / -664,033 | 409 / +444,942 | 4,736 / +237,195 | 1.33R / 0.27R |
| M12 | 1,027 / -447,910 | 363 / +342,327 | 1,774 / +47,534 | 1.61R / 0.49R |
| M13 | 1,377 / -752,968 | 390 / +376,207 | 6,187 / +209,911 | 1.34R / 0.25R |
| M14 | 1,235 / -713,038 | 497 / +541,540 | 4,937 / +170,485 | 1.32R / 0.32R |
| M15 | 371 / -155,064 | 113 / +92,627 | 1,556 / +42,071 | 1.40R / 0.27R |

High stop MAE and low MFE on stop exits point to entry-quality or regime-mismatch issues, especially for M7, M10, M12 and M13. More restrictive expected-move filters alone risk removing too many trades without fixing the adverse entry path.

## Chronological cohorts (entry year, trades fully exited before cohort end)

| Model | Variant | Cohort | Trades | Net PF | Net bps | Net-R |
|---|---|---|---:|---:|---:|---:|
| M6 | RR3_VOL12 | 2021–2024 development | 1,479 | 1.205 | +65,377 | +93.6 |
| M6 | RR3_VOL12 | 2025 validation | 396 | 1.159 | +11,315 | +33.2 |
| M6 | RR3_VOL12 | 2026 retrospective | 332 | 1.056 | +2,610 | +3.4 |
| M7 | BB_Z_1_8 | 2021–2024 development | 3,449 | 0.815 | -137,043 | -444.2 |
| M7 | BB_Z_1_8 | 2025 validation | 857 | 0.828 | -26,018 | -118.3 |
| M7 | BB_Z_1_8 | 2026 retrospective | 705 | 0.785 | -21,463 | -66.6 |
| M8 | HOLD48_VOL10 | 2021–2024 development | 1,145 | 1.037 | +9,134 | +46.3 |
| M8 | HOLD48_VOL10 | 2025 validation | 332 | 1.548 | +29,059 | +71.4 |
| M8 | HOLD48_VOL10 | 2026 retrospective | 269 | 0.740 | -12,522 | -28.8 |
| M10 | BASELINE | 2021–2024 development | 4,251 | 1.045 | +37,089 | +60.7 |
| M10 | BASELINE | 2025 validation | 1,167 | 0.980 | -3,634 | +28.2 |
| M10 | BASELINE | 2026 retrospective | 872 | 0.870 | -14,659 | -45.1 |
| M12 | HOLD_72H | 2021–2024 development | 1,921 | 0.976 | -13,064 | -21.1 |
| M12 | HOLD_72H | 2025 validation | 518 | 0.832 | -21,469 | -30.8 |
| M12 | HOLD_72H | 2026 retrospective | 416 | 0.984 | -1,192 | -23.4 |
| M13 | BASELINE | 2021–2024 development | 5,490 | 0.879 | -121,836 | -95.1 |
| M13 | BASELINE | 2025 validation | 1,303 | 0.898 | -20,515 | -7.4 |
| M13 | BASELINE | 2026 retrospective | 1,152 | 0.828 | -23,903 | -63.7 |
| M14 | MOMENTUM_21 | 2021–2024 development | 4,681 | 1.028 | +25,471 | +72.0 |
| M14 | MOMENTUM_21 | 2025 validation | 1,147 | 0.977 | -4,192 | +36.1 |
| M14 | MOMENTUM_21 | 2026 retrospective | 945 | 0.963 | -4,402 | -12.4 |
| M15 | ATR_TRAIL_2_5_H48 | 2021–2024 development | 1,283 | 1.117 | +25,932 | +52.9 |
| M15 | ATR_TRAIL_2_5_H48 | 2025 validation | 351 | 1.077 | +4,798 | +29.6 |
| M15 | ATR_TRAIL_2_5_H48 | 2026 retrospective | 298 | 0.740 | -12,271 | -21.4 |

Yearwise exit-year counts, net bps, net-R, PF and per-symbol raw price-point diagnostics are available in the run artifact CSVs. Crypto has no universal pip size; comparable reporting uses net bps and net-R, with raw or net-equivalent price units kept symbol-specific.

## Yearwise exit-year results (4h, BASE)

Year is assigned by UTC exit time. Counts, net bps and PF are recalculated from valid trade-ledger rows. The 2026 column is retrospective through 31 October, not a pristine holdout.

| Model | Variant | Year | Trades | Net PF | R-PF | Net bps | Net-R |
|---|---|---:|---:|---:|---:|---:|---:|
| M6 | RR3_VOL12 | 2021 | 381 | 1.278 | 1.173 | +32,622 | +19.6 |
| M6 | RR3_VOL12 | 2022 | 369 | 1.132 | 1.174 | +10,002 | +17.6 |
| M6 | RR3_VOL12 | 2023 | 344 | 1.137 | 1.293 | +8,236 | +32.5 |
| M6 | RR3_VOL12 | 2024 | 385 | 1.221 | 1.220 | +14,517 | +23.9 |
| M6 | RR3_VOL12 | 2025 | 396 | 1.159 | 1.288 | +11,315 | +33.2 |
| M6 | RR3_VOL12 | 2026 | 334 | 1.033 | 1.013 | +1,589 | +1.4 |
| M7 | BB_Z_1_8 | 2021 | 843 | 0.884 | 0.803 | -30,089 | -79.4 |
| M7 | BB_Z_1_8 | 2022 | 855 | 0.742 | 0.684 | -48,428 | -134.9 |
| M7 | BB_Z_1_8 | 2023 | 849 | 0.926 | 0.846 | -8,593 | -63.2 |
| M7 | BB_Z_1_8 | 2024 | 902 | 0.720 | 0.659 | -49,932 | -166.8 |
| M7 | BB_Z_1_8 | 2025 | 857 | 0.828 | 0.737 | -26,018 | -118.3 |
| M7 | BB_Z_1_8 | 2026 | 707 | 0.798 | 0.817 | -20,190 | -62.4 |
| M8 | HOLD48_VOL10 | 2021 | 298 | 0.978 | 1.045 | -1,940 | +6.0 |
| M8 | HOLD48_VOL10 | 2022 | 280 | 1.115 | 1.150 | +6,791 | +18.9 |
| M8 | HOLD48_VOL10 | 2023 | 288 | 0.817 | 0.900 | -9,247 | -14.4 |
| M8 | HOLD48_VOL10 | 2024 | 279 | 1.263 | 1.289 | +13,530 | +35.8 |
| M8 | HOLD48_VOL10 | 2025 | 334 | 1.536 | 1.522 | +28,641 | +70.7 |
| M8 | HOLD48_VOL10 | 2026 | 274 | 0.730 | 0.793 | -13,225 | -31.2 |
| M10 | BASELINE | 2021 | 1,139 | 1.195 | 1.257 | +57,909 | +83.3 |
| M10 | BASELINE | 2022 | 1,041 | 1.013 | 1.065 | +2,460 | +19.8 |
| M10 | BASELINE | 2023 | 1,021 | 0.859 | 0.901 | -20,657 | -32.2 |
| M10 | BASELINE | 2024 | 1,050 | 0.985 | 0.969 | -2,623 | -10.2 |
| M10 | BASELINE | 2025 | 1,169 | 0.977 | 1.078 | -4,228 | +27.3 |
| M10 | BASELINE | 2026 | 876 | 0.869 | 0.840 | -14,757 | -45.5 |
| M12 | HOLD_72H | 2021 | 500 | 0.859 | 0.779 | -31,263 | -68.5 |
| M12 | HOLD_72H | 2022 | 463 | 1.005 | 1.007 | +703 | +1.8 |
| M12 | HOLD_72H | 2023 | 451 | 1.105 | 1.212 | +8,805 | +50.4 |
| M12 | HOLD_72H | 2024 | 507 | 1.075 | 0.983 | +8,692 | -4.8 |
| M12 | HOLD_72H | 2025 | 518 | 0.832 | 0.902 | -21,469 | -30.8 |
| M12 | HOLD_72H | 2026 | 416 | 0.984 | 0.907 | -1,192 | -23.4 |
| M13 | BASELINE | 2021 | 1,473 | 0.887 | 0.982 | -43,663 | -7.6 |
| M13 | BASELINE | 2022 | 1,420 | 0.864 | 0.933 | -36,274 | -28.9 |
| M13 | BASELINE | 2023 | 1,234 | 0.795 | 0.830 | -33,572 | -67.3 |
| M13 | BASELINE | 2024 | 1,363 | 0.957 | 1.023 | -8,328 | +8.7 |
| M13 | BASELINE | 2025 | 1,309 | 0.895 | 0.978 | -21,164 | -8.7 |
| M13 | BASELINE | 2026 | 1,155 | 0.829 | 0.830 | -23,850 | -63.3 |
| M14 | MOMENTUM_21 | 2021 | 1,107 | 1.085 | 1.082 | +29,195 | +28.6 |
| M14 | MOMENTUM_21 | 2022 | 1,207 | 1.002 | 1.027 | +546 | +10.0 |
| M14 | MOMENTUM_21 | 2023 | 1,160 | 0.958 | 1.014 | -6,446 | +5.2 |
| M14 | MOMENTUM_21 | 2024 | 1,207 | 1.011 | 1.074 | +2,175 | +28.3 |
| M14 | MOMENTUM_21 | 2025 | 1,147 | 0.977 | 1.102 | -4,192 | +36.1 |
| M14 | MOMENTUM_21 | 2026 | 946 | 0.964 | 0.961 | -4,291 | -12.2 |
| M15 | ATR_TRAIL_2_5_H48 | 2021 | 313 | 1.244 | 1.300 | +18,255 | +30.2 |
| M15 | ATR_TRAIL_2_5_H48 | 2022 | 320 | 1.088 | 1.110 | +4,665 | +12.0 |
| M15 | ATR_TRAIL_2_5_H48 | 2023 | 342 | 0.890 | 0.926 | -4,965 | -9.4 |
| M15 | ATR_TRAIL_2_5_H48 | 2024 | 308 | 1.163 | 1.175 | +7,976 | +20.0 |
| M15 | ATR_TRAIL_2_5_H48 | 2025 | 353 | 1.081 | 1.215 | +5,052 | +30.2 |
| M15 | ATR_TRAIL_2_5_H48 | 2026 | 305 | 0.763 | 0.868 | -11,182 | -18.1 |

## Per-symbol 4h results at base costs

All figures are per symbol stream, not portfolio results. Exposure is total valid holding minutes divided by the 2021-01-01 to 2026-11-01 observation window. Gross points are raw directional price-point sums in each symbol's quoted units. Median net-equivalent points/trade is entry price × net return percent; it includes fees, slippage and funding and is not an exchange tick. M10/M13 omit BTC as it is the benchmark, not a traded leg.

| Model / variant | Symbol | Trades | PF | Net bps | Net-R | Win % | Avg / median hold (h) | Max DD % | Exposure % | Gross points | Median net-equiv points/trade |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M6 RR3_VOL12 | SOLUSDT | 338 | 1.227 | +16,080 | +29.6 | 51.8 | 22.82 / 24.00 | -7.29 | 15.09 | +194.323120 | +0.066262 |
| M6 RR3_VOL12 | XRPUSDT | 281 | 1.115 | +7,379 | +15.4 | 43.4 | 22.18 / 24.00 | -10.21 | 12.19 | +1.360660 | -0.005114 |
| M6 RR3_VOL12 | BNBUSDT | 320 | 1.067 | +3,777 | +11.3 | 41.6 | 22.69 / 24.00 | -12.05 | 14.20 | +322.608513 | -2.022127 |
| M6 RR3_VOL12 | DOGEUSDT | 286 | 1.518 | +39,866 | +31.3 | 45.1 | 21.96 / 24.00 | -8.36 | 12.28 | +0.665496 | -0.000775 |
| M6 RR3_VOL12 | ADAUSDT | 334 | 1.117 | +8,156 | +15.3 | 42.8 | 22.75 / 24.00 | -11.02 | 14.87 | +1.646640 | -0.003064 |
| M6 RR3_VOL12 | BTCUSDT | 330 | 1.015 | +613 | +10.2 | 48.2 | 22.57 / 24.00 | -9.33 | 14.57 | +14,096.638658 | -49.123762 |
| M6 RR3_VOL12 | ETHUSDT | 320 | 1.042 | +2,410 | +15.1 | 48.4 | 22.75 / 24.00 | -7.61 | 14.24 | +2,069.377101 | -6.992430 |
| M7 BB_Z_1_8 | SOLUSDT | 705 | 0.718 | -51,150 | -128.5 | 41.1 | 17.62 / 20.00 | -100.00 | 24.30 | -397.578141 | -0.558195 |
| M7 BB_Z_1_8 | XRPUSDT | 712 | 0.892 | -16,127 | -51.2 | 46.4 | 16.65 / 20.00 | -53.76 | 23.19 | -0.365687 | -0.006917 |
| M7 BB_Z_1_8 | BNBUSDT | 720 | 0.828 | -19,481 | -78.5 | 45.1 | 16.89 / 20.00 | -85.25 | 23.79 | -501.448745 | -2.459869 |
| M7 BB_Z_1_8 | DOGEUSDT | 738 | 0.839 | -30,151 | -96.2 | 44.0 | 15.98 / 20.00 | -99.66 | 23.08 | -0.407882 | -0.001350 |
| M7 BB_Z_1_8 | ADAUSDT | 702 | 0.839 | -24,334 | -76.0 | 45.4 | 17.30 / 24.00 | -79.75 | 23.76 | -1.559697 | -0.003658 |
| M7 BB_Z_1_8 | BTCUSDT | 729 | 0.760 | -23,011 | -116.3 | 41.8 | 17.05 / 20.00 | -100.00 | 24.32 | -44,306.881664 | -330.347329 |
| M7 BB_Z_1_8 | ETHUSDT | 707 | 0.836 | -18,997 | -78.2 | 46.1 | 17.18 / 20.00 | -85.68 | 23.76 | -2,929.570785 | -13.745187 |
| M8 HOLD48_VOL10 | SOLUSDT | 252 | 1.300 | +17,410 | +42.8 | 49.6 | 36.98 / 48.00 | -10.52 | 18.23 | +342.566980 | -0.037565 |
| M8 HOLD48_VOL10 | XRPUSDT | 248 | 0.918 | -4,442 | -3.5 | 39.9 | 33.42 / 40.00 | -22.53 | 16.21 | +0.941857 | -0.010305 |
| M8 HOLD48_VOL10 | BNBUSDT | 239 | 0.917 | -3,490 | -7.9 | 42.3 | 34.39 / 40.00 | -19.36 | 16.08 | -20.218560 | -4.155921 |
| M8 HOLD48_VOL10 | DOGEUSDT | 239 | 1.315 | +16,599 | +37.9 | 46.4 | 32.90 / 36.00 | -6.94 | 15.38 | +0.518579 | -0.000680 |
| M8 HOLD48_VOL10 | ADAUSDT | 238 | 1.054 | +2,895 | +13.6 | 45.0 | 36.37 / 44.00 | -14.64 | 16.93 | +0.855696 | -0.003501 |
| M8 HOLD48_VOL10 | BTCUSDT | 270 | 0.912 | -3,452 | +1.6 | 43.0 | 34.10 / 40.00 | -18.52 | 18.01 | +12,238.091897 | -366.728279 |
| M8 HOLD48_VOL10 | ETHUSDT | 267 | 0.981 | -969 | +1.2 | 39.7 | 34.61 / 40.00 | -12.62 | 18.08 | +2,419.168114 | -29.295559 |
| M10 BASELINE | SOLUSDT | 1,108 | 1.028 | +6,529 | +12.7 | 47.2 | 22.01 / 24.00 | -24.36 | 47.71 | +117.956967 | -0.160791 |
| M10 BASELINE | XRPUSDT | 995 | 0.975 | -4,406 | -6.5 | 44.6 | 21.87 / 24.00 | -38.96 | 42.57 | +2.170026 | -0.002327 |
| M10 BASELINE | BNBUSDT | 924 | 1.100 | +13,103 | +20.6 | 48.3 | 21.44 / 24.00 | -10.62 | 38.76 | +714.162620 | -0.284674 |
| M10 BASELINE | DOGEUSDT | 1,156 | 1.061 | +14,127 | +13.2 | 44.2 | 21.82 / 24.00 | -20.81 | 49.33 | +0.286362 | -0.000435 |
| M10 BASELINE | ADAUSDT | 1,171 | 0.995 | -1,084 | +9.2 | 46.1 | 22.19 / 24.00 | -13.12 | 50.82 | +1.041334 | -0.001170 |
| M10 BASELINE | ETHUSDT | 942 | 0.929 | -10,165 | -6.9 | 45.9 | 21.93 / 24.00 | -27.92 | 40.41 | +1,900.433587 | -5.307432 |
| M12 HOLD_72H | SOLUSDT | 421 | 0.873 | -17,962 | -8.7 | 37.3 | 40.31 / 36.00 | -29.53 | 33.20 | -193.997270 | -1.102404 |
| M12 HOLD_72H | XRPUSDT | 375 | 1.035 | +3,624 | -10.1 | 37.1 | 36.75 / 28.00 | -30.87 | 26.96 | +1.725182 | -0.013450 |
| M12 HOLD_72H | BNBUSDT | 411 | 1.027 | +2,442 | -11.2 | 38.7 | 34.20 / 24.00 | -27.96 | 27.50 | +576.236991 | -5.210348 |
| M12 HOLD_72H | DOGEUSDT | 414 | 0.944 | -7,778 | -37.9 | 35.0 | 36.11 / 28.00 | -50.19 | 29.24 | -0.290213 | -0.002381 |
| M12 HOLD_72H | ADAUSDT | 421 | 0.941 | -7,358 | -21.7 | 37.8 | 38.17 / 32.00 | -29.28 | 31.43 | -1.712350 | -0.007847 |
| M12 HOLD_72H | BTCUSDT | 409 | 0.928 | -4,897 | -5.5 | 40.3 | 39.25 / 32.00 | -18.89 | 31.40 | +2,118.042240 | -405.852337 |
| M12 HOLD_72H | ETHUSDT | 404 | 0.959 | -3,795 | +19.8 | 39.1 | 40.22 / 36.00 | -18.61 | 31.78 | +1,954.722492 | -28.931417 |
| M13 BASELINE | SOLUSDT | 1,300 | 0.858 | -39,756 | -28.0 | 45.9 | 22.14 / 24.00 | -36.49 | 56.30 | -115.629303 | -0.203786 |
| M13 BASELINE | XRPUSDT | 1,291 | 0.922 | -15,857 | -19.0 | 43.1 | 21.91 / 24.00 | -32.30 | 55.34 | -0.343389 | -0.003115 |
| M13 BASELINE | BNBUSDT | 1,387 | 0.811 | -35,591 | -51.4 | 43.0 | 21.97 / 24.00 | -58.32 | 59.62 | -222.271797 | -1.509398 |
| M13 BASELINE | DOGEUSDT | 1,292 | 0.824 | -44,181 | -45.3 | 42.7 | 22.23 / 24.00 | -48.55 | 56.19 | -0.169907 | -0.000493 |
| M13 BASELINE | ADAUSDT | 1,303 | 0.928 | -16,752 | -2.3 | 47.0 | 22.28 / 24.00 | -22.12 | 56.79 | -0.814509 | -0.001084 |
| M13 BASELINE | ETHUSDT | 1,381 | 0.924 | -14,714 | -21.0 | 45.0 | 21.96 / 24.00 | -28.50 | 59.33 | +2,066.307625 | -6.038206 |
| M14 MOMENTUM_21 | SOLUSDT | 978 | 1.071 | +14,798 | +44.2 | 47.5 | 22.13 / 24.00 | -11.08 | 42.35 | +237.201791 | -0.081332 |
| M14 MOMENTUM_21 | XRPUSDT | 961 | 0.966 | -6,726 | -6.6 | 41.5 | 21.54 / 24.00 | -36.18 | 40.49 | +0.797411 | -0.005140 |
| M14 MOMENTUM_21 | BNBUSDT | 936 | 0.902 | -15,113 | -27.9 | 42.5 | 21.52 / 24.00 | -41.90 | 39.40 | -150.536406 | -2.067729 |
| M14 MOMENTUM_21 | DOGEUSDT | 1,001 | 1.111 | +25,605 | +44.4 | 44.9 | 21.44 / 24.00 | -15.01 | 41.98 | +0.438364 | -0.000505 |
| M14 MOMENTUM_21 | ADAUSDT | 917 | 1.002 | +330 | +29.5 | 48.5 | 22.06 / 24.00 | -10.11 | 39.57 | +0.559644 | -0.000473 |
| M14 MOMENTUM_21 | BTCUSDT | 1,016 | 0.950 | -5,588 | -7.1 | 44.6 | 21.74 / 24.00 | -17.94 | 43.22 | +54,686.761425 | -107.227630 |
| M14 MOMENTUM_21 | ETHUSDT | 965 | 1.025 | +3,682 | +19.5 | 46.2 | 22.07 / 24.00 | -17.13 | 41.66 | +5,727.849752 | -6.527951 |
| M15 ATR_TRAIL_2_5_H48 | SOLUSDT | 267 | 1.267 | +14,380 | +28.9 | 49.1 | 37.75 / 48.00 | -12.29 | 19.72 | +167.191922 | -0.034118 |
| M15 ATR_TRAIL_2_5_H48 | XRPUSDT | 287 | 0.907 | -4,875 | -10.4 | 36.6 | 36.72 / 48.00 | -19.64 | 20.62 | +0.238335 | -0.007887 |
| M15 ATR_TRAIL_2_5_H48 | BNBUSDT | 266 | 1.068 | +2,608 | +13.2 | 44.4 | 37.49 / 48.00 | -14.03 | 19.51 | +177.795838 | -1.875899 |
| M15 ATR_TRAIL_2_5_H48 | DOGEUSDT | 267 | 1.061 | +3,121 | +4.1 | 40.5 | 36.13 / 44.00 | -20.02 | 18.87 | +0.240696 | -0.000773 |
| M15 ATR_TRAIL_2_5_H48 | ADAUSDT | 267 | 1.135 | +7,225 | +16.1 | 45.3 | 37.36 / 48.00 | -12.32 | 19.51 | +1.533911 | -0.003067 |
| M15 ATR_TRAIL_2_5_H48 | BTCUSDT | 295 | 0.828 | -6,468 | -2.2 | 40.0 | 36.50 / 48.00 | -10.77 | 21.06 | -16,789.405491 | -249.087050 |
| M15 ATR_TRAIL_2_5_H48 | ETHUSDT | 292 | 1.085 | +3,811 | +15.2 | 43.5 | 37.79 / 48.00 | -10.19 | 21.59 | +3,044.882716 | -13.069043 |

## Monte Carlo block-bootstrap diagnostic

| Model | Variant | Symbol streams | Median P(net-R > 0) | Worst symbol P(net-R > 0) | Median p05 net-R | Median p50 net-R |
|---|---|---:|---:|---:|---:|---:|
| M6 | RR3_VOL12 | 7 | 88.0% | 71.2% | -7.0 | +16.8 |
| M7 | BB_Z_1_8 | 7 | 0.0% | 0.0% | -128.4 | -85.6 |
| M8 | HOLD48_VOL10 | 7 | 69.0% | 18.2% | -24.5 | +11.6 |
| M10 | BASELINE | 6 | 59.5% | 29.0% | -31.6 | +7.2 |
| M12 | HOLD_72H | 7 | 11.2% | 6.2% | -52.7 | -22.3 |
| M13 | BASELINE | 6 | 0.0% | 0.0% | -71.2 | -46.5 |
| M14 | MOMENTUM_21 | 7 | 85.2% | 54.6% | -13.7 | +26.0 |
| M15 | ATR_TRAIL_2_5_H48 | 7 | 72.6% | 36.0% | -16.8 | +12.7 |

These are distributions across separate symbol streams, not a portfolio probability.

## Decisions and next work

- M6 RR3_VOL12 is the strongest balanced candidate so far: 89.2% baseline-entry overlap, 93.1% total count retention, and remains positive through 10/5 bps per side. It is approximately breakeven at 15/10. HOLD48_STOP3 is more severe-cost resistant but gives up more trades.
- M8 HOLD48_VOL10 retains 94.7% of baseline entry timestamps and is positive through moderate costs; it turns slightly negative at 10/5. HOLD48_EXP15 is more robust at 10/5 but has lower trade retention and fails 15/10. 2026 is negative for both.
- M14 MOMENTUM_21 is mildly positive at base costs but fails moderate costs and has negative 2025/2026 net bps.
- M15 ATR_TRAIL_2_5_H48 improves base and 2025 but fails high costs and 2026 retrospective.
- M7, M10, M12 and M13 need entry/regime diagnosis before further threshold tightening. No model is approved for live trading.
- The active data terms remain non-commercial research/personal non-production backtesting only. See [RESEARCH_SOURCES.md](https://github.com/cheraibarath6-ai/Backtester-Remaining-/blob/research/funding-notional-audit-v2/RESEARCH_SOURCES.md). These historical results do not grant live/commercial execution rights.

Next: run the new eight-engine retention-gated walk-forward diagnostic at 1h and 4h. Its candidate selector requires at least 80% baseline-entry overlap and 80% total trade-count retention for non-baseline variants. Since the profiles were identified after broad historical sweeps, those walk-forward results will be retrospective diagnostics; preserve a separate untouched forward holdout for new data after 2026-11-01.

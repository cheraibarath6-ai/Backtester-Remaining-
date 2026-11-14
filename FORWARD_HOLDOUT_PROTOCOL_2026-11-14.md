# Frozen eight-engine forward holdout protocol — 14 November 2026

## Purpose

Reserve a genuinely forward evaluation window beginning **2026-11-01 00:00 UTC**. The holdout is not used to select parameters, adjust filters, change stops/targets or choose between variants. The same frozen definitions are scored on each monthly cumulative run.

## Frozen variants

| Model | Baseline control | Frozen candidate | Reason for candidate freeze |
|---|---|---|---|
| M6 | BASELINE | RR3_VOL12 | Best balance of development/2025 results and retained trade opportunities |
| M7 | BASELINE | — | No candidate demonstrated a positive after-cost edge; baseline retained as diagnostic control |
| M8 | BASELINE | HOLD48_VOL10 | Positive development and 2025 validation with 94.7% baseline-entry overlap |
| M10 | BASELINE | EMA_FAST_100 | Positive 2025 validation and 98.1% total count retention; entry overlap is lower (74.2%), so treat as a changed entry set, not a simple filter |
| M12 | BASELINE | — | No candidate passed both development and validation; keep baseline diagnostic only |
| M13 | BASELINE | BTC_LOOKBACK_4 | Better development and 2025 results than baseline; only 32.2% baseline-entry overlap, so treat as a distinct signal definition |
| M14 | BASELINE | MOMENTUM_21 | Better development and 2025 validation than baseline, with 85.9% baseline-entry overlap |
| M15 | BASELINE | ATR_TRAIL_2_5_H48 | Better development and 2025 validation, with 94.6% baseline-entry overlap |

These are frozen test definitions, not live approvals. M7 and M12 have no candidate frozen because their after-cost edge remains negative. M10 and M13 candidates materially change the entry set; their holdout comparisons must not be described as trade-preserving filters.

## Data protocol

- History for indicators: official Binance Vision USD-M monthly 1m klines from 2021-01-01 through 2026-10-31.
- Holdout tail: official Binance Vision USD-M daily 1m archives from 2026-11-01 through the last fully completed UTC day, with a verified SHA256 companion file required for every day.
- Funding: official Binance Vision monthly USD-M funding archives or the official Binance Futures funding API. Reject third-party fallback, zero-funding assumptions, empty holdout funding or a maximum settlement gap over 8.5 hours.
- Score only after at least 30 complete UTC days are available. The first intended monthly score is after November 2026 is complete.
- Current UTC day is excluded by the exclusive end date.
- Require at least 99.5% holdout candle coverage and complete checksum-verified daily archives. Keep DATA_GAP and END_OF_SAMPLE rows in the audit ledger, but exclude them from performance metrics.
- Entry signals use completed bars and next-bar execution. Base execution costs are 5 bps fee and 2 bps slippage per side. Do not modify these frozen costs during the holdout series.

## Evaluation

For each symbol, timeframe, model, baseline and frozen candidate, retain trade count, net bps, net-R, net PF, R-PF, win rate, average/median holding time, drawdown, exposure, fees, slippage, funding, cost share and per-trade ledger. Report baseline-to-candidate deltas per symbol. Do not sum symbols into a portfolio return or combine engines.

The initial window is likely to have a small trade sample. Do not claim statistical significance or promote a model on the first month alone. Continue the same frozen definitions as the window grows. Any future parameter changes must be treated as a new research version with a separate later holdout, not retroactively applied to this holdout.

## Workflow status

The workflow definition is committed on the research branch as .github/workflows/eight-engine-forward-holdout.yml. GitHub scheduled workflows run only from the repository's default branch, so this scheduled job will not execute while PR #2 remains an unmerged draft. The workflow is ready for activation after an explicit merge decision; no merge was made. Manual dispatch also requires the workflow to be available from the default branch.

## Licensing

Historical Binance Vision data terms are restricted to non-commercial research/personal non-production backtesting. This protocol does not authorize live or commercial automated execution.

# Public Strategy and Data Sources

This document records public research sources inspected for the independent-engine programme. The strategies in `crypto_research/independent_models.py` are independently implemented from documented trading concepts. No source files were copied verbatim into this repository.

## Strategy references

| Candidate | Public source | Licence/status | Use in this project |
|---|---|---|---|
| M6 Donchian breakout | [crypto-backtest-engine / DonchianTrendFollow](https://github.com/vivchar2002-cyber/crypto-backtest-engine/blob/main/strategies/trend_follow.py) | MIT | Inspected actual H1 Donchian + H4 bias + ATR trailing-stop implementation. Our M6 baseline remains independent; a separate H1/H4 trailing-stop variant is queued for testing. The source README publishes no independently verifiable performance result. |
| M7 Bollinger mean reversion | [Freqtrade community strategy collection](https://github.com/davidzr/freqtrade-strategies) | GPL-3.0; repository archived | Indicator-family reference only; no source code copied |
| M8 Volatility expansion | [Freqtrade community strategy collection](https://github.com/davidzr/freqtrade-strategies) | GPL-3.0; repository archived | Squeeze/expansion concept; independent implementation |
| M9 VWAP and volume imbalance | [BB_RPB_TSL_RNG_VWAP strategy](https://github.com/davidzr/freqtrade-strategies/tree/main/strategies/BB_RPB_TSL_RNG_VWAP) | GPL-3.0; repository archived | VWAP and volume-flow idea; independent simplified implementation, no source code copied |
| M10 Relative momentum | [Systematic Crypto Research](https://github.com/PeterLP123/systematic-crypto-research) | MIT | Relative-strength and cost-aware validation research reference |
| M11 Open-interest pressure | [Binance USD-M daily metrics schema reference](https://github.com/BobbyAxerol/trading-historical-data/blob/main/BINANCE_FUTURES_METRICS_5M.md) | Repository-specific terms; data remains Binance Vision data | Field semantics and archive structure only |
| M12 Regime-specific standalone strategy | [Systematic Crypto Research](https://github.com/PeterLP123/systematic-crypto-research) | MIT | Walk-forward and regime research reference; this project uses one standalone regime-switching rule |
| M13 BTC lead-lag | [Systematic Crypto Research](https://github.com/PeterLP123/systematic-crypto-research) | MIT | Relative-return and BTC/altcoin relationship research reference |
| M14 ADX momentum | [Official Freqtrade ADXMomentum](https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/berlinguyinca/ADXMomentum.py) | GPL-3.0 | Actual long-only 1h rule inspected. Our implementation is independently written and symmetric long/short; no source code copied. |
| M15 Awesome MACD | [Official Freqtrade AwesomeMacd](https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/berlinguyinca/AwesomeMacd.py) | GPL-3.0 | Actual long-only 1h rule inspected. Our implementation is independently written and symmetric long/short; no source code copied. |

### Existing research evidence (not our backtest)

[PeterLP123/systematic-crypto-research](https://github.com/PeterLP123/systematic-crypto-research) is an MIT-licensed research project with a reproducible walk-forward pipeline. Its README reports a trend-following result of +9.54% over a 263-day continuous post-selection window (Sharpe 1.251, maximum drawdown -4.30%) and a BTC-dominance mean-reversion result of -6.96% (Sharpe -1.521, only seven entries). Those are the authors' reported results on their own daily spot/basket methodology, not evidence that the corresponding strategy will work on our intraday USD-M perpetual tests.

[Freqtrade community strategies](https://github.com/davidzr/freqtrade-strategies) is archived and GPL-3.0 licensed. It contains examples including ADXMomentum, AwesomeMacd and VWAP-related strategies. The repository's existence, popularity, or author backtests are not treated as proof of positive expectancy. GPL-3.0 source code is not copied into this project; strategy ideas are reimplemented independently.

## Data sources and restrictions

- [Binance Public Data repository](https://github.com/binance/binance-public-data) documents the public archive structure and checksum files.
- USD-M perpetual 1-minute klines: `https://data.binance.vision/data/futures/um/monthly/klines/{SYMBOL}/1m/{SYMBOL}-1m-{YYYY-MM}.zip`.
- USD-M perpetual funding: `https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{YYYY-MM}.zip`.
- USD-M perpetual metrics (5-minute open interest and positioning fields): `https://data.binance.vision/data/futures/um/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{YYYY-MM-DD}.zip`.
- Binance Vision ZIP checksum companions are checked when available. Data parsers detect millisecond/microsecond/nanosecond timestamp magnitude and retain UTC timestamps.

**Important licence restriction:** Binance Vision Dataset Terms v1.0 (last updated 26 August 2026; see the official [terms document](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md)) grant datasets under CC BY-NC-SA 4.0, except where specifically designated otherwise. They limit use to non-commercial research, education and personal non-production historical backtesting; they prohibit use for live proprietary trading execution, commercial automated order generation, or compensated signal distribution. Any redistribution of derived work must follow the stated attribution and ShareAlike conditions. The current programme is historical research only. Do not treat these data as licensed for a future live/commercial execution system without obtaining separate rights and checking the then-current terms.

## Research integrity

- Publicly reported PF/return claims are leads only; they are not imported as our results.
- Each candidate is tested as a separate strategy. There is no ensemble, signal voting or cross-model confirmation.
- M3 is outside this repository and is not modified.
- All results must be net of fees, slippage and perpetual funding cashflows.
- Funding cashflows apply to every open USD-M perpetual position at a settlement timestamp. Funding is an M5 signal feature only for M5; it is not an M5-only holding cost.
- A strategy is not selected from an in-sample PF ranking. Chronological validation and holdout evidence are required.


## Public candidates screened out or treated cautiously

- [MultiMa](https://github.com/davidzr/freqtrade-strategies/blob/main/strategies/MultiMa/MultiMa.py) reports only 18 trades in its embedded 2,000-candle optimisation note. It may be worth a later low-frequency experiment, but it does not meet our preferred trade-count evidence threshold as published.
- [UniversalMACD](https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/UniversalMACD.py) embeds a 40-trade long-only spot result. That is too small to substantiate the reported high win rate; the code's own comments also show a 5-minute spot setup. It is not included in the first-pass engine set because M15 already tests an independent MACD/Awesome Oscillator family.
- [SupertrendStrategy](https://github.com/davidzr/freqtrade-strategies/blob/main/strategies/SupertrendStrategy/SupertrendStrategy.py) embeds a 202-trade ADA/USDT spot result from 2018-04-18 to 2021-08-18, with a reported 59.98% drawdown. It is a potential future candidate, but the single-pair historical result and drawdown do not establish a robust futures edge.
- The [SuperTrend strategy](https://github.com/davidzr/freqtrade-strategies/blob/main/strategies/SuperTrend/SuperTrend.py) explicitly cautions that its custom indicator implementation is not validated against the original paper or another trusted reference. Any later Supertrend test must independently validate the indicator calculation first.

These public embedded results are not independently verified and are not used as our performance evidence. The first-pass set favours strategy families that can be implemented transparently and tested with the same futures execution model.


## Additional independent research framework inspected

[Baruna240/Momo-Quant-Lab](https://github.com/Baruna240/Momo-Quant-Lab) is MIT-licensed and contains a reproducible paper-trading lab with separate spot/futures strategy tests, cost modelling and time-ordered validation. Its published findings cover only about 117–133 days for the altcoin/futures comparison: 4h swing was +1.1% on spot, while breakout, RSI dip and EMA trend were negative; the listed perpetual strategies were also negative (futures AI -18.8%, swing long/short -25.7%, short RSI -29.0%, short breakdown -61.5%). These are the repository author's simulator results, not our independently verified results, and the short sample is not enough to establish a durable edge.

Its research pipeline is a useful validation reference: time-ordered walk-forward splits, 2x cost stress, one-bar-late entry, removing the top 5% of trades, Monte Carlo drawdown and a significance threshold that rises with the number of configurations tried. We will incorporate these robustness checks after the first independent screen; we will not treat its reported spot/futures performance as proof of an engine.


## Additional public repositories inspected (2026-11-13)

- [vivchar2002-cyber/crypto-backtest-engine](https://github.com/vivchar2002-cyber/crypto-backtest-engine) — MIT-licensed. Its actual `DonchianTrendFollow` source uses an H1 prior-channel breakout, H4 directional bias, ATR-based initial stop and chandelier trailing exit. This is a useful M6 variant to test independently. The README describes it as an example and does not provide a verified performance record; no result is imported.
- [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies) — GPL-3.0. The current official repository contains `ADXMomentum`, `AwesomeMacd`, and `ReinforcedAverageStrategy`. The latter's own source docstring says it does not perform particularly well and is a proof of concept, despite a third-party web article attributing a strong result to it. We therefore exclude that headline claim until independently reproduced. GPL source is inspected for rule descriptions only; no source is copied.
- [abailey81/Crypto-Statistical-Arbitrage](https://github.com/abailey81/Crypto-Statistical-Arbitrage) — MIT. Its README claims 44,652 BTC futures-curve trades, PF 28.53, and 203.70% return over a walk-forward test. However, its Phase 3 orchestrator allocates capital across four separate strategies (calendar spreads, cross-venue, synthetic futures, and roll optimization) across multiple venues. That headline is therefore an aggregate, not a result for one independent strategy. It is a future research lead for a standalone funding-carry/term-structure candidate only after each component is isolated and historical multi-venue data and costs are verified. No claimed metrics are imported into this project.


## Historical liquidation-data audit (2026-11-13)

- Binance's official USD-M `forceOrder` stream is a live WebSocket snapshot feed. Binance states that at most the latest liquidation order per symbol in each 1,000 ms window is published; it is not a complete event tape. Binance's 2021 announcement also says the historical REST liquidation enquiry endpoint was discontinued. Official Binance public archives therefore do not provide a complete historical liquidation series for the 2021-2026 backtest.
- [CryptoHFTData Binance liquidation archive](https://www.cryptohftdata.com/datasets/binance-liquidation-data) starts on 2025-06-28 and is hourly Parquet. Its own documentation warns that the exchange stream is sampled/lower-bound data; free access is rate-limited and does not cover the full research period.
- [MoonDev Binance liquidation archive](https://moondev.com/docs) documents 35M+ events from 2024-06-04 to 2026-04-23, plus a live segment from 2026-07-18 onward. It has a permanent 2026-04-23 to 2026-07-18 gap, and bulk historical access requires a Quant Elite API key. It cannot supply a continuous free 2021-2026 series.
- [CoinGlass Pair Liquidation History](https://docs.coinglass.com/reference/liquidation-history) exposes long/short USD liquidation aggregates through an API; the Hobbyist plan is limited to intervals of 4h or longer, and access requires an API key. Historical start/coverage must be verified from actual responses before use.
- Decision: do not fabricate liquidation events from price/OI or treat sampled forceOrder messages as a complete tape. M11 remains explicitly OI-pressure-only until a licensed, coverage-audited liquidation source is available. A later 4h liquidation-aggregate variant can be tested separately if a permitted API source is obtained.





### Additional strategy and engine references verified in this audit branch

| Candidate / role | Repository and inspected source | Licence status | Decision |
|---|---|---|---|
| M6 Donchian | [zekiayberk/Donchian-ML-Strategy](https://github.com/zekiayberk/Donchian-ML-Strategy), especially `indicators/donchian.py`, `docs/strategy.md`, and `run_wfo.py` | MIT; LICENSE file verified | Adds a concrete Donchian + ATR trailing-stop + walk-forward reference. Its README describes optional ML filtering; that filter will remain off in the standalone comparison unless tested as a separate model. |
| M7 mean reversion | [PatrickSebastine/mean-reversion-trading-bot](https://github.com/PatrickSebastine/mean-reversion-trading-bot), `strategies.py` and README | MIT; LICENSE file verified | Concrete Bollinger/RSI mean-reversion reference with long/short simulation and fees/slippage claims. No robust independent performance evidence was imported. |
| Backtest accounting reference | [zionhann/open-binancian-futures](https://github.com/zionhann/open-binancian-futures), `open_binancian_futures/backtesting.py` | MIT; LICENSE file verified | Inspected as a Binance USD-M framework with explicit cost-model abstraction and deterministic OHLC execution. Used as a design reference only; no code copied. |
| M13 BTC-to-altcoin lead-lag | [mamipour/lead-lag-trader](https://github.com/mamipour/lead-lag-trader) | Public repository; no LICENSE file found in the checked root path | README describes BTC impulse / altcoin delayed-response logic, regime filters and short holding windows. Treat as idea-only; do not copy code or assume reuse rights without an explicit licence. Its claimed trading behavior is not independently validated here. |

The above repositories are implementation references, not proof of a profitable edge. Their README claims and configuration examples are not substituted for the Binance USD-M backtests in this repository.


## Additional lead-lag and unlicensed-source audit (2026-11-13)

- [nateemma/strategies](https://github.com/nateemma/strategies) — GPL-3.0; the repository's `btc_corr/FINAL_REPORT.md` was inspected as a research result, not copied code. It studies Binance.US 1h data for BTC plus 12 alts from 2024-04 through 2026-07, with a 4h cross-check. Its causal rolling analysis reports lag-0 correlation as the peak for all pairs and collapse toward zero at lag 1h; its own conclusion is that BTC co-moves with these alts rather than leading them at hourly resolution. It reports a small lift from BTC volatility/trend regime features, not from lagged BTC returns. This is negative prior evidence for M13, not our Binance USD-M result. Keep M13 as a falsifiable standalone test, but do not infer that a lead-lag edge exists.
- [mamipour/lead-lag-trader](https://github.com/mamipour/lead-lag-trader) — no LICENSE file found at the checked repository root. The README describes BTC impulse / altcoin delayed-response logic. Treat it as idea-only; no source code is reused.
- [DTennant/crypto-swing-backtest](https://github.com/DTennant/crypto-swing-backtest), [crazystorm720/algo_trading](https://github.com/crazystorm720/algo_trading), and [flatmoonsociety/fmzquant-strategies-english](https://github.com/flatmoonsociety/fmzquant-strategies-english) — public repositories with relevant Bollinger/RSI or squeeze examples, but no repository-level licence was found in the inspected metadata. They are idea-only and are not sources for copied code.
- [freqtrade/freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies) — official GPL-3.0 repository. Its current tree includes `user_data/strategies/berlinguyinca/ADXMomentum.py` and `AwesomeMacd.py`; both were inspected as rule references. GPL source is not copied into this project.
- GitHub searches for "open interest taker ratio crypto strategy" and "regime switching crypto trading strategy" did not identify a clearly licensed, reproducible standalone USD-M futures implementation with a credible historical record. Unlicensed OI/regime examples remain idea-only; our M11/M12 implementations are independently authored and tested in this repository.


## M13 falsification evidence — BTC/altcoin lead-lag

- [nateemma/strategies — btc_corr/FINAL_REPORT.md](https://github.com/nateemma/strategies/blob/master/btc_corr/FINAL_REPORT.md) is a public BTC/altcoin correlation study. The repository is treated as GPL-3.0 research material for this programme; no code or report text is copied into the implementation.
- The study uses Binance.US 1h data for BTC plus 12 alts over roughly 2024-04 to 2026-07, with a 4h cross-check. It reports lag-0 correlation as the peak for all pairs and both timeframes, with the lag-1h correlation collapsing to approximately zero (examples: SOL 0.747 to -0.016; ETH 0.791 to 0.004). Its conclusion is that BTC co-moves with alts rather than leading them at hourly resolution.
- It reports a small BTC-feature predictive lift through volatility/trend-regime features, not lagged BTC returns. That is not evidence for the current M13 return-impulse rule.
- Use: falsification prior only. M13 remains an independently tested, non-overlapping BTC-impulse/alt-response hypothesis; it is not assumed to work, and the external study's results are not imported as our performance.


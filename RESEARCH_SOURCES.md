# Public Strategy and Data Sources

This document records public research sources inspected for the independent-engine programme. The strategies in `crypto_research/independent_models.py` are independently implemented from documented trading concepts. No source files were copied verbatim into this repository.

## Strategy references

| Candidate | Public source | Licence/status | Use in this project |
|---|---|---|---|
| M6 Donchian breakout | [Systematic trend-following literature and channel-breakout implementations](https://github.com/search?q=crypto+Donchian+breakout&type=repositories) | Each repository has its own terms | Independent 55-bar prior-channel breakout baseline; not copied from a specific repository |
| M7 Bollinger mean reversion | [Freqtrade community strategy collection](https://github.com/davidzr/freqtrade-strategies) | GPL-3.0; repository archived | Indicator-family reference only; no source code copied |
| M8 Volatility expansion | [Freqtrade community strategy collection](https://github.com/davidzr/freqtrade-strategies) | GPL-3.0; repository archived | Squeeze/expansion concept; independent implementation |
| M9 VWAP and volume imbalance | [BB_RPB_TSL_RNG_VWAP strategy](https://github.com/davidzr/freqtrade-strategies/tree/main/strategies/BB_RPB_TSL_RNG_VWAP) | GPL-3.0; repository archived | VWAP and volume-flow idea; independent simplified implementation, no source code copied |
| M10 Relative momentum | [Systematic Crypto Research](https://github.com/PeterLP123/systematic-crypto-research) | MIT | Relative-strength and cost-aware validation research reference |
| M11 Open-interest pressure | [Binance USD-M daily metrics schema reference](https://github.com/BobbyAxerol/trading-historical-data/blob/main/BINANCE_FUTURES_METRICS_5M.md) | Repository-specific terms; data remains Binance Vision data | Field semantics and archive structure only |
| M12 Regime-specific standalone strategy | [Systematic Crypto Research](https://github.com/PeterLP123/systematic-crypto-research) | MIT | Walk-forward and regime research reference; this project uses one standalone regime-switching rule |
| M13 BTC lead-lag | [Systematic Crypto Research](https://github.com/PeterLP123/systematic-crypto-research) | MIT | Relative-return and BTC/altcoin relationship research reference |
| M14 ADX momentum | [ADXMomentum strategy](https://github.com/davidzr/freqtrade-strategies/blob/main/strategies/ADXMomentum/ADXMomentum.py) | GPL-3.0; repository archived | Published rule description inspected; independent formula implementation, no source code copied |
| M15 Awesome MACD | [AwesomeMacd strategy](https://github.com/davidzr/freqtrade-strategies/blob/main/strategies/AwesomeMacd/AwesomeMacd.py) | GPL-3.0; repository archived | Published rule description inspected; independent formula implementation, no source code copied |

### Existing research evidence (not our backtest)

[PeterLP123/systematic-crypto-research](https://github.com/PeterLP123/systematic-crypto-research) is an MIT-licensed research project with a reproducible walk-forward pipeline. Its README reports a trend-following result of +9.54% over a 263-day continuous post-selection window (Sharpe 1.251, maximum drawdown -4.30%) and a BTC-dominance mean-reversion result of -6.96% (Sharpe -1.521, only seven entries). Those are the authors' reported results on their own daily spot/basket methodology, not evidence that the corresponding strategy will work on our intraday USD-M perpetual tests.

[Freqtrade community strategies](https://github.com/davidzr/freqtrade-strategies) is archived and GPL-3.0 licensed. It contains examples including ADXMomentum, AwesomeMacd and VWAP-related strategies. The repository's existence, popularity, or author backtests are not treated as proof of positive expectancy. GPL-3.0 source code is not copied into this project; strategy ideas are reimplemented independently.

## Data sources and restrictions

- [Binance Public Data repository](https://github.com/binance/binance-public-data) documents the public archive structure and checksum files.
- USD-M perpetual 1-minute klines: `https://data.binance.vision/data/futures/um/monthly/klines/{SYMBOL}/1m/{SYMBOL}-1m-{YYYY-MM}.zip`.
- USD-M perpetual funding: `https://data.binance.vision/data/futures/um/monthly/fundingRate/{SYMBOL}/{SYMBOL}-fundingRate-{YYYY-MM}.zip`.
- USD-M perpetual metrics (5-minute open interest and positioning fields): `https://data.binance.vision/data/futures/um/daily/metrics/{SYMBOL}/{SYMBOL}-metrics-{YYYY-MM-DD}.zip`.
- Binance Vision ZIP checksum companions are checked when available. Data parsers detect millisecond/microsecond/nanosecond timestamp magnitude and retain UTC timestamps.

**Important licence restriction:** Binance's current [Vision Dataset Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md) grant datasets under CC BY-NC-SA 4.0, except where specifically designated otherwise. They limit use to non-commercial research, education and personal non-production historical backtesting; they prohibit use for live proprietary trading execution, commercial automated order generation, or compensated signal distribution. Any redistribution of derived work must follow the stated attribution and ShareAlike conditions. The current programme is historical research only. Do not treat these data as licensed for a future live/commercial execution system without obtaining separate rights and checking the then-current terms.

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

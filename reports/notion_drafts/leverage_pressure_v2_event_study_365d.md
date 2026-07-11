# Leverage Pressure v2 Event Study — First Pass Result

- created_at: 2026-06-01T06:37:54.794363+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_365d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: first_pass_exploratory

## Method

- Bybit BTC/ETH fixture `bybit_leverage_pressure_fixture_365d.jsonl`, 1h feature grid.
- Uses settled funding only; predicted funding is not used.
- Equal-weight ordinal score: funding pressure + OI expansion + perp/spot divergence + weak spot confirmation.
- Primary readout: whether high-score buckets have worse downside 5% quantile than low-score buckets across 4h/8h/12h/24h.
- 7d rolling warmup is used only to get a first-pass read; this is not sufficient for robust final claims.

## Results by symbol

### BTCUSDT

- valid hourly events: 8534
- window: 2025-06-09 17:00:00+00:00 → 2026-05-31 06:00:00+00:00
- funding points: 1095
- OI points: 36600

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = 0.2340%; supports=False
- 8h: high-minus-low 5% quantile = 0.2846%; supports=False
- 12h: high-minus-low 5% quantile = 0.2333%; supports=False
- 24h: high-minus-low 5% quantile = 0.0109%; supports=False

#### 24h controls

- full_score_top_quartile: n=2378, q05_24h=-3.4403%, q10_24h=-2.5475%, mean_24h=-0.1318%, mae_q05_24h=-4.5726%
- high_funding_only: n=2917, q05_24h=-3.3376%, q10_24h=-2.4471%, mean_24h=-0.1703%, mae_q05_24h=-4.4177%
- rising_oi_only: n=6286, q05_24h=-3.5349%, q10_24h=-2.6908%, mean_24h=-0.1240%, mae_q05_24h=-4.7719%
- funding_plus_oi: n=2220, q05_24h=-3.3274%, q10_24h=-2.4866%, mean_24h=-0.1377%, mae_q05_24h=-4.4170%
- high_volatility: n=2134, q05_24h=-4.8702%, q10_24h=-3.1453%, mean_24h=-0.1655%, mae_q05_24h=-7.0727%
- negative_momentum: n=2134, q05_24h=-4.1136%, q10_24h=-3.0062%, mean_24h=-0.1408%, mae_q05_24h=-5.5365%

#### Bucket tables

**4h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-1.5842%, q10=-1.0510%, mean=-0.0135%, mae_q05=-2.2489%
- mid: n=2845, score_mean=2.45, q05=-1.3572%, q10=-0.8806%, mean=0.0065%, mae_q05=-1.9420%
- high: n=2845, score_mean=4.42, q05=-1.3502%, q10=-0.8658%, mean=-0.0347%, mae_q05=-1.8952%

**8h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-2.2133%, q10=-1.4489%, mean=-0.0060%, mae_q05=-3.0930%
- mid: n=2845, score_mean=2.45, q05=-2.2596%, q10=-1.4683%, mean=-0.0381%, mae_q05=-2.9447%
- high: n=2845, score_mean=4.42, q05=-1.9287%, q10=-1.3751%, mean=-0.0410%, mae_q05=-2.6940%

**12h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-2.6473%, q10=-1.9237%, mean=-0.0527%, mae_q05=-3.7114%
- mid: n=2845, score_mean=2.45, q05=-2.5123%, q10=-1.8190%, mean=-0.0272%, mae_q05=-3.4828%
- high: n=2845, score_mean=4.42, q05=-2.4140%, q10=-1.6942%, mean=-0.0498%, mae_q05=-3.2501%

**24h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-3.3668%, q10=-2.5428%, mean=-0.0471%, mae_q05=-4.7912%
- mid: n=2845, score_mean=2.45, q05=-3.7590%, q10=-2.6500%, mean=-0.1169%, mae_q05=-5.0148%
- high: n=2845, score_mean=4.42, q05=-3.3559%, q10=-2.5599%, mean=-0.0979%, mae_q05=-4.4295%


### ETHUSDT

- valid hourly events: 8534
- window: 2025-06-09 17:00:00+00:00 → 2026-05-31 06:00:00+00:00
- funding points: 1095
- OI points: 36600

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = 0.4992%; supports=False
- 8h: high-minus-low 5% quantile = 0.6470%; supports=False
- 12h: high-minus-low 5% quantile = 0.5074%; supports=False
- 24h: high-minus-low 5% quantile = 0.7997%; supports=False

#### 24h controls

- full_score_top_quartile: n=2445, q05_24h=-5.0403%, q10_24h=-3.9110%, mean_24h=-0.0037%, mae_q05_24h=-6.8087%
- high_funding_only: n=2893, q05_24h=-5.3932%, q10_24h=-3.8856%, mean_24h=0.0838%, mae_q05_24h=-7.2437%
- rising_oi_only: n=6329, q05_24h=-5.4924%, q10_24h=-4.1235%, mean_24h=-0.1475%, mae_q05_24h=-7.4888%
- funding_plus_oi: n=2071, q05_24h=-5.6345%, q10_24h=-4.0308%, mean_24h=-0.0551%, mae_q05_24h=-7.6888%
- high_volatility: n=2134, q05_24h=-6.6065%, q10_24h=-4.7406%, mean_24h=-0.2189%, mae_q05_24h=-9.8173%
- negative_momentum: n=2134, q05_24h=-6.8219%, q10_24h=-4.7164%, mean_24h=-0.3079%, mae_q05_24h=-9.8609%

#### Bucket tables

**4h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-2.5078%, q10=-1.5236%, mean=-0.0421%, mae_q05=-3.6513%
- mid: n=2845, score_mean=2.48, q05=-2.2073%, q10=-1.4357%, mean=0.0404%, mae_q05=-3.1575%
- high: n=2845, score_mean=4.45, q05=-2.0086%, q10=-1.3507%, mean=-0.0035%, mae_q05=-2.8248%

**8h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-3.5341%, q10=-2.4008%, mean=-0.0353%, mae_q05=-4.8600%
- mid: n=2845, score_mean=2.48, q05=-3.2538%, q10=-2.1913%, mean=0.0551%, mae_q05=-4.4624%
- high: n=2845, score_mean=4.45, q05=-2.8870%, q10=-2.0132%, mean=-0.0330%, mae_q05=-3.9546%

**12h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-4.1948%, q10=-2.9921%, mean=-0.0475%, mae_q05=-5.7581%
- mid: n=2845, score_mean=2.48, q05=-3.9975%, q10=-2.7030%, mean=0.0654%, mae_q05=-5.4845%
- high: n=2845, score_mean=4.45, q05=-3.6874%, q10=-2.5606%, mean=-0.0450%, mae_q05=-4.7970%

**24h forward return buckets**
- low: n=2844, score_mean=0.78, q05=-5.6823%, q10=-4.2970%, mean=-0.1255%, mae_q05=-7.7382%
- mid: n=2845, score_mean=2.48, q05=-5.6881%, q10=-4.1422%, mean=0.0864%, mae_q05=-7.8717%
- high: n=2845, score_mean=4.45, q05=-4.8826%, q10=-3.7614%, mean=-0.0286%, mae_q05=-6.5684%

## Conservative conclusion

Conclusion label: `weak_or_reject_first_pass`

Interpretation:

- Exploratory first pass only; not a paper-trading candidate.
- 30d is too short for robust regime claims.
- Settled funding may be too sparse/late for the intended mechanism if results are weak or inconsistent.
- If predicted funding becomes necessary, activate Jayda/DataProvider review before using it.

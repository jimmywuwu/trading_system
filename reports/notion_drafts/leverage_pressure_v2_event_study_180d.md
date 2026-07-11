# Leverage Pressure v2 Event Study — First Pass Result

- created_at: 2026-06-01T06:05:45.896098+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_180d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: first_pass_exploratory

## Method

- Bybit BTC/ETH fixture `bybit_leverage_pressure_fixture_180d.jsonl`, 1h feature grid.
- Uses settled funding only; predicted funding is not used.
- Equal-weight ordinal score: funding pressure + OI expansion + perp/spot divergence + weak spot confirmation.
- Primary readout: whether high-score buckets have worse downside 5% quantile than low-score buckets across 4h/8h/12h/24h.
- 7d rolling warmup is used only to get a first-pass read; this is not sufficient for robust final claims.

## Results by symbol

### BTCUSDT

- valid hourly events: 4093
- window: 2025-12-11 17:00:00+00:00 → 2026-05-31 05:00:00+00:00
- funding points: 540
- OI points: 18000

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = -0.0421%; supports=True
- 8h: high-minus-low 5% quantile = -0.0823%; supports=True
- 12h: high-minus-low 5% quantile = 0.1873%; supports=False
- 24h: high-minus-low 5% quantile = 0.4276%; supports=False

#### 24h controls

- full_score_top_quartile: n=1045, q05_24h=-3.2250%, q10_24h=-2.5010%, mean_24h=-0.1718%, mae_q05_24h=-4.3825%
- high_funding_only: n=1154, q05_24h=-3.6235%, q10_24h=-2.5541%, mean_24h=-0.3574%, mae_q05_24h=-4.6405%
- rising_oi_only: n=3095, q05_24h=-3.8668%, q10_24h=-2.7712%, mean_24h=-0.1176%, mae_q05_24h=-4.9721%
- funding_plus_oi: n=911, q05_24h=-3.7544%, q10_24h=-2.5822%, mean_24h=-0.3874%, mae_q05_24h=-4.6870%
- high_volatility: n=1024, q05_24h=-4.8623%, q10_24h=-3.4382%, mean_24h=-0.2621%, mae_q05_24h=-7.3938%
- negative_momentum: n=1024, q05_24h=-4.4661%, q10_24h=-3.6824%, mean_24h=-0.1938%, mae_q05_24h=-6.0364%

#### Bucket tables

**4h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-1.5365%, q10=-0.9964%, mean=0.0037%, mae_q05=-2.2059%
- mid: n=1364, score_mean=2.29, q05=-1.4287%, q10=-1.0163%, mean=0.0159%, mae_q05=-2.1098%
- high: n=1365, score_mean=4.22, q05=-1.5787%, q10=-0.9583%, mean=-0.0641%, mae_q05=-2.0844%

**8h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-1.9980%, q10=-1.4185%, mean=0.0395%, mae_q05=-3.0605%
- mid: n=1364, score_mean=2.29, q05=-2.4335%, q10=-1.6322%, mean=-0.0505%, mae_q05=-3.2461%
- high: n=1365, score_mean=4.22, q05=-2.0803%, q10=-1.4922%, mean=-0.0854%, mae_q05=-2.8119%

**12h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-2.7389%, q10=-1.9248%, mean=0.0218%, mae_q05=-3.7755%
- mid: n=1364, score_mean=2.29, q05=-2.6066%, q10=-2.0291%, mean=-0.0744%, mae_q05=-3.7580%
- high: n=1365, score_mean=4.22, q05=-2.5516%, q10=-1.7490%, mean=-0.0961%, mae_q05=-3.4347%

**24h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-3.6132%, q10=-2.5345%, mean=0.0937%, mae_q05=-5.0954%
- mid: n=1364, score_mean=2.29, q05=-4.0891%, q10=-3.0229%, mean=-0.2377%, mae_q05=-5.4079%
- high: n=1365, score_mean=4.22, q05=-3.1857%, q10=-2.4945%, mean=-0.1629%, mae_q05=-4.2332%


### ETHUSDT

- valid hourly events: 4093
- window: 2025-12-11 17:00:00+00:00 → 2026-05-31 05:00:00+00:00
- funding points: 540
- OI points: 18000

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = -0.0990%; supports=True
- 8h: high-minus-low 5% quantile = 0.2392%; supports=False
- 12h: high-minus-low 5% quantile = -0.1734%; supports=True
- 24h: high-minus-low 5% quantile = 0.5113%; supports=False

#### 24h controls

- full_score_top_quartile: n=1061, q05_24h=-4.9484%, q10_24h=-3.9208%, mean_24h=-0.3294%, mae_q05_24h=-6.4786%
- high_funding_only: n=1152, q05_24h=-5.5909%, q10_24h=-4.1845%, mean_24h=-0.6068%, mae_q05_24h=-6.9894%
- rising_oi_only: n=3078, q05_24h=-5.0191%, q10_24h=-3.9739%, mean_24h=-0.2625%, mae_q05_24h=-6.8040%
- funding_plus_oi: n=903, q05_24h=-5.3296%, q10_24h=-4.1383%, mean_24h=-0.6220%, mae_q05_24h=-6.5115%
- high_volatility: n=1024, q05_24h=-7.0465%, q10_24h=-4.9339%, mean_24h=-0.6843%, mae_q05_24h=-9.9275%
- negative_momentum: n=1024, q05_24h=-7.0628%, q10_24h=-4.7311%, mean_24h=-0.4341%, mae_q05_24h=-9.6860%

#### Bucket tables

**4h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-1.9735%, q10=-1.2389%, mean=-0.0006%, mae_q05=-3.0675%
- mid: n=1364, score_mean=2.27, q05=-2.2517%, q10=-1.5622%, mean=-0.0393%, mae_q05=-3.1165%
- high: n=1365, score_mean=4.28, q05=-2.0725%, q10=-1.4230%, mean=-0.0678%, mae_q05=-2.8481%

**8h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-3.0905%, q10=-1.9870%, mean=-0.0008%, mae_q05=-4.5303%
- mid: n=1364, score_mean=2.27, q05=-3.3955%, q10=-2.2424%, mean=-0.0468%, mae_q05=-4.4145%
- high: n=1365, score_mean=4.28, q05=-2.8513%, q10=-2.0620%, mean=-0.1727%, mae_q05=-3.9886%

**12h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-3.5586%, q10=-2.5359%, mean=0.0239%, mae_q05=-5.1181%
- mid: n=1364, score_mean=2.27, q05=-4.0672%, q10=-2.8509%, mean=-0.0840%, mae_q05=-5.3047%
- high: n=1365, score_mean=4.28, q05=-3.7320%, q10=-2.5949%, mean=-0.2741%, mae_q05=-4.8369%

**24h forward return buckets**
- low: n=1364, score_mean=0.74, q05=-5.3081%, q10=-3.8398%, mean=-0.0965%, mae_q05=-7.2296%
- mid: n=1364, score_mean=2.27, q05=-5.5595%, q10=-4.1030%, mean=-0.2485%, mae_q05=-7.5569%
- high: n=1365, score_mean=4.28, q05=-4.7968%, q10=-3.7984%, mean=-0.3353%, mae_q05=-6.1385%

## Conservative conclusion

Conclusion label: `research_only_needs_revision`

Interpretation:

- Exploratory first pass only; not a paper-trading candidate.
- 30d is too short for robust regime claims.
- Settled funding may be too sparse/late for the intended mechanism if results are weak or inconsistent.
- If predicted funding becomes necessary, activate Jayda/DataProvider review before using it.

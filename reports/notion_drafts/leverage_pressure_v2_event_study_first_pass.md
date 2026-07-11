# Leverage Pressure v2 Event Study — First Pass Result

- created_at: 2026-05-30T07:35:52.625586+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_30d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: first_pass_exploratory

## Method

- 30d Bybit BTC/ETH fixture, 1h feature grid.
- Uses settled funding only; predicted funding is not used.
- Equal-weight ordinal score: funding pressure + OI expansion + perp/spot divergence + weak spot confirmation.
- Primary readout: whether high-score buckets have worse downside 5% quantile than low-score buckets across 4h/8h/12h/24h.
- 7d rolling warmup is used only to get a first-pass read; this is not sufficient for robust final claims.

## Results by symbol

### BTCUSDT

- valid hourly events: 494
- window: 2026-05-08 18:00:00+00:00 → 2026-05-29 07:00:00+00:00
- funding points: 90
- OI points: 3000

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = 0.1841%; supports=False
- 8h: high-minus-low 5% quantile = 0.4298%; supports=False
- 12h: high-minus-low 5% quantile = 0.4185%; supports=False
- 24h: high-minus-low 5% quantile = 0.7054%; supports=False

#### 24h controls

- full_score_top_quartile: n=236, q05_24h=-2.6805%, q10_24h=-2.1011%, mean_24h=-0.2869%, mae_q05_24h=-3.3735%
- high_funding_only: n=176, q05_24h=-2.3799%, q10_24h=-1.7752%, mean_24h=-0.1476%, mae_q05_24h=-2.9812%
- rising_oi_only: n=381, q05_24h=-2.9756%, q10_24h=-2.4550%, mean_24h=-0.3750%, mae_q05_24h=-3.6159%
- funding_plus_oi: n=137, q05_24h=-1.6435%, q10_24h=-1.4823%, mean_24h=-0.1058%, mae_q05_24h=-2.8240%
- high_volatility: n=124, q05_24h=-2.9561%, q10_24h=-2.7395%, mean_24h=-0.5961%, mae_q05_24h=-3.4457%
- negative_momentum: n=124, q05_24h=-2.7159%, q10_24h=-1.7203%, mean_24h=0.0347%, mae_q05_24h=-3.5624%

#### Bucket tables

**4h forward return buckets**
- low: n=164, score_mean=0.87, q05=-1.1325%, q10=-0.8665%, mean=-0.0821%, mae_q05=-1.4992%
- mid: n=165, score_mean=2.43, q05=-1.3536%, q10=-0.8735%, mean=-0.1136%, mae_q05=-1.9727%
- high: n=165, score_mean=4.13, q05=-0.9484%, q10=-0.6227%, mean=-0.0033%, mae_q05=-1.4688%

**8h forward return buckets**
- low: n=164, score_mean=0.87, q05=-1.7823%, q10=-1.3099%, mean=-0.1723%, mae_q05=-2.1450%
- mid: n=165, score_mean=2.43, q05=-1.6152%, q10=-1.2746%, mean=-0.1870%, mae_q05=-2.1637%
- high: n=165, score_mean=4.13, q05=-1.3525%, q10=-1.0256%, mean=-0.0560%, mae_q05=-1.8015%

**12h forward return buckets**
- low: n=164, score_mean=0.87, q05=-2.1574%, q10=-1.6974%, mean=-0.2764%, mae_q05=-2.6905%
- mid: n=165, score_mean=2.43, q05=-1.6910%, q10=-1.5728%, mean=-0.1993%, mae_q05=-2.3168%
- high: n=165, score_mean=4.13, q05=-1.7388%, q10=-1.5530%, mean=-0.1410%, mae_q05=-2.4343%

**24h forward return buckets**
- low: n=164, score_mean=0.87, q05=-3.1488%, q10=-2.6737%, mean=-0.6106%, mae_q05=-3.8978%
- mid: n=165, score_mean=2.43, q05=-2.8174%, q10=-2.6892%, mean=-0.5473%, mae_q05=-3.3909%
- high: n=165, score_mean=4.13, q05=-2.4434%, q10=-1.9424%, mean=-0.0888%, mae_q05=-3.0462%


### ETHUSDT

- valid hourly events: 494
- window: 2026-05-08 18:00:00+00:00 → 2026-05-29 07:00:00+00:00
- funding points: 90
- OI points: 3000

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = -0.7952%; supports=True
- 8h: high-minus-low 5% quantile = -0.6648%; supports=True
- 12h: high-minus-low 5% quantile = -0.3221%; supports=True
- 24h: high-minus-low 5% quantile = 0.0661%; supports=False

#### 24h controls

- full_score_top_quartile: n=127, q05_24h=-3.4761%, q10_24h=-3.1156%, mean_24h=-0.7662%, mae_q05_24h=-5.1909%
- high_funding_only: n=183, q05_24h=-3.0076%, q10_24h=-2.7006%, mean_24h=-0.3607%, mae_q05_24h=-4.7025%
- rising_oi_only: n=377, q05_24h=-3.9675%, q10_24h=-3.2259%, mean_24h=-0.6392%, mae_q05_24h=-5.2249%
- funding_plus_oi: n=136, q05_24h=-2.9211%, q10_24h=-2.7399%, mean_24h=-0.3348%, mae_q05_24h=-4.8350%
- high_volatility: n=124, q05_24h=-3.0369%, q10_24h=-2.3136%, mean_24h=-0.2986%, mae_q05_24h=-3.5891%
- negative_momentum: n=124, q05_24h=-2.6995%, q10_24h=-2.1766%, mean_24h=0.2020%, mae_q05_24h=-4.1434%

#### Bucket tables

**4h forward return buckets**
- low: n=164, score_mean=0.77, q05=-1.3472%, q10=-0.9765%, mean=-0.0479%, mae_q05=-2.0034%
- mid: n=165, score_mean=2.34, q05=-1.5260%, q10=-0.8597%, mean=-0.0096%, mae_q05=-2.3590%
- high: n=165, score_mean=4.32, q05=-2.1424%, q10=-1.5371%, mean=-0.2692%, mae_q05=-2.8899%

**8h forward return buckets**
- low: n=164, score_mean=0.77, q05=-2.0799%, q10=-1.4862%, mean=-0.1112%, mae_q05=-2.8028%
- mid: n=165, score_mean=2.34, q05=-1.9955%, q10=-1.5589%, mean=-0.1385%, mae_q05=-2.9329%
- high: n=165, score_mean=4.32, q05=-2.7446%, q10=-2.0950%, mean=-0.4147%, mae_q05=-3.5283%

**12h forward return buckets**
- low: n=164, score_mean=0.77, q05=-2.6789%, q10=-2.1390%, mean=-0.1868%, mae_q05=-3.1006%
- mid: n=165, score_mean=2.34, q05=-2.3564%, q10=-1.9302%, mean=-0.1938%, mae_q05=-3.3126%
- high: n=165, score_mean=4.32, q05=-3.0010%, q10=-2.4777%, mean=-0.5942%, mae_q05=-4.4174%

**24h forward return buckets**
- low: n=164, score_mean=0.77, q05=-3.6445%, q10=-3.0415%, mean=-0.7769%, mae_q05=-4.8860%
- mid: n=165, score_mean=2.34, q05=-3.5760%, q10=-3.0955%, mean=-0.5552%, mae_q05=-4.5420%
- high: n=165, score_mean=4.32, q05=-3.5785%, q10=-3.0777%, mean=-0.6301%, mae_q05=-5.2645%

## Conservative conclusion

Conclusion label: `research_only_needs_revision`

Interpretation:

- Exploratory first pass only; not a paper-trading candidate.
- 30d is too short for robust regime claims.
- Settled funding may be too sparse/late for the intended mechanism if results are weak or inconsistent.
- If predicted funding becomes necessary, activate Jayda/DataProvider review before using it.

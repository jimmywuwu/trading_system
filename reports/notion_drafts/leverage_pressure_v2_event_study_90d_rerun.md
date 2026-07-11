# Leverage Pressure v2 Event Study — First Pass Result

- created_at: 2026-06-01T05:53:23.514618+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_90d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: first_pass_exploratory

## Method

- Bybit BTC/ETH fixture `bybit_leverage_pressure_fixture_90d.jsonl`, 1h feature grid.
- Uses settled funding only; predicted funding is not used.
- Equal-weight ordinal score: funding pressure + OI expansion + perp/spot divergence + weak spot confirmation.
- Primary readout: whether high-score buckets have worse downside 5% quantile than low-score buckets across 4h/8h/12h/24h.
- 7d rolling warmup is used only to get a first-pass read; this is not sufficient for robust final claims.

## Results by symbol

### BTCUSDT

- valid hourly events: 1934
- window: 2026-03-09 18:00:00+00:00 → 2026-05-29 07:00:00+00:00
- funding points: 270
- OI points: 9000

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = 0.0998%; supports=False
- 8h: high-minus-low 5% quantile = 0.1201%; supports=False
- 12h: high-minus-low 5% quantile = -0.0127%; supports=True
- 24h: high-minus-low 5% quantile = -0.1804%; supports=True

#### 24h controls

- full_score_top_quartile: n=524, q05_24h=-2.7879%, q10_24h=-2.2094%, mean_24h=0.0442%, mae_q05_24h=-3.5924%
- high_funding_only: n=624, q05_24h=-3.0981%, q10_24h=-2.4760%, mean_24h=-0.2775%, mae_q05_24h=-3.6102%
- rising_oi_only: n=1425, q05_24h=-3.1577%, q10_24h=-2.4757%, mean_24h=0.0125%, mae_q05_24h=-3.9074%
- funding_plus_oi: n=463, q05_24h=-3.2274%, q10_24h=-2.5173%, mean_24h=-0.3796%, mae_q05_24h=-3.6903%
- high_volatility: n=484, q05_24h=-2.5193%, q10_24h=-2.0399%, mean_24h=-0.0597%, mae_q05_24h=-3.4082%
- negative_momentum: n=484, q05_24h=-3.4531%, q10_24h=-2.2136%, mean_24h=0.1840%, mae_q05_24h=-4.3798%

#### Bucket tables

**4h forward return buckets**
- low: n=644, score_mean=0.78, q05=-1.2375%, q10=-0.8695%, mean=0.0006%, mae_q05=-1.8109%
- mid: n=645, score_mean=2.39, q05=-1.2803%, q10=-0.8758%, mean=0.0418%, mae_q05=-1.8957%
- high: n=645, score_mean=4.25, q05=-1.1377%, q10=-0.7892%, mean=0.0098%, mae_q05=-1.6296%

**8h forward return buckets**
- low: n=644, score_mean=0.78, q05=-1.7846%, q10=-1.3031%, mean=0.0328%, mae_q05=-2.3647%
- mid: n=645, score_mean=2.39, q05=-1.7328%, q10=-1.2783%, mean=0.0286%, mae_q05=-2.3793%
- high: n=645, score_mean=4.25, q05=-1.6645%, q10=-1.2154%, mean=0.0387%, mae_q05=-2.2717%

**12h forward return buckets**
- low: n=644, score_mean=0.78, q05=-1.9764%, q10=-1.4311%, mean=0.0726%, mae_q05=-2.7911%
- mid: n=645, score_mean=2.39, q05=-2.1756%, q10=-1.5589%, mean=0.0777%, mae_q05=-2.8888%
- high: n=645, score_mean=4.25, q05=-1.9891%, q10=-1.4367%, mean=-0.0065%, mae_q05=-2.6922%

**24h forward return buckets**
- low: n=644, score_mean=0.78, q05=-2.6216%, q10=-2.0449%, mean=0.2744%, mae_q05=-3.5432%
- mid: n=645, score_mean=2.39, q05=-3.3482%, q10=-2.6960%, mean=0.0139%, mae_q05=-4.0845%
- high: n=645, score_mean=4.25, q05=-2.8020%, q10=-2.2113%, mean=-0.0445%, mae_q05=-3.5607%


### ETHUSDT

- valid hourly events: 1934
- window: 2026-03-09 18:00:00+00:00 → 2026-05-29 07:00:00+00:00
- funding points: 270
- OI points: 9000

#### Tail-fragility diagnostic

- 4h: high-minus-low 5% quantile = -0.4150%; supports=True
- 8h: high-minus-low 5% quantile = -0.1872%; supports=True
- 12h: high-minus-low 5% quantile = -0.4583%; supports=True
- 24h: high-minus-low 5% quantile = -0.5426%; supports=True

#### 24h controls

- full_score_top_quartile: n=503, q05_24h=-4.2345%, q10_24h=-3.2522%, mean_24h=-0.1759%, mae_q05_24h=-5.2113%
- high_funding_only: n=547, q05_24h=-4.0506%, q10_24h=-3.1727%, mean_24h=-0.3227%, mae_q05_24h=-5.1342%
- rising_oi_only: n=1367, q05_24h=-4.2888%, q10_24h=-3.3927%, mean_24h=-0.1806%, mae_q05_24h=-5.3975%
- funding_plus_oi: n=433, q05_24h=-4.2888%, q10_24h=-3.3101%, mean_24h=-0.4962%, mae_q05_24h=-5.2323%
- high_volatility: n=484, q05_24h=-3.2360%, q10_24h=-2.8185%, mean_24h=0.0287%, mae_q05_24h=-4.3057%
- negative_momentum: n=484, q05_24h=-3.4748%, q10_24h=-2.7509%, mean_24h=0.2202%, mae_q05_24h=-4.6422%

#### Bucket tables

**4h forward return buckets**
- low: n=644, score_mean=0.74, q05=-1.4618%, q10=-1.0471%, mean=0.0221%, mae_q05=-2.2752%
- mid: n=645, score_mean=2.23, q05=-1.7238%, q10=-1.1436%, mean=0.0504%, mae_q05=-2.3573%
- high: n=645, score_mean=4.24, q05=-1.8769%, q10=-1.3364%, mean=-0.0585%, mae_q05=-2.5649%

**8h forward return buckets**
- low: n=644, score_mean=0.74, q05=-2.2795%, q10=-1.6009%, mean=0.0112%, mae_q05=-3.1221%
- mid: n=645, score_mean=2.23, q05=-2.3856%, q10=-1.6785%, mean=0.0859%, mae_q05=-2.9985%
- high: n=645, score_mean=4.24, q05=-2.4667%, q10=-1.9001%, mean=-0.0679%, mae_q05=-3.3150%

**12h forward return buckets**
- low: n=644, score_mean=0.74, q05=-2.7304%, q10=-1.9116%, mean=0.0342%, mae_q05=-3.7604%
- mid: n=645, score_mean=2.23, q05=-2.8270%, q10=-2.1808%, mean=0.1160%, mae_q05=-3.6460%
- high: n=645, score_mean=4.24, q05=-3.1887%, q10=-2.2899%, mean=-0.1040%, mae_q05=-4.1962%

**24h forward return buckets**
- low: n=644, score_mean=0.74, q05=-3.5000%, q10=-2.9809%, mean=0.1636%, mae_q05=-4.8205%
- mid: n=645, score_mean=2.23, q05=-4.0276%, q10=-3.3899%, mean=0.1269%, mae_q05=-5.0775%
- high: n=645, score_mean=4.24, q05=-4.0426%, q10=-3.1426%, mean=-0.2358%, mae_q05=-5.2107%

## Conservative conclusion

Conclusion label: `research_only_needs_revision`

Interpretation:

- Exploratory first pass only; not a paper-trading candidate.
- 30d is too short for robust regime claims.
- Settled funding may be too sparse/late for the intended mechanism if results are weak or inconsistent.
- If predicted funding becomes necessary, activate Jayda/DataProvider review before using it.

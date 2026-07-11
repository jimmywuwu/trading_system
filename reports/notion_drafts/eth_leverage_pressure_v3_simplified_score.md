# ETH Leverage Pressure v3 — Simplified Score Validation

- created_at: 2026-06-01T05:56:48.650373+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_90d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: exploratory_v3_validation

## 0. V3 definition

V3 removes `weak_spot_confirmation` from the core score because v2 decomposition did not show it had positive incremental value.

```text
eth_leverage_pressure_v3 = funding_pressure + oi_expansion + perp_spot_divergence
```

This is still a research score, not a signal contract or strategy.

## 1. Main bucket result: high-minus-low 5% quantile

### funding_oi
- 4h: diff=-0.3293%; low_q05=-1.6125%; high_q05=-1.9418%; high_score_mean=2.42
- 8h: diff=-0.2098%; low_q05=-2.4948%; high_q05=-2.7045%; high_score_mean=2.42
- 12h: diff=-0.5815%; low_q05=-2.8480%; high_q05=-3.4295%; high_score_mean=2.42
- 24h: diff=-0.1831%; low_q05=-4.0556%; high_q05=-4.2387%; high_score_mean=2.42

### v3
- 4h: diff=-0.6343%; low_q05=-1.4001%; high_q05=-2.0343%; high_score_mean=3.22
- 8h: diff=-0.2007%; low_q05=-2.3397%; high_q05=-2.5403%; high_score_mean=3.22
- 12h: diff=-0.5015%; low_q05=-2.7221%; high_q05=-3.2236%; high_score_mean=3.22
- 24h: diff=-0.7576%; low_q05=-3.5000%; high_q05=-4.2576%; high_score_mean=3.22

### full
- 4h: diff=-0.4150%; low_q05=-1.4618%; high_q05=-1.8769%; high_score_mean=4.24
- 8h: diff=-0.1872%; low_q05=-2.2795%; high_q05=-2.4667%; high_score_mean=4.24
- 12h: diff=-0.4583%; low_q05=-2.7304%; high_q05=-3.1887%; high_score_mean=4.24
- 24h: diff=-0.5426%; low_q05=-3.5000%; high_q05=-4.0426%; high_score_mean=4.24

## 2. Time-split sanity check

### first_half
- window: 2026-03-09 18:00:00+00:00 → 2026-04-19 00:00:00+00:00; n=967
- funding_oi: 4h=0.1217%, 8h=-0.2397%, 12h=-0.2947%, 24h=0.8766%
- v3: 4h=-0.4683%, 8h=0.2097%, 12h=-0.3764%, 24h=-0.3114%
- full: 4h=-0.5229%, 8h=0.2899%, 12h=-0.8106%, 24h=-0.2822%

### second_half
- window: 2026-04-19 01:00:00+00:00 → 2026-05-29 07:00:00+00:00; n=967
- funding_oi: 4h=-0.4251%, 8h=-0.3940%, 12h=-0.7697%, 24h=-0.2469%
- v3: 4h=-0.7257%, 8h=-0.4703%, 12h=-0.7703%, 24h=-0.3048%
- full: 4h=-0.2455%, 8h=-0.3246%, 12h=-0.5097%, 24h=-0.1833%

### first_third
- window: 2026-03-09 18:00:00+00:00 → 2026-04-05 13:00:00+00:00; n=644
- funding_oi: 4h=-0.5066%, 8h=-1.1371%, 12h=-1.2925%, 24h=-1.5825%
- v3: 4h=-0.3297%, 8h=0.2272%, 12h=-0.5759%, 24h=0.7754%
- full: 4h=0.0595%, 8h=0.9110%, 12h=-0.1356%, 24h=0.7300%

### middle_third
- window: 2026-04-05 14:00:00+00:00 → 2026-05-02 10:00:00+00:00; n=645
- funding_oi: 4h=-0.4249%, 8h=-0.8229%, 12h=-1.1084%, 24h=-0.4841%
- v3: 4h=-0.4330%, 8h=-0.7468%, 12h=-1.0794%, 24h=-0.5662%
- full: 4h=-0.3445%, 8h=-0.7450%, 12h=-0.9905%, 24h=-0.5590%

### last_third
- window: 2026-05-02 11:00:00+00:00 → 2026-05-29 07:00:00+00:00; n=645
- funding_oi: 4h=-0.8722%, 8h=-1.0177%, 12h=-0.6248%, 24h=-0.6693%
- v3: 4h=-0.6905%, 8h=-0.6808%, 12h=-0.4957%, 24h=-0.3758%
- full: 4h=-0.5423%, 8h=-0.5784%, 12h=-0.5630%, 24h=-0.1654%

## 3. 24h top-quartile controls

- funding: n=547, q05_24h=-4.0506%, q10_24h=-3.1727%, mean_24h=-0.3227%, mae_q05_24h=-5.1342%
- oi: n=1506, q05_24h=-4.2144%, q10_24h=-3.3348%, mean_24h=-0.0439%, mae_q05_24h=-5.2814%
- funding_oi: n=686, q05_24h=-4.1554%, q10_24h=-3.3984%, mean_24h=-0.3098%, mae_q05_24h=-5.2558%
- v3: n=551, q05_24h=-4.2540%, q10_24h=-3.4642%, mean_24h=-0.4395%, mae_q05_24h=-5.2614%
- full: n=503, q05_24h=-4.2345%, q10_24h=-3.2522%, mean_24h=-0.1759%, mae_q05_24h=-5.2113%
- high_vol: n=484, q05_24h=-3.2360%, q10_24h=-2.8185%, mean_24h=0.0287%, mae_q05_24h=-4.3057%
- neg_mom: n=484, q05_24h=-3.4748%, q10_24h=-2.7509%, mean_24h=0.2202%, mae_q05_24h=-4.6422%

## 4. Episode concentration

- V3 high-bucket 24h q05 threshold: -4.2576%
- tail event count at/below q05: 33
- top tail days:
  - 2026-03-25: count=10, worst_24h=-5.3990%, avg_24h=-4.8597%
  - 2026-05-22: count=5, worst_24h=-4.7052%, avg_24h=-4.5121%
  - 2026-04-01: count=4, worst_24h=-4.8904%, avg_24h=-4.6048%
  - 2026-03-18: count=3, worst_24h=-6.0049%, avg_24h=-5.7162%
  - 2026-05-27: count=3, worst_24h=-4.7603%, avg_24h=-4.5556%
  - 2026-03-26: count=3, worst_24h=-4.6744%, avg_24h=-4.4738%
  - 2026-04-11: count=2, worst_24h=-5.0950%, avg_24h=-4.8185%
  - 2026-03-17: count=1, worst_24h=-6.2613%, avg_24h=-6.2613%
  - 2026-05-17: count=1, worst_24h=-4.8994%, avg_24h=-4.8994%
  - 2026-03-21: count=1, worst_24h=-4.5291%, avg_24h=-4.5291%

## 5. Toy long-risk filter sanity check

This is not a trading recommendation. It only tests whether high V3 periods are bad times to hold passive long exposure in this sample.

- buy-and-hold return over valid hourly sample: -0.4450%
- flat-during-v3-high return, zero cost: 2.5679%
- buy-and-hold max drawdown: -19.2935%
- flat-during-v3-high max drawdown: -18.2190%
- flat hours: 645/1934

## 6. Conservative interpretation

- v3 supportive horizons: 4/4
- full supportive horizons: 4/4
- funding+OI supportive horizons: 4/4
- 24h v3 time-split support across halves: 2/2

Conclusion label: `research_only_risk_filter_candidate_needs_longer_sample`

Current decision:

- V3 is cleaner than full score because it removes weak_spot, which was not supported as an incremental component.
- V3 still needs longer data and market-wide controls before any SignalContract.
- If V3 mainly overlaps with OI/funding controls, keep it as a research-only risk filter candidate rather than directional alpha.

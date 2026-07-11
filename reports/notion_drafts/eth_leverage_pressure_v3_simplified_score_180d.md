# ETH Leverage Pressure v3 — Simplified Score Validation

- created_at: 2026-06-01T06:17:29.167702+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_180d.jsonl`
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
- 4h: diff=-0.4979%; low_q05=-1.8467%; high_q05=-2.3446%; high_score_mean=2.43
- 8h: diff=-0.2260%; low_q05=-3.1617%; high_q05=-3.3877%; high_score_mean=2.43
- 12h: diff=-0.5232%; low_q05=-3.7503%; high_q05=-4.2734%; high_score_mean=2.43
- 24h: diff=0.6676%; low_q05=-6.0580%; high_q05=-5.3904%; high_score_mean=2.43

### v3
- 4h: diff=-0.2692%; low_q05=-2.0249%; high_q05=-2.2941%; high_score_mean=3.26
- 8h: diff=-0.0020%; low_q05=-3.2586%; high_q05=-3.2605%; high_score_mean=3.26
- 12h: diff=-0.4348%; low_q05=-3.6606%; high_q05=-4.0953%; high_score_mean=3.26
- 24h: diff=0.4103%; low_q05=-5.4936%; high_q05=-5.0833%; high_score_mean=3.26

### full
- 4h: diff=-0.0990%; low_q05=-1.9735%; high_q05=-2.0725%; high_score_mean=4.28
- 8h: diff=0.2392%; low_q05=-3.0905%; high_q05=-2.8513%; high_score_mean=4.28
- 12h: diff=-0.1734%; low_q05=-3.5586%; high_q05=-3.7320%; high_score_mean=4.28
- 24h: diff=0.5113%; low_q05=-5.3081%; high_q05=-4.7968%; high_score_mean=4.28

## 2. Time-split sanity check

### first_half
- window: 2025-12-11 17:00:00+00:00 → 2026-03-06 22:00:00+00:00; n=2046
- funding_oi: 4h=-1.2218%, 8h=-1.5371%, 12h=-2.1290%, 24h=-1.7222%
- v3: 4h=-0.5487%, 8h=-0.5570%, 12h=-1.2349%, 24h=-0.0943%
- full: 4h=-0.3716%, 8h=-0.4981%, 12h=-1.0209%, 24h=-0.0243%

### second_half
- window: 2026-03-06 23:00:00+00:00 → 2026-05-31 05:00:00+00:00; n=2047
- funding_oi: 4h=-0.2601%, 8h=-0.3651%, 12h=-0.5483%, 24h=0.0275%
- v3: 4h=-0.6377%, 8h=-0.3029%, 12h=-0.4483%, 24h=-0.6409%
- full: 4h=-0.3787%, 8h=-0.1332%, 12h=-0.3496%, 24h=-0.3682%

### first_third
- window: 2025-12-11 17:00:00+00:00 → 2026-02-06 12:00:00+00:00; n=1364
- funding_oi: 4h=-1.0324%, 8h=-1.6719%, 12h=-2.5013%, 24h=-0.8829%
- v3: 4h=-1.8148%, 8h=-2.6558%, 12h=-3.1816%, 24h=-3.5659%
- full: 4h=-0.1140%, 8h=-0.5492%, 12h=-1.1635%, 24h=-0.4555%

### middle_third
- window: 2026-02-06 13:00:00+00:00 → 2026-04-04 08:00:00+00:00; n=1364
- funding_oi: 4h=-0.3968%, 8h=-0.4940%, 12h=-0.8978%, 24h=0.0465%
- v3: 4h=-0.1807%, 8h=-0.0394%, 12h=-0.4890%, 24h=0.3736%
- full: 4h=-0.0246%, 8h=0.2832%, 12h=-0.3169%, 24h=0.0058%

### last_third
- window: 2026-04-04 09:00:00+00:00 → 2026-05-31 05:00:00+00:00; n=1365
- funding_oi: 4h=-0.5124%, 8h=-0.6737%, 12h=-0.7709%, 24h=-0.2807%
- v3: 4h=-0.6778%, 8h=-0.7455%, 12h=-0.7736%, 24h=-0.4516%
- full: 4h=-0.3102%, 8h=-0.4782%, 12h=-0.4638%, 24h=-0.2578%

## 3. 24h top-quartile controls

- funding: n=1152, q05_24h=-5.5909%, q10_24h=-4.1845%, mean_24h=-0.6068%, mae_q05_24h=-6.9894%
- oi: n=3220, q05_24h=-4.9496%, q10_24h=-3.9063%, mean_24h=-0.2035%, mae_q05_24h=-6.7075%
- funding_oi: n=1537, q05_24h=-5.2481%, q10_24h=-3.9611%, mean_24h=-0.4631%, mae_q05_24h=-6.5936%
- v3: n=1216, q05_24h=-5.3334%, q10_24h=-4.1537%, mean_24h=-0.6488%, mae_q05_24h=-6.9302%
- full: n=1061, q05_24h=-4.9484%, q10_24h=-3.9208%, mean_24h=-0.3294%, mae_q05_24h=-6.4786%
- high_vol: n=1024, q05_24h=-7.0465%, q10_24h=-4.9339%, mean_24h=-0.6843%, mae_q05_24h=-9.9275%
- neg_mom: n=1024, q05_24h=-7.0628%, q10_24h=-4.7311%, mean_24h=-0.4341%, mae_q05_24h=-9.6860%

## 4. Episode concentration

- V3 high-bucket 24h q05 threshold: -5.0833%
- tail event count at/below q05: 69
- top tail days:
  - 2026-02-04: count=11, worst_24h=-13.9007%, avg_24h=-8.6357%
  - 2025-12-15: count=8, worst_24h=-7.1977%, avg_24h=-6.6432%
  - 2026-01-29: count=6, worst_24h=-8.0656%, avg_24h=-6.9615%
  - 2026-02-05: count=5, worst_24h=-10.0914%, avg_24h=-8.0144%
  - 2026-01-31: count=4, worst_24h=-10.2015%, avg_24h=-9.9060%
  - 2026-01-30: count=3, worst_24h=-13.1401%, avg_24h=-11.7347%
  - 2026-02-01: count=3, worst_24h=-7.7670%, avg_24h=-6.8459%
  - 2026-01-20: count=3, worst_24h=-7.2438%, avg_24h=-6.6179%
  - 2026-02-14: count=3, worst_24h=-7.0212%, avg_24h=-6.1116%
  - 2026-02-15: count=3, worst_24h=-6.2607%, avg_24h=-5.9152%

## 5. Toy long-risk filter sanity check

This is not a trading recommendation. It only tests whether high V3 periods are bad times to hold passive long exposure in this sample.

- buy-and-hold return over valid hourly sample: -36.0664%
- flat-during-v3-high return, zero cost: -11.2968%
- buy-and-hold max drawdown: -46.3455%
- flat-during-v3-high max drawdown: -37.4556%
- flat hours: 1365/4093

## 6. Conservative interpretation

- v3 supportive horizons: 3/4
- full supportive horizons: 2/4
- funding+OI supportive horizons: 3/4
- 24h v3 time-split support across halves: 2/2

Conclusion label: `research_only_risk_filter_candidate_needs_longer_sample`

Current decision:

- V3 is cleaner than full score because it removes weak_spot, which was not supported as an incremental component.
- V3 still needs longer data and market-wide controls before any SignalContract.
- If V3 mainly overlaps with OI/funding controls, keep it as a research-only risk filter candidate rather than directional alpha.

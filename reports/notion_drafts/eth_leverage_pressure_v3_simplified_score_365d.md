# ETH Leverage Pressure v3 — Simplified Score Validation

- created_at: 2026-06-01T07:07:44.945595+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_365d.jsonl`
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
- 4h: diff=0.1533%; low_q05=-2.3078%; high_q05=-2.1545%; high_score_mean=2.77
- 8h: diff=0.3289%; low_q05=-3.4040%; high_q05=-3.0751%; high_score_mean=2.77
- 12h: diff=0.2607%; low_q05=-4.0557%; high_q05=-3.7950%; high_score_mean=2.77
- 24h: diff=0.3852%; low_q05=-5.7681%; high_q05=-5.3830%; high_score_mean=2.77

### v3
- 4h: diff=0.3581%; low_q05=-2.5494%; high_q05=-2.1913%; high_score_mean=3.54
- 8h: diff=0.4646%; low_q05=-3.6257%; high_q05=-3.1611%; high_score_mean=3.54
- 12h: diff=0.2782%; low_q05=-4.2715%; high_q05=-3.9933%; high_score_mean=3.54
- 24h: diff=0.2713%; low_q05=-5.7707%; high_q05=-5.4994%; high_score_mean=3.54

### full
- 4h: diff=0.4992%; low_q05=-2.5078%; high_q05=-2.0086%; high_score_mean=4.45
- 8h: diff=0.6470%; low_q05=-3.5341%; high_q05=-2.8870%; high_score_mean=4.45
- 12h: diff=0.5074%; low_q05=-4.1948%; high_q05=-3.6874%; high_score_mean=4.45
- 24h: diff=0.7997%; low_q05=-5.6823%; high_q05=-4.8826%; high_score_mean=4.45

## 2. Time-split sanity check

### first_half
- window: 2025-06-09 17:00:00+00:00 → 2025-12-04 11:00:00+00:00; n=4267
- funding_oi: 4h=0.1384%, 8h=0.0978%, 12h=0.0872%, 24h=0.1018%
- v3: 4h=0.4472%, 8h=0.3306%, 12h=0.2101%, 24h=0.1277%
- full: 4h=0.5997%, 8h=0.3843%, 12h=0.4962%, 24h=0.7894%

### second_half
- window: 2025-12-04 12:00:00+00:00 → 2026-05-31 06:00:00+00:00; n=4267
- funding_oi: 4h=-0.1580%, 8h=-0.0543%, 12h=0.5087%, 24h=-0.0121%
- v3: 4h=0.3346%, 8h=0.7741%, 12h=0.5993%, 24h=0.4429%
- full: 4h=0.4000%, 8h=0.8025%, 12h=0.4251%, 24h=0.4690%

### first_third
- window: 2025-06-09 17:00:00+00:00 → 2025-10-06 04:00:00+00:00; n=2844
- funding_oi: 4h=0.0363%, 8h=0.7013%, 12h=0.7570%, 24h=1.4715%
- v3: 4h=0.0241%, 8h=0.5133%, 12h=0.7338%, 24h=1.1082%
- full: 4h=0.1236%, 8h=0.5334%, 12h=0.8628%, 24h=1.0440%

### middle_third
- window: 2025-10-06 05:00:00+00:00 → 2026-02-01 17:00:00+00:00; n=2845
- funding_oi: 4h=0.3526%, 8h=-0.2032%, 12h=-0.2468%, 24h=-0.2574%
- v3: 4h=0.7242%, 8h=0.0191%, 12h=-0.2824%, 24h=-1.2358%
- full: 4h=0.8321%, 8h=-0.0467%, 12h=0.2870%, 24h=-0.6390%

### last_third
- window: 2026-02-01 18:00:00+00:00 → 2026-05-31 06:00:00+00:00; n=2845
- funding_oi: 4h=0.0143%, 8h=0.5110%, 12h=0.6641%, 24h=0.1198%
- v3: 4h=-0.1496%, 8h=0.3716%, 12h=0.0641%, 24h=-0.4428%
- full: 4h=-0.0378%, 8h=0.4316%, 12h=0.0204%, 24h=-0.2557%

## 3. 24h top-quartile controls

- funding: n=2893, q05_24h=-5.3932%, q10_24h=-3.8856%, mean_24h=0.0838%, mae_q05_24h=-7.2437%
- oi: n=6564, q05_24h=-5.3889%, q10_24h=-4.0629%, mean_24h=-0.0544%, mae_q05_24h=-7.3783%
- funding_oi: n=3514, q05_24h=-5.2413%, q10_24h=-3.8193%, mean_24h=0.1355%, mae_q05_24h=-6.9822%
- v3: n=3022, q05_24h=-5.4705%, q10_24h=-4.0303%, mean_24h=0.0519%, mae_q05_24h=-7.6446%
- full: n=2445, q05_24h=-5.0403%, q10_24h=-3.9110%, mean_24h=-0.0037%, mae_q05_24h=-6.8087%
- high_vol: n=2134, q05_24h=-6.6065%, q10_24h=-4.7406%, mean_24h=-0.2189%, mae_q05_24h=-9.8173%
- neg_mom: n=2134, q05_24h=-6.8219%, q10_24h=-4.7164%, mean_24h=-0.3079%, mae_q05_24h=-9.8609%

## 4. Episode concentration

- V3 high-bucket 24h q05 threshold: -5.4994%
- tail event count at/below q05: 143
- top tail days:
  - 2025-09-21: count=16, worst_24h=-8.0131%, avg_24h=-6.6299%
  - 2025-10-10: count=14, worst_24h=-14.6629%, avg_24h=-12.4597%
  - 2026-02-04: count=13, worst_24h=-13.9007%, avg_24h=-8.0288%
  - 2026-02-05: count=11, worst_24h=-14.9718%, avg_24h=-10.0549%
  - 2025-11-20: count=10, worst_24h=-11.0886%, avg_24h=-8.3134%
  - 2025-08-25: count=7, worst_24h=-8.4767%, avg_24h=-7.0667%
  - 2025-08-24: count=6, worst_24h=-9.1298%, avg_24h=-8.0783%
  - 2025-11-18: count=5, worst_24h=-8.4085%, avg_24h=-7.1229%
  - 2025-11-12: count=5, worst_24h=-7.2072%, avg_24h=-6.4641%
  - 2026-03-18: count=5, worst_24h=-6.0049%, avg_24h=-5.6859%

## 5. Toy long-risk filter sanity check

This is not a trading recommendation. It only tests whether high V3 periods are bad times to hold passive long exposure in this sample.

- buy-and-hold return over valid hourly sample: -20.6587%
- flat-during-v3-high return, zero cost: -31.1911%
- buy-and-hold max drawdown: -63.2241%
- flat-during-v3-high max drawdown: -52.7681%
- flat hours: 2845/8534

## 6. Conservative interpretation

- v3 supportive horizons: 0/4
- full supportive horizons: 0/4
- funding+OI supportive horizons: 0/4
- 24h v3 time-split support across halves: 0/2

Conclusion label: `weak_or_reject_v3`

Current decision:

- V3 is cleaner than full score because it removes weak_spot, which was not supported as an incremental component.
- V3 still needs longer data and market-wide controls before any SignalContract.
- If V3 mainly overlaps with OI/funding controls, keep it as a research-only risk filter candidate rather than directional alpha.

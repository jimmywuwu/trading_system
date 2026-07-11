# ETH Leverage Pressure v2 — Component Decomposition

- created_at: 2026-06-01T06:16:21.003226+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_180d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: exploratory_decomposition

## Question

Does the full leverage-pressure score add information beyond funding/OI, or is ETH downside-tail separation mostly explained by simpler components?

## Data / method

- valid hourly events: 4093
- window: 2025-12-11 17:00:00+00:00 → 2026-05-31 05:00:00+00:00
- score variants tested: funding, OI, divergence, weak_spot, funding+OI, funding+OI+divergence, divergence+weak_spot, full.
- primary metric: high bucket minus low bucket 5% forward-return quantile. Negative is supportive: high score has worse left tail.

## 1. Bucket ablation: high-minus-low 5% quantile

### funding
- 4h: diff=0.0532%; low_q05=-2.2772%; high_q05=-2.2240%; low_score_mean=0.00; high_score_mean=1.21
- 8h: diff=0.2370%; low_q05=-3.5211%; high_q05=-3.2841%; low_score_mean=0.00; high_score_mean=1.21
- 12h: diff=0.3429%; low_q05=-4.1913%; high_q05=-3.8484%; low_score_mean=0.00; high_score_mean=1.21
- 24h: diff=1.1157%; low_q05=-6.4235%; high_q05=-5.3078%; low_score_mean=0.00; high_score_mean=1.21

### oi
- 4h: diff=-0.4346%; low_q05=-1.6342%; high_q05=-2.0688%; low_score_mean=0.36; high_score_mean=1.52
- 8h: diff=-0.1881%; low_q05=-2.6052%; high_q05=-2.7933%; low_score_mean=0.36; high_score_mean=1.52
- 12h: diff=-0.0284%; low_q05=-3.3360%; high_q05=-3.3644%; low_score_mean=0.36; high_score_mean=1.52
- 24h: diff=0.9225%; low_q05=-4.9791%; high_q05=-4.0566%; low_score_mean=0.36; high_score_mean=1.52

### divergence
- 4h: diff=0.7212%; low_q05=-2.7117%; high_q05=-1.9905%; low_score_mean=0.00; high_score_mean=1.45
- 8h: diff=0.9243%; low_q05=-3.8303%; high_q05=-2.9060%; low_score_mean=0.00; high_score_mean=1.45
- 12h: diff=0.4728%; low_q05=-4.3211%; high_q05=-3.8483%; low_score_mean=0.00; high_score_mean=1.45
- 24h: diff=0.6256%; low_q05=-6.0823%; high_q05=-5.4568%; low_score_mean=0.00; high_score_mean=1.45

### weak_spot
- 4h: diff=0.7051%; low_q05=-2.5819%; high_q05=-1.8769%; low_score_mean=0.00; high_score_mean=1.55
- 8h: diff=1.1651%; low_q05=-3.8687%; high_q05=-2.7036%; low_score_mean=0.00; high_score_mean=1.55
- 12h: diff=0.7770%; low_q05=-4.4912%; high_q05=-3.7142%; low_score_mean=0.00; high_score_mean=1.55
- 24h: diff=2.2891%; low_q05=-7.0594%; high_q05=-4.7703%; low_score_mean=0.00; high_score_mean=1.55

### funding_oi
- 4h: diff=-0.4979%; low_q05=-1.8467%; high_q05=-2.3446%; low_score_mean=0.53; high_score_mean=2.43
- 8h: diff=-0.2260%; low_q05=-3.1617%; high_q05=-3.3877%; low_score_mean=0.53; high_score_mean=2.43
- 12h: diff=-0.5232%; low_q05=-3.7503%; high_q05=-4.2734%; low_score_mean=0.53; high_score_mean=2.43
- 24h: diff=0.6676%; low_q05=-6.0580%; high_q05=-5.3904%; low_score_mean=0.53; high_score_mean=2.43

### funding_oi_div
- 4h: diff=-0.2692%; low_q05=-2.0249%; high_q05=-2.2941%; low_score_mean=0.71; high_score_mean=3.26
- 8h: diff=-0.0020%; low_q05=-3.2586%; high_q05=-3.2605%; low_score_mean=0.71; high_score_mean=3.26
- 12h: diff=-0.4348%; low_q05=-3.6606%; high_q05=-4.0953%; low_score_mean=0.71; high_score_mean=3.26
- 24h: diff=0.4103%; low_q05=-5.4936%; high_q05=-5.0833%; low_score_mean=0.71; high_score_mean=3.26

### div_weak_spot
- 4h: diff=0.6617%; low_q05=-2.6201%; high_q05=-1.9584%; low_score_mean=0.00; high_score_mean=2.75
- 8h: diff=0.8742%; low_q05=-3.7885%; high_q05=-2.9142%; low_score_mean=0.00; high_score_mean=2.75
- 12h: diff=0.4115%; low_q05=-4.2537%; high_q05=-3.8422%; low_score_mean=0.00; high_score_mean=2.75
- 24h: diff=0.8530%; low_q05=-6.0944%; high_q05=-5.2414%; low_score_mean=0.00; high_score_mean=2.75

### full
- 4h: diff=-0.0990%; low_q05=-1.9735%; high_q05=-2.0725%; low_score_mean=0.74; high_score_mean=4.28
- 8h: diff=0.2392%; low_q05=-3.0905%; high_q05=-2.8513%; low_score_mean=0.74; high_score_mean=4.28
- 12h: diff=-0.1734%; low_q05=-3.5586%; high_q05=-3.7320%; low_score_mean=0.74; high_score_mean=4.28
- 24h: diff=0.5113%; low_q05=-5.3081%; high_q05=-4.7968%; low_score_mean=0.74; high_score_mean=4.28

## 2. 24h top-quartile controls

- funding: n=1152, q05_24h=-5.5909%, q10_24h=-4.1845%, mean_24h=-0.6068%, mae_q05_24h=-6.9894%
- oi: n=3220, q05_24h=-4.9496%, q10_24h=-3.9063%, mean_24h=-0.2035%, mae_q05_24h=-6.7075%
- divergence: n=1644, q05_24h=-5.3131%, q10_24h=-4.0979%, mean_24h=-0.3235%, mae_q05_24h=-7.2233%
- weak_spot: n=1257, q05_24h=-4.8860%, q10_24h=-3.6544%, mean_24h=-0.1061%, mae_q05_24h=-6.3027%
- funding_oi: n=1537, q05_24h=-5.2481%, q10_24h=-3.9611%, mean_24h=-0.4631%, mae_q05_24h=-6.5936%
- funding_oi_div: n=1216, q05_24h=-5.3334%, q10_24h=-4.1537%, mean_24h=-0.6488%, mae_q05_24h=-6.9302%
- div_weak_spot: n=1439, q05_24h=-5.1507%, q10_24h=-3.9605%, mean_24h=-0.2262%, mae_q05_24h=-6.8922%
- full: n=1061, q05_24h=-4.9484%, q10_24h=-3.9208%, mean_24h=-0.3294%, mae_q05_24h=-6.4786%

## 3. Episode concentration check

- full high-bucket 24h q05 threshold: -4.7968%
- tail event count at/below q05: 69
- tail days by concentration:
  - 2026-03-18: count=7, worst_24h=-6.5301%, avg_24h=-5.6974%
  - 2026-02-04: count=6, worst_24h=-11.8781%, avg_24h=-8.4649%
  - 2026-03-25: count=6, worst_24h=-5.3990%, avg_24h=-5.2034%
  - 2026-01-31: count=5, worst_24h=-10.2015%, avg_24h=-9.7603%
  - 2026-02-01: count=4, worst_24h=-8.4763%, avg_24h=-7.2535%
  - 2026-01-29: count=4, worst_24h=-8.0656%, avg_24h=-7.2105%
  - 2025-12-15: count=4, worst_24h=-6.7089%, avg_24h=-6.5189%
  - 2026-02-05: count=3, worst_24h=-8.5877%, avg_24h=-6.9298%
  - 2026-02-14: count=3, worst_24h=-7.0212%, avg_24h=-6.1116%
  - 2026-02-15: count=3, worst_24h=-6.2607%, avg_24h=-5.9152%

## 4. Conservative interpretation

- full score supportive horizons: 2/4
- funding+OI supportive horizons: 3/4
- funding+OI+divergence supportive horizons: 3/4
- If full score does not materially beat funding+OI or funding+OI+divergence, weak spot confirmation is not yet proven as incremental information.
- If the q05 tail is concentrated in a small number of adjacent days, treat this as regime-specific evidence rather than robust alpha.

Conclusion label: `weak_or_reject: full score does not robustly separate ETH downside tails.`
# ETH Leverage Pressure v2 — Component Decomposition

- created_at: 2026-06-01T05:55:09.540715+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_90d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: exploratory_decomposition

## Question

Does the full leverage-pressure score add information beyond funding/OI, or is ETH downside-tail separation mostly explained by simpler components?

## Data / method

- valid hourly events: 1934
- window: 2026-03-09 18:00:00+00:00 → 2026-05-29 07:00:00+00:00
- score variants tested: funding, OI, divergence, weak_spot, funding+OI, funding+OI+divergence, divergence+weak_spot, full.
- primary metric: high bucket minus low bucket 5% forward-return quantile. Negative is supportive: high score has worse left tail.

## 1. Bucket ablation: high-minus-low 5% quantile

### funding
- 4h: diff=0.1815%; low_q05=-2.0584%; high_q05=-1.8769%; low_score_mean=0.00; high_score_mean=1.18
- 8h: diff=0.2839%; low_q05=-2.7733%; high_q05=-2.4893%; low_score_mean=0.00; high_score_mean=1.18
- 12h: diff=0.6828%; low_q05=-3.6734%; high_q05=-2.9906%; low_score_mean=0.00; high_score_mean=1.18
- 24h: diff=-0.0039%; low_q05=-4.2435%; high_q05=-4.2474%; low_score_mean=0.00; high_score_mean=1.18

### oi
- 4h: diff=-0.3554%; low_q05=-1.5432%; high_q05=-1.8986%; low_score_mean=0.34; high_score_mean=1.46
- 8h: diff=0.2150%; low_q05=-2.5147%; high_q05=-2.2997%; low_score_mean=0.34; high_score_mean=1.46
- 12h: diff=-0.2645%; low_q05=-2.7664%; high_q05=-3.0309%; low_score_mean=0.34; high_score_mean=1.46
- 24h: diff=-0.0055%; low_q05=-3.8832%; high_q05=-3.8886%; low_score_mean=0.34; high_score_mean=1.46

### divergence
- 4h: diff=0.1336%; low_q05=-1.8144%; high_q05=-1.6808%; low_score_mean=0.00; high_score_mean=1.45
- 8h: diff=0.2545%; low_q05=-2.6577%; high_q05=-2.4032%; low_score_mean=0.00; high_score_mean=1.45
- 12h: diff=0.4708%; low_q05=-3.2440%; high_q05=-2.7732%; low_score_mean=0.00; high_score_mean=1.45
- 24h: diff=0.6198%; low_q05=-4.2125%; high_q05=-3.5927%; low_score_mean=0.00; high_score_mean=1.45

### weak_spot
- 4h: diff=0.2798%; low_q05=-1.9067%; high_q05=-1.6269%; low_score_mean=0.00; high_score_mean=1.57
- 8h: diff=0.6318%; low_q05=-2.7524%; high_q05=-2.1206%; low_score_mean=0.00; high_score_mean=1.57
- 12h: diff=0.2886%; low_q05=-3.3223%; high_q05=-3.0337%; low_score_mean=0.00; high_score_mean=1.57
- 24h: diff=0.5623%; low_q05=-4.4006%; high_q05=-3.8382%; low_score_mean=0.00; high_score_mean=1.57

### funding_oi
- 4h: diff=-0.3293%; low_q05=-1.6125%; high_q05=-1.9418%; low_score_mean=0.49; high_score_mean=2.42
- 8h: diff=-0.2098%; low_q05=-2.4948%; high_q05=-2.7045%; low_score_mean=0.49; high_score_mean=2.42
- 12h: diff=-0.5815%; low_q05=-2.8480%; high_q05=-3.4295%; low_score_mean=0.49; high_score_mean=2.42
- 24h: diff=-0.1831%; low_q05=-4.0556%; high_q05=-4.2387%; low_score_mean=0.49; high_score_mean=2.42

### funding_oi_div
- 4h: diff=-0.6343%; low_q05=-1.4001%; high_q05=-2.0343%; low_score_mean=0.71; high_score_mean=3.22
- 8h: diff=-0.2007%; low_q05=-2.3397%; high_q05=-2.5403%; low_score_mean=0.71; high_score_mean=3.22
- 12h: diff=-0.5015%; low_q05=-2.7221%; high_q05=-3.2236%; low_score_mean=0.71; high_score_mean=3.22
- 24h: diff=-0.7576%; low_q05=-3.5000%; high_q05=-4.2576%; low_score_mean=0.71; high_score_mean=3.22

### div_weak_spot
- 4h: diff=0.2197%; low_q05=-1.8466%; high_q05=-1.6269%; low_score_mean=0.00; high_score_mean=2.75
- 8h: diff=0.5124%; low_q05=-2.6783%; high_q05=-2.1660%; low_score_mean=0.00; high_score_mean=2.75
- 12h: diff=0.1743%; low_q05=-3.2067%; high_q05=-3.0324%; low_score_mean=0.00; high_score_mean=2.75
- 24h: diff=0.5391%; low_q05=-4.2435%; high_q05=-3.7044%; low_score_mean=0.00; high_score_mean=2.75

### full
- 4h: diff=-0.4150%; low_q05=-1.4618%; high_q05=-1.8769%; low_score_mean=0.74; high_score_mean=4.24
- 8h: diff=-0.1872%; low_q05=-2.2795%; high_q05=-2.4667%; low_score_mean=0.74; high_score_mean=4.24
- 12h: diff=-0.4583%; low_q05=-2.7304%; high_q05=-3.1887%; low_score_mean=0.74; high_score_mean=4.24
- 24h: diff=-0.5426%; low_q05=-3.5000%; high_q05=-4.0426%; low_score_mean=0.74; high_score_mean=4.24

## 2. 24h top-quartile controls

- funding: n=547, q05_24h=-4.0506%, q10_24h=-3.1727%, mean_24h=-0.3227%, mae_q05_24h=-5.1342%
- oi: n=1506, q05_24h=-4.2144%, q10_24h=-3.3348%, mean_24h=-0.0439%, mae_q05_24h=-5.2814%
- divergence: n=783, q05_24h=-4.0253%, q10_24h=-3.2847%, mean_24h=-0.0106%, mae_q05_24h=-5.1997%
- weak_spot: n=613, q05_24h=-3.6893%, q10_24h=-3.0397%, mean_24h=0.0868%, mae_q05_24h=-4.9743%
- funding_oi: n=686, q05_24h=-4.1554%, q10_24h=-3.3984%, mean_24h=-0.3098%, mae_q05_24h=-5.2558%
- funding_oi_div: n=551, q05_24h=-4.2540%, q10_24h=-3.4642%, mean_24h=-0.4395%, mae_q05_24h=-5.2614%
- div_weak_spot: n=696, q05_24h=-3.8766%, q10_24h=-3.0673%, mean_24h=0.0832%, mae_q05_24h=-5.0614%
- full: n=503, q05_24h=-4.2345%, q10_24h=-3.2522%, mean_24h=-0.1759%, mae_q05_24h=-5.2113%

## 3. Episode concentration check

- full high-bucket 24h q05 threshold: -4.0426%
- tail event count at/below q05: 33
- tail days by concentration:
  - 2026-03-25: count=6, worst_24h=-5.3311%, avg_24h=-4.7036%
  - 2026-03-18: count=5, worst_24h=-6.0049%, avg_24h=-5.6859%
  - 2026-05-27: count=5, worst_24h=-4.7603%, avg_24h=-4.4157%
  - 2026-03-21: count=4, worst_24h=-5.0017%, avg_24h=-4.4333%
  - 2026-03-26: count=3, worst_24h=-4.6744%, avg_24h=-4.4738%
  - 2026-03-17: count=2, worst_24h=-6.2613%, avg_24h=-6.0293%
  - 2026-04-11: count=2, worst_24h=-5.0950%, avg_24h=-4.8185%
  - 2026-04-01: count=2, worst_24h=-4.8904%, avg_24h=-4.6090%
  - 2026-05-22: count=2, worst_24h=-4.3348%, avg_24h=-4.3260%
  - 2026-05-17: count=1, worst_24h=-4.8994%, avg_24h=-4.8994%

## 4. Conservative interpretation

- full score supportive horizons: 4/4
- funding+OI supportive horizons: 4/4
- funding+OI+divergence supportive horizons: 4/4
- If full score does not materially beat funding+OI or funding+OI+divergence, weak spot confirmation is not yet proven as incremental information.
- If the q05 tail is concentrated in a small number of adjacent days, treat this as regime-specific evidence rather than robust alpha.

Conclusion label: `research_only_needs_revision: ETH tail separation exists, but incremental full-score value is not proven.`
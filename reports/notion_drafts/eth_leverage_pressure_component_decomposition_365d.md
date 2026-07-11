# ETH Leverage Pressure v2 — Component Decomposition

- created_at: 2026-06-01T06:43:15.414810+00:00
- fixture: `/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_365d.jsonl`
- created_by: QUANT
- created_by_agent: JAQUAN
- status: exploratory_decomposition

## Question

Does the full leverage-pressure score add information beyond funding/OI, or is ETH downside-tail separation mostly explained by simpler components?

## Data / method

- valid hourly events: 8534
- window: 2025-06-09 17:00:00+00:00 → 2026-05-31 06:00:00+00:00
- score variants tested: funding, OI, divergence, weak_spot, funding+OI, funding+OI+divergence, divergence+weak_spot, full.
- primary metric: high bucket minus low bucket 5% forward-return quantile. Negative is supportive: high score has worse left tail.

## 1. Bucket ablation: high-minus-low 5% quantile

### funding
- 4h: diff=0.3194%; low_q05=-2.4560%; high_q05=-2.1366%; low_score_mean=0.00; high_score_mean=1.72
- 8h: diff=0.3921%; low_q05=-3.5645%; high_q05=-3.1724%; low_score_mean=0.00; high_score_mean=1.72
- 12h: diff=0.2876%; low_q05=-4.2059%; high_q05=-3.9184%; low_score_mean=0.00; high_score_mean=1.72
- 24h: diff=0.3159%; low_q05=-5.7730%; high_q05=-5.4571%; low_score_mean=0.00; high_score_mean=1.72

### oi
- 4h: diff=0.0251%; low_q05=-1.9874%; high_q05=-1.9624%; low_score_mean=0.31; high_score_mean=1.48
- 8h: diff=0.4011%; low_q05=-3.0570%; high_q05=-2.6558%; low_score_mean=0.31; high_score_mean=1.48
- 12h: diff=0.7140%; low_q05=-3.9574%; high_q05=-3.2435%; low_score_mean=0.31; high_score_mean=1.48
- 24h: diff=1.0452%; low_q05=-5.4271%; high_q05=-4.3819%; low_score_mean=0.31; high_score_mean=1.48

### divergence
- 4h: diff=0.4449%; low_q05=-2.4909%; high_q05=-2.0460%; low_score_mean=0.00; high_score_mean=1.45
- 8h: diff=0.2615%; low_q05=-3.4585%; high_q05=-3.1970%; low_score_mean=0.00; high_score_mean=1.45
- 12h: diff=0.0919%; low_q05=-4.1709%; high_q05=-4.0790%; low_score_mean=0.00; high_score_mean=1.45
- 24h: diff=0.0031%; low_q05=-5.6514%; high_q05=-5.6483%; low_score_mean=0.00; high_score_mean=1.45

### weak_spot
- 4h: diff=0.4156%; low_q05=-2.4242%; high_q05=-2.0086%; low_score_mean=0.00; high_score_mean=1.53
- 8h: diff=0.1758%; low_q05=-3.3038%; high_q05=-3.1280%; low_score_mean=0.00; high_score_mean=1.53
- 12h: diff=0.2871%; low_q05=-4.0831%; high_q05=-3.7960%; low_score_mean=0.00; high_score_mean=1.53
- 24h: diff=0.7906%; low_q05=-5.7185%; high_q05=-4.9280%; low_score_mean=0.00; high_score_mean=1.53

### funding_oi
- 4h: diff=0.1533%; low_q05=-2.3078%; high_q05=-2.1545%; low_score_mean=0.52; high_score_mean=2.77
- 8h: diff=0.3289%; low_q05=-3.4040%; high_q05=-3.0751%; low_score_mean=0.52; high_score_mean=2.77
- 12h: diff=0.2607%; low_q05=-4.0557%; high_q05=-3.7950%; low_score_mean=0.52; high_score_mean=2.77
- 24h: diff=0.3852%; low_q05=-5.7681%; high_q05=-5.3830%; low_score_mean=0.52; high_score_mean=2.77

### funding_oi_div
- 4h: diff=0.3581%; low_q05=-2.5494%; high_q05=-2.1913%; low_score_mean=0.71; high_score_mean=3.54
- 8h: diff=0.4646%; low_q05=-3.6257%; high_q05=-3.1611%; low_score_mean=0.71; high_score_mean=3.54
- 12h: diff=0.2782%; low_q05=-4.2715%; high_q05=-3.9933%; low_score_mean=0.71; high_score_mean=3.54
- 24h: diff=0.2713%; low_q05=-5.7707%; high_q05=-5.4994%; low_score_mean=0.71; high_score_mean=3.54

### div_weak_spot
- 4h: diff=0.2578%; low_q05=-2.3336%; high_q05=-2.0758%; low_score_mean=0.00; high_score_mean=2.74
- 8h: diff=0.0354%; low_q05=-3.2972%; high_q05=-3.2618%; low_score_mean=0.00; high_score_mean=2.74
- 12h: diff=0.0921%; low_q05=-3.9970%; high_q05=-3.9048%; low_score_mean=0.00; high_score_mean=2.74
- 24h: diff=0.1355%; low_q05=-5.4661%; high_q05=-5.3306%; low_score_mean=0.00; high_score_mean=2.74

### full
- 4h: diff=0.4992%; low_q05=-2.5078%; high_q05=-2.0086%; low_score_mean=0.78; high_score_mean=4.45
- 8h: diff=0.6470%; low_q05=-3.5341%; high_q05=-2.8870%; low_score_mean=0.78; high_score_mean=4.45
- 12h: diff=0.5074%; low_q05=-4.1948%; high_q05=-3.6874%; low_score_mean=0.78; high_score_mean=4.45
- 24h: diff=0.7997%; low_q05=-5.6823%; high_q05=-4.8826%; low_score_mean=0.78; high_score_mean=4.45

## 2. 24h top-quartile controls

- funding: n=2893, q05_24h=-5.3932%, q10_24h=-3.8856%, mean_24h=0.0838%, mae_q05_24h=-7.2437%
- oi: n=6564, q05_24h=-5.3889%, q10_24h=-4.0629%, mean_24h=-0.0544%, mae_q05_24h=-7.3783%
- divergence: n=3426, q05_24h=-5.4709%, q10_24h=-4.1096%, mean_24h=-0.0546%, mae_q05_24h=-7.5389%
- weak_spot: n=2592, q05_24h=-5.1263%, q10_24h=-3.8437%, mean_24h=0.0040%, mae_q05_24h=-7.0526%
- funding_oi: n=3514, q05_24h=-5.2413%, q10_24h=-3.8193%, mean_24h=0.1355%, mae_q05_24h=-6.9822%
- funding_oi_div: n=3022, q05_24h=-5.4705%, q10_24h=-4.0303%, mean_24h=0.0519%, mae_q05_24h=-7.6446%
- div_weak_spot: n=2990, q05_24h=-5.3315%, q10_24h=-3.9951%, mean_24h=-0.0375%, mae_q05_24h=-7.3751%
- full: n=2445, q05_24h=-5.0403%, q10_24h=-3.9110%, mean_24h=-0.0037%, mae_q05_24h=-6.8087%

## 3. Episode concentration check

- full high-bucket 24h q05 threshold: -4.8826%
- tail event count at/below q05: 143
- tail days by concentration:
  - 2025-09-21: count=9, worst_24h=-8.0131%, avg_24h=-6.7470%
  - 2025-10-10: count=7, worst_24h=-14.6629%, avg_24h=-12.4713%
  - 2026-02-04: count=7, worst_24h=-13.9007%, avg_24h=-8.8392%
  - 2025-11-20: count=6, worst_24h=-11.0886%, avg_24h=-8.7670%
  - 2025-11-30: count=6, worst_24h=-9.4633%, avg_24h=-7.5699%
  - 2025-11-02: count=6, worst_24h=-7.0139%, avg_24h=-6.2439%
  - 2026-02-05: count=5, worst_24h=-10.0914%, avg_24h=-8.0144%
  - 2025-07-31: count=5, worst_24h=-6.3644%, avg_24h=-5.6302%
  - 2026-03-18: count=5, worst_24h=-6.0049%, avg_24h=-5.6859%
  - 2025-10-07: count=5, worst_24h=-5.8115%, avg_24h=-5.4281%

## 4. Conservative interpretation

- full score supportive horizons: 0/4
- funding+OI supportive horizons: 0/4
- funding+OI+divergence supportive horizons: 0/4
- If full score does not materially beat funding+OI or funding+OI+divergence, weak spot confirmation is not yet proven as incremental information.
- If the q05 tail is concentrated in a small number of adjacent days, treat this as regime-specific evidence rather than robust alpha.

Conclusion label: `weak_or_reject: full score does not robustly separate ETH downside tails.`
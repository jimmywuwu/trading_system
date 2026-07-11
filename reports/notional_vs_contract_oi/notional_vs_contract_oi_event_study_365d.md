# Notional OI vs Contract OI Deleveraging Classifier — 365d First Pass

- Fixture: `data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl`
- Venue/symbols: Bybit BTCUSDT, ETHUSDT
- Aggregation: hourly last close/OI
- Event window: 4h changes; outcome horizons: 4h/24h/48h/72h
- Cluster rule: 24h cooldown

## Data quality
- BTCUSDT: raw OI hourly coverage `1.000`, raw OI hours `8761/8761`, gaps>1h `0`, max gap `0`
- ETHUSDT: raw OI hourly coverage `1.000`, raw OI hours `8761/8761`, gaps>1h `0`, max gap `0`

## Event definitions
- A_true_deleverage: 4h price <= -0.75%, notional OI <= -1.00%, raw/contract OI <= -0.50%
- B_passive_notional_shrink: 4h price <= -0.75%, notional OI <= -1.00%, raw/contract OI > -0.25%
- C_short_build_or_sticky_leverage: 4h price <= -0.75%, raw/contract OI >= +0.50%
- D_risk_on_leverage_build: 4h price >= +0.75%, raw/contract OI >= +0.50%, notional OI >= +1.00%

## BTCUSDT
- Baseline 24h abs return mean: `1.55%`
- A_true_deleverage: clustered `145` / raw `464`; 24h mean return `0.05%`, 24h abs `1.71%`, 24h max DD `-1.45%`
- B_passive_notional_shrink: clustered `85` / raw `147`; 24h mean return `0.09%`, 24h abs `2.01%`, 24h max DD `-1.54%`
- C_short_build_or_sticky_leverage: clustered `123` / raw `436`; 24h mean return `-0.16%`, 24h abs `1.66%`, 24h max DD `-1.56%`
- D_risk_on_leverage_build: clustered `136` / raw `475`; 24h mean return `-0.05%`, 24h abs `1.66%`, 24h max DD `-1.50%`

## ETHUSDT
- Baseline 24h abs return mean: `2.50%`
- A_true_deleverage: clustered `203` / raw `838`; 24h mean return `-0.07%`, 24h abs `2.62%`, 24h max DD `-2.17%`
- B_passive_notional_shrink: clustered `113` / raw `233`; 24h mean return `-0.08%`, 24h abs `2.60%`, 24h max DD `-2.28%`
- C_short_build_or_sticky_leverage: clustered `160` / raw `580`; 24h mean return `-0.33%`, 24h abs `2.50%`, 24h max DD `-2.28%`
- D_risk_on_leverage_build: clustered `192` / raw `771`; 24h mean return `-0.27%`, 24h abs `2.76%`, 24h max DD `-2.27%`

## First-pass interpretation
- This is a classifier/risk-regime study, not a trading signal or Trader handoff.
- Use the JSON for full quantiles and sample events; chat summary should stay conservative.
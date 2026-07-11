# OI Contraction / Deleveraging Volatility Regime — 365d First-Pass Event Study

## Setup

- Fixture: `data/bybit_leverage_pressure_fixture_365d.jsonl`
- Symbols: BTCUSDT, ETHUSDT
- Aggregation: hourly last perp close and hourly OI
- Event: 4h OI change bottom decile; controls include top-decile OI expansion, volatility-matched, return-matched, and vol+return+UTC-hour matched non-events.
- Primary horizons: 4h and 24h; secondary: 1h, 8h, 48h.

## BTCUSDT

- Window: `2025-06-01T14:00:00+00:00` to `2026-06-01T14:00:00+00:00`
- Eligible hourly rows: 8693
- 4h OI change thresholds: bottom 10% `-2.2065%`, top 10% `2.2731%`

### Baseline mean abs forward return
- 4h: 0.5943%
- 24h: 1.5466%
- 48h: 2.2058%

### OI contraction bottom decile

- Raw events: 870; 24h-cooldown clustered episodes: 191; matched-control candidates: 1906
- 4h abs return mean: event `0.6612%` vs matched `0.6695%` vs clustered `0.6723%` vs baseline `0.5943%`
- 24h abs return mean: event `1.7833%` vs matched `1.6886%` vs clustered `1.6656%` vs baseline `1.5466%`
- 48h abs return mean: event `2.4983%` vs matched `2.3466%` vs clustered `2.3171%` vs baseline `2.2058%`
- 24h signed return q05/q95: `-3.5789%` / `4.5392%`

### OI expansion top decile

- Raw events: 870; 24h-cooldown clustered episodes: 187; matched-control candidates: 1944
- 4h abs return mean: event `0.6922%` vs matched `0.6558%` vs clustered `0.6276%` vs baseline `0.5943%`
- 24h abs return mean: event `1.5868%` vs matched `1.6909%` vs clustered `1.6852%` vs baseline `1.5466%`
- 48h abs return mean: event `2.2332%` vs matched `2.3004%` vs clustered `2.3431%` vs baseline `2.2058%`
- 24h signed return q05/q95: `-3.5438%` / `3.0387%`

## ETHUSDT

- Window: `2025-06-01T14:00:00+00:00` to `2026-06-01T14:00:00+00:00`
- Eligible hourly rows: 8693
- 4h OI change thresholds: bottom 10% `-2.8378%`, top 10% `2.8749%`

### Baseline mean abs forward return
- 4h: 0.9226%
- 24h: 2.4906%
- 48h: 3.6633%

### OI contraction bottom decile

- Raw events: 870; 24h-cooldown clustered episodes: 197; matched-control candidates: 1538
- 4h abs return mean: event `1.0226%` vs matched `0.9765%` vs clustered `1.1044%` vs baseline `0.9226%`
- 24h abs return mean: event `2.7468%` vs matched `2.6168%` vs clustered `2.8003%` vs baseline `2.4906%`
- 48h abs return mean: event `3.9264%` vs matched `3.7801%` vs clustered `3.9062%` vs baseline `3.6633%`
- 24h signed return q05/q95: `-5.8506%` / `6.6260%`

### OI expansion top decile

- Raw events: 870; 24h-cooldown clustered episodes: 184; matched-control candidates: 1679
- 4h abs return mean: event `1.0296%` vs matched `0.9945%` vs clustered `1.0460%` vs baseline `0.9226%`
- 24h abs return mean: event `2.6690%` vs matched `2.5926%` vs clustered `2.7418%` vs baseline `2.4906%`
- 48h abs return mean: event `3.8151%` vs matched `3.7595%` vs clustered `3.9935%` vs baseline `3.6633%`
- 24h signed return q05/q95: `-5.4044%` / `5.9322%`

## First-pass conclusion

- BTC shows a clear raw 24h absolute-return lift after bottom-decile OI contraction, but much of it weakens when matched on recent volatility, recent 4h return, and UTC hour.
- ETH shows a smaller raw lift; after matching, the incremental effect is marginal and not obviously stronger than controls.
- Non-overlapping 24h episode clustering reduces sample size materially; BTC still has elevated 24h abs return, ETH is mixed.
- This is not enough for SignalContract or Trader handoff. It remains a Research Only / continue-if-controls-improve candidate.

## Recommended next step

Tighten the event study before requesting larger data: use rolling 90d percentile thresholds, explicit episode-level bootstrap/confidence intervals, and a recent-vol/return matched sampling procedure with equalized counts. If the matched incremental effect remains small, reject as redundant with realized-volatility controls.
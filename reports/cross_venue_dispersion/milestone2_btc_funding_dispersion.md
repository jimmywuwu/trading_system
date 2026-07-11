# Milestone 2 BTC funding dispersion first-pass
Created: `2026-06-17T00:59:23Z`
## Exact command
```bash
python3 reports/cross_venue_dispersion/run_milestone2_funding_dispersion.py --days 30
```
## Scope
- Asset: BTC
- Venues: Bybit, OKX, Hyperliquid
- Rail: replay-safe historical funding only
- Explicit exclusions: current-state OI as historical evidence; Trader handoff; regulated historical OI/funding claims.
## Counts
- Bybit funding rows: `91`
- OKX funding rows: `91`
- Hyperliquid funding rows: `720`
- Common three-venue timestamps: `90`
- Top-decile dispersion events: `9`
## Dispersion stats
- median range: `0.0000590555`
- p75 range: `0.0000839916`
- p90 event threshold: `0.0000901538`
- max range: `0.0001559339`
- mean 8h post-event dispersion change: `-0.0000468675`
- mean 24h post-event dispersion change: `-0.0000551513`
## Conservative decision
`first_pass_completed_research_only` — Funding-history-only cross-venue dispersion fixture is sufficient for a conservative first-pass descriptive/event study. This is not a tradable signal and does not support Trader handoff.
## DataProvider TODO
- Persist raw funding-history payloads and normalized rows with source endpoint, event_ts_utc, observed_at_utc, raw payload hash.
- Add deterministic pagination tests for Bybit funding history and OKX funding-rate-history beyond a single latest page before extending horizon >30d.
- Keep current-state OI excluded from historical evidence until a forward archive exists; archived snapshots are replay-safe only from observed_at_utc onward.
- If price-return event study is desired, explicitly approve/add replay-safe candle rails per venue rather than silently mixing unreviewed endpoints.
## Next gate
QUANT may review funding-only persistence/convergence after DataProvider turns this disposable pull into a reproducible fixture; no strategy/sizing gate yet.
## Tail sample of aligned rows
```json
[
  {
    "dispersion_range": 8.14247750096e-05,
    "dispersion_std": 3.8090495661580244e-05,
    "event_ms": 1781510400000,
    "event_ts_utc": "2026-06-15T08:00:00Z",
    "max_abs_pair_spread": 8.14247750096e-05,
    "mean_rate": -1.5061591669866666e-05,
    "rates": {
      "bybit": 1.124e-05,
      "hyperliquid": 1.25e-05,
      "okx": -6.89247750096e-05
    }
  },
  {
    "dispersion_range": 7.47309810096e-05,
    "dispersion_std": 3.277226056514127e-05,
    "event_ms": 1781539200000,
    "event_ts_utc": "2026-06-15T16:00:00Z",
    "max_abs_pair_spread": 7.47309810096e-05,
    "mean_rate": -2.8075393669866665e-05,
    "rates": {
      "bybit": -1.115e-05,
      "hyperliquid": 8.274e-07,
      "okx": -7.39035810096e-05
    }
  },
  {
    "dispersion_range": 4.07699107801e-05,
    "dispersion_std": 1.675159593966898e-05,
    "event_ms": 1781568000000,
    "event_ts_utc": "2026-06-16T00:00:00Z",
    "max_abs_pair_spread": 4.07699107801e-05,
    "mean_rate": 5.946196406633334e-06,
    "rates": {
      "bybit": 2.767e-05,
      "hyperliquid": 3.2685e-06,
      "okx": -1.30999107801e-05
    }
  },
  {
    "dispersion_range": 6.02471212018e-05,
    "dispersion_std": 2.5994703279650193e-05,
    "event_ms": 1781596800000,
    "event_ts_utc": "2026-06-16T08:00:00Z",
    "max_abs_pair_spread": 6.02471212018e-05,
    "mean_rate": -3.505277373393334e-05,
    "rates": {
      "bybit": -4.695e-05,
      "hyperliquid": 1.0194e-06,
      "okx": -5.92277212018e-05
    }
  },
  {
    "dispersion_range": 5.9884330984300004e-05,
    "dispersion_std": 2.472354599118396e-05,
    "event_ms": 1781625600000,
    "event_ts_utc": "2026-06-16T16:00:00Z",
    "max_abs_pair_spread": 5.9884330984300004e-05,
    "mean_rate": 1.6473523005233332e-05,
    "rates": {
      "bybit": 4.902e-05,
      "hyperliquid": 1.12649e-05,
      "okx": -1.08643309843e-05
    }
  }
]
```

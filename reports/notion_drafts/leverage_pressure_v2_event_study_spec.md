# Leverage Pressure v2 Event Study Spec

<callout icon="🧪" color="blue_bg">
This spec defines the next empirical pass for the leverage-pressure research. It fixes the question, score construction, controls, and rejection gates before any broad threshold search.
</callout>

## Metadata

- created_at: 2026-05-30T15:13:18+08:00
- created_by: QUANT
- created_by_agent: JAQUAN
- related_revision_note: `Leverage Pressure v2 Research Revision Note`
- status: draft_for_empirical_pass
- validation_note: artifact CLI `quant_tools.artifacts` unavailable on current branch; this is a Markdown Quant spec, not CLI-validated YAML.

## 1. Research question

```text
Does a leverage-fragility score built from funding pressure, OI expansion, perp/spot divergence, and weak spot confirmation monotonically identify worse future downside tails over 4h-24h horizons?
```

Primary output is evidence about conditional downside distribution, not a tradeable short strategy.

## 2. Universe

First pass only:

- BTCUSDT
- ETHUSDT

Rationale: liquid majors reduce microstructure noise and keep the first falsification test clean.

## 3. Required observations

Minimum observations visible by each `signal_time`:

- linear perp candle: open/high/low/close/volume/turnover
- spot candle: open/high/low/close/volume/turnover
- perp open interest snapshot
- settled perp funding rate
- derived perp-spot basis if available

Optional but excluded from first pass unless separately reviewed:

- predicted funding snapshots
- liquidation prints
- orderbook depth / spread

## 4. Feature construction

All rolling features must use only observations with `observed_at <= signal_time`.

Candidate fixed windows:

- feature cadence: 1h
- rolling baseline: 14d if fixture length supports it; otherwise label as insufficient for robust z-score/percentile work
- OI change windows: 4h, 8h, 24h
- forward horizons: 4h, 8h, 12h, 24h

### Components

```text
funding_pressure_component:
  funding percentile or z-score, using settled funding only in first pass

oi_expansion_component:
  OI percent change over fixed lookback

perp_spot_divergence_component:
  perp return - spot return, or basis expansion

weak_spot_confirmation_component:
  spot volume percentile not expanding while perp pressure rises
```

Composite score:

```text
score = funding_pressure + oi_expansion + perp_spot_divergence + weak_spot_confirmation
```

No optimized weights in first pass. Use equal weights or bucket each component into ordinal bins.

## 5. Bucket test

For each symbol and horizon:

1. Compute score at each eligible `signal_time`.
2. Split into buckets by score quantile, e.g. low / mid / high or quintiles if enough samples.
3. Compare future downside distribution by bucket.
4. Test whether high-score buckets have worse downside tails than low-score buckets.

Primary metrics:

- event count
- mean forward return
- median forward return
- 5% forward-return quantile
- 10% forward-return quantile
- max adverse excursion
- probability of return below volatility-scaled downside threshold
- percentage of effect contributed by top crash episodes

## 6. Controls

Run the same distribution table for:

- unconditional periods
- high funding only
- rising OI only
- funding + OI without spot confirmation
- realized volatility buckets
- recent momentum buckets
- bull / bear / sideways regime buckets
- same-frequency random timestamp sample if feasible

Key gate:

```text
full score must add tail separation beyond funding + OI and volatility/momentum controls.
```

## 7. Regime attribution

At minimum label periods by:

- recent trend: up / down / sideways
- realized volatility: low / mid / high
- crisis/liquidation-like period if identifiable from returns

Do not claim structural alpha if results are just bear-market proxy or one crash replay.

## 8. Acceptance / rejection gates

### Supports v2 if

- high-score bucket has worse 5%/10% downside quantiles across multiple horizons
- BTC and ETH are directionally consistent
- full score beats high-funding-only and funding+OI controls
- result is not dominated by one episode
- data coverage is adequate and replay-safe enough for research-only claims

### Needs revision if

- event count is too low
- bucket ordering is unstable
- settled funding is too sparse/late for the mechanism
- weak spot confirmation adds ambiguous value

### Reject if

- no monotonic downside-tail separation
- controls explain the effect
- only one tuned threshold works
- point-in-time semantics fail
- result is single-crash dominated

## 9. Implementation boundary

This empirical pass may produce:

- `SignalResearchResult` / research report
- revised `ObservationRequirements` if predicted funding is needed
- future `SignalContract` only if risk-filter semantics survive

It must not produce:

- production strategy
- sizing rule
- Trader handoff
- live trading recommendation

## 10. First-pass expected conclusion format

Use conservative labels:

```text
reject | research_only_needs_revision | research_only_risk_filter_candidate
```

No `paper_trade_candidate` unless the distributional evidence, data review, controls, and cost/execution caveats all clear the gate.

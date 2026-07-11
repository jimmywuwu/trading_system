## First-pass 365d event-study result — 2026-06-01

<callout icon="⚠️" color="yellow_bg">
	**Important data caveat:** the candle fixture covers 8761 hourly bars, but the OI series only has 3294 distinct hourly buckets per symbol (~37.6% hourly coverage), with 182 gaps >1h and max OI gap around 31h. So this is not yet a clean full-year OI study. Treat it as a first-pass on available OI windows, not a promotion-quality validation.
</callout>

### Test design

- Fixture: `data/bybit_leverage_pressure_fixture_365d.jsonl`
- Symbols: BTCUSDT, ETHUSDT
- Event: 4h OI change bottom decile
- Controls:
	- unconditional baseline
	- OI expansion top decile
	- matched non-events by recent 24h realized volatility, recent 4h return, and UTC hour
	- 24h cooldown clustering to reduce repeated counting of the same episode
- Primary horizons: 4h and 24h
- Secondary horizon: 48h

### Data coverage

```yaml
BTCUSDT:
  fixture_hours: 8761
  oi_distinct_hours: 3294
  oi_hour_coverage_ratio: 37.6%
  eligible_event_rows: 2534
  oi_gaps_gt_1h: 182
  max_oi_gap_h: 31
ETHUSDT:
  fixture_hours: 8761
  oi_distinct_hours: 3294
  oi_hour_coverage_ratio: 37.6%
  eligible_event_rows: 2534
  oi_gaps_gt_1h: 182
  max_oi_gap_h: 31
```

This matters because the OI observations are not uniformly available across the full calendar. UTC-hour matching helps, but does not fully solve fixture coverage bias.

### BTCUSDT result

```yaml
baseline_abs_return:
  4h: 0.5187%
  24h: 1.5895%
  48h: 2.2928%

oi_contraction_bottom_decile:
  raw_events: 254
  clustered_24h_episodes: 90
  event_abs_return:
    4h: 0.6452%
    24h: 2.0182%
    48h: 2.9282%
  matched_control_abs_return:
    4h: 0.6518%
    24h: 1.8608%
    48h: 2.6606%
  clustered_abs_return:
    4h: 0.6940%
    24h: 1.7190%
    48h: 2.7185%
  bootstrap_event_minus_matched_95ci:
    4h: [-0.1253%, 0.1100%]
    24h: [-0.1859%, 0.5043%]
    48h: [-0.1991%, 0.7181%]
```

BTC has raw uplift, especially at 24h/48h. But after matching recent volatility, recent return, and UTC hour, the bootstrap interval still crosses zero. So the incremental value is suggestive but not robust.

### ETHUSDT result

```yaml
baseline_abs_return:
  4h: 0.7781%
  24h: 2.4454%
  48h: 3.7956%

oi_contraction_bottom_decile:
  raw_events: 254
  clustered_24h_episodes: 95
  event_abs_return:
    4h: 0.9410%
    24h: 2.7895%
    48h: 4.2499%
  matched_control_abs_return:
    4h: 1.0529%
    24h: 2.5295%
    48h: 3.9791%
  clustered_abs_return:
    4h: 1.0010%
    24h: 2.5894%
    48h: 3.9228%
  bootstrap_event_minus_matched_95ci:
    4h: [-0.3018%, 0.0771%]
    24h: [-0.1763%, 0.7068%]
    48h: [-0.3959%, 0.9369%]
```

ETH also has raw uplift at 24h/48h, but 4h is worse than matched controls, and 24h/48h intervals cross zero. This is weaker than BTC.

### Interpretation

Current evidence says:

```text
OI contraction is associated with higher future realized movement in raw comparisons,
but much of that association may be explained by recent volatility, recent return, UTC session, and event clustering.
```

So the research is not dead, but it is not yet strong.

### Gate decision

```yaml
status: research_only_needs_revision
signal_contract: no
trader_handoff: no
larger_data_request: not_yet
```

I would not ask DataProvider for a 2-3y multi-venue build yet. First we should fix the first-pass design:

1. use rolling 90d percentile thresholds instead of full-sample thresholds;
2. run episode-level bootstrap instead of raw hourly-event bootstrap;
3. use equal-count matched sampling by recent volatility, recent return, and UTC hour;
4. verify whether the OI coverage gaps are a fixture limitation or expected Bybit endpoint behavior;
5. only continue if BTC and ETH still show incremental 24h/48h volatility information after those controls.

### Conservative conclusion

This is currently a **plausible market-structure note**, not an alpha or tradeable risk filter.

The useful version would need to prove that OI contraction adds information beyond simply saying: "the market was already volatile recently." Right now that remains unproven. Annoying, but that is exactly the distinction that keeps us from worshipping a dressed-up volatility proxy.

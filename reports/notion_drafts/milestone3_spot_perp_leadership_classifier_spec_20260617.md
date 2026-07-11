# Milestone 3 — Spot-led vs Perp-led Leadership Classifier Spec

Created: `2026-06-17T01:30:34Z`  
Created by: HERMES for JAQUAN/QUANT  
Status: `ready_for_data_provider_handoff__quant_backtest_blocked_until_fixture`  
Roadmap reference: `reports/notion_drafts/crypto_structural_inefficiency_research_roadmap.md`  
M2 evidence checked:
- `reports/cross_venue_dispersion/milestone2_btc_funding_dispersion.md`
- `reports/cross_venue_dispersion/milestone2_feasibility_data_provider_handoff.md`

## 0. M2 gate check

Milestone 2 has a completed funding-history-only first pass:

```yaml
m2_decision: first_pass_completed_research_only
m2_scope: BTC, Bybit/OKX/Hyperliquid, replay-safe historical funding only
m2_common_three_venue_timestamps: 90
m2_top_decile_dispersion_events: 9
m2_trader_handoff: false
```

The M2 output is sufficient to open a mechanism-first M3 specification, but not sufficient to run a spot/perp leadership backtest. M2 also documents DataProvider TODOs that should carry forward:

- persist raw payloads + normalized rows with `source_endpoint`, `event_ts_utc`, `observed_at_utc`, and raw payload hash;
- add deterministic pagination tests before extending horizons;
- keep current-state OI out of historical evidence until archived;
- do not silently mix unreviewed candle/price endpoints into event studies.

Implication: M3 should be handed to DataProvider as an observation/fixture build first. QUANT should not convert this into strategy research until the fixture can be regenerated from stored raw artifacts.

## 1. Mechanism-first hypothesis

### Core mechanism

Crypto price moves can be initiated by different flow types:

1. **Spot-led move:** spot market price/volume leads perp price, basis does not expand aggressively, and perp OI/funding either lags or confirms later. This is more consistent with real demand/supply or inventory transfer.
2. **Perp-led move:** perp price/basis/volume leads spot, OI and/or funding expand quickly, and spot volume confirmation is weak. This is more consistent with levered positioning, dealer hedging pressure, or forced-flow chasing.
3. **Mixed confirmation:** spot and perp move together with aligned volume and moderate leverage metrics. This is less interesting but useful as a control state.
4. **No confirmation / noise:** price move lacks robust spot or perp participation; likely microstructure noise or venue-local artifact.

### Primary hypothesis

```yaml
H1:
  If an upward move is spot-led, forward continuation quality should be better
  and downside tail risk should be lower than a perp-led upward move of similar
  size, realized volatility, UTC hour, and funding regime.

H2:
  If a downward move is perp-led with rising OI/funding or expanding negative
  basis pressure, forward volatility and squeeze/reversal probability should be
  higher than a spot-led selloff of similar size.

H3:
  Spot confirmation should improve the interpretability of leverage-pressure
  states from Milestone 1 and cross-venue funding dispersion states from
  Milestone 2; it is a classifier/risk annotation first, not standalone alpha.
```

Null expectation: most apparent lead-lag effects decay after controlling for move size, recent volatility, spread/liquidity proxies, venue timestamp semantics, and event overlap. Markets adapt; public candles are not exactly forbidden knowledge.

## 2. Classification target

Classify discrete move events, not every bar. Candidate labels:

```yaml
labels:
  spot_led_up:
    price_move: up
    spot_return_or_volume_leads: true
    perp_basis_expansion: low_to_moderate
    oi_funding_confirmation: lagged_or_moderate

  perp_led_up:
    price_move: up
    perp_return_or_volume_leads: true
    basis_expansion: positive_and_fast
    oi_or_funding_expansion: true
    spot_volume_confirmation: weak_or_lagged

  spot_led_down:
    price_move: down
    spot_return_or_volume_leads: true
    perp_leverage_confirmation: weak_or_lagged

  perp_led_down:
    price_move: down
    perp_return_or_volume_leads: true
    basis_pressure: negative_or_contracting_fast
    oi_or_funding_stress: true

  mixed_confirmation:
    spot_and_perp_move_together: true
    volume_confirmation: both_sides
    leverage_metrics: not_extreme

  no_confirmation:
    price_move: true
    leadership_signal: weak_or_conflicting
```

Recommended first-pass event trigger:

```yaml
event_trigger:
  bar_size: 5m or 15m if available; hourly only as coarse fallback
  move_definition:
    abs_return_percentile: rolling_90d_p90_or_p95
    minimum_absolute_return_bps: asset_specific_floor
  event_spacing:
    non_overlap_window: 4h minimum for intraday study
    cluster_id: event_date_or_volatility_cluster
```

## 3. ObservationRequirements

M3 requires synchronized spot and perp observations with explicit exchange event time and collection/availability time.

### Minimum required observations

```yaml
ObservationRequirements:
  universe:
    primary_assets: [BTC, ETH]
    pilot_asset: BTC
    primary_venue_pairs:
      - venue: Bybit
        spot: BTCUSDT spot
        perp: BTCUSDT linear perpetual
      - venue: OKX
        spot: BTC-USDT spot
        perp: BTC-USDT-SWAP
      - venue: Binance_or_Coinbase_optional
        note: include only if replay-safe raw artifacts and terms/access are acceptable

  required_fields_per_bar:
    common:
      - venue
      - instrument_id
      - market_type: spot | linear_perp | inverse_perp | derived
      - base_asset
      - quote_asset
      - bar_interval
      - event_ts_utc
      - observed_at_utc
      - source_endpoint
      - raw_payload_hash
      - replay_safe_history

    spot_candle:
      - open
      - high
      - low
      - close
      - volume_base
      - volume_quote_if_available
      - trade_count_if_available

    perp_candle_or_mark:
      - open
      - high
      - low
      - close
      - volume_base_or_contracts
      - volume_quote_if_available
      - mark_price_if_available
      - index_price_if_available

    perp_leverage_state:
      - open_interest_native
      - open_interest_unit
      - open_interest_notional_if_available
      - funding_rate
      - funding_event_ts_utc
      - next_funding_time_if_current_snapshot

    derived:
      - perp_spot_basis_bps
      - spot_return
      - perp_return
      - spot_volume_percentile_rolling
      - perp_volume_percentile_rolling
      - oi_change
      - funding_change
      - lead_lag_score
```

### Availability semantics

- Historical candles can be replay-safe if the endpoint is deterministic and raw payloads are stored.
- Funding history should use settlement/effective timestamp as `event_ts_utc`.
- Current-state OI/funding snapshots are not historical evidence until archived; they become replay-safe only from `observed_at_utc` onward.
- Derived fields must use the max observed time of their inputs: `derived.observed_at_utc = max(input.observed_at_utc)`.

## 4. DataProvider source needs

### Immediate handoff scope

```yaml
DataProviderHandoff:
  priority: high
  build_type: reproducible_fixture_not_live_backtest
  horizon:
    smoke_test: 30d
    useful_first_pass: 180d
    preferred_robustness: 365d+
  granularity:
    preferred: 5m
    acceptable_first_pass: 15m
    coarse_fallback: 1h, but label as low_power
  venues:
    phase_1: Bybit BTC/ETH spot + linear perp candles, OI history, funding history
    phase_2: OKX BTC/ETH spot + swap candles, funding history, OI history if verified
    phase_3: Hyperliquid/Binance/Coinbase only after source semantics review
```

### Required DataProvider acceptance criteria

- Regenerate fixture from stored raw payloads without live endpoint calls.
- One schema can represent spot candles, perp candles/marks, OI, funding, and derived basis.
- Unit metadata retained for volume and OI. Contract volume cannot quietly become base volume by vibes.
- Deterministic pagination/window tests for every historical endpoint.
- Completeness report by `(venue, asset, market_type, observation_kind, interval)` including expected bars, actual bars, duplicate keys, max gap, and timezone normalization.
- Timestamp semantics documented in README/schema note.
- For each derived spot/perp pair, record exact pairing rule and tolerated timestamp skew.

### Known current availability from repository scan

- Existing Bybit leverage fixture appears to include spot/perp candles, OI, funding, and derived basis for BTC/ETH, but this spec does **not** assume it is enough for M3 until DataProvider certifies the raw-artifact regeneration path and interval/volume semantics for leadership labels.
- M2 funding dispersion fixture does not provide spot/perp volume leadership observations.
- Coinbase BTC spot candles exist locally, but Coinbase derivatives OI/funding is current-state/forward-archive only from the M2 feasibility note and should not be used as historical leverage evidence yet.

## 5. Feature contract for QUANT after fixture exists

```yaml
FeatureContract:
  returns:
    spot_ret_5m_15m_1h
    perp_ret_5m_15m_1h
    return_spread: perp_ret - spot_ret

  volume_impulse:
    spot_volume_z_or_percentile_rolling_90d_same_hour
    perp_volume_z_or_percentile_rolling_90d_same_hour
    volume_lead_ratio: perp_volume_impulse - spot_volume_impulse

  leverage_pressure:
    oi_change_1h_4h_24h
    funding_level
    funding_change
    basis_bps
    basis_change

  leadership_scores:
    spot_lead_score:
      positive_inputs: [spot_return_leads, spot_volume_impulse, basis_not_extreme]
      negative_inputs: [perp_return_leads, oi_surge_without_spot]
    perp_lead_score:
      positive_inputs: [perp_return_leads, perp_volume_impulse, basis_expansion, oi_surge]
      negative_inputs: [spot_volume_confirmation]

  labels:
    generated_only_at_event_times: true
    ambiguous_events_allowed: no_confirmation_or_mixed
```

Avoid black-box prediction in first pass. The classifier should be auditable enough that a skeptical human can explain why a move was called spot-led or perp-led without needing a séance with XGBoost.

## 6. Controls and benchmarks

Minimum controls:

- recent realized volatility bucket;
- event return magnitude bucket;
- recent trend / prior 24h return;
- UTC hour and weekend flag;
- funding regime before event;
- market beta regime if multi-asset sample is used;
- event overlap / clustered standard errors or cluster bootstrap by date;
- same-venue controls before cross-venue claims;
- spot-only and perp-only simple benchmarks.

Negative controls:

- shuffled leadership labels within same day/hour bucket;
- future information leak test by shifting derived features forward/backward;
- random event times matched on volatility and UTC hour;
- compare to naive `large move continues/reverses` baseline.

## 7. Validation plan

### Stage A — Data validation only

- Run DataProvider completeness report.
- Verify raw-to-normalized traceability on sampled rows.
- Verify spot/perp timestamp pairing and interval consistency.
- Reject or downgrade if volume units or OI units are ambiguous.

### Stage B — Descriptive classifier audit

- Count labels by asset, venue, UTC hour, volatility bucket.
- Inspect top 20 events per label manually with raw fields and derived scores.
- Confirm labels are not dominated by one venue outage/gap or one liquidation day.

### Stage C — Event study

Outcomes:

```yaml
outcomes:
  forward_return: [1h, 4h, 8h, 24h]
  realized_volatility: [4h, 8h, 24h]
  max_adverse_excursion: [4h, 24h]
  max_favorable_excursion: [4h, 24h]
  continuation_probability: thresholded_directional_followthrough
  failed_breakout_probability: move_reverses_more_than_x_bps
```

Required comparisons:

- spot-led up vs perp-led up after matched controls;
- spot-led down vs perp-led down after matched controls;
- mixed confirmation vs no confirmation;
- M1 leverage-state labels with and without M3 spot/perp confirmation;
- M2 high funding dispersion events with and without M3 leadership confirmation.

Statistical treatment:

- non-overlap event clustering;
- bootstrap confidence intervals by event date or volatility cluster;
- report medians, tails, and hit rates, not only means;
- out-of-sample split by time after label thresholds are fixed.

## 8. Promotion gates

```yaml
ResearchOnly:
  condition: labels are coherent and descriptive, but effects are mixed or mostly CI-overlap-zero
  allowed_use: dashboard/risk annotation
  disallowed_use: sizing or standalone trading

RiskFilterCandidate:
  condition:
    - spot/perp confirmation materially improves tail-risk or failed-breakout classification
    - effect survives matched controls and non-overlap clustering
    - no obvious timestamp/unit/data leak
  allowed_use: future Trader discussion as filter only

PaperCandidate:
  condition:
    - robust out-of-sample evidence across assets or venues
    - costs/slippage assumptions plausible
    - event definitions reproducible from stored artifacts
  note: not expected from first pass
```

No Trader handoff from this spec alone.

## 9. Stop / reject conditions

Stop or reject M3 escalation if any of the following holds:

- Cannot regenerate spot/perp/OI/funding fixture from stored raw artifacts.
- Spot and perp observations cannot be aligned without large or inconsistent timestamp skew.
- Volume units differ across venues and cannot be normalized or clearly separated.
- OI/funding fields are current-state only and there is no forward archive covering the study window.
- Label counts are too sparse after non-overlap filtering, e.g. fewer than ~30 events per primary class for BTC first pass.
- Leadership labels are dominated by a single outage, liquidation day, exchange-specific quirk, or one asset.
- Effects disappear under volatility/return/UTC-hour matched controls.
- A naive return-size or volatility baseline explains outcomes as well as the leadership classifier.
- Any implementation requires lookahead fields such as next funding before it was observable.

## 10. Recommended next owner

```yaml
next_owner: DATA_PROVIDER_DEVELOPER
handoff_status: ready_for_data_provider_handoff
quant_status: blocked_until_reproducible_fixture_and_data_quality_report
trader_status: not_ready
```

Recommended next task:

> Build a reproducible BTC-first spot/perp leadership fixture with raw payload archive, normalized spot/perp candles, OI, funding, basis, completeness report, and timestamp/unit semantics. Start with Bybit if its raw-artifact path can be certified; add OKX only after endpoint/pagination review.


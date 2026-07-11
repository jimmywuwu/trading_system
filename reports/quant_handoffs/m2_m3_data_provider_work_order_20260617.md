# QUANT handoff — M2/M3 DataProvider work order

Created: `2026-06-17T08:19:28Z`  
Created by: Jaquan/QUANT cron handoff  
Audience: Jayda / DATA_PROVIDER_DEVELOPER  
Scope: concise Quant-side work order only. This does not modify Jayda-owned docs.

## Evidence inspected

- `reports/cross_venue_dispersion/milestone2_btc_funding_dispersion.md`
- `reports/cross_venue_dispersion/milestone2_feasibility_data_provider_handoff.md`
- `reports/notion_drafts/milestone3_spot_perp_leadership_classifier_spec_20260617.md`
- `reports/notion_drafts/jayda_todo_bybit_oi_pagination_gap.md`
- `reports/notion_drafts/jayda_response_us_regulated_perp_feasibility.md`
- `reports/data_quality/bybit_leverage_fixture_365d_20260614_regen_preflight.json`

## Formalized repo artifacts

Added during `2026-06-17T09:22:47Z` hourly QUANT cadence:

- `artifacts/quant/m3_observation_requirements_20260617.md`
- `artifacts/quant/m3_data_provider_handoff_20260617.md`

Added during `2026-06-17T11:29:49Z` hourly QUANT cadence:

- `artifacts/quant/m2_m3_gate_status_20260617.md`

These are Quant-owned handoff/status artifacts distilled from this report plus the M2/M3 evidence below; they do not modify Jayda-owned docs and do not create Trader readiness.

## Gate summary

```yaml
M2_cross_venue_funding_dispersion:
  status: completed_research_only
  evidence:
    source_report: reports/cross_venue_dispersion/milestone2_btc_funding_dispersion.md
    scope: BTC, Bybit/OKX/Hyperliquid, replay-safe historical funding only
    rows:
      bybit_funding: 91
      okx_funding: 91
      hyperliquid_funding: 720
      common_three_venue_timestamps: 90
      top_decile_dispersion_events: 9
  limits:
    - current-state OI excluded from historical evidence
    - regulated Coinbase/CME historical OI/funding claims excluded
    - no Trader handoff
  next_gate: DataProvider must persist raw funding payloads + normalized rows and make fixture reproducible without live endpoint calls

M2_regulated_perp_feasibility:
  status: monitoring_event_study_only
  evidence:
    source_report: reports/cross_venue_dispersion/milestone2_feasibility_data_provider_handoff.md
    coinbase_derivatives: current product state usable only from observed_at forward if polled
    cme: blocked from runtime via HTTP 403 / deferred unless vendor or manual replay-safe source exists
  limits:
    - Coinbase OI/funding is not replay-safe historical evidence until forward archive exists
    - use label coinbase_observable_regulated, not full US-regulated coverage
  trader_status: not_ready

M3_spot_perp_leadership_classifier:
  status: spec_ready_but_quant_backtest_blocked
  evidence:
    source_spec: reports/notion_drafts/milestone3_spot_perp_leadership_classifier_spec_20260617.md
  data_dependency: synchronized spot/perp candles, OI, funding, basis, volume semantics, raw payload hashes, timestamp availability semantics
  allowed_now: DataProvider observation/fixture build
  blocked_now:
    - QUANT backtest
    - SignalContract
    - Trader sizing or portfolio review
  trader_status: not_ready
```

## Concise DataProvider work order

### 1. Make M2 funding dispersion reproducible

Owner: `DATA_PROVIDER_DEVELOPER`

Acceptance:

- Persist raw funding-history payloads and normalized rows for Bybit, OKX, and Hyperliquid BTC.
- Required fields per normalized funding row:
  - `venue`
  - `instrument_id`
  - `base_asset`
  - `quote_asset`
  - `rail = funding_history`
  - `event_ts_utc` using venue settlement/effective timestamp
  - `observed_at_utc` using ingestion/collection time or explicitly documented simulated visibility if regenerated historically
  - `funding_rate`
  - `source_endpoint`
  - `raw_payload_hash`
  - `replay_safe_history`
- Add deterministic pagination/window tests before extending the M2 horizon beyond 30d.
- Fixture must regenerate from stored raw files without hitting live APIs.

Stop condition:

- Stop promotion if event sets cannot be reproduced from stored artifacts or if `event_ts_utc` / `observed_at_utc` semantics are ambiguous.

### 2. Preserve the fixed Bybit OI path as a prerequisite for M3

Evidence state:

- Earlier Quant diagnostic `reports/notion_drafts/jayda_todo_bybit_oi_pagination_gap.md` identified `nextPageCursor` loss as blocking OI-based research.
- Current regenerated preflight `reports/data_quality/bybit_leverage_fixture_365d_20260614_regen_preflight.json` shows the repaired fixture has:
  - `line_count: 1053382`
  - BTC and ETH 5m OI rows: `105120` each
  - no hourly candle/OI alignment gaps for BTC or ETH
  - `raw_payload_hash_missing_rows: 0`

Acceptance:

- Keep regression coverage for multi-page `/v5/market/open-interest` pagination.
- Keep completeness report in future fixture generations: expected bars, actual bars, duplicate keys, max gap, source endpoints, raw hash coverage.
- Do not let a clean coverage summary quietly become a trading conclusion. Annoying, but useful.

### 3. Build M3 BTC-first spot/perp leadership fixture

Owner: `DATA_PROVIDER_DEVELOPER`

Build type:

```yaml
build_type: reproducible_fixture_not_live_backtest
pilot_asset: BTC
secondary_asset: ETH_if_same_schema_passes_without_special_cases
preferred_granularity: 5m
acceptable_first_pass: 15m
coarse_fallback: 1h_low_power_label_required
horizon:
  smoke_test: 30d
  useful_first_pass: 180d
  preferred_robustness: 365d+
```

Phase 1 venue:

- Bybit BTC/ETH spot + linear perp candles, OI history, funding history, mark/index if available, derived spot/perp basis.

Phase 2 venue:

- OKX BTC/ETH spot + swap candles and funding history after endpoint/pagination review; OI only if historical source is verified or forward archive is explicitly used.

Phase 3 venue:

- Hyperliquid/Binance/Coinbase only after source semantics/access review. Coinbase derivatives OI/funding remains forward-archive-only for historical leverage evidence.

## Formal M3 ObservationRequirements

```yaml
ObservationRequirements:
  universe:
    primary_assets: [BTC, ETH]
    pilot_asset: BTC
    venue_pairs:
      phase_1:
        - venue: Bybit
          spot: BTCUSDT spot
          perp: BTCUSDT linear perpetual
          optional_eth_same_schema: true
      phase_2:
        - venue: OKX
          spot: BTC-USDT spot
          perp: BTC-USDT-SWAP
      phase_3_after_review:
        - Hyperliquid
        - Binance
        - Coinbase

  required_fields_per_observation:
    common:
      - venue
      - instrument_id
      - market_type: spot | linear_perp | inverse_perp | derived
      - base_asset
      - quote_asset
      - observation_kind: spot_candle | perp_candle | mark_price | open_interest | funding | basis
      - interval
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
      - lead_lag_score_inputs_only
```

Availability semantics:

- Historical candles may be replay-safe only if raw payloads are stored and endpoint/window behavior is deterministic.
- Funding history uses settlement/effective timestamp as `event_ts_utc`.
- Current-state OI/funding snapshots are not historical evidence until archived; they become replay-safe only from `observed_at_utc` onward.
- Derived rows must use `observed_at_utc = max(input_observed_at_utc)`.
- Pairing rules must document tolerated timestamp skew and whether bars are closed before use.

## Formal M3 DataProviderHandoff

```yaml
DataProviderHandoff:
  priority: high
  next_owner: DATA_PROVIDER_DEVELOPER
  requested_artifacts:
    - raw payload archive for all source endpoints
    - normalized fixture JSONL or equivalent table
    - schema/README documenting timestamps, units, and replay-safety
    - completeness report by venue/asset/market_type/observation_kind/interval
    - pagination/window regression tests for each historical endpoint
    - sampled raw-to-normalized traceability proof

  acceptance_criteria:
    - fixture regenerates from stored raw payloads without live endpoint calls
    - no duplicate logical keys for venue/instrument/observation_kind/event_ts/observed_at
    - raw_payload_hash present on source-derived rows
    - volume and OI units retained; no silent contract/base/notional conversion
    - timestamp pairing rule for each spot/perp pair is explicit
    - current-state rails are marked non-replay-safe until archived
    - completeness report includes expected rows, actual rows, duplicate keys, max gap, timezone normalization, and source endpoint counts

  handback_to_quant_when:
    - BTC pilot fixture passes completeness and traceability checks
    - DataProvider documents which rails are replay-safe and which are forward-archive-only
    - event set can be reproduced offline from stored artifacts

  quant_after_handback:
    - run Stage A data validation only
    - then descriptive classifier audit
    - only then event study with matched controls and non-overlap clustering

  trader_gate:
    status: not_ready
    reason: no SignalContract, no sizing assumptions, no execution/cost review, no out-of-sample evidence
```

## QUANT stop/reject conditions after DataProvider handback

- Cannot regenerate fixture from stored raw artifacts.
- Spot/perp observations cannot be aligned without large or inconsistent timestamp skew.
- Volume or OI units are ambiguous.
- OI/funding fields are current-state-only and no forward archive covers the study window.
- Fewer than roughly 30 non-overlapping BTC events per primary class after filtering.
- Leadership labels are dominated by one outage, liquidation day, exchange quirk, or single asset.
- Effects disappear under return/volatility/UTC-hour matched controls.
- Any feature requires lookahead, including next funding before it was observable.

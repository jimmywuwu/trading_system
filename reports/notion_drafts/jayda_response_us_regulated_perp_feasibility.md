# Jayda DataProvider response — US-regulated perp feasibility

Created: 2026-06-02  
Owner: Jayda / DataProvider Developer  
Requester: Jaquan / Quant  
Request: US-regulated perp data feasibility for cross-venue leverage segmentation

## Short answer

**Accepted with constraints.** A first monitoring / event-study framework is feasible, but the first pass should be labeled **research-only / monitoring-only**, not a backtest-ready directional signal.

The strongest usable source right now is **Coinbase Derivatives / Coinbase Financial Markets via Coinbase public brokerage market endpoints**. It exposes BTC/ETH perpetual-style futures and dated nano futures with current product specs, 24h volume, current open interest, current funding rate for perp products, index/settlement price fields, ticker trades, and historical candles.

However, the key limitation is important:

> Coinbase exposes useful current product state and candles, but I do **not** yet see a replay-safe historical OI / funding history endpoint equivalent to Bybit/OKX/Hyperliquid funding history. Historical `observed_at` for Coinbase OI/funding should therefore be generated only from our own polling archive, or treated as approximate/simulated in a fixture.

Kalshi should be **watchlist-only** for this specific regime filter until a relevant public crypto perpetual dataset is identified. CME should be **deferred or vendor/manual-source only** in our current stack because public CME pages/endpoints were blocked from this runtime and are likely not clean enough for automated point-in-time fixture generation without a paid/vendor path.

Offshore comparison rails are feasible with different confidence levels: Bybit, OKX, and Hyperliquid are usable; Binance funding is usable, but Binance OI history returned HTTP 202/empty from this runtime again and should not be primary unless we solve that access path.

## Live source probes from this environment

### Coinbase Financial Markets / Coinbase Derivatives

Probe URL:

```text
GET https://api.coinbase.com/api/v3/brokerage/market/products?product_type=FUTURE&limit=100
```

Confirmed BTC/ETH instruments:

```text
BIP-20DEC30-CDE  BTC PERP       product_venue=FCM  contract_size=0.01 BTC  funding_interval=3600s
ETP-20DEC30-CDE  ETH PERP       product_venue=FCM  contract_size=0.1 ETH   funding_interval=3600s
BIT-26JUN26-CDE  BTC dated fut  product_venue=FCM  contract_size=0.01 BTC
ET-26JUN26-CDE   ETH dated fut  product_venue=FCM  contract_size=0.1 ETH
```

Observed fields in `future_product_details` for BTC/ETH PERP include:

- `contract_code`
- `contract_expiry`: long-dated 2030-12-20 for perp-style products
- `contract_size`
- `contract_root_unit`
- `group_description`
- `twenty_four_by_seven`
- `funding_interval`: `3600s`
- `open_interest`
- `funding_rate`
- `funding_time`
- `settlement_price`
- `index_price`
- `intraday_margin_rate`
- `overnight_margin_rate`

Working endpoints:

```text
GET /api/v3/brokerage/market/products/{product_id}
GET /api/v3/brokerage/market/products/{product_id}/ticker
GET /api/v3/brokerage/market/products/{product_id}/candles?start=...&end=...&granularity=ONE_HOUR
```

DataProvider interpretation:

- Product specs: **usable now**.
- 1h candles / volume: **usable now**.
- Current OI / current funding: **usable now as live observations if polled**.
- Historical candles: **usable now**.
- Historical OI/funding: **not accepted as replay-safe unless we archive by polling**.

### Kalshi

Probe URL:

```text
GET https://api.elections.kalshi.com/trade-api/v2/markets?limit=10&search=bitcoin
GET https://api.elections.kalshi.com/trade-api/v2/events?limit=10&search=bitcoin
```

Result: public API is reachable, but searches did not surface a clean BTC/ETH perpetual-style product suitable for this request. The returned markets looked unrelated or general prediction/event markets.

DataProvider interpretation:

- Kalshi API: **reachable**.
- Relevant BTC/ETH perp-like public data: **not confirmed**.
- Status: **watchlist-only / deferred**.
- If Quant wants Kalshi specifically, we need exact tickers/series and a separate product-mechanics review. Event/binary contracts should not be compared directly with perp funding/OI.

### CME BTC/ETH futures

Probe URLs attempted:

```text
https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.contractSpecs.html
https://www.cmegroup.com/markets/cryptocurrencies/ether/ether.contractSpecs.html
https://www.cmegroup.com/CmeWS/mvc/Volume/Details/F?tradeDate=...&exchange=CME&foi=FUT
```

Result: CME web/API paths returned HTTP 403 from this runtime.

DataProvider interpretation:

- CME product mechanics are important for the research idea.
- But in our current runtime, CME is **not yet an automated fixture source**.
- Treat CME basis/OI/volume as **deferred unless we add a vendor/source path** such as paid CME data, Nasdaq Data Link/Quandl if available, a broker feed, or a manually reviewed public dataset with clear publication timestamps.

### Offshore comparison rails

Confirmed reachable:

```text
Bybit OI:
GET https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=1h&limit=3

Bybit funding:
GET https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=3

OKX instruments:
GET https://www.okx.com/api/v5/public/instruments?instType=SWAP&uly=BTC-USDT

OKX funding:
GET https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP

OKX open interest:
GET https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP

Hyperliquid meta/context:
POST https://api.hyperliquid.xyz/info {"type":"metaAndAssetCtxs"}

Hyperliquid funding history:
POST https://api.hyperliquid.xyz/info {"type":"fundingHistory","coin":"BTC","startTime":...}

Hyperliquid candles:
POST https://api.hyperliquid.xyz/info {"type":"candleSnapshot", ...}
```

Notes:

- Bybit remains usable, but must keep the pagination fix from PR #10: follow `nextPageCursor`, reject repeated cursors, and do not silently accept endpoint-limit truncation.
- OKX gives current funding and OI snapshots plus instrument metadata; historical funding/OI needs a follow-up endpoint review if required beyond current snapshots.
- Hyperliquid is strong for BTC/ETH: `metaAndAssetCtxs` returns current funding, openInterest, dayNtlVlm, dayBaseVlm, oracle/mark/mid; `fundingHistory` returns historical hourly funding/premium; `candleSnapshot` returns historical candles.
- Binance funding history is reachable, but Binance OI history returned HTTP 202 with empty body again from this runtime. Do not make Binance OI primary unless that access path is fixed.

## Recommended first-pass source status

```yaml
source_status:
  coinbase_derivatives_fcm:
    status: usable_now_with_constraints
    use_for:
      - regulated_perp_product_specs
      - regulated_perp_current_open_interest_if_polled
      - regulated_perp_current_funding_if_polled
      - regulated_perp_1h_candles_and_volume
      - regulated_dated_future_candles_volume_specs
    not_safe_for_without_polling_archive:
      - historical_open_interest_replay
      - historical_funding_replay

  kalshi:
    status: watchlist_only
    reason: no clean BTC_ETH_perp_like_public_product_confirmed_in_probe

  cme:
    status: deferred_vendor_or_manual_source
    reason: public CME paths blocked from this runtime; point_in_time automated fixture not established

  bybit:
    status: usable_now
    caveat: must use pagination-safe OI provider

  okx:
    status: usable_now_for_current_snapshots_and_specs
    follow_up: review historical funding/OI endpoints before long replay fixture

  hyperliquid:
    status: usable_now
    use_for:
      - current_funding_oi_volume_mark_oracle
      - funding_history
      - candles

  binance:
    status: partial
    usable_for:
      - funding_history
    not_primary_for:
      - open_interest_history_from_this_runtime
```

## Timestamp semantics

### Coinbase product spec / current product state

Observation kinds:

- `regulated_perp_product_spec`
- `regulated_perp_current_state`

Rules:

```text
occurred_at = source response retrieval time, unless the field has its own timestamp such as funding_time
observed_at = ingestion receive time
published_at = null unless source provides one
retrieved_at = ingestion receive time
```

For `funding_rate` with `funding_time`:

```text
occurred_at = funding_time
observed_at = ingestion receive time
```

Do **not** backfill historical funding/OI from a current endpoint as if it existed historically.

### Coinbase candles / volume

```text
occurred_at_start = candle start
occurred_at = candle close time
observed_at = candle close time + conservative availability lag for historical replay, or exact receive time for live polling
volume_unit = contracts
notional_volume_usd = contracts * contract_size * close_price
```

For historical candles, use simulated conservative availability only if clearly labeled.

### Offshore funding

For settled historical funding:

```text
occurred_at = exchange funding settlement timestamp
observed_at = occurred_at + conservative publication lag for historical fixture, or exact receive time for live polling
```

For predicted/current funding snapshots:

```text
occurred_at = source timestamp / next funding timestamp if available
observed_at = ingestion receive time
```

Do not merge settled funding and predicted funding under one field without `metric_name` / `calculation_rule`.

### Open interest snapshots

```text
occurred_at = source snapshot timestamp if provided; otherwise ingestion receive time
observed_at = ingestion receive time for live/current snapshot
historical observed_at = simulated only if source lacks true publication timestamp
```

If OI is only current-state from Coinbase/OKX, historical OI requires polling archive.

### CME dated futures basis

If a source is later accepted:

```text
futures.occurred_at = close/settlement timestamp or quote snapshot time
spot.occurred_at = matched spot reference timestamp
basis.occurred_at = max(futures.occurred_at, spot.occurred_at)
basis.observed_at = max(futures.observed_at, spot.observed_at)
```

Contract rollover and expiry must be explicit; front-month basis and continuous-series basis are different observations.

## Comparability cautions

Do **not** compare raw Coinbase FCM perp funding directly to Bybit/OKX/Hyperliquid funding without labels.

Reasons:

- Coinbase products are CFM/FCM regulated futures with specific margin/session/risk rules.
- BTC/ETH perps appear as long-dated expiring contracts (`2030-12-20`) with perp-like funding every 1h.
- Contract size is small fixed notional exposure unit: BTC perp/futures `0.01 BTC`; ETH perp/futures `0.1 ETH`.
- Offshore perps have different margining, liquidity, liquidation mechanics, insurance/ADL regimes, funding formulas, and venue user base.
- CME dated futures have expiry/roll mechanics and no perp funding.
- Kalshi event markets, if relevant, are event/binary products and should not be treated as linear perp substitutes.

Safe normalized monitoring fields:

```yaml
normalized_fields:
  - venue
  - regulatory_bucket: [us_regulated_fcm, cme_dated_futures, offshore_cex_perp, offshore_dex_perp, event_contract]
  - product_family
  - instrument_id
  - subject: [BTC, ETH]
  - contract_type: [perp_style_future, dated_future, swap_perp, event_contract]
  - contract_size_base
  - volume_contracts
  - volume_base
  - volume_notional_usd
  - open_interest_contracts
  - open_interest_base
  - open_interest_notional_usd
  - funding_or_basis_metric_name
  - funding_or_basis_value
  - funding_interval
  - calculation_rule
  - occurred_at
  - observed_at
  - source_endpoint
  - retrieved_at
```

Recommended first regime features:

```yaml
monitoring_features:
  - coinbase_perp_oi_notional_share_vs_offshore
  - coinbase_perp_volume_notional_share_vs_offshore
  - coinbase_funding_minus_hyperliquid_funding
  - coinbase_funding_minus_bybit_funding
  - regulated_vs_offshore_oi_dispersion_zscore
  - regulated_vs_offshore_volume_share_change
  - dated_future_basis_vs_perp_funding_proxy
```

But only use features whose source has replay-safe availability. Otherwise mark as live-monitoring-only.

## Minimum fixture proposal

### Phase 0: live monitoring archive first

Because Coinbase historical OI/funding replay is the main missing piece, I recommend first implementing a polling archive rather than forcing a backtest fixture.

Scope:

```yaml
symbols: [BTC, ETH]
regulated:
  coinbase_fcm:
    products:
      - BIP-20DEC30-CDE
      - ETP-20DEC30-CDE
      - nearest BTC dated future, e.g. BIT-26JUN26-CDE
      - nearest ETH dated future, e.g. ET-26JUN26-CDE
    polling_interval: 1h
    observations:
      - product_spec_snapshot
      - current_open_interest
      - current_funding_rate
      - index_price
      - settlement_price
      - 1h candle_volume

offshore:
  bybit: [funding_history, open_interest, 1h candles]
  hyperliquid: [funding_history, open_interest snapshots, 1h candles, day volume]
  okx: [current funding/OI/specs; historical follow-up]

spot:
  coinbase_spot_or_bybit_spot:
    observations: [1h candles, volume]
```

Proposed implementation path:

```text
providers/coinbase_derivatives_provider.py
scripts/export_cross_venue_leverage_fixture.py
data/cross_venue_leverage_fixture_30d.jsonl
reports/cross_venue_leverage_regime/data_feasibility.md
```

Initial command shape:

```bash
python3 scripts/export_cross_venue_leverage_fixture.py \
  --subjects BTC,ETH \
  --regulated coinbase_fcm \
  --offshore bybit,hyperliquid,okx \
  --granularity 1h \
  --days 30 \
  --out data/cross_venue_leverage_fixture_30d.jsonl
```

Acceptance constraint: until a Coinbase OI/funding polling archive exists, the fixture can include Coinbase historical candles and product state snapshots retrieved during generation, but should not claim historical OI/funding replay.

### Phase 1: 30d monitoring fixture

After polling archive exists for at least 30 days:

- build BTC/ETH 1h fixture
- include exact ingestion `observed_at` for Coinbase snapshots
- compare with Bybit/Hyperliquid/OKX offshore rails
- produce a `DataProviderHandoff`

### Phase 2: research event study

Only after Phase 1 passes data integrity review should Quant create the first `MarketStructureNote` / `ResearchHypothesis`. I would not start a backtest before this.

## Data integrity risks

```yaml
risks:
  missing_coinbase_historical_oi_funding:
    severity: high
    mitigation: live polling archive; do not simulate unless labeled research_only

  product_spec_mismatch:
    severity: high
    mitigation: typed contract metadata and regulatory_bucket fields

  coinbase_perp_as_long_dated_future:
    severity: medium_high
    mitigation: represent as perp_style_future, not offshore swap_perp

  cme_access_blocked_or_vendor_dependent:
    severity: medium_high
    mitigation: defer until source path is explicit

  bybit_oi_pagination:
    severity: high
    mitigation: use PR #10 pagination-safe provider

  binance_oi_access_unreliable:
    severity: medium
    mitigation: avoid as primary OI source for now

  thin_launch_liquidity:
    severity: medium
    mitigation: track volume/OI adoption as the outcome, not assume stable market depth

  timestamp_semantics:
    severity: high
    mitigation: strict occurred_at/observed_at/source_endpoint/retrieved_at on every observation
```

## Decision

```yaml
decision: accepted_with_constraints
recommended_status: Waiting Review
first_pass_use: monitoring_only_or_research_only
safe_to_start_signal_contract: false
safe_to_start_backtest: false
safe_to_start_data_provider_spike: true
```

I recommend Jaquan proceeds with a `MarketStructureNote` only after accepting the monitoring-only constraint. The next engineering task should be a small DataProvider spike for Coinbase FCM product/candle/current-state ingestion plus Hyperliquid/Bybit comparison observations, not a full signal/backtest.

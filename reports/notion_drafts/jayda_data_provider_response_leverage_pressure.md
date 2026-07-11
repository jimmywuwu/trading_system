# Jayda DataProvider response — Leverage Pressure BTC/ETH fixture

Created: 2026-05-28T16:03:34Z  
Owner: Jayda / DataProvider Developer  
Request: Jaquan / Quant  
Related PR: https://github.com/jimmywuwu/trading_system/pull/6

## Short answer

**Accepted with constraints.** We can support a first-pass BTC/ETH event-study fixture for funding + open interest + perp candles + spot candles, but the fixture must be labeled as a **conservative replay fixture**, not a perfect reconstruction of historical API receive time.

Recommended first-pass venue: **Bybit linear USDT perps + Bybit spot USDT pairs**.

Reason: live API checks from this environment successfully returned BTCUSDT and ETHUSDT for:

- linear funding history
- linear open interest snapshots at 5m
- linear perp klines at 5m
- spot klines at 5m

Candidate mapping:

- BTC perp: `bybit:linear:BTCUSDT`
- BTC spot: `bybit:spot:BTCUSDT`
- ETH perp: `bybit:linear:ETHUSDT`
- ETH spot: `bybit:spot:ETHUSDT`

Binance remains a fallback candidate because its candle/funding endpoints are clear, but the open-interest-history endpoint returned HTTP 202 with an empty body from this runtime during the first check, so I would not choose it as primary until that path is made reliable.

## Feasibility by observation kind

### `perp_funding_rate`

Status: **supported for settled historical funding; quoted/predicted funding needs live capture or another archival source.**

Bybit `funding/history` returns historical funding rates with `fundingRateTimestamp`. For this fixture I would represent these as **settled funding observations**, not predicted intra-interval quotes.

Semantics:

- `occurred_at`: funding settlement timestamp / funding interval boundary from exchange.
- `observed_at` for historical fixture: `occurred_at + conservative_publication_lag` such as 60s, unless empirical polling later shows a better lag.
- `published_at`: unavailable unless the endpoint exposes a separate publication timestamp; store null.

Important: if Quant needs **predicted next funding** as it evolved during the interval, historical exchange funding-history endpoints are not enough. That requires live polling snapshots or a vendor archive that preserves quote-time history.

### `perp_open_interest`

Status: **supported at 5m snapshots for first-pass fixture.**

Bybit `open-interest` returned 5m BTCUSDT and ETHUSDT records with `timestamp` and `openInterest`.

Semantics:

- `occurred_at`: exchange OI snapshot timestamp.
- `observed_at` for historical fixture: `timestamp + conservative_publication_lag`, initially 60s.
- Store raw `openInterest` exactly as returned.
- Store unit metadata explicitly. For Bybit linear contracts, treat the raw value as exchange-native OI quantity and compute a normalized notional with the matched point-in-time mark/close price.

Normalization rule:

```plain text
open_interest_notional_usdt = raw_open_interest * mark_or_perp_close_price
normalization_observed_at = max(oi.observed_at, price.observed_at)
```

If we use perp candle close instead of mark price for first pass, that limitation must be recorded in `normalization_source`.

### `perp_candle`

Status: **supported.**

Bybit linear kline returns start timestamp and OHLCV/turnover. Use 5m first to keep fixture size manageable.

Semantics:

- `occurred_at_start`: exchange candle interval start.
- `occurred_at`: interval close time, because the final OHLCV is only known after close.
- `observed_at`: interval close time + ingestion/publication allowance, initially 5s to 30s for fixture replay.
- Incomplete current candles must not be emitted as closed candles.

### `spot_candle`

Status: **supported.**

Bybit spot kline returned BTCUSDT and ETHUSDT 5m candles.

Semantics mirror perp candles:

- `occurred_at_start`: exchange candle interval start.
- `occurred_at`: interval close time.
- `observed_at`: interval close time + ingestion/publication allowance.
- Use same venue family and quote currency as perp to avoid obvious venue/quote mismatch in first pass.

### `perp_spot_basis`

Status: **derive from point-in-time-safe inputs.**

For first pass, derive from perp close or mark-price observation and spot close.

Semantics:

```plain text
basis.occurred_at = max(perp_price.occurred_at, spot_price.occurred_at)
basis.observed_at = max(perp_price.observed_at, spot_price.observed_at)
basis_bps = (perp_price - spot_price) / spot_price * 10000
```

If mark/index price is not captured separately, label the derived field as `basis_from_perp_close_vs_spot_close`, not as true mark/index basis.

### `liquidation_print_optional`

Status: **defer / optional unavailable for first-pass trigger.**

Historical liquidation prints are the easiest place to accidentally import a time machine. Exchange/websocket liquidation feeds can be point-in-time live, but historical REST availability and completeness are not guaranteed enough for me to bless as a mandatory input without more source review.

Recommendation: do not use liquidation prints for signal construction. If later available from a vendor with explicit event-time and ingestion-time history, include them only as attribution.

### `orderbook_liquidity_optional`

Status: **defer / optional unavailable for first-pass historical fixture.**

Live orderbook snapshots are feasible, but 14 days of historical top-depth with replayable `observed_at` is not reliably available from ordinary exchange REST endpoints. Do not use coarse or backfilled orderbook snapshots as if they were live top-of-book liquidity.

## Answers to Jaquan's specific questions

1. **Source / venue:** use Bybit first pass: `linear BTCUSDT/ETHUSDT` perps + `spot BTCUSDT/ETHUSDT`.
2. **Funding quoted / predicted / settled:** settled historical funding is supported. Predicted/quoted funding history is not reconstructable from simple funding-history endpoints; needs live polling or archival snapshots.
3. **OI units:** store raw exchange-native `openInterest` plus explicit unit metadata. For normalized research features, compute USDT notional from raw OI and point-in-time price.
4. **Replay-stable OI notional:** yes, if the normalization price is itself an Observation and `open_interest_notional.observed_at = max(oi.observed_at, price.observed_at)`.
5. **Candle timestamps:** kline timestamps are interval starts; closed candle values should use interval close as feature `occurred_at`.
6. **Reconstruct `observed_at`:** live: exact receive time. Historical: only conservative simulated availability unless we have archived ingestion logs. This is acceptable for first-pass feasibility if explicitly labeled.
7. **Revisions/backfills:** assume possible. Store `retrieved_at`, `source_endpoint`, `raw_payload_hash`, `ingestion_run_id`, and never silently overwrite fixture versions.
8. **Missing / duplicate / late policy:** mandatory inputs missing or stale => no event. Dedupe by venue/symbol/kind/occurred_at/source. Late observations enter replay only when `observed_at <= replay_clock_time`.
9. **Liquidation prints:** not accepted as historical mandatory input yet. Optional attribution only after a separate source review.
10. **Orderbook top-depth:** not accepted for first-pass historical fixture. Live capture later is feasible.

## Proposed minimum fixture

Time range: **14 days**, preferably selected to contain at least one elevated-funding + rising-OI period.

Granularity: **5m** first pass.

Expected records per symbol:

- perp candles: 14 * 24 * 12 = 4032
- spot candles: 4032
- OI snapshots: 4032
- settled funding: roughly 42 if 8h funding interval

For BTC + ETH total expected mandatory observations: roughly **16.2k candle/OI records + funding records**, plus derived basis records if materialized.

## Observation JSONL shape

```json
{
  "kind": "perp_open_interest",
  "venue": "bybit",
  "market_type": "linear_perp",
  "symbol": "BTCUSDT",
  "subject": "BTC-PERP",
  "occurred_at": "2026-05-01T00:05:00Z",
  "observed_at": "2026-05-01T00:06:00Z",
  "published_at": null,
  "payload": {
    "open_interest_raw": "61382.88700000",
    "open_interest_unit": "exchange_native_linear_contract_quantity",
    "normalization_price": "...",
    "open_interest_notional_usdt": "..."
  },
  "source": {
    "provider": "bybit_rest",
    "endpoint": "/v5/market/open-interest",
    "retrieved_at": "...",
    "raw_payload_hash": "...",
    "ingestion_run_id": "..."
  }
}
```

## Provider policies

### Missing / stale

- Funding, OI, perp candles, and spot candles are mandatory.
- If any mandatory observation is missing inside the required lookback, emit no research event for that timestamp.
- Do not impute OI or funding for event creation.

### Duplicate

Dedupe key:

```plain text
(provider, venue, market_type, symbol, kind, occurred_at, source_endpoint)
```

If payload differs for the same key across ingestion runs, store as a new fixture/artifact version with revision metadata.

### Late arrival

Replay rule remains:

```plain text
visible_to_quant iff observed_at <= replay_clock_time
```

Late observations can affect future states only after their `observed_at`.

### Revision / backfill

- Store raw payload hashes.
- Store retrieval time and endpoint parameters.
- Fixture reruns must create a new `fixture_version` rather than overwriting old observations.
- If a later endpoint result differs from the original fixture, record it as a revision event, not an invisible correction.

## Decision

Status: **Accepted with constraints / waiting Quant review.**

I can proceed with a Bybit 14-day BTC/ETH 5m fixture plan if Jaquan accepts these two constraints:

1. historical `observed_at` is conservative simulated availability, not true historical receive time;
2. liquidation and orderbook data are excluded from first-pass signal construction and reserved for optional attribution.

If she needs predicted funding snapshots or orderbook/liquidation history with true point-in-time availability, we should narrow the source requirement or use a paid archival/vendor dataset before implementation.

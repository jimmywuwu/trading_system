# Milestone 2 — Cross-venue funding/OI dispersion feasibility + DataProvider handoff

Created by: HERMES  
Source spike: `spikes/001-cross-venue-leverage-feasibility/`  
Evidence inspected:
- `spikes/001-cross-venue-leverage-feasibility/out/verdict.md`
- `spikes/001-cross-venue-leverage-feasibility/out/raw_results.json`

## Decision

**Proceed with a monitoring/event-study build, not a replay-safe backtest/signal build.**

Reason: offshore historical funding/OI rails are partially replay-safe now, but the regulated Coinbase perp-style OI/funding rail is current-state only from the probed endpoint. CME public web access is blocked from this runtime (`HTTP 403`). Any claim about historical regulated OI/funding replay-safety would be unsupported.

Use label: `coinbase_observable_regulated` rather than full US-regulated market coverage. Tiny but important distinction; otherwise we accidentally cosplay as a data vendor.

## Replay-safety by rail

| Venue | Rail | Current status | Replay-safe now? | Handoff implication |
|---|---|---:|---:|---|
| Coinbase Derivatives | current product state: perp/future metadata, current OI, current funding-like fields | `ok` | **No** | Requires forward polling archive before any historical regulated OI/funding event study or backtest. |
| Coinbase Derivatives | candle history | `ok` | **Yes, price/volume only** | Useful as regulated price/volume context; insufficient alone for leverage-pressure research. |
| Bybit | historical open interest | `ok` | **Yes** | Can seed offshore OI replay rail; provider must implement pagination-safe cursor/window handling. |
| Bybit | historical funding | `ok` | **Yes** | Can seed offshore funding replay rail; align on `fundingRateTimestamp`. |
| Hyperliquid | current OI/mark/oracle/funding state | `ok` | **No** | Requires forward archive for OI/current-state replay. Do not treat current OI as historical. |
| Hyperliquid | funding history | `ok` | **Yes** | Replayable for settled funding observations; align on `time`. |
| OKX | current funding | `ok` | **No** | Current/next funding snapshot only; archive if using non-settled current values. |
| OKX | current OI | `ok` | **No** | Useful for monitoring; OI history not established by this spike. Needs separate endpoint/vendor review or forward archive. |
| OKX | funding history | `ok` | **Yes** | Replayable settled funding rail; align on `fundingTime`. |
| CME | public web futures endpoints | `blocked` | **No** | Deferred until reliable vendor/manual replay-safe source exists. |

## Timestamp semantics to preserve

DataProvider should store both **exchange event time** and **collection time**. Mixing them would produce very elegant nonsense.

Minimum fields per record:

- `venue`
- `instrument_id`
- `base_asset` / `quote_asset` where known
- `rail`: `current_state`, `funding_history`, `oi_history`, `candle_history`
- `event_ts_utc`: exchange-provided event/settlement/candle timestamp
- `observed_at_utc`: ingestion timestamp assigned by our collector
- `value_fields`: raw numeric fields, unnormalized units retained
- `raw_payload_hash` or equivalent payload identity
- `source_endpoint`

Rail-specific semantics:

- **Current-state endpoints**: `event_ts_utc` is venue field if available (`funding_time`, `ts`, etc.); otherwise null/derived with explicit flag. `observed_at_utc` is the replay boundary. These records are only replay-safe from the moment our archive starts.
- **Funding history endpoints**: `event_ts_utc` is the funding settlement/effective timestamp (`fundingRateTimestamp`, Hyperliquid `time`, OKX `fundingTime`). These are replay-safe for settled observations only.
- **OI history endpoints**: `event_ts_utc` is the venue OI sample timestamp (`timestamp` for Bybit). Need monotonic pagination and duplicate handling.
- **Candles**: `event_ts_utc` is candle start time. Coinbase candles are replay-safe for price/volume, not for OI/funding.

## Minimum fixture needed before QUANT event study

Create a small but audit-friendly fixture first; do not jump directly to strategy research.

Required minimum fixture:

1. **Symbols**: BTC first; ETH optional if same schema passes without special cases.
2. **Venues**:
   - Coinbase Derivatives current product state archive for BTC perp-style product (`BIP-20DEC30-CDE` observed in spike) and any matched ETH perp-style product if included.
   - Bybit BTCUSDT historical OI + funding.
   - Hyperliquid BTC funding history; current-state archive if OI is needed.
   - OKX BTC-USDT-SWAP funding history; OKX OI only via forward archive or separate verified historical source.
3. **Horizon**:
   - For immediate smoke test: 7 calendar days of forward Coinbase/current-state archive plus offshore replay rails.
   - For first useful event study: 30 calendar days minimum.
   - For stronger regime discussion: 60–90 days, especially if events are sparse.
4. **Granularity**:
   - Hourly collection for Coinbase current product state, matching observed Coinbase perp `funding_interval = 3600s`.
   - Store raw snapshots; downstream can resample, but cannot recreate missing observations. Shocking, I know.
5. **Integrity checks**:
   - No duplicate `(venue, instrument_id, rail, event_ts_utc, observed_at_utc)` rows.
   - Monotonic event timestamps within each historical pull window.
   - Unit metadata retained for OI (`contracts`, `base`, `USD notional`, or venue-native field names).
   - Explicit flag for `replay_safe_history` at rail level.

## Next executable event-study path

1. **DATA_PROVIDER_DEVELOPER**: implement forward archive collector for Coinbase Derivatives product endpoint snapshots.
   - Endpoint from spike: `https://api.coinbase.com/api/v3/brokerage/market/products?product_type=FUTURE&limit=100`
   - Persist raw payload plus normalized fields: product id, display name, contract size, index/settlement price, funding rate/time, open interest, margin fields, `observed_at_utc`.
2. **DATA_PROVIDER_DEVELOPER**: implement/verify offshore replay loaders:
   - Bybit historical OI + funding with cursor/window pagination.
   - Hyperliquid funding history; current-state archive only if OI enters the study.
   - OKX funding history; OKX OI remains current-only unless a historical endpoint/vendor is separately verified.
3. **HERMES/QUANT handoff after fixture exists**: define event labels using only replay-safe-at-decision-time data:
   - Regulated-vs-offshore funding dispersion shock.
   - Regulated-vs-offshore OI change divergence, but only after Coinbase/current OI archive has enough forward history.
   - Offshore-only control events from Bybit/Hyperliquid/OKX histories.
4. **QUANT first study**: non-trading event study over forward archive window:
   - outcome windows: +1h, +4h, +8h, +24h returns/realized volatility/liquidation-proxy if available;
   - bootstrap confidence intervals by event date;
   - report sparse-event limitations explicitly.
5. **Promotion gate**: only discuss signal/backtest path after DataProvider can reproduce the same event set from stored artifacts without live endpoint calls.

## DataProvider acceptance criteria

- A fixture can be regenerated from stored raw files without hitting live APIs.
- Each normalized row links back to raw payload and source endpoint.
- Current-state rails are marked `replay_safe_history = false` until archived; archived snapshots are marked replay-safe only from their `observed_at_utc` onward.
- CME is excluded or manually/vendor-sourced; no silent fallback to unreliable public web endpoint.
- README/schema note documents timestamp semantics and unit handling.

## Stop condition

Stop Milestone 2 escalation if the regulated rail cannot collect stable Coinbase snapshots for at least 7 consecutive days, or if normalized OI/funding fields cannot be tied back to raw payload fields without ambiguity.

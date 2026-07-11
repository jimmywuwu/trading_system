# Roadmap Acceleration Schedule — 2026-06-17

**Owner role:** QUANT  
**Owner agent:** JAQUAN  
**Created:** 2026-06-17 00:11 CST

## Correction / operating rule

Acceleration must mean real execution and scheduled blocks, not optimistic chat narration. If a block is missed, report it as missed.

## Already run now

Command:

```bash
python3 spikes/001-cross-venue-leverage-feasibility/probe_cross_venue_leverage.py
```

Observed result:

- Verdict: `PARTIAL`
- OK rails: 9
- Blocked/error rails: 2
- Coinbase current product state: usable for forward archive / monitoring, not replay-safe OI/funding history
- Coinbase candle history: replay-safe price/volume only, insufficient for leverage backtest
- Bybit OI/funding history: replay-safe, with pagination caveat
- Hyperliquid current state: useful but archive needed for OI replay
- Hyperliquid funding history: replay-safe
- OKX funding history: replay-safe
- OKX current OI: useful current state, historical OI still needs source review
- CME public web from runtime: blocked HTTP 403, vendor/manual/deferred

## Scheduled acceleration blocks

### 00:30 — Milestone 2 feasibility + DataProvider handoff note

Job: `fc93406599cb`

Deliverable target:

- `reports/cross_venue_dispersion/` or `reports/notion_drafts/`
- feasibility summary
- replay-safe vs archive-needed rail classification
- DataProvider handoff/TODO if needed

### 02:00 — Milestone 2 funding dispersion first-pass attempt

Job: `96a9f03a795d`

Scope:

- Use only replay-safe funding history rails where possible: Bybit / OKX / Hyperliquid.
- Avoid current-state OI as historical evidence.
- Produce JSON + Markdown if enough history is accessible.
- If blocked, write blocker report instead of inventing results.

### 09:30 — Milestone 3 spot-led vs perp-led spec

Job: `35abeff646d2`

Scope:

- Only after checking M2 outputs.
- Produce mechanism-first spec, ObservationRequirements, controls, validation plan, and reject conditions.
- Do not jump into backtest without data requirements.

## Gate policy under acceleration

- Faster cadence, same evidence standard.
- No Trader handoff unless robustness justifies it.
- Negative/blocker reports count as progress if verified and documented.
- Cross-venue source semantics must be explicit before any alpha claim.

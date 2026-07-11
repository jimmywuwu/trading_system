# Spike 001: cross-venue leverage feasibility

## Question

Can we build a narrow **Coinbase-observable regulated perp-style rail** and compare it with offshore perp rails without violating point-in-time semantics?

## Scope

This is a disposable spike, not a production DataProvider.

It probes:

- Coinbase Derivatives / Coinbase FCM public brokerage market products and candles
- Bybit OI/funding historical endpoints
- Hyperliquid current state and funding history
- OKX current OI/funding and funding history
- CME public web endpoints from this runtime

## Run

```bash
python3 spikes/001-cross-venue-leverage-feasibility/probe_cross_venue_leverage.py
```

Outputs:

- `out/raw_results.json`
- `out/verdict.md`

## Expected verdict shape

- `VALIDATED`: enough replay-safe data exists for the research question.
- `PARTIAL`: monitoring/event-study is feasible, but historical backtest/signal claims are unsafe.
- `INVALIDATED`: the core data rails are unavailable or semantically unusable.

## Current verdict

`PARTIAL`: Coinbase current OI/funding is useful for forward monitoring, but not enough for historical replay unless we archive it from now onward. CME public web endpoints returned HTTP 403 from this runtime, so CME should require vendor/manual source before it is treated as an automated regulated rail.

See `out/verdict.md` for the run evidence and Jaquan discussion points.

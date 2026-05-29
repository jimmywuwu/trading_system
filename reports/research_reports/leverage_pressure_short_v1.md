# Leverage Pressure SHORT v1 — First-pass Research Report

**created_by:** QUANT  
**created_by_agent:** JAQUAN  
**signal_contract:** `signal_contract_leverage_pressure_short_v1`  
**research_result:** `signal_research_leverage_pressure_short_v1`

## Summary

The v1 leverage-pressure SHORT signal did **not** emit any events on a 30-day Bybit BTCUSDT replay fixture.

That does not reject the broader liquidation-pressure mechanism. It does reject the idea that this specific v1 contract is ready for serious backtesting or Trader handoff.

Dry version: the strategy did not lose money because it did not trade. This is technically robust, but only in the way a unplugged toaster is fire-safe.

## Data Scope

- Venue/source: Bybit public REST
- Symbol: `BTCUSDT`
- Window: `2026-04-29T15:30:30Z` → `2026-05-29T15:26:00Z`
- Normalized observations: `43,287`
- Linear-perp 5m candles: `8,639`
- Replay model: conservative simulated historical `observed_at`

Important caveat: historical `observed_at` is simulated availability time, not archived receive time. Funding is settled funding history, not reconstructed predicted funding visible before settlement.

## Methodology

1. Exported a normalized Bybit leverage-pressure fixture.
2. Replayed `LeveragePressureShortSignal` using a 24h rolling visible-observation window.
3. Required the v1 contract gates:
   - funding rate ≥ `0.0003`
   - 24h OI change ≥ `5%`
   - perp/spot basis ≥ `10 bps`
4. Intended to measure 4h, 8h, and 24h forward SHORT returns.
5. Compared against cash, buy-and-hold long, and always-short baselines.

## Key Results

- Signal events: `0`
- Max settled funding observed: `0.0001`
- Contract funding threshold: `0.0003`
- Max perp-spot basis observed: `-1.91916677 bps`
- Contract basis threshold: `10 bps`
- 24h OI-change observations above 5%: `1,166`
- Buy-and-hold long over fixture: `-3.487821%`
- Always-short over fixture: `+3.487821%`

Interpretation: OI pressure existed at times, but the funding and positive-basis gates did not confirm. The contract failed before edge estimation became meaningful.

## Benchmark Interpretation

The signal stayed flat, so realized signal exposure was equivalent to cash.

The always-short baseline made money during this down month, but that is not evidence for this signal. A down month rewarding short exposure is a market-state fact, not structural alpha.

## Robustness Interpretation

This fails the first robustness gate: frequency sanity.

With zero events, we cannot honestly evaluate:

- forward-return edge
- strength sorting
- confidence sorting
- train/test behavior
- walk-forward stability
- cost sensitivity
- event-level regime attribution

Trying to optimize parameters from here would be overfit-by-embarrassment. The next step should be mechanism/contract revision, not parameter fishing.

## Failure Modes Found

1. **Positive-basis gate mismatch**
   - Bybit BTCUSDT perp traded at a small discount throughout the fixture.
   - If liquidation pressure can appear with negative or cross-venue basis, v1's basis rule is too narrow.

2. **Settled funding may be the wrong observation**
   - Settled funding history is not the same as decision-time predicted funding.
   - The mechanism wants crowded long pressure before unwind, not a post-settlement archive.

3. **Venue-specific structure may matter**
   - A single Bybit BTCUSDT venue view may miss cross-exchange leverage pressure.

4. **Directional market baseline contamination**
   - Always-short did well in this window, but that alone does not validate the leverage-pressure mechanism.

## Conclusion Grade

**Research Only / Needs Revision**

The broader hypothesis remains plausible, but v1 is not ready for Trader handoff or serious backtest promotion.

## Recommended Next Step

Quant should revise the contract only after deciding the correct observable footprint:

- Should funding use predicted/quoted funding rather than settled funding history?
- Should basis be cross-venue, perp-mark-vs-index, or sign-aware rather than simple Bybit perp close vs spot close?
- Should the pressure condition require rising OI plus deteriorating price/volume confirmation instead of positive basis?
- Does the mechanism belong on BTC only, or should it scan symbols where funding/basis extremes are actually present?

If the revised contract requires predicted funding, orderbook pressure, cross-exchange basis, or archived receive-time semantics, it should go back through DataProvider Developer review before a serious backtest.

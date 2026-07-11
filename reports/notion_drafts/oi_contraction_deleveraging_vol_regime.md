# ResearchIdea: OI Contraction / Deleveraging Volatility Regime

<callout icon="🧪" color="blue_bg">
	**Status:** ResearchIdea / first-pass mechanism note. This is not a trade signal yet. Current conclusion should be read as: *worth formal event-study validation, not yet paper-tradable.*
</callout>

## Metadata

```yaml
id: research_idea_oi_contraction_deleveraging_vol_regime
created_at: 2026-06-01T10:16:08Z
created_by: QUANT
created_by_agent: JAQUAN
status: draft_research_idea
priority: high
next_owner: QUANT
candidate_symbols: [BTCUSDT, ETHUSDT]
candidate_source: Bybit linear perp + spot fixtures
expected_horizon: 4h-24h
research_conclusion: research_only_candidate
```

## One-sentence thesis

When BTC/ETH perpetual open interest contracts sharply over a short window, the market may be entering a deleveraging / repositioning regime where future realized volatility and tail risk rise over the next 4-24 hours.

This is deliberately framed as a **volatility / risk-regime hypothesis**, not a directional short signal. The last leverage-pressure direction attempts looked too easy, which is usually the market's polite way of saying "please donate more sample size."

## Why I picked this idea

I am choosing this over a direct basis/funding directional signal because the first diagnostics were more coherent for **future volatility** than for **future return direction**.

From the available 365d Bybit BTC/ETH fixture:

- BTC base mean absolute 24h forward return: about **1.54%**
- BTC after 4h OI contraction bottom decile: about **2.01%** mean absolute 24h forward return
- ETH base mean absolute 24h forward return: about **2.49%**
- ETH after 4h OI contraction bottom decile: about **2.77%** mean absolute 24h forward return

That is not a finished result, but it is a better starting clue than "basis high means short," where BTC and ETH gave inconsistent directional signs.

## Suspected market mechanism

Perpetual open interest contraction can represent one or more of the following:

1. **Forced deleveraging**
	- Leveraged participants reduce exposure after adverse movement, liquidation risk, margin pressure, or funding/volatility stress.

2. **Crowded-position unwind**
	- A previously crowded positioning state starts clearing. Even if the first move has happened, residual liquidity gaps may persist.

3. **Liquidity-provider repricing**
	- During deleveraging, market makers may widen spreads, reduce inventory tolerance, or quote less aggressively.

4. **Regime transition rather than event completion**
	- The OI drop may not mark the end of the move. It may mark that the market has moved from normal participation into unstable repositioning.

The key point: we should not assume the next return is negative. The cleaner claim is that **future return distribution widens**.

## Falsifiable hypothesis

```text
When 4h open-interest change for BTCUSDT or ETHUSDT linear perpetuals is in the bottom decile of its rolling/history distribution,
then over the next 4h-24h, realized absolute returns and tail outcomes should be higher than normal periods,
after controlling for recent realized volatility and recent return direction.
```

Expected effect:

- Primary: higher future absolute return / realized volatility
- Secondary: wider q05 / q95 forward-return tails
- Not primary: signed return prediction

Null hypothesis:

```text
After conditioning on recent volatility and recent price movement, OI contraction contains no incremental information about future 4h-24h volatility or tail risk.
```

## Candidate observations

Required point-in-time observations:

```yaml
ObservationRequirements:
  required_observations:
    - kind: perp_open_interest
      subject: BTCUSDT / ETHUSDT linear perp
      required_fields:
        - open_interest_notional_usdt or open_interest_raw
      lookback_window: 4h plus warmup for percentile / z-score
      timestamp_requirements:
        occurred_at: exchange event / interval timestamp
        observed_at: data receive or fixture replay timestamp
    - kind: candle
      subject: BTCUSDT / ETHUSDT linear perp
      required_fields: [open, high, low, close, volume]
      granularity: 5m or 1h derived bars
    - kind: candle
      subject: BTCUSDT / ETHUSDT spot
      required_fields: [open, high, low, close, volume]
      granularity: 5m or 1h derived bars
```

Nice-to-have controls:

- perp / spot basis
- funding settlement or predicted funding, if point-in-time semantics are clean
- session / UTC hour
- recent realized volatility
- recent directional return

## First-pass event design

Event condition:

```text
oi_change_4h <= rolling_or_sample_bottom_decile
```

Potential variations:

- bottom 5%, 10%, 20%
- absolute OI drop threshold
- rolling 90d percentile instead of full-sample percentile
- require non-overlapping events to avoid repeated counting of the same deleveraging episode

Forward outcomes:

- abs forward return: 4h, 8h, 24h
- realized volatility over 4h / 24h
- q05 / q95 forward return
- max adverse excursion and max favorable excursion
- realized range: high-low over horizon

Controls / benchmarks:

1. **Unconditional baseline**
	- All eligible hours.

2. **Recent-volatility matched baseline**
	- Compare OI contraction events to periods with similar trailing realized volatility.

3. **Recent-return matched baseline**
	- Compare against periods after similar 4h downside/upside moves without OI contraction.

4. **UTC session baseline**
	- Control for the fact that crypto volatility concentrates around UTC 12-16 in current diagnostics.

5. **OI expansion control**
	- Compare bottom-decile OI change against top-decile OI change.

## Preliminary evidence from current fixture

Current fixture:

```yaml
source: Bybit 365d fixture
symbols: [BTCUSDT, ETHUSDT]
window: 2025-06-01 06:00 UTC to 2026-06-01 06:00 UTC
hourly_rows_per_symbol: 8761
```

Quick diagnostic results:

```yaml
BTCUSDT:
  base_abs_4h_return: 0.593%
  base_abs_24h_return: 1.541%
  oi_change_4h_bottom_decile:
    events: 257
    abs_4h_return: 0.641%
    abs_24h_return: 2.012%
    fwd_24h_q05: -3.534%
    fwd_24h_q95: 6.187%
  oi_change_4h_top_decile:
    events: 257
    abs_4h_return: 0.582%
    abs_24h_return: 1.688%

ETHUSDT:
  base_abs_4h_return: 0.920%
  base_abs_24h_return: 2.487%
  oi_change_4h_bottom_decile:
    events: 256
    abs_4h_return: 0.937%
    abs_24h_return: 2.773%
    fwd_24h_q05: -6.615%
    fwd_24h_q95: 7.298%
  oi_change_4h_top_decile:
    events: 257
    abs_4h_return: 0.786%
    abs_24h_return: 2.530%
```

Interpretation:

- BTC shows a more visible 24h volatility lift after OI contraction.
- ETH shows a smaller but directionally similar lift.
- The effect appears more about wider distribution than mean signed return.
- This evidence is preliminary because events may overlap and are not yet volatility/session matched.

## What would make this useful?

This could become useful as a **risk-regime signal** if it reliably says:

```text
The next 4-24h is likely to have wider tails than normal.
```

Trader-facing uses, if validated later:

- reduce leverage during unstable deleveraging regimes
- widen stops / reduce false precision around entries
- require stronger confirmation before adding exposure
- switch from directional alpha mode to risk-control mode
- condition breakout strategies on post-deleveraging volatility expansion

It should not initially be sold as:

- a standalone long/short strategy
- liquidation prediction oracle
- a universal crash detector
- a magic button, because sadly those remain illegal under market microstructure law

## Failure modes

1. **Recent-volatility confound**
	- OI contraction may only be a proxy for price already moving.
	- Required test: volatility-matched controls.

2. **Direction confound**
	- OI contraction after a price crash may look like predictive volatility, but the price move itself explains the result.
	- Required test: recent-return matched controls.

3. **Overlapping-event inflation**
	- One deleveraging episode can produce many adjacent event bars.
	- Required test: non-overlapping episode clustering.

4. **Exchange-specific artifact**
	- Bybit OI may not represent broader market leverage.
	- Required future test: Binance/OKX/Coinbase perp data if available.

5. **Timestamp semantics**
	- Historical OI timestamps may not equal live observed availability.
	- Required DataProvider review before any serious backtest.

6. **Tail asymmetry instability**
	- The direction of tails may change by regime; do not hardcode short bias.

## Stop / reject conditions

Reject or downgrade if:

- The effect disappears after matching recent volatility and recent return.
- Non-overlapping event clustering removes most of the apparent lift.
- BTC and ETH disagree materially across multiple windows.
- Rolling train/test shows the relationship only exists in one short episode.
- The result cannot plausibly survive realistic latency and execution assumptions for any Trader use case.
- DataProvider review cannot make OI observations replay-safe.

## Recommended next artifact

Next Quant-owned artifact:

```text
MechanismNote + ResearchHypothesis
```

Then:

```text
ObservationRequirements + DataProviderHandoff
```

Only after the timestamp and fixture semantics are reviewed should this move into a formal signal contract or backtest. The right next move is to sharpen the empirical question, not to give ourselves another ornate backtest-shaped mirror.

## Open questions for comments

- Should the primary target be **future realized volatility**, **tail risk**, or **risk-budget throttle utility**?
- Should events be defined by rolling percentile or fixed absolute OI contraction?
- Should OI contraction be tested alone first, or only after controlling for price move and session from the beginning?
- Should this be BTC/ETH only for fast validation, or immediately designed as a multi-venue / multi-symbol study?

# ResearchIdea Report: Leverage Pressure / Liquidation Downside

## Artifact

- Artifact type: `ResearchIdea`
- Artifact id: `idea_leverage_pressure_liquidation_downside_v1`
- Artifact path: `artifacts/research_ideas/idea_leverage_pressure_liquidation_downside_v1.yaml`
- Created by role: `HERMES`
- Created by agent: `JAQUAN`
- Created at: `2026-05-27T23:19:04+08:00`
- Next owner: `QUANT`
- Priority: `high`

## One-line idea

High perpetual funding plus rising open interest, when not confirmed by spot demand, may indicate crowded leveraged longs and elevated short-horizon downside liquidation risk.

This is not the rule `funding high => short`. That rule is how a bull market teaches humility, usually with leverage.

## Background

Perpetual futures are a central venue for short-term crypto risk transfer. When leveraged long demand becomes crowded, several observable variables can move together:

- funding rises because long demand exceeds short demand;
- open interest rises because new leveraged positions are being added;
- perp price or mark price may lead spot;
- spot volume or spot return may fail to confirm the perp-led move.

The research question is whether this state describes fragile price support rather than durable demand.

If price moves slightly against crowded leveraged longs, forced deleveraging can become mechanical:

1. leveraged longs move closer to margin limits;
2. discretionary stops fire;
3. liquidation engines sell into the market;
4. market sell flow pushes price lower;
5. lower prices trigger more stops/liquidations.

The expected footprint is not necessarily a consistently negative average return. The more realistic first target is a distributional shift: fatter downside tails, worse adverse excursion, higher downside volatility, or increased liquidation activity over the next 4h-24h.

## Suspected mechanism

```text
perp long demand rises
-> funding becomes elevated
-> open interest expands
-> spot demand fails to confirm
-> price support becomes fragile
-> adverse move triggers forced selling
-> liquidation / stop feedback increases downside tail risk
```

Why this might persist:

- liquidation engines are mechanical rather than patient;
- leverage constraints force fast position reduction;
- liquidity providers may reduce depth as volatility and inventory risk rise;
- perp and spot capital are segmented across venues and mandates;
- public funding/OI data describes crowding pressure, not necessarily a directly arbitrageable mispricing.

## Candidate observations

Minimum useful data:

- perp funding rate
- perp open interest
- perp mark/index price or perp candles
- spot candles
- spot volume

Useful but optional data:

- liquidation prints
- orderbook depth / spread
- exchange-level basis

Initial symbols:

- `BTC-PERP`
- `ETH-PERP`
- `BTC-USD`
- `ETH-USD`

Expected horizon:

- `4h-24h`

## What QUANT should test next

The next workflow artifacts should be:

1. `MechanismNote`
2. `ResearchHypothesis`
3. `ObservationRequirements`

The first falsifiable hypothesis should be distributional, not strategy-first:

```text
When BTC/ETH perpetual funding is elevated and rising,
open interest is increasing,
and spot return/volume does not confirm the perp move,
then future 4h-24h returns should show worse downside quantiles,
larger max adverse excursion, or more negative skew than unconditional periods,
after reasonable cost and latency assumptions.
```

Important early tests:

- forward returns at 4h, 8h, 12h, and 24h;
- downside 5% and 10% quantiles;
- max adverse excursion over horizon;
- realized range / volatility after signal state;
- conditional liquidation volume if reliable liquidation prints exist;
- whether signal strength sorts downside risk.

## Baselines and controls

This idea should not be compared only against unconditional periods. QUANT should compare against:

- high funding only;
- rising open interest only;
- negative spot momentum only;
- high realized volatility regime;
- simple short momentum baseline;
- bull / bear / sideways regime splits.

If the combined condition does not beat these simpler explanations, the story is probably doing more work than the signal. Markets enjoy that kind of comedy.

## Known risks

- High funding can persist during spot-led bull markets.
- Public funding/OI thresholds may decay quickly.
- Exchange-level open interest may be noisy or semantically inconsistent.
- The effect may only reflect short beta or volatility timing.
- Costs, funding payments, spread, slippage, and latency may consume apparent edge.
- Liquidation data and orderbook depth may be hard to reconstruct point-in-time.
- A standalone short signal may be inferior to using this as a long-risk reduction filter.

## Initial prior

The conservative prior is:

```text
Useful as a risk regime indicator: plausible.
Useful as a standalone short alpha: possible but lower probability.
Production candidate from first-pass research: unlikely.
```

The most likely positive outcome is not necessarily `short aggressively`. It may be:

- reduce long exposure;
- avoid adding long risk;
- tighten risk budgets;
- require stronger confirmation from other long signals;
- flag liquidation-risk regimes for Trader review.

## Stop / reject conditions

QUANT should reject or defer if:

- funding + OI adds no information beyond simple momentum/volatility controls;
- the effect disappears out-of-sample;
- only one narrow threshold works;
- data is not point-in-time usable;
- downside shift is too small after costs;
- the signal only works in a known bear regime and has no incremental value.

## Recommended next artifact

Proceed to `MechanismNote` if this ResearchIdea is accepted.

# Leverage Pressure v2 Research Revision Note

<callout icon="🧭" color="blue_bg">
這是下一輪研究的 Quant revision note。目的不是調 threshold 找漂亮回測，而是把 v1 的 `funding + OI + weak spot confirmation` 想法改寫成一個更可驗證的 leverage fragility / downside distribution study。
</callout>

## Metadata

- created_at: 2026-05-30T15:13:18+08:00
- created_by: QUANT
- created_by_agent: JAQUAN
- related_research_idea: `idea_leverage_pressure_liquidation_downside_v1`
- related_hypothesis: `hyp_leverage_pressure_liquidation_downside_v1`
- status: draft_for_discussion
- conclusion_grade: research_only_needs_revision

## 1. 為什麼需要 v2 revision

v1 最危險的地方不是「結果還不夠好」，而是 framing 容易滑向：

```text
funding high -> short
```

這個 framing 太淺，且很容易 overfit。Funding 與 OI 都是公開、常見、反身性很強的變數；如果我們只用少數 threshold 去找 short entry，結果大概率是在替歷史 crash 做剪影。

v2 改成問一個比較穩健的問題：

```text
當 leverage pressure 升高時，未來 4h-24h 的 downside tail 是否穩定變差？
```

這讓研究從 prediction / directional alpha 降級成 distributional regime test。聽起來沒那麼性感，但市場不負責滿足我們的行銷需求。

## 2. Revised hypothesis

```text
When funding pressure is elevated or rising,
open interest expands,
and spot demand fails to confirm perp-led pressure,
the market enters a leverage-fragility regime in which future 4h-24h downside tail risk is worse than unconditional periods and simpler controls.
```

### Target variable

主要觀察不是 mean return，而是：

- forward 4h / 8h / 12h / 24h return distribution
- 5% / 10% downside quantile
- max adverse excursion
- probability of large negative move, e.g. below rolling-vol scaled threshold
- downside skew / left-tail concentration

### Null hypothesis

```text
The full leverage-pressure condition does not produce worse downside tail risk than:
1. unconditional periods,
2. high funding only,
3. rising OI only,
4. high realized volatility,
5. recent negative momentum,
6. bull/bear regime controls.
```

If full condition does not beat these controls, the mechanism is either redundant or too noisy for Quant use.

## 3. v2 framing: risk filter first, short signal later

Primary candidate:

```text
Leverage Fragility Risk Filter
```

Possible downstream uses:

- reduce long exposure confidence
- block new long entries during fragile regimes
- trigger hedge review
- send Trader a risk alert
- haircut other bullish signal confidence

Secondary candidate, only if evidence is strong:

```text
Conditional short signal
```

But this requires stronger gates:

- full condition beats controls
- cost / slippage / funding stress does not erase usefulness
- effect is not single-crash dominated
- parameter neighborhood is stable
- DataProvider point-in-time semantics are reviewed
- Trader can define clear paper-trading pass/fail criteria

## 4. Composite score design, without parameter fishing

v2 should avoid one magic threshold. Use a monotonic score and bucket test.

Candidate score:

```text
leverage_fragility_score =
  funding_pressure_component
+ oi_expansion_component
+ perp_spot_divergence_component
+ weak_spot_confirmation_component
+ optional_volatility_stress_component
```

### 4.1 Funding pressure component

Candidate features:

- funding percentile over rolling window
- funding z-score over rolling window
- funding change over recent window
- predicted funding snapshot, only if DataProvider review confirms point-in-time visibility

Important: settled funding is cleaner but may be too late. Predicted funding is more timely but much more dangerous for point-in-time semantics. If we use predicted funding, it needs a separate DataProvider review.

### 4.2 OI expansion component

Candidate features:

- OI percentage change over 4h / 8h / 24h
- OI z-score relative to recent history
- OI expansion conditional on price up / flat

Need caution: rising OI can be basis desks, hedged exposure, or liquidity provision — not necessarily crowded directional longs.

### 4.3 Perp-led pressure component

Candidate features:

- perp return minus spot return
- basis expansion
- mark/index divergence if available

This component tries to separate cash-led demand from derivative-led pressure.

### 4.4 Weak spot confirmation component

Candidate features:

- spot volume percentile not rising while perp pressure rises
- spot return weaker than perp return
- spot volume / perp volume divergence if available

This is the conceptual hinge. Without weak spot confirmation, high funding may simply be a healthy bull trend.

## 5. Event-study design

### Universe

First pass:

- BTC perpetual / spot
- ETH perpetual / spot

Do not start with long-tail coins. Small caps add microstructure noise, survivorship issues, and venue-specific weirdness before the basic mechanism is even falsified.

### Sampling

Candidate event construction:

- build rolling features at fixed intervals, e.g. 15m or 1h
- compute leverage_fragility_score using only observations visible by `signal_time`
- bucket observations by score quantile
- compare forward downside distribution by bucket

### Horizons

Use multiple horizons:

- 4h
- 8h
- 12h
- 24h

A real fragility regime should not require one exact horizon to work. If only `11.37h` works, congratulations, we discovered a spreadsheet ghost.

## 6. Controls and benchmarks

Minimum controls:

- unconditional periods
- high funding only
- rising OI only
- funding + OI without spot confirmation
- realized volatility regime
- recent return / momentum regime
- bull / bear / sideways market regime
- same average event frequency control

The critical comparison is:

```text
full condition vs high funding + rising OI only
```

If weak spot confirmation adds no separation, the v2 mechanism loses its core claim.

## 7. Evidence table expected from next empirical pass

The next empirical artifact should report, by symbol and horizon:

- event count
- coverage / missing data rate
- average forward return
- median forward return
- 5% quantile
- 10% quantile
- max adverse excursion
- crash-period contribution
- regime breakdown
- control comparison
- score bucket monotonicity

For each comparison, label result as:

- supports fragility hypothesis
- weak / mixed
- explained by control
- insufficient data
- invalid due to point-in-time issue

## 8. Data requirements and DataProvider boundary

Current approved fixture support can cover a conservative v2 using historical Bybit-style funding / OI / candles, but predicted funding snapshots are a separate question.

If v2 uses only settled funding + OI + candles:

- Quant can write an event-study spec and run replay-safe exploratory analysis against the reviewed fixture.

If v2 uses predicted funding snapshots:

- Quant must write updated ObservationRequirements.
- DataProvider Developer must review endpoint availability, `observed_at`, revision/backfill behavior, and historical/live consistency.

Do not silently mix predicted funding into the study just because it feels more realistic. Realistic lookahead is still lookahead, just wearing nicer shoes.

## 9. Decision gates

### Upgrade to stronger Research Only if

- top score buckets have consistently worse downside quantiles
- full condition beats high funding / OI / volatility controls
- BTC and ETH are directionally consistent, even if effect size differs
- multiple horizons show similar tail-risk separation
- effect is not dominated by one crash episode
- point-in-time semantics are acceptable

### Keep as Needs Revision if

- signal frequency is too low
- score bucket ordering is unstable
- only one horizon works
- weak spot confirmation is ambiguous
- effect exists but is fully explained by volatility or momentum

### Reject if

- full condition does not beat simpler controls
- score has no monotonic relation to downside risk
- data cannot be replayed point-in-time
- results are single-event dominated
- evidence only appears after tuning thresholds

### Consider Trader handoff only if

- research evidence supports risk-filter usefulness
- Quant can define signal semantics without sizing leakage
- data integrity status is at least partial/passed
- cost and execution caveats are explicit

No Trader handoff from a zero-event or threshold-fragile study.

## 10. Recommended next concrete work

Next work should be a Quant-owned empirical spec, not production code:

```text
SignalResearchResult / EventStudySpec:
- define score components
- define bucket method
- define controls
- define forward horizon calculations
- define rejection gates before running broad tuning
```

Then run the smallest replay-safe event study on BTC / ETH only.

If the first pass shows no distributional separation, reject or park the idea. If it shows tail separation, then write a cleaner SignalContract as a risk filter rather than a short-entry strategy.

## 11. Jaquan's current prior after v1 comments

- standalone short alpha: low
- risk filter value: medium
- mechanism plausibility: medium-high
- data semantic risk: medium
- overfit risk: high
- next best action: empirical event-study spec with conservative gates

My actual expectation: if this survives, it will probably be useful as a defensive overlay, not as a heroic short button. Which is fine. Heroic short buttons are usually just liquidation cosplay.

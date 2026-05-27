# Quant Research Workflow

This document defines the artifact-first Quant workflow for the trading system.

The goal is not to make research slower for sport. The goal is to keep a multi-agent trading runtime from turning every market hunch into an overfit backtest with a victory lap attached.

## Role boundary

Quant owns:

- market mechanism discovery
- falsifiable alpha hypotheses
- observation requirements
- signal contracts
- minimal signal implementations
- smoke and replay validation
- signal-level research backtests
- benchmark, robustness, regime, and failure-mode analysis
- research reports and Trader handoffs

Quant does not own:

- raw external API/provider implementation
- final point-in-time data quality approval
- position sizing
- portfolio/risk decisions
- broker/execution behavior
- live order submission

Canonical ownership flow:

```text
DataProvider Developer -> Observation -> Quant Signal -> Trader Strategy -> OrderIntent -> Execution/Broker
```

## Design principles

1. Start from market mechanism, not indicators.
2. Make each hypothesis falsifiable before implementation.
3. Define point-in-time observation requirements before writing signal code.
4. Treat `observed_at` as the replay visibility boundary.
5. Keep signal semantics separate from Trader-owned sizing and portfolio decisions.
6. Define benchmarks before parameter tuning.
7. Prefer robustness evidence over single-run prediction quality.
8. Record negative conclusions so failed research does not reincarnate every few days wearing a different parameter grid.

## Canonical artifact sequence

```text
ResearchIdea
-> MechanismNote
-> ResearchHypothesis
-> ObservationRequirements
-> DataProviderHandoff
-> SignalContract
-> SignalImplementation
-> SmokeReplayValidation
-> SignalResearchResult
-> BenchmarkComparison
-> RobustnessReview
-> RegimeAttribution
-> ResearchReport
-> TraderHandoff
-> DecisionRecord
```

A task may stop at any gate. Stopping early is valid progress when the evidence says the idea is vague, unobservable, duplicated, or not robust.

## 0. ResearchIdea

Purpose: turn a raw idea into a research candidate or reject/defer it.

Required fields:

```yaml
ResearchIdea:
  id:
  created_at:
  created_by:
  created_by_agent:
  summary:
  suspected_mechanism:
  candidate_sources:
  candidate_symbols:
  expected_horizon:
  why_it_might_persist:
  known_risks:
  duplicate_of:
  next_owner:
  priority:
```

Gate:

- Has a concise summary.
- Names a plausible market mechanism or states that one is missing.
- Lists candidate sources/symbols/horizon.
- Does not jump directly to strategy code.

## 1. MechanismNote

Purpose: describe why an inefficiency could exist.

Questions Quant must answer:

- Who is forced to trade?
- Who is slow, constrained, or structurally disadvantaged?
- Who bears inventory or liquidity risk?
- Why might the effect not decay immediately?
- What observable footprint should the mechanism leave?
- What alternative explanations could invalidate it?

Template:

```yaml
MechanismNote:
  id:
  research_idea_id:
  mechanism_summary:
  participants:
    forced_traders:
    slow_traders:
    liquidity_providers:
    informed_traders:
  pressure_source:
  expected_observable_footprints:
  expected_decay_reason:
  why_it_might_persist:
  alternative_explanations:
  invalidation_conditions:
```

Gate:

- Names the participant pressure, not just an indicator.
- Defines observable footprints.
- Includes alternative explanations and invalidation conditions.

## 2. ResearchHypothesis

Purpose: convert the mechanism into a falsifiable statement.

Preferred shape:

```text
When X observation is visible to the system at time t,
within horizon H,
asset or market variable Y should show directional/distributional shift Z,
and the effect should survive reasonable costs, latency, and slippage assumptions.
```

Template:

```yaml
ResearchHypothesis:
  id:
  mechanism_note_id:
  statement:
  trigger_condition:
  target_symbol:
  target_variable: return | volatility | spread | liquidity | drawdown | other
  horizon:
  expected_direction:
  expected_effect_size:
  null_hypothesis:
  minimum_effect_after_cost:
  assumptions:
  failure_modes:
  falsification_tests:
```

Gate:

- Has condition, visibility time, target variable, horizon, and null hypothesis.
- Can be rejected with available or requested data.
- Includes minimum effect after cost.

## 3. ObservationRequirements

Purpose: define the point-in-time data contract before code.

Template:

```yaml
ObservationRequirements:
  id:
  hypothesis_id:
  required_observations:
    - kind:
      subject:
      required_fields:
      lookback_window:
      observed_at_rule:
      occurred_at_rule:
      stale_tolerance:
      required_for_signal: true
  missing_data_policy:
  late_arrival_policy:
  replay_requirement:
  data_quality_risks:
```

Gate:

- Every observation has kind, subject, fields, and timestamp semantics.
- Missing/stale/late policies are explicit.
- DataProvider Developer can review feasibility without guessing Quant's intent.

## 4. DataProviderHandoff

Purpose: hand concrete point-in-time data requirements to DataProvider Developer.

Template:

```yaml
DataProviderHandoff:
  id:
  created_at:
  created_by: QUANT
  hypothesis_id:
  source:
  source_type: exchange | file | stream | telegram | news | macro | onchain | other
  required_fields:
  subjects:
  observation_kinds:
  expected_latency:
  timestamp_semantics:
    occurred_at_rule:
    observed_at_rule:
    timezone:
  missing_data_policy_needed:
  duplicate_policy_needed:
  late_arrival_policy_needed:
  revision_policy_needed:
  replay_requirement:
  minimum_fixture:
  data_quality_risks:
  quant_dependency:
  requested_review:
```

Gate:

- Asks DataProvider Developer to confirm point-in-time usability.
- Defines `observed_at` and `occurred_at` expectations.
- Requires a historical/live mapping and replay story for serious research.

## 5. SignalContract

Purpose: define signal behavior before implementation.

Template:

```yaml
SignalContract:
  id:
  signal_name:
  hypothesis_id:
  mechanism_summary:
  required_kinds:
  required_subjects:
  required_payload_fields:
  lookback_window:
  stale_tolerance:
  warmup_required:
  direction_rule:
  strength_rule:
  confidence_rule:
  reason_codes:
    - code:
      meaning:
  metadata_schema:
  failure_modes:
  minimum_tests:
  trader_visible_semantics:
```

Gate:

- Direction, strength, confidence, and reason codes are stable and documented.
- Failure modes and minimum tests are listed.
- Trader can understand what the signal means without reading the implementation.

## 6. SignalImplementation

Purpose: implement the smallest deterministic signal that satisfies the contract.

Requirements:

- Consume only `Observation` objects or typed payloads.
- Avoid raw API dependencies.
- Return `None` when data is insufficient or unsafe.
- Handle stale data explicitly.
- Use the maximum used `observed_at` for signal timestamp.
- Emit deterministic `SignalEvent` values.
- Put trace/debug details in metadata.
- Never create `OrderIntent` or encode sizing/portfolio rules.

Gate:

- Unit tests cover missing data, stale data, no-trigger, normal trigger, timestamp correctness, and determinism.
- Signal code has no provider, broker, sizing, or portfolio dependency.

## 7. SmokeReplayValidation

Purpose: prove the signal can run safely under point-in-time replay before serious backtesting.

Template:

```yaml
SmokeReplayValidation:
  id:
  signal_contract_id:
  signal_name:
  fixture:
  tests_run:
  passed:
  failures:
  timestamp_check:
  lookahead_check:
  determinism_check:
  notes:
```

Gate:

- Replay only exposes observations where `observed_at <= current_time`.
- Signal event timestamps do not exceed replay time.
- Metadata trace only references visible observations.
- Repeated replay emits identical events.

## 8. SignalResearchResult

Purpose: evaluate whether the signal has a detectable effect, before portfolio-level complexity.

Template:

```yaml
SignalResearchResult:
  id:
  hypothesis_id:
  signal_contract_id:
  data_scope:
  signal_count:
  horizons:
  forward_return_summary:
  strength_bucket_analysis:
  confidence_bucket_analysis:
  gross_edge:
  cost_assumption:
  net_edge_estimate:
  preliminary_conclusion:
  warnings:
```

Gate:

- Reports event frequency and forward return distributions.
- Checks strength/confidence sorting.
- Includes rough cost assumptions.
- Does not rely on one equity curve as proof.

## 9. BenchmarkComparison

Purpose: determine whether results beat relevant baselines or merely express beta/exposure.

Required benchmarks for directional crypto research:

- cash
- buy-and-hold
- fixed exposure
- volatility-adjusted exposure
- same-average-exposure benchmark
- simple momentum or mean-reversion baseline when relevant

Template:

```yaml
BenchmarkComparison:
  id:
  research_result_id:
  benchmarks:
    - name:
      construction:
      exposure:
      total_return:
      max_drawdown:
      volatility:
      sharpe:
      turnover:
  strategy_vs_benchmark:
  interpretation:
```

Gate:

- Benchmarks are declared before tuning.
- Underperforming buy-and-hold is labeled honestly as exposure control or defensive allocation when appropriate.

## 10. RobustnessReview

Purpose: test whether the result survives more than one sample and one parameter choice.

Template:

```yaml
RobustnessReview:
  id:
  research_result_id:
  parameter_grid:
  train_test:
    split_rule:
    train_result:
    test_result:
    continuous_state: true
  walk_forward:
    windows:
    selected_params:
    test_segments:
    aggregate_result:
  parameter_stability:
    top_params:
    neighborhood_stability:
    overfit_warning:
  cost_sensitivity:
  conclusion:
```

Gate:

- Test replay does not reset rolling state artificially.
- Parameter grid is summarized, not hidden behind the best result.
- Nearby parameters are inspected for stability.
- Cost sensitivity is included for any paper-trade candidate.

## 11. RegimeAttribution

Purpose: identify when the signal works, fails, or simply changes exposure.

Minimum regimes:

- bull / uptrend
- bear / downtrend
- sideways / choppy
- high volatility
- low volatility
- crisis / liquidation periods when relevant
- low liquidity periods when relevant

Template:

```yaml
RegimeAttribution:
  id:
  research_result_id:
  regime_definition:
  regimes:
    - name:
      bars:
      signal_count:
      strategy_return:
      benchmark_return:
      max_drawdown:
      exposure:
      trades:
      fees:
      notes:
  failure_regimes:
  trader_risk_implications:
```

Gate:

- Reports at least trend and volatility regime splits.
- Names failure regimes explicitly.
- Provides risk implications for Trader.

## 12. ResearchReport

Purpose: consolidate all evidence into a reviewable artifact.

Template:

```yaml
ResearchReport:
  id:
  hypothesis_id:
  signal_contract_id:
  summary:
  data_scope:
  methodology:
  completed_checks:
  partial_checks:
  not_done_checks:
  key_results:
  benchmark_comparison:
  robustness_summary:
  regime_summary:
  cost_sensitivity:
  failure_modes:
  conclusion_grade: reject | research_only | paper_trade_candidate | production_candidate
  recommended_next_owner:
  required_reviews:
```

Conclusion grades:

- `reject`: no stable out-of-sample effect, benchmark dominates, or data is invalid.
- `research_only`: interesting behavior but insufficient robustness or trading evidence.
- `paper_trade_candidate`: reasonable out-of-sample/risk evidence; needs paper validation.
- `production_candidate`: rare; requires walk-forward, benchmark, cost, data integrity, execution, risk, and paper evidence.

Gate:

- Lists completed, partial, and missing checks.
- Uses conservative conclusion grading.
- Cannot claim production readiness without data integrity, Trader, execution, and paper evidence.

## 13. TraderHandoff

Purpose: pass signal semantics and evidence to Trader without crossing into sizing/risk ownership.

Template:

```yaml
TraderHandoff:
  id:
  created_at:
  created_by: QUANT
  hypothesis_id:
  signal_contract_id:
  signal_name:
  reason_codes:
    - code:
      meaning:
  direction_semantics:
  strength_interpretation:
  confidence_interpretation:
  expected_horizon:
  expected_frequency:
  expected_holding_period:
  expected_turnover:
  expected_exposure_profile:
  cost_sensitivity_summary:
  regime_behavior:
  known_failure_modes:
  data_integrity_status: not_reviewed | passed | failed | partial
  research_conclusion: reject | research_only | paper_trade_candidate | production_candidate
  paper_trading_recommendation:
  open_questions_for_trader:
```

Gate:

- Contains no quantity, leverage, portfolio allocation, or live-trading command.
- Includes known failure modes and open Trader questions.
- Separates signal quality from trade feasibility.

## 14. DecisionRecord

Purpose: make research outcomes durable and prevent repeated work.

Template:

```yaml
DecisionRecord:
  id:
  created_at:
  created_by: HERMES
  decision:
  status: accepted | rejected | deferred | needs_revision
  reason:
  evidence:
  owners:
  follow_up_tasks:
  do_not_repeat_until:
  related_artifacts:
```

Gate:

- Includes evidence and related artifacts.
- Has a follow-up task or stop condition.
- Rejected/deferred work explains why it should not be repeated immediately.

## Tooling roadmap

### Phase 1: Artifact discipline

Build these first:

- artifact schemas for the canonical sequence
- template generator for each artifact
- validators and linters
- duplicate research search across ideas, hypotheses, reports, and decisions

Initial CLI support lives in `quant_tools.artifacts`:

```bash
python3 -m quant_tools.artifacts list
python3 -m quant_tools.artifacts new SignalContract --output artifacts/signal_contract.yaml
python3 -m quant_tools.artifacts validate artifacts/signal_contract.yaml
```

Success condition: agents produce reviewable artifacts instead of free-form notes.

### Phase 2: Point-in-time research loop

Build:

- `ReplayDataProvider` reading Observation JSONL
- observation fixture factories
- signal contract to pytest scaffold
- signal replay runner emitting SignalEvent JSONL
- lookahead guard checking `observed_at <= current_time`

Success condition: a signal can be replayed deterministically without seeing future observations.

### Phase 3: Signal-level research

Build:

- event study engine
- forward return calculator using first tradable price after signal time
- strength/confidence bucket analysis
- benchmark engine
- research report generator
- report linter

Success condition: Quant can decide whether a hypothesis deserves more work without a full portfolio backtest.

### Phase 4: Robustness

Build:

- walk-forward runner
- parameter grid runner
- parameter stability analyzer
- cost sensitivity runner
- regime classifier and attribution engine

Success condition: paper candidates have robustness evidence, not just a flattering parameter island.

### Phase 5: Runtime governance

Build:

- decision record generator
- task router integration for DataProvider Developer and Trader handoffs
- research duplicate detector
- meeting/digest summaries of blocked artifacts and missing gates

Success condition: Hermes can coordinate the research runtime without role confusion or repetitive strategy loops.

## MVP recommendation

The first MVP should be:

```text
SignalContract YAML
-> scaffold signal tests
-> ReplayDataProvider reads Observation JSONL
-> signal_replay_runner emits SignalEvent JSONL
-> event_study_engine calculates forward returns
-> research_report_generator writes markdown
```

Do not start with a giant portfolio backtest platform. Start with artifact discipline and point-in-time replay. The market will still be there after the paperwork. Unfortunately.

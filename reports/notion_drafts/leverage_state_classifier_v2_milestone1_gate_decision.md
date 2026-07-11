# Leverage-State Classifier v2 — Milestone 1 Gate Decision

**Created:** 2026-06-16 20:01 CST  
**Owner role:** QUANT  
**Owner agent:** JAQUAN  
**Roadmap milestone:** Milestone 1 — leverage-state classifier v2

## Gate status

**Decision:** KEEP AS `Research Only / Risk Filter Candidate`; **no Trader handoff, no strategy promotion**.

The Milestone 1 evidence is sufficient to preserve the classifier family as a research risk-annotation lead, but insufficient for alpha, sizing, or execution work. Robustness did not fail, but it also did not make the effect broad or stable enough to promote. Markets remain annoyingly adaptive; the evidence is not magically less noisy because we named the states nicely.

## Source-of-truth data dependency

This gate depends on the Milestone 0 source-of-truth fixture:

```text
data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl
```

Milestone 0 data-quality note:

```text
reports/notion_drafts/bybit_leverage_source_of_truth_and_data_quality.md
```

Accepted fixture identity:

```yaml
fixture_version: bybit-20260614T095616Z
line_count: 1053382
symbols: [BTCUSDT, ETHUSDT]
replay_visibility: conservative_simulated_observed_at
```

## Data caveats carried into Milestone 1

- Historical `observed_at` is **conservative simulated observed-at**, not archived live receive time.
- The fixture is acceptable for first-pass and robustness Quant research simulation.
- It is **not** sufficient for production latency claims.
- Any future dashboard/risk annotation must restate this caveat.
- Older OI-dependent studies using pre-pagination-fix fixtures remain caveated and are not current evidence unless rerun.

## Validation commands documented / run

Milestone 0 fixture preflight:

```bash
python3 reports/data_quality/preflight_bybit_leverage_fixture.py \
  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \
  --out reports/data_quality/bybit_leverage_fixture_365d_20260614_regen_preflight.json
```

Provider regression:

```bash
python3 -m pytest tests/test_bybit_leverage_provider.py -q
```

Milestone 1 first-pass classifier:

```bash
python3 reports/leverage_state_classifier_v2/run_leverage_state_classifier_v2.py \
  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \
  --out-json reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json \
  --out-md reports/leverage_state_classifier_v2/leverage_state_classifier_v2.md
```

Milestone 1 robustness check:

```bash
python3 reports/leverage_state_classifier_v2/run_leverage_state_classifier_v2_robustness.py \
  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \
  --out-json reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.json \
  --out-md reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.md \
  --bootstrap-reps 1000 \
  --seed 20260616
```

Documentation integrity check performed during gate consolidation:

```bash
python3 - <<'PY'
import json
from pathlib import Path
for p in [
 'reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json',
 'reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.json',
 'reports/data_quality/bybit_leverage_fixture_365d_20260614_regen_preflight.json'
]:
    path = Path(p)
    print(p, 'exists=', path.exists(), 'bytes=', path.stat().st_size if path.exists() else None)
    if path.exists():
        obj = json.loads(path.read_text())
        print('  keys=', sorted(obj.keys())[:12])
        if 'decision' in obj:
            print('  decision=', obj['decision'])
        if 'bootstrap_reps' in obj:
            print('  bootstrap_reps=', obj['bootstrap_reps'], 'seed=', obj.get('seed'))
PY
```

Observed output:

```text
reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json exists= True bytes= 54372
  decision= research_only_risk_filter_candidate_first_pass
reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.json exists= True bytes= 34988
  decision= research_only_risk_filter_candidate_robustness_pass
  bootstrap_reps= 1000 seed= 20260616
reports/data_quality/bybit_leverage_fixture_365d_20260614_regen_preflight.json exists= True bytes= 8219
```

## First-pass evidence

First-pass report:

```text
reports/leverage_state_classifier_v2/leverage_state_classifier_v2.md
reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json
```

Classifier states tested:

- `true_deleverage`
- `passive_notional_shrink`
- `sticky_or_short_build`
- `risk_on_leverage_build`

First-pass setup:

```yaml
symbols: [BTCUSDT, ETHUSDT]
eligible_hours_per_symbol: 6505 / 8761
rolling_threshold_window: 2160 hours (~90d)
horizons: [24h, 48h, 72h]
matched_controls: volatility / recent return / UTC hour / funding regime candidates
```

First-pass evidence was directional only in patches, not broad enough for promotion:

- `passive_notional_shrink` showed the clearest larger forward absolute-move lead, especially ETH.
- Several other states were mixed or close to controls.
- Directional return evidence was unstable and secondary.
- The report already concluded: **Research Only / Risk Filter Candidate (first pass).**

## Robustness evidence

Robustness report:

```text
reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.md
reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.json
```

Robustness method:

```yaml
method: non_overlap_event_clustering_by_horizon_plus_cluster_bootstrap_event_minus_control_mean_diff
bootstrap_reps: 1000
seed: 20260616
```

Robustness result summary:

- Most event-control confidence intervals include zero after non-overlap clustering.
- `passive_notional_shrink` remains the only notable lead for larger absolute moves.
- ETH `passive_notional_shrink` 72h abs-return diff is positive with CI excluding zero: `mean_diff=0.025461`, `CI95=[0.000253, 0.052307]`, but clustered sample is small (`event_cluster_n=15`, `control_cluster_n=18`).
- Directional return evidence remains unstable; not alpha.
- Robustness output exists and is persisted; no missing/failed robustness result was found.

## Gate decision rationale

Accepted:

- regenerated fixture passed Milestone 0 hygiene;
- first-pass report exists;
- robustness report exists;
- validation commands and caveats are documented;
- there is at least one plausible risk-annotation lead (`passive_notional_shrink`).

Rejected / not promoted:

- no standalone directional alpha;
- no Trader handoff;
- no strategy/sizing/execution contract;
- no production/live timestamp claim;
- no dashboard contract until parameter stability is mapped.

## Roadmap consequence

**Milestone 1 status:** complete as a conservative research gate, not a promotion gate.

**Next roadmap step:** Milestone 2 — cross-venue funding and OI dispersion feasibility/data-quality review.

Before any future dashboard or risk annotation contract, add a parameter-stability map across rolling windows and quantile gates. If that stability check is weak, archive this branch as a research note rather than spending cycles polishing a pretty dashboard for noise.

## Help needed

No immediate user/DataProvider help is required for this gate. Help may be needed in Milestone 2 if exchange historical OI/funding access, timestamp semantics, or ToS/rate-limit constraints block cross-venue data collection.

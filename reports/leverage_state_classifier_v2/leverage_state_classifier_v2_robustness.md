# Leverage-State Classifier v2 — Milestone 1 Robustness Note

**Decision:** Research Only / Risk Filter Candidate. No Trader handoff.

## Scope

Small validation pass on existing classifier semantics: non-overlap clustering by forecast horizon plus cluster bootstrap confidence intervals for event-control mean differences.

## Inputs

- Fixture: `data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl`
- Fixture versions: `bybit-20260614T095616Z`
- Replay visibility: `conservative_simulated_observed_at`
- Rolling threshold window: 2160 hours
- Bootstrap reps: 1000; seed: 20260616

## Evidence summary

Mean diff is event minus matched-control after clustering overlapping event timestamps. CI is 95% cluster bootstrap CI.

### BTCUSDT

#### true_deleverage

Raw events: 341 | raw controls: 778

- 24h abs_return diff=-0.000960 CI95=[-0.006421, 0.004797] clusters e/c=44/72; rv diff=-0.000637 CI95=[-0.004513, 0.003281]; return diff=-0.004360 CI95=[-0.011903, 0.002796]
- 48h abs_return diff=0.002284 CI95=[-0.004908, 0.009173] clusters e/c=38/38; rv diff=0.001324 CI95=[-0.003520, 0.006025]; return diff=-0.000292 CI95=[-0.011117, 0.010520]
- 72h abs_return diff=-0.001756 CI95=[-0.009052, 0.005449] clusters e/c=29/27; rv diff=0.002019 CI95=[-0.003432, 0.008537]; return diff=-0.004411 CI95=[-0.017340, 0.008758]

#### passive_notional_shrink

Raw events: 56 | raw controls: 236

- 24h abs_return diff=0.002326 CI95=[-0.008644, 0.015515] clusters e/c=17/32; rv diff=0.006228 CI95=[-0.000045, 0.013028]; return diff=-0.003126 CI95=[-0.018466, 0.014443]
- 48h abs_return diff=0.003171 CI95=[-0.012600, 0.020739] clusters e/c=14/23; rv diff=0.004890 CI95=[-0.005514, 0.014161]; return diff=0.001218 CI95=[-0.014838, 0.019057]
- 72h abs_return diff=0.006751 CI95=[-0.007153, 0.021857] clusters e/c=13/21; rv diff=0.005661 CI95=[-0.003885, 0.015241]; return diff=0.004946 CI95=[-0.019843, 0.027857]

#### sticky_or_short_build

Raw events: 551 | raw controls: 689

- 24h abs_return diff=-0.001101 CI95=[-0.006161, 0.005173] clusters e/c=37/79; rv diff=0.001641 CI95=[-0.002706, 0.006419]; return diff=-0.007016 CI95=[-0.014954, 0.000163]
- 48h abs_return diff=0.002145 CI95=[-0.006040, 0.010401] clusters e/c=32/40; rv diff=0.004892 CI95=[-0.000629, 0.011008]; return diff=-0.012408 CI95=[-0.024969, 0.000189]
- 72h abs_return diff=0.000070 CI95=[-0.008529, 0.008422] clusters e/c=27/24; rv diff=0.004741 CI95=[-0.002581, 0.012032]; return diff=-0.003921 CI95=[-0.018142, 0.010949]

#### risk_on_leverage_build

Raw events: 468 | raw controls: 676

- 24h abs_return diff=-0.001403 CI95=[-0.005468, 0.003284] clusters e/c=41/74; rv diff=0.000347 CI95=[-0.002373, 0.003178]; return diff=-0.000798 CI95=[-0.007016, 0.005512]
- 48h abs_return diff=-0.001037 CI95=[-0.008956, 0.007652] clusters e/c=34/43; rv diff=-0.000409 CI95=[-0.004987, 0.004480]; return diff=-0.001292 CI95=[-0.013063, 0.010157]
- 72h abs_return diff=-0.002652 CI95=[-0.013657, 0.008207] clusters e/c=28/26; rv diff=0.001174 CI95=[-0.005496, 0.007102]; return diff=0.000749 CI95=[-0.013763, 0.015514]

### ETHUSDT

#### true_deleverage

Raw events: 386 | raw controls: 806

- 24h abs_return diff=0.002655 CI95=[-0.004857, 0.009464] clusters e/c=46/64; rv diff=0.001875 CI95=[-0.003987, 0.007005]; return diff=-0.011359 CI95=[-0.021457, -0.001503]
- 48h abs_return diff=0.001405 CI95=[-0.010172, 0.012418] clusters e/c=37/41; rv diff=0.001197 CI95=[-0.005537, 0.008026]; return diff=-0.011393 CI95=[-0.026172, 0.002625]
- 72h abs_return diff=0.001137 CI95=[-0.015650, 0.017931] clusters e/c=29/28; rv diff=0.003030 CI95=[-0.006319, 0.013336]; return diff=-0.006995 CI95=[-0.029227, 0.016682]

#### passive_notional_shrink

Raw events: 80 | raw controls: 296

- 24h abs_return diff=0.010827 CI95=[-0.001926, 0.023485] clusters e/c=20/31; rv diff=0.003972 CI95=[-0.004138, 0.012515]; return diff=0.003034 CI95=[-0.013865, 0.019576]
- 48h abs_return diff=0.017296 CI95=[-0.002871, 0.038106] clusters e/c=15/24; rv diff=0.005333 CI95=[-0.005552, 0.016460]; return diff=0.011967 CI95=[-0.017027, 0.039760]
- 72h abs_return diff=0.025461 CI95=[0.000253, 0.052307] clusters e/c=15/18; rv diff=0.002955 CI95=[-0.010342, 0.017069]; return diff=0.020524 CI95=[-0.022781, 0.059939]

#### sticky_or_short_build

Raw events: 470 | raw controls: 781

- 24h abs_return diff=0.000020 CI95=[-0.008382, 0.009093] clusters e/c=40/72; rv diff=0.004149 CI95=[-0.002108, 0.010481]; return diff=-0.009612 CI95=[-0.021061, 0.001523]
- 48h abs_return diff=0.001304 CI95=[-0.010953, 0.015365] clusters e/c=27/42; rv diff=0.005137 CI95=[-0.002660, 0.013892]; return diff=-0.001821 CI95=[-0.020008, 0.015677]
- 72h abs_return diff=0.004150 CI95=[-0.013579, 0.022921] clusters e/c=25/23; rv diff=0.006768 CI95=[-0.002880, 0.016947]; return diff=-0.011794 CI95=[-0.038570, 0.014531]

#### risk_on_leverage_build

Raw events: 465 | raw controls: 650

- 24h abs_return diff=-0.000962 CI95=[-0.006263, 0.003821] clusters e/c=47/74; rv diff=-0.000013 CI95=[-0.003904, 0.003721]; return diff=0.000517 CI95=[-0.006767, 0.008625]
- 48h abs_return diff=-0.000352 CI95=[-0.009947, 0.008729] clusters e/c=36/42; rv diff=0.001464 CI95=[-0.004749, 0.007588]; return diff=-0.001076 CI95=[-0.013634, 0.011067]
- 72h abs_return diff=-0.003908 CI95=[-0.018653, 0.009865] clusters e/c=30/33; rv diff=-0.003185 CI95=[-0.012193, 0.005192]; return diff=0.003466 CI95=[-0.015792, 0.022356]

## Interpretation

- Robustness is still weak: most event-control CIs include zero after non-overlap clustering.
- `passive_notional_shrink` remains the main investigation lead for larger absolute moves, especially ETH 72h, but small clustered sample counts prevent promotion.
- Directional return evidence remains unstable and should not be treated as alpha.
- Conservative conclusion is preserved: research-only risk annotation candidate, not a strategy or Trader handoff.

## Commands run

```bash
python3 reports/leverage_state_classifier_v2/run_leverage_state_classifier_v2.py \
  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \
  --out-json reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json \
  --out-md reports/leverage_state_classifier_v2/leverage_state_classifier_v2.md

python3 reports/leverage_state_classifier_v2/run_leverage_state_classifier_v2_robustness.py \
  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \
  --out-json reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.json \
  --out-md reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.md \
  --bootstrap-reps 1000 \
  --seed 20260616
```

## Actual command output

First-pass rerun stdout:

```json
{
  "by_symbol": {
    "BTCUSDT": {
      "eligible_count": 6505,
      "events": {
        "passive_notional_shrink": 56,
        "risk_on_leverage_build": 468,
        "sticky_or_short_build": 551,
        "true_deleverage": 341
      }
    },
    "ETHUSDT": {
      "eligible_count": 6505,
      "events": {
        "passive_notional_shrink": 80,
        "risk_on_leverage_build": 465,
        "sticky_or_short_build": 470,
        "true_deleverage": 386
      }
    }
  },
  "out_json": "reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json",
  "out_md": "reports/leverage_state_classifier_v2/leverage_state_classifier_v2.md"
}
```

Robustness rerun stdout was the JSON digest emitted by `run_leverage_state_classifier_v2_robustness.py`; the complete persisted output is `reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.json`. Key exact stdout values for abs-return cluster bootstrap are reproduced in the Evidence summary above.

## Next gate

Parameter-stability map across rolling windows and quantile gates; only then consider whether a dashboard-level risk annotation contract is worth drafting. Still no Trader handoff.

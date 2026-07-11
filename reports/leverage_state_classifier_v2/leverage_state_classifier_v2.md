# Leverage-State Classifier v2 — First-Pass Event Study

**Decision:** Research Only / Risk Filter Candidate (first pass).

This study tests whether raw-vs-notional OI state is more useful as a volatility/risk-regime classifier than as standalone directional alpha.

## Inputs and validation

- Fixture: `data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl`
- Fixture versions: `bybit-20260614T095616Z`
- Replay visibility: `conservative_simulated_observed_at`
- Rolling threshold window: 2160 hours (~90d)
- Requires Milestone 0 data-quality gate to pass before interpretation.

## Classifier states

- `true_deleverage`: price down + notional OI low-tail + raw OI low-tail.
- `passive_notional_shrink`: price down + notional OI low-tail + raw OI flat/up.
- `sticky_or_short_build`: price down + raw OI high-tail.
- `risk_on_leverage_build`: price up + raw OI high-tail + notional OI high-tail.

## Results summary

### BTCUSDT

Eligible hours: 6505 / 8761

#### true_deleverage

Events: 341 | matched-control candidates: 778
- 24h: mean abs return event=0.018092781259214787, control=0.020993257248427537; mean return event=-0.001727783409174034, control=-0.002890390453368669
- 48h: mean abs return event=0.02409449909040437, control=0.02668091101092092; mean return event=0.004400623782690838, control=-0.003171567389122931
- 72h: mean abs return event=0.028326688391512464, control=0.03487827859231829; mean return event=-0.0020771178895294144, control=-0.0037665104994607074

#### passive_notional_shrink

Events: 56 | matched-control candidates: 236
- 24h: mean abs return event=0.0372625092129341, control=0.026236728958402594; mean return event=0.02510176359371491, control=-0.008768395935395476
- 48h: mean abs return event=0.05517216103874198, control=0.03447369184131554; mean return event=0.03391381786766979, control=-0.005521446788070398
- 72h: mean abs return event=0.058584212912487645, control=0.04016268673734619; mean return event=0.0352666305236067, control=-0.009573781976574287

#### sticky_or_short_build

Events: 551 | matched-control candidates: 689
- 24h: mean abs return event=0.02112744879909505, control=0.019820247638819156; mean return event=-0.0023839595698039364, control=-0.001988035062429048
- 48h: mean abs return event=0.025271616116802315, control=0.026314259660108856; mean return event=-0.002370559552258672, control=-0.0005882002050856297
- 72h: mean abs return event=0.030236321855800635, control=0.03289311054332182; mean return event=-0.0017661978401617606, control=-0.0021208991097281834

#### risk_on_leverage_build

Events: 468 | matched-control candidates: 676
- 24h: mean abs return event=0.01384786765589186, control=0.01524658389340195; mean return event=-0.0031510310001045447, control=-0.0021039180293727935
- 48h: mean abs return event=0.02417741436813776, control=0.01957924094229237; mean return event=-0.0027516968339362825, control=-0.0037814938038709797
- 72h: mean abs return event=0.02701696887233288, control=0.02823077400368622; mean return event=-0.001582363913863589, control=-0.009045091756330632

### ETHUSDT

Eligible hours: 6505 / 8761

#### true_deleverage

Events: 386 | matched-control candidates: 806
- 24h: mean abs return event=0.03094910965265622, control=0.02848483058514363; mean return event=-0.004234017037878712, control=-0.005160152888851608
- 48h: mean abs return event=0.037592722257792935, control=0.04119725304014401; mean return event=-0.0021198533820435237, control=-0.00325692058085956
- 72h: mean abs return event=0.049153667492108165, control=0.05118625610801059; mean return event=-0.005145516122843814, control=-0.006061111799046386

#### passive_notional_shrink

Events: 80 | matched-control candidates: 296
- 24h: mean abs return event=0.04610644218687834, control=0.03343160672125596; mean return event=0.009497205103219247, control=-0.008587834167195135
- 48h: mean abs return event=0.07076916578399332, control=0.04184680517146452; mean return event=0.008489658552259262, control=0.003253580962314169
- 72h: mean abs return event=0.09344112993062983, control=0.05712522974115558; mean return event=0.008539313590108222, control=-0.003834627916144997

#### sticky_or_short_build

Events: 470 | matched-control candidates: 781
- 24h: mean abs return event=0.02604584703066695, control=0.028194014793631227; mean return event=-0.004045853275301995, control=-0.004241382750788974
- 48h: mean abs return event=0.036636313752240635, control=0.03857639344796246; mean return event=-0.004370952401802755, control=-0.002199254202999924
- 72h: mean abs return event=0.049095513951620456, control=0.04662319599180426; mean return event=-0.0166386481545274, control=-0.00015621873264210588

#### risk_on_leverage_build

Events: 465 | matched-control candidates: 650
- 24h: mean abs return event=0.02033052603879596, control=0.02270550808241479; mean return event=-0.006801709532175656, control=-0.0024386520724444106
- 48h: mean abs return event=0.03233986495082435, control=0.03392330345208218; mean return event=-0.011863693858404962, control=-0.005588740262160182
- 72h: mean abs return event=0.03945852693351447, control=0.04132344520919144; mean return event=-0.013939078777457108, control=-0.014902236025610185

## Interpretation

This is a first-pass classifier study. It should not be promoted to Trader handoff from this evidence alone.
The useful question is whether any state reliably annotates fragility/volatility or bad-entry risk after matched controls, not whether it prints a clean directional trade.

## Validation commands

```bash
python3 reports/leverage_state_classifier_v2/run_leverage_state_classifier_v2.py \
  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \
  --out-json reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json \
  --out-md reports/leverage_state_classifier_v2/leverage_state_classifier_v2.md
```

## Caveats

- Historical `observed_at` is simulated conservatively, not archived live receive time.
- Matched controls are first-pass candidates, not bootstrap confidence intervals.
- Event states can overlap across definitions; this is acceptable for exploratory risk annotation but not final contract semantics.
- No Trader handoff without robustness, stability, and dashboard-level interpretability.

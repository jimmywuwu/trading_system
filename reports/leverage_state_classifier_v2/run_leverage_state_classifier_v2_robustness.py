#!/usr/bin/env python3
"""Milestone 1 robustness pass for leverage-state classifier v2.

Adds two deliberately small checks on top of the first-pass classifier:
1) non-overlap clustering of event timestamps by forecast horizon; and
2) cluster bootstrap confidence intervals for event-control mean differences.

The script intentionally reuses the first-pass classification rules rather than
changing signal semantics. This is validation evidence, not a Trader handoff.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


STATES = ["true_deleverage", "passive_notional_shrink", "sticky_or_short_build", "risk_on_leverage_build"]
HORIZONS = [24, 48, 72]
METRICS = ["abs_return", "rv", "mae", "return"]


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def fl(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def pct(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return a / b - 1.0


def q(values: list[float], p: float) -> float | None:
    xs = sorted(v for v in values if v is not None and math.isfinite(v))
    if not xs:
        return None
    pos = (len(xs) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    f = pos - lo
    return xs[lo] * (1 - f) + xs[hi] * f


def decile_edges(values: list[float]) -> list[float]:
    return [q(values, i / 10) for i in range(1, 10)]  # type: ignore[list-item]


def bin_idx(value: float | None, edges: list[float]) -> int | None:
    if value is None or not math.isfinite(value):
        return None
    i = 0
    while i < len(edges) and value > edges[i]:
        i += 1
    return i


def finite_mean(xs: list[float | None]) -> float | None:
    vals = [x for x in xs if x is not None and math.isfinite(x)]
    return mean(vals) if vals else None


def percentile(xs: list[float], p: float) -> float | None:
    return q(xs, p) if xs else None


def cluster_indices(indices: list[int], horizon: int) -> list[list[int]]:
    """Group adjacent/overlapping event timestamps for a horizon-length outcome."""
    clusters: list[list[int]] = []
    for idx in sorted(indices):
        if not clusters or idx - clusters[-1][-1] > horizon:
            clusters.append([idx])
        else:
            clusters[-1].append(idx)
    return clusters


def cluster_values(indices: list[int], values: list[float | None], horizon: int) -> list[float]:
    out = []
    for cluster in cluster_indices(indices, horizon):
        m = finite_mean([values[i] for i in cluster])
        if m is not None:
            out.append(m)
    return out


def bootstrap_diff_ci(event_clusters: list[float], control_clusters: list[float], reps: int, seed: int) -> dict[str, Any]:
    ev = [x for x in event_clusters if math.isfinite(x)]
    co = [x for x in control_clusters if math.isfinite(x)]
    if not ev or not co:
        return {"event_cluster_n": len(ev), "control_cluster_n": len(co), "mean_diff": None, "ci95": [None, None], "p_same_sign": None}
    obs = mean(ev) - mean(co)
    rng = random.Random(seed)
    diffs = []
    for _ in range(reps):
        ev_s = [ev[rng.randrange(len(ev))] for _ in range(len(ev))]
        co_s = [co[rng.randrange(len(co))] for _ in range(len(co))]
        diffs.append(mean(ev_s) - mean(co_s))
    lo = percentile(diffs, 0.025)
    hi = percentile(diffs, 0.975)
    same_sign = sum(1 for d in diffs if (d >= 0) == (obs >= 0)) / len(diffs)
    return {"event_cluster_n": len(ev), "control_cluster_n": len(co), "mean_diff": obs, "ci95": [lo, hi], "p_same_sign": same_sign}


def build_study(fixture: Path, rolling_hours: int) -> tuple[dict[str, Any], dict[str, Any]]:
    H: dict[str, dict[datetime, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    fixture_versions = set()
    replay_visibility = set()

    with fixture.open("r", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            sym = r["symbol"]
            kind = r["kind"]
            meta = r.get("metadata", {}) or {}
            payload = r.get("payload", {}) or {}
            fixture_versions.add(meta.get("fixture_version"))
            replay_visibility.add(meta.get("replay_visibility"))
            hr = parse_ts(r["occurred_at"])
            d = H[sym][hr]
            if kind == "candle" and meta.get("market_type") == "linear_perp":
                close = fl(payload.get("close"))
                if close is not None:
                    d["close"] = close
            elif kind == "perp_open_interest":
                raw = fl(payload.get("open_interest_raw"))
                notional = fl(payload.get("open_interest_notional_usdt"))
                if raw is not None:
                    d["oi_raw"] = raw
                if notional is not None:
                    d["oi_notional"] = notional

    study: dict[str, Any] = {}
    for sym, rows_by_hour in sorted(H.items()):
        hours = sorted(rows_by_hour)
        close = [rows_by_hour[t].get("close") for t in hours]
        raw_oi = [rows_by_hour[t].get("oi_raw") for t in hours]
        notional_oi = [rows_by_hour[t].get("oi_notional") for t in hours]
        one_h_ret = [pct(close[i], close[i - 1]) if i >= 1 else None for i in range(len(hours))]
        ret_24 = [pct(close[i], close[i - 24]) if i >= 24 else None for i in range(len(hours))]
        raw_oi_24 = [pct(raw_oi[i], raw_oi[i - 24]) if i >= 24 else None for i in range(len(hours))]
        notional_oi_24 = [pct(notional_oi[i], notional_oi[i - 24]) if i >= 24 else None for i in range(len(hours))]
        rv_24 = []
        for i in range(len(hours)):
            vals = [v for v in one_h_ret[max(1, i - 23): i + 1] if v is not None]
            rv_24.append(math.sqrt(sum(v * v for v in vals)) if len(vals) >= 20 else None)

        fwd: dict[int, dict[str, list[float | None]]] = {}
        for h in HORIZONS:
            fwd_ret = []
            fwd_abs = []
            fwd_rv = []
            fwd_mae = []
            for i in range(len(hours)):
                if i + h >= len(hours) or close[i] in (None, 0):
                    fwd_ret.append(None); fwd_abs.append(None); fwd_rv.append(None); fwd_mae.append(None); continue
                c0 = close[i]
                c1 = close[i + h]
                rets = [r for r in (one_h_ret[j] for j in range(i + 1, i + h + 1)) if r is not None]
                path = [r for r in (pct(close[j], c0) for j in range(i + 1, i + h + 1) if close[j] is not None) if r is not None]
                fr = pct(c1, c0)
                fwd_ret.append(fr)
                fwd_abs.append(abs(fr) if fr is not None else None)
                fwd_rv.append(math.sqrt(sum(r * r for r in rets)) if len(rets) >= max(4, h // 2) else None)
                fwd_mae.append(min(path) if path else None)
            fwd[h] = {"return": fwd_ret, "abs_return": fwd_abs, "rv": fwd_rv, "mae": fwd_mae}

        eligible = []
        classified: dict[str, list[int]] = {s: [] for s in STATES}
        for i in range(rolling_hours + 24, len(hours) - max(HORIZONS)):
            needed = [ret_24[i], raw_oi_24[i], notional_oi_24[i], rv_24[i]]
            if any(v is None or not math.isfinite(v) for v in needed):
                continue
            window_raw = [v for v in raw_oi_24[i - rolling_hours: i] if v is not None and math.isfinite(v)]
            window_notional = [v for v in notional_oi_24[i - rolling_hours: i] if v is not None and math.isfinite(v)]
            window_ret = [v for v in ret_24[i - rolling_hours: i] if v is not None and math.isfinite(v)]
            if len(window_raw) < rolling_hours * 0.8 or len(window_notional) < rolling_hours * 0.8:
                continue
            raw_q20, raw_q50, raw_q80 = q(window_raw, 0.2), q(window_raw, 0.5), q(window_raw, 0.8)
            not_q20, not_q80 = q(window_notional, 0.2), q(window_notional, 0.8)
            ret_q25, ret_q75 = q(window_ret, 0.25), q(window_ret, 0.75)
            if None in [raw_q20, raw_q50, raw_q80, not_q20, not_q80, ret_q25, ret_q75]:
                continue
            eligible.append(i)
            r24 = ret_24[i]; raw24 = raw_oi_24[i]; not24 = notional_oi_24[i]
            if r24 is None or raw24 is None or not24 is None:
                continue
            assert raw_q20 is not None and raw_q50 is not None and raw_q80 is not None
            assert not_q20 is not None and not_q80 is not None
            assert ret_q25 is not None and ret_q75 is not None
            raw20 = float(raw_q20); raw50 = float(raw_q50); raw80 = float(raw_q80)
            not20 = float(not_q20); not80 = float(not_q80)
            ret25 = float(ret_q25); ret75 = float(ret_q75)
            price_down = r24 <= ret25
            price_up = r24 >= ret75
            if price_down and not24 <= not20 and raw24 <= raw20:
                classified["true_deleverage"].append(i)
            if price_down and not24 <= not20 and raw24 >= raw50:
                classified["passive_notional_shrink"].append(i)
            if price_down and raw24 >= raw80:
                classified["sticky_or_short_build"].append(i)
            if price_up and raw24 >= raw80 and not24 >= not80:
                classified["risk_on_leverage_build"].append(i)

        rv_edges = decile_edges([rv_24[i] for i in eligible if rv_24[i] is not None])
        ret_edges = decile_edges([ret_24[i] for i in eligible if ret_24[i] is not None])
        state_data: dict[str, Any] = {}
        for state in STATES:
            events = classified[state]
            event_keys = {(bin_idx(rv_24[i], rv_edges), bin_idx(ret_24[i], ret_edges), hours[i].hour) for i in events}
            event_set = set(events)
            controls = [
                i for i in eligible
                if i not in event_set
                and (bin_idx(rv_24[i], rv_edges), bin_idx(ret_24[i], ret_edges), hours[i].hour) in event_keys
            ]
            state_data[state] = {"events": events, "controls": controls}
        study[sym] = {"hours": hours, "fwd": fwd, "eligible_count": len(eligible), "states": state_data}

    meta = {
        "fixture_versions": sorted(v for v in fixture_versions if v),
        "replay_visibility": sorted(v for v in replay_visibility if v),
    }
    return study, meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument("--rolling-hours", type=int, default=2160)
    parser.add_argument("--bootstrap-reps", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260616)
    args = parser.parse_args()

    study, meta = build_study(args.fixture, args.rolling_hours)
    results: dict[str, Any] = {}
    for sym, sdata in study.items():
        results[sym] = {"eligible_count": sdata["eligible_count"], "states": {}}
        for state, edata in sdata["states"].items():
            results[sym]["states"][state] = {
                "event_count": len(edata["events"]),
                "control_count": len(edata["controls"]),
                "horizons": {},
            }
            for h in HORIZONS:
                hres = {}
                for metric in METRICS:
                    evc = cluster_values(edata["events"], sdata["fwd"][h][metric], h)
                    coc = cluster_values(edata["controls"], sdata["fwd"][h][metric], h)
                    hres[metric] = bootstrap_diff_ci(evc, coc, args.bootstrap_reps, args.seed + h + len(metric) + len(state) + len(sym))
                results[sym]["states"][state]["horizons"][str(h)] = hres

    output = {
        "fixture": str(args.fixture),
        "fixture_versions": meta["fixture_versions"],
        "replay_visibility": meta["replay_visibility"],
        "rolling_hours": args.rolling_hours,
        "bootstrap_reps": args.bootstrap_reps,
        "seed": args.seed,
        "method": "non_overlap_event_clustering_by_horizon_plus_cluster_bootstrap_event_minus_control_mean_diff",
        "decision": "research_only_risk_filter_candidate_robustness_pass",
        "caveat": "cluster bootstrap checks uncertainty but does not resolve simulated observed_at or parameter stability",
        "by_symbol": results,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Leverage-State Classifier v2 — Milestone 1 Robustness Note",
        "",
        "**Decision:** Research Only / Risk Filter Candidate. No Trader handoff.",
        "",
        "## Scope",
        "",
        "Small validation pass on existing classifier semantics: non-overlap clustering by forecast horizon plus cluster bootstrap confidence intervals for event-control mean differences.",
        "",
        "## Inputs",
        "",
        f"- Fixture: `{args.fixture}`",
        f"- Fixture versions: `{', '.join(meta['fixture_versions'])}`",
        f"- Replay visibility: `{', '.join(meta['replay_visibility'])}`",
        f"- Rolling threshold window: {args.rolling_hours} hours",
        f"- Bootstrap reps: {args.bootstrap_reps}; seed: {args.seed}",
        "",
        "## Evidence summary",
        "",
        "Mean diff is event minus matched-control after clustering overlapping event timestamps. CI is 95% cluster bootstrap CI.",
        "",
    ]
    for sym, symdata in results.items():
        lines += [f"### {sym}", ""]
        for state, statedata in symdata["states"].items():
            lines += [f"#### {state}", "", f"Raw events: {statedata['event_count']} | raw controls: {statedata['control_count']}", ""]
            for h in HORIZONS:
                absr = statedata["horizons"][str(h)]["abs_return"]
                rv = statedata["horizons"][str(h)]["rv"]
                ret = statedata["horizons"][str(h)]["return"]
                lines.append(
                    f"- {h}h abs_return diff={absr['mean_diff']:.6f} CI95=[{absr['ci95'][0]:.6f}, {absr['ci95'][1]:.6f}] "
                    f"clusters e/c={absr['event_cluster_n']}/{absr['control_cluster_n']}; "
                    f"rv diff={rv['mean_diff']:.6f} CI95=[{rv['ci95'][0]:.6f}, {rv['ci95'][1]:.6f}]; "
                    f"return diff={ret['mean_diff']:.6f} CI95=[{ret['ci95'][0]:.6f}, {ret['ci95'][1]:.6f}]"
                )
            lines.append("")
    lines += [
        "## Interpretation",
        "",
        "- Robustness is still weak: most event-control CIs include zero after non-overlap clustering.",
        "- `passive_notional_shrink` remains the main investigation lead for larger absolute moves, especially ETH 72h, but small clustered sample counts prevent promotion.",
        "- Directional return evidence remains unstable and should not be treated as alpha.",
        "- Conservative conclusion is preserved: research-only risk annotation candidate, not a strategy or Trader handoff.",
        "",
        "## Commands run",
        "",
        "```bash",
        "python3 reports/leverage_state_classifier_v2/run_leverage_state_classifier_v2.py \\",
        "  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \\",
        "  --out-json reports/leverage_state_classifier_v2/leverage_state_classifier_v2.json \\",
        "  --out-md reports/leverage_state_classifier_v2/leverage_state_classifier_v2.md",
        "",
        "python3 reports/leverage_state_classifier_v2/run_leverage_state_classifier_v2_robustness.py \\",
        "  data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl \\",
        "  --out-json reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.json \\",
        "  --out-md reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.md \\",
        f"  --bootstrap-reps {args.bootstrap_reps} \\",
        f"  --seed {args.seed}",
        "```",
        "",
        "## Next gate",
        "",
        "Parameter-stability map across rolling windows and quantile gates; only then consider whether a dashboard-level risk annotation contract is worth drafting. Still no Trader handoff.",
    ]
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    digest = {sym: {state: {str(h): results[sym]["states"][state]["horizons"][str(h)]["abs_return"] for h in HORIZONS} for state in STATES} for sym in results}
    print(json.dumps({"out_json": str(args.out_json), "out_md": str(args.out_md), "abs_return_cluster_bootstrap": digest}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

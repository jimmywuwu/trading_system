"""Pairwise funding-gap statistics from the milestone2 aligned fixture.

Purpose (Gate 0-2 grounding): distinguish the two trade variants —
(a) event-driven convergence capture, (b) persistent carry on a stable
venue-pair gap — by measuring mean/median pairwise gaps and their
sign persistence over the 30d aligned sample.

Usage:
    python3 reports/research/cross-venue-funding-dispersion/run_pairwise_gap_stats.py
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / "cross_venue_dispersion" / "milestone2_btc_funding_dispersion.json"


def main() -> None:
    data = json.loads(SOURCE.read_text())
    rows = None
    for key in ("aligned_rows", "rows", "tail_sample"):
        if isinstance(data.get(key), list) and data[key]:
            rows = data[key]
            break
    if rows is None:
        # fall back: find any list of dicts containing a "rates" mapping
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict) and "rates" in value[0]:
                rows = value
                break
    if rows is None:
        raise SystemExit(f"no aligned rows found; top-level keys: {list(data.keys())}")

    venues = sorted(rows[0]["rates"].keys())
    print(f"aligned rows: {len(rows)}  venues: {venues}")

    for a, b in combinations(venues, 2):
        gaps = [row["rates"][a] - row["rates"][b] for row in rows if a in row["rates"] and b in row["rates"]]
        gaps_bps = [gap * 10_000 for gap in gaps]  # 1 bps = 0.0001
        n = len(gaps_bps)
        mean = sum(gaps_bps) / n
        ordered = sorted(gaps_bps)
        median = ordered[n // 2]
        pos = sum(1 for gap in gaps_bps if gap > 0)
        # sign persistence: fraction of consecutive pairs keeping the same sign
        same_sign = sum(
            1 for x, y in zip(gaps_bps, gaps_bps[1:]) if (x > 0) == (y > 0)
        ) / max(n - 1, 1)
        print(
            f"{a:>12} - {b:<12} n={n:3d} mean={mean:+.3f}bps/8h median={median:+.3f} "
            f"pos_rate={pos/n:.2f} sign_persistence={same_sign:.2f} "
            f"annualized_mean={mean * 3 * 365 / 100:+.2f}%/yr"
        )


if __name__ == "__main__":
    main()

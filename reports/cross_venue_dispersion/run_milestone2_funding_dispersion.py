#!/usr/bin/env python3
"""
Milestone 2 disposable cross-venue BTC funding dispersion first-pass.

Scope constraints:
- Uses only public historical funding rails previously marked replay-safe:
  Bybit BTCUSDT funding history, OKX BTC-USDT-SWAP funding history,
  Hyperliquid BTC fundingHistory.
- Does NOT use current-state OI as historical evidence.
- Event study is funding-only: dispersion persistence/convergence, not a tradable return study.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "reports" / "cross_venue_dispersion"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_from_ms(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def http_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 20) -> Any:
    data = None
    headers = {"User-Agent": "trading_system_milestone2_dispersion/0.1"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


@dataclass(frozen=True)
class FundingPoint:
    venue: str
    instrument: str
    event_ms: int
    funding_rate: float
    raw: dict[str, Any]

    def normalized(self) -> dict[str, Any]:
        return {
            "venue": self.venue,
            "instrument": self.instrument,
            "event_ts_utc": iso_from_ms(self.event_ms),
            "event_ms": self.event_ms,
            "funding_rate": self.funding_rate,
        }


def fetch_bybit(start_ms: int, end_ms: int) -> tuple[list[FundingPoint], dict[str, Any]]:
    # Bybit v5 max limit is sufficient for 30d of 8h funding, but page defensively.
    endpoint = "https://api.bybit.com/v5/market/funding/history"
    cursor_end = end_ms
    points: dict[int, FundingPoint] = {}
    calls = []
    while cursor_end >= start_ms:
        params = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "startTime": str(start_ms),
            "endTime": str(cursor_end),
            "limit": "200",
        }
        url = endpoint + "?" + urllib.parse.urlencode(params)
        data = http_json(url)
        calls.append(url)
        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit retCode={data.get('retCode')} retMsg={data.get('retMsg')}")
        rows = data.get("result", {}).get("list", []) or []
        if not rows:
            break
        min_seen = None
        for r in rows:
            ts = int(r["fundingRateTimestamp"])
            if start_ms <= ts <= end_ms:
                points[ts] = FundingPoint("bybit", "BTCUSDT", ts, float(r["fundingRate"]), r)
            min_seen = ts if min_seen is None else min(min_seen, ts)
        if len(rows) < 200 or min_seen is None or min_seen <= start_ms:
            break
        cursor_end = min_seen - 1
        time.sleep(0.12)
    meta = {"endpoint": endpoint, "calls": calls, "count": len(points), "replay_safe_history": True}
    return sorted(points.values(), key=lambda x: x.event_ms), meta


def fetch_okx(start_ms: int, end_ms: int) -> tuple[list[FundingPoint], dict[str, Any]]:
    endpoint = "https://www.okx.com/api/v5/public/funding-rate-history"
    params = {"instId": "BTC-USDT-SWAP", "limit": "100"}
    url = endpoint + "?" + urllib.parse.urlencode(params)
    data = http_json(url)
    if data.get("code") != "0":
        raise RuntimeError(f"OKX code={data.get('code')} msg={data.get('msg')}")
    points = []
    for r in data.get("data", []) or []:
        ts = int(r["fundingTime"])
        if start_ms <= ts <= end_ms:
            # OKX history exposes realizedRate on newer rows; fundingRate is expected/settled-like depending row.
            rate_s = r.get("realizedRate") or r.get("fundingRate")
            points.append(FundingPoint("okx", "BTC-USDT-SWAP", ts, float(rate_s), r))
    meta = {"endpoint": endpoint, "calls": [url], "count": len(points), "replay_safe_history": True, "note": "public endpoint returned latest page only; no older pagination attempted for first-pass if 30d fits limit=100"}
    return sorted(points, key=lambda x: x.event_ms), meta


def fetch_hyperliquid(start_ms: int, end_ms: int) -> tuple[list[FundingPoint], dict[str, Any]]:
    endpoint = "https://api.hyperliquid.xyz/info"
    cursor_start = start_ms
    points_by_ts: dict[int, FundingPoint] = {}
    calls = []
    # Hyperliquid fundingHistory appears page-limited (~500 rows). Walk forward until end_ms.
    while cursor_start <= end_ms:
        payload = {"type": "fundingHistory", "coin": "BTC", "startTime": cursor_start, "endTime": end_ms}
        data = http_json(endpoint, method="POST", payload=payload)
        calls.append({"url": endpoint, "payload": payload, "rows": len(data) if isinstance(data, list) else None})
        if not isinstance(data, list):
            raise RuntimeError(f"Hyperliquid unexpected payload type: {type(data).__name__}")
        if not data:
            break
        max_seen = None
        for r in data:
            ts = int(r["time"])
            if start_ms <= ts <= end_ms:
                points_by_ts[ts] = FundingPoint("hyperliquid", "BTC", ts, float(r["fundingRate"]), r)
            max_seen = ts if max_seen is None else max(max_seen, ts)
        if max_seen is None or max_seen >= end_ms or len(data) < 500:
            break
        cursor_start = max_seen + 1
        time.sleep(0.12)
    points = sorted(points_by_ts.values(), key=lambda x: x.event_ms)
    meta = {"endpoint": endpoint, "calls": calls, "count": len(points), "replay_safe_history": True}
    return points, meta


def nearest_by_bucket(points: list[FundingPoint], target_ms: int, tolerance_ms: int = 15 * 60 * 1000) -> FundingPoint | None:
    candidates = [p for p in points if abs(p.event_ms - target_ms) <= tolerance_ms]
    if not candidates:
        return None
    return min(candidates, key=lambda p: abs(p.event_ms - target_ms))


def percentile(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    ys = sorted(xs)
    if len(ys) == 1:
        return ys[0]
    pos = (len(ys) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return ys[lo]
    return ys[lo] * (hi - pos) + ys[hi] * (pos - lo)


def safe_mean(xs: list[float]) -> float | None:
    return statistics.mean(xs) if xs else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-common", type=int, default=20)
    ap.add_argument("--out-prefix", default="milestone2_btc_funding_dispersion")
    args = ap.parse_args()

    observed_at = utc_now_iso()
    end_ms = int(time.time() // 3600 * 3600 * 1000)  # last full UTC hour boundary
    start_ms = end_ms - args.days * 24 * 3600 * 1000

    errors: dict[str, str] = {}
    all_points: dict[str, list[FundingPoint]] = {}
    source_meta: dict[str, Any] = {}
    for venue, fn in [("bybit", fetch_bybit), ("okx", fetch_okx), ("hyperliquid", fetch_hyperliquid)]:
        try:
            pts, meta = fn(start_ms, end_ms)
            all_points[venue] = pts
            source_meta[venue] = meta
        except Exception as exc:  # honest blocker capture
            errors[venue] = repr(exc)
            all_points[venue] = []
            source_meta[venue] = {"error": repr(exc), "replay_safe_history": True}

    # Use Bybit 8h settlement timestamps as anchor. Match OKX exact-ish 8h and HL hourly within 15m.
    common = []
    bybit_points = all_points.get("bybit", [])
    for b in bybit_points:
        o = nearest_by_bucket(all_points.get("okx", []), b.event_ms)
        h = nearest_by_bucket(all_points.get("hyperliquid", []), b.event_ms)
        if not (o and h):
            continue
        rates = {"bybit": b.funding_rate, "okx": o.funding_rate, "hyperliquid": h.funding_rate}
        vals = list(rates.values())
        mean = statistics.mean(vals)
        common.append({
            "event_ts_utc": iso_from_ms(b.event_ms),
            "event_ms": b.event_ms,
            "rates": rates,
            "dispersion_range": max(vals) - min(vals),
            "dispersion_std": statistics.pstdev(vals),
            "mean_rate": mean,
            "max_abs_pair_spread": max(abs(vals[i] - vals[j]) for i in range(len(vals)) for j in range(i + 1, len(vals))),
        })
    common.sort(key=lambda r: r["event_ms"])

    dispersions = [r["dispersion_range"] for r in common]
    p90 = percentile(dispersions, 0.90)
    p75 = percentile(dispersions, 0.75)
    median = percentile(dispersions, 0.50)

    events = []
    # Conservative non-overlapping-ish event selection: top decile, at least one 8h step apart implicitly by timestamps.
    threshold = p90
    if threshold is not None:
        for idx, row in enumerate(common[:-3]):
            if row["dispersion_range"] >= threshold:
                nxt1 = common[idx + 1]
                nxt3 = common[idx + 3] if idx + 3 < len(common) else None
                events.append({
                    "event_ts_utc": row["event_ts_utc"],
                    "dispersion_t0": row["dispersion_range"],
                    "rates_t0": row["rates"],
                    "dispersion_t_plus_8h": nxt1["dispersion_range"],
                    "delta_dispersion_8h": nxt1["dispersion_range"] - row["dispersion_range"],
                    "dispersion_t_plus_24h": nxt3["dispersion_range"] if nxt3 else None,
                    "delta_dispersion_24h": (nxt3["dispersion_range"] - row["dispersion_range"]) if nxt3 else None,
                })

    deltas8 = [e["delta_dispersion_8h"] for e in events if e.get("delta_dispersion_8h") is not None]
    deltas24 = [e["delta_dispersion_24h"] for e in events if e.get("delta_dispersion_24h") is not None]

    sufficient = len(common) >= args.min_common and not errors
    decision = "first_pass_completed_research_only" if sufficient else "blocked_or_insufficient_history"
    conclusion = (
        "Funding-history-only cross-venue dispersion fixture is sufficient for a conservative first-pass descriptive/event study. "
        "This is not a tradable signal and does not support Trader handoff."
        if sufficient else
        "Could not complete a valid first-pass event study with the requested replay-safe rails; treat as DataProvider blocker."
    )

    result = {
        "observed_at_utc": observed_at,
        "command_intended": f"python3 reports/cross_venue_dispersion/run_milestone2_funding_dispersion.py --days {args.days}",
        "scope": {
            "asset": "BTC",
            "venues": ["bybit", "okx", "hyperliquid"],
            "rails": "historical funding only",
            "excluded": ["current-state OI as historical evidence", "regulated Coinbase/CME OI/funding historical claims", "Trader handoff"],
            "start_utc": iso_from_ms(start_ms),
            "end_utc": iso_from_ms(end_ms),
        },
        "source_meta": source_meta,
        "errors": errors,
        "counts": {venue: len(pts) for venue, pts in all_points.items()} | {"common_three_venue_timestamps": len(common), "events_top_decile": len(events)},
        "summary_stats": {
            "dispersion_range_median": median,
            "dispersion_range_p75": p75,
            "dispersion_range_p90_event_threshold": p90,
            "dispersion_range_max": max(dispersions) if dispersions else None,
            "event_delta_dispersion_8h_mean": safe_mean(deltas8),
            "event_delta_dispersion_24h_mean": safe_mean(deltas24),
            "events_with_8h_outcome": len(deltas8),
            "events_with_24h_outcome": len(deltas24),
        },
        "sample_common_rows_tail": common[-5:],
        "events": events,
        "decision": decision,
        "conclusion": conclusion,
        "data_provider_todo": [
            "Persist raw funding-history payloads and normalized rows with source endpoint, event_ts_utc, observed_at_utc, raw payload hash.",
            "Add deterministic pagination tests for Bybit funding history and OKX funding-rate-history beyond a single latest page before extending horizon >30d.",
            "Keep current-state OI excluded from historical evidence until a forward archive exists; archived snapshots are replay-safe only from observed_at_utc onward.",
            "If price-return event study is desired, explicitly approve/add replay-safe candle rails per venue rather than silently mixing unreviewed endpoints.",
        ],
        "next_gate": "QUANT may review funding-only persistence/convergence after DataProvider turns this disposable pull into a reproducible fixture; no strategy/sizing gate yet.",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / f"{args.out_prefix}.json"
    md_path = OUT_DIR / f"{args.out_prefix}.md"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    def fmt(x: Any) -> str:
        if x is None:
            return "n/a"
        if isinstance(x, float):
            return f"{x:.10f}"
        return str(x)

    md = []
    md.append("# Milestone 2 BTC funding dispersion first-pass\n")
    md.append(f"Created: `{observed_at}`\n")
    md.append("## Exact command\n")
    md.append(f"```bash\npython3 reports/cross_venue_dispersion/run_milestone2_funding_dispersion.py --days {args.days}\n```\n")
    md.append("## Scope\n")
    md.append("- Asset: BTC\n- Venues: Bybit, OKX, Hyperliquid\n- Rail: replay-safe historical funding only\n- Explicit exclusions: current-state OI as historical evidence; Trader handoff; regulated historical OI/funding claims.\n")
    md.append("## Counts\n")
    md.append(f"- Bybit funding rows: `{len(all_points.get('bybit', []))}`\n")
    md.append(f"- OKX funding rows: `{len(all_points.get('okx', []))}`\n")
    md.append(f"- Hyperliquid funding rows: `{len(all_points.get('hyperliquid', []))}`\n")
    md.append(f"- Common three-venue timestamps: `{len(common)}`\n")
    md.append(f"- Top-decile dispersion events: `{len(events)}`\n")
    if errors:
        md.append("## API errors / blockers\n")
        for venue, err in errors.items():
            md.append(f"- `{venue}`: `{err}`\n")
    md.append("## Dispersion stats\n")
    md.append(f"- median range: `{fmt(median)}`\n")
    md.append(f"- p75 range: `{fmt(p75)}`\n")
    md.append(f"- p90 event threshold: `{fmt(p90)}`\n")
    md.append(f"- max range: `{fmt(max(dispersions) if dispersions else None)}`\n")
    md.append(f"- mean 8h post-event dispersion change: `{fmt(safe_mean(deltas8))}`\n")
    md.append(f"- mean 24h post-event dispersion change: `{fmt(safe_mean(deltas24))}`\n")
    md.append("## Conservative decision\n")
    md.append(f"`{decision}` — {conclusion}\n")
    md.append("## DataProvider TODO\n")
    for item in result["data_provider_todo"]:
        md.append(f"- {item}\n")
    md.append("## Next gate\n")
    md.append(result["next_gate"] + "\n")
    md.append("## Tail sample of aligned rows\n")
    md.append("```json\n" + json.dumps(common[-5:], indent=2, sort_keys=True) + "\n```\n")
    md_path.write_text("".join(md), encoding="utf-8")

    print(json.dumps({
        "json_path": str(json_path.relative_to(ROOT)),
        "markdown_path": str(md_path.relative_to(ROOT)),
        "decision": decision,
        "counts": result["counts"],
        "summary_stats": result["summary_stats"],
        "errors": errors,
    }, indent=2, sort_keys=True))
    return 0 if sufficient else 2


if __name__ == "__main__":
    raise SystemExit(main())

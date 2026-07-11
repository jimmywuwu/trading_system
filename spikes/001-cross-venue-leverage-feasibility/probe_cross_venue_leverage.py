#!/usr/bin/env python3
"""Disposable spike: probe observable leverage rails for regulated/offshore crypto perps.

This is intentionally not a production DataProvider. It asks one feasibility question:
Can we collect a small, timestamped, schema-like sample across Coinbase-observable
regulated perp-style products and offshore perp venues without pretending current
state is historical replay data?
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


@dataclass
class ProbeResult:
    venue: str
    rail: str
    status: str
    observed_at: str
    endpoint: str
    subject: str | None = None
    fields_seen: list[str] | None = None
    sample: dict[str, Any] | list[Any] | None = None
    count: int | None = None
    replay_safe_history: bool | None = None
    notes: list[str] | None = None
    error: str | None = None


def request_json(url: str, headers: dict[str, str] | None = None, timeout: int = 25) -> Any:
    h = {"User-Agent": "trading-system-spike/001"}
    if headers:
        h.update(headers)
    req = Request(url, headers=h)
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def safe_probe(fn):
    try:
        return fn()
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        return [ProbeResult(fn.__name__.replace("probe_", ""), "unknown", "error", iso(now_utc()), "", error=f"HTTP {e.code}: {body}")]
    except URLError as e:
        return [ProbeResult(fn.__name__.replace("probe_", ""), "unknown", "error", iso(now_utc()), "", error=f"URL error: {e}")]
    except Exception as e:  # spike should report failures, not hide them
        return [ProbeResult(fn.__name__.replace("probe_", ""), "unknown", "error", iso(now_utc()), "", error=repr(e))]


def probe_coinbase() -> list[ProbeResult]:
    observed = iso(now_utc())
    base = "https://api.coinbase.com/api/v3/brokerage/market/products"
    url = base + "?" + urlencode({"product_type": "FUTURE", "limit": "100"})
    payload = request_json(url)
    products = payload.get("products", [])
    interesting = [p for p in products if p.get("product_id") in {"BIP-20DEC30-CDE", "ETP-20DEC30-CDE", "BIT-26JUN26-CDE", "ET-26JUN26-CDE"}]
    if not interesting:
        interesting = products[:4]
    results: list[ProbeResult] = [
        ProbeResult(
            venue="coinbase_derivatives",
            rail="regulated_current_product_state",
            status="ok" if interesting else "partial",
            observed_at=observed,
            endpoint=url,
            fields_seen=sorted(interesting[0].keys()) if interesting else sorted(payload.keys()),
            sample=[{k: p.get(k) for k in ["product_id", "display_name", "product_type", "contract_expiry_type", "open_interest", "funding_rate", "funding_time", "future_product_details"] if k in p} for p in interesting],
            count=len(interesting),
            replay_safe_history=False,
            notes=[
                "Product endpoint exposes current state including OI/funding-like fields for perp products.",
                "This is not a replay-safe historical OI/funding endpoint; requires forward polling archive.",
            ],
        )
    ]
    # Try candles for one product as replay-safe price/volume history.
    if interesting:
        product_id = interesting[0].get("product_id")
        end = now_utc().replace(minute=0, second=0, microsecond=0)
        start = end - timedelta(hours=6)
        candle_url = f"{base}/{product_id}/candles?" + urlencode({"start": str(int(start.timestamp())), "end": str(int(end.timestamp())), "granularity": "ONE_HOUR"})
        candles = request_json(candle_url).get("candles", [])
        results.append(
            ProbeResult(
                venue="coinbase_derivatives",
                rail="regulated_candle_history",
                status="ok" if candles else "partial",
                observed_at=observed,
                endpoint=candle_url,
                subject=product_id,
                fields_seen=sorted(candles[0].keys()) if candles else [],
                sample=candles[:3],
                count=len(candles),
                replay_safe_history=True,
                notes=["Candle history is available, but price/volume alone is insufficient for leverage-pressure backtest."],
            )
        )
    return results


def probe_bybit() -> list[ProbeResult]:
    observed = iso(now_utc())
    end_ms = int(now_utc().timestamp() * 1000)
    start_ms = int((now_utc() - timedelta(hours=6)).timestamp() * 1000)
    results = []
    endpoints = [
        ("offshore_oi_history", "https://api.bybit.com/v5/market/open-interest?" + urlencode({"category":"linear","symbol":"BTCUSDT","intervalTime":"1h","startTime":str(start_ms),"endTime":str(end_ms)}), True),
        ("offshore_funding_history", "https://api.bybit.com/v5/market/funding/history?" + urlencode({"category":"linear","symbol":"BTCUSDT","startTime":str(start_ms),"endTime":str(end_ms)}), True),
    ]
    for rail, url, replay in endpoints:
        payload = request_json(url)
        rows = payload.get("result", {}).get("list", [])
        results.append(ProbeResult(
            venue="bybit", rail=rail, status="ok" if rows else "partial", observed_at=observed, endpoint=url, subject="BTCUSDT",
            fields_seen=sorted(rows[0].keys()) if rows else sorted(payload.keys()), sample=rows[:3], count=len(rows), replay_safe_history=replay,
            notes=["Historical endpoint exists; production provider must keep pagination-safe cursor/window handling."]
        ))
    return results


def probe_hyperliquid() -> list[ProbeResult]:
    observed = iso(now_utc())
    url = "https://api.hyperliquid.xyz/info"
    meta = request_json(url, headers={"Content-Type": "application/json"}) if False else None
    # urllib Request with body for POST
    def post(payload: dict[str, Any]) -> Any:
        data = json.dumps(payload).encode()
        req = Request(url, data=data, headers={"Content-Type":"application/json", "User-Agent":"trading-system-spike/001"}, method="POST")
        with urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode())
    mids = post({"type":"allMids"})
    meta_ctx = post({"type":"metaAndAssetCtxs"})
    funding = post({"type":"fundingHistory", "coin":"BTC", "startTime": int((now_utc()-timedelta(hours=24)).timestamp()*1000)})
    btc_idx = [i for i, asset in enumerate(meta_ctx[0].get("universe", [])) if asset.get("name") == "BTC"]
    btc_ctx = meta_ctx[1][btc_idx[0]] if btc_idx else {}
    return [
        ProbeResult("hyperliquid", "offshore_current_state", "ok", observed, url, "BTC", sorted(btc_ctx.keys()), btc_ctx, 1, False, ["Current OI/mark/oracle/funding available; archive needed for current-state replay."]),
        ProbeResult("hyperliquid", "offshore_funding_history", "ok" if funding else "partial", observed, url, "BTC", sorted(funding[0].keys()) if funding else [], funding[:3], len(funding), True, ["Funding history endpoint is directly replayable for settled funding observations."]),
    ]


def probe_okx() -> list[ProbeResult]:
    observed = iso(now_utc())
    base = "https://www.okx.com"
    results = []
    for rail, path, params, replay in [
        ("offshore_current_funding", "/api/v5/public/funding-rate", {"instId":"BTC-USDT-SWAP"}, False),
        ("offshore_current_oi", "/api/v5/public/open-interest", {"instType":"SWAP","instId":"BTC-USDT-SWAP"}, False),
        ("offshore_funding_history", "/api/v5/public/funding-rate-history", {"instId":"BTC-USDT-SWAP","limit":"10"}, True),
    ]:
        url = base + path + "?" + urlencode(params)
        payload = request_json(url)
        rows = payload.get("data", [])
        results.append(ProbeResult("okx", rail, "ok" if rows else "partial", observed, url, "BTC-USDT-SWAP", sorted(rows[0].keys()) if rows else sorted(payload.keys()), rows[:3], len(rows), replay, ["OKX current OI/funding is useful; OI history still needs separate endpoint/vendor review." if "oi" in rail else "Funding history exists."]))
    return results


def probe_cme() -> list[ProbeResult]:
    observed = iso(now_utc())
    urls = [
        "https://www.cmegroup.com/CmeWS/mvc/Quotes/Future/8478/G",
        "https://www.cmegroup.com/CmeWS/mvc/ProductCalendar/Future/8478",
    ]
    results = []
    for url in urls:
        try:
            payload = request_json(url)
            results.append(ProbeResult("cme", "regulated_cme_public_web", "ok", observed, url, fields_seen=sorted(payload.keys()) if isinstance(payload, dict) else [], sample=payload if isinstance(payload, dict) else None, replay_safe_history=False, notes=["Public endpoint responded in this runtime; still not vendor-grade historical OI/funding."]))
        except HTTPError as e:
            results.append(ProbeResult("cme", "regulated_cme_public_web", "blocked", observed, url, replay_safe_history=False, error=f"HTTP {e.code}", notes=["CME public web endpoint is not reliable from this runtime; treat as deferred/vendor/manual source."]))
    return results


def write_markdown(results: list[ProbeResult]) -> str:
    ok = [r for r in results if r.status == "ok"]
    partial = [r for r in results if r.status == "partial"]
    blocked = [r for r in results if r.status in {"blocked", "error"}]
    lines = [
        "# Spike 001: cross-venue leverage feasibility",
        "",
        f"Run observed_at: {iso(now_utc())}",
        "",
        "## Question",
        "Can we build a narrow Coinbase-observable regulated perp-style rail and compare it with offshore perp rails without violating point-in-time semantics?",
        "",
        "## Verdict: PARTIAL",
        "",
        "The monitoring/event-study version is feasible. The backtest/signal version is not yet safe because Coinbase regulated OI/funding appears current-state only unless we build a forward archive, and CME is not a reliable automated source from this runtime.",
        "",
        "## Summary",
        f"- OK rails: {len(ok)}",
        f"- Partial rails: {len(partial)}",
        f"- Blocked/error rails: {len(blocked)}",
        "",
        "## Results",
    ]
    for r in results:
        lines += [
            f"### {r.venue} — {r.rail}",
            f"- status: `{r.status}`",
            f"- subject: `{r.subject}`",
            f"- replay_safe_history: `{r.replay_safe_history}`",
            f"- count: `{r.count}`",
            f"- endpoint: `{r.endpoint}`",
        ]
        if r.fields_seen:
            lines.append(f"- fields_seen: `{', '.join(r.fields_seen[:25])}`")
        if r.notes:
            lines.append("- notes:")
            lines.extend([f"  - {n}" for n in r.notes])
        if r.error:
            lines.append(f"- error: `{r.error}`")
        lines.append("")
    lines += [
        "## Recommendation for real build",
        "- Build a forward polling archive before any regulated OI/funding backtest claims.",
        "- Label Coinbase as `coinbase_observable_regulated`, not as full US-regulated market coverage.",
        "- Treat CME as `deferred_vendor_or_manual_source` until there is a reliable replay-safe source.",
        "- Offshore first-pass rails can include Bybit, Hyperliquid, and OKX, but normalize timestamp semantics separately for current-state vs historical endpoints.",
        "",
        "## Jaquan discussion points",
        "1. Is a Coinbase-only regulated rail useful enough for his regime classifier, or does the research require CME before starting?",
        "2. What minimum archive horizon makes the event study useful: 30, 60, or 90 days?",
        "3. Should the first output be a monitoring dashboard/regime annotation rather than a signal contract?",
        "4. Does he want offshore comparison to prioritize Bybit+Hyperliquid only, or include OKX despite OI-history ambiguity?",
        "5. What exact decision boundary would promote this from research-only to backtest-safe?",
    ]
    md = "\n".join(lines) + "\n"
    (OUT_DIR / "verdict.md").write_text(md)
    return md


def main() -> int:
    probes = [probe_coinbase, probe_bybit, probe_hyperliquid, probe_okx, probe_cme]
    results: list[ProbeResult] = []
    for fn in probes:
        got = safe_probe(fn)
        results.extend(got)
        time.sleep(0.2)
    (OUT_DIR / "raw_results.json").write_text(json.dumps([asdict(r) for r in results], indent=2, sort_keys=True))
    md = write_markdown(results)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())

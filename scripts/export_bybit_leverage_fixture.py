from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from providers.bybit_leverage_provider import BybitLeveragePressureProvider, BybitRawArchive


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a conservative Bybit leverage-pressure Observation JSONL fixture.")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--end", type=parse_timestamp, default=None, help="UTC end timestamp, e.g. 2026-05-28T00:00:00Z")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"])
    parser.add_argument("--output", type=Path, default=Path("data/bybit_leverage_pressure_fixture.jsonl"))
    parser.add_argument("--request-delay", type=float, default=0.05)
    parser.add_argument("--rate-limit-retry-delay", type=float, default=2.0, help="Base seconds to sleep before retrying Bybit retCode 10006")
    parser.add_argument("--rate-limit-max-retries", type=int, default=5, help="Retries per request window/page for Bybit retCode 10006")
    parser.add_argument("--raw-archive-dir", type=Path, default=None, help="Record raw endpoint payloads to this directory while exporting")
    parser.add_argument("--replay-raw-archive-dir", type=Path, default=None, help="Regenerate fixture from a stored raw archive without live endpoint calls")
    args = parser.parse_args()
    if args.raw_archive_dir and args.replay_raw_archive_dir:
        parser.error("--raw-archive-dir and --replay-raw-archive-dir are mutually exclusive")

    end = args.end or datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    archive = None
    http_get = None
    if args.raw_archive_dir:
        archive = BybitRawArchive(args.raw_archive_dir)
        http_get = archive.recording_http_get(BybitLeveragePressureProvider._default_http_get)
    elif args.replay_raw_archive_dir:
        archive = BybitRawArchive(args.replay_raw_archive_dir)
        http_get = archive.replay_http_get()

    provider = BybitLeveragePressureProvider(
        request_delay_seconds=args.request_delay,
        http_get=http_get,
        rate_limit_retry_delay_seconds=args.rate_limit_retry_delay,
        rate_limit_max_retries=args.rate_limit_max_retries,
    )
    observations = provider.get_observations(start=start, end=end, subjects=args.symbols)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        for row in provider.to_jsonl_rows(observations):
            file.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    print(
        f"wrote {len(observations)} observations to {args.output} "
        f"for {','.join(args.symbols)} from {start.isoformat()} to {end.isoformat()}"
    )
    if archive is not None:
        print(f"raw archive: {archive.path}")


if __name__ == "__main__":
    main()

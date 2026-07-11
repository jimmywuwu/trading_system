# Bybit OI pagination gap blocks leverage-pressure research

## Request summary

Please fix the Bybit open-interest ingestion for `/v5/market/open-interest`. Current fixtures appear to miss most 5m OI rows because the provider does not follow `nextPageCursor`.

This blocks Quant reruns for:

- Leverage Pressure v2/v3
- OI Contraction / Deleveraging Volatility Regime

## Evidence from Quant diagnostics

Observed fixture coverage:

```yaml
30d_fixture:
  oi_hour_coverage: ~37.4%
  max_gap: ~31h
90d_fixture:
  oi_hour_coverage: ~35.4%
  max_gap: ~32h
180d_fixture:
  oi_hour_coverage: ~35.4%
  max_gap: ~32h
365d_fixture:
  oi_hour_coverage: ~37.6%
  max_gap: ~31h
```

Live sanity check:

```yaml
endpoint: /v5/market/open-interest
request_window: 2025-06-02T06:30Z -> 2025-06-04T06:30Z
params:
  category: linear
  symbol: BTCUSDT
  intervalTime: 5min
  limit: 1000
returned_rows: 200
returned_range: 2025-06-03T13:55Z -> 2025-06-04T06:30Z
nextPageCursor: present
```

Following `nextPageCursor` returns the missing rows:

```yaml
page_0: 200 rows, 2025-06-03T13:55Z -> 2025-06-04T06:30Z
page_1: 200 rows, 2025-06-02T21:15Z -> 2025-06-03T13:50Z
page_2: 177 rows, 2025-06-02T06:30Z -> 2025-06-02T21:10Z
```

Likely root cause:

```yaml
provider_file: providers/bybit_leverage_provider.py
method: _iter_windowed_payloads / fetch_open_interest
issue: _iter_windowed_payloads yields only first page and ignores result.nextPageCursor
api_behavior: open-interest endpoint caps at 200 rows for 5m OI even when limit=1000
request_window: 2 days
captured_per_window: ~16h40m
missed_per_window: ~31h20m
```

## Required fix

- Follow `result.nextPageCursor` for `/v5/market/open-interest` until empty.
- Preserve deterministic ordering and dedupe by `(symbol, kind, occurred_at, endpoint)`.
- Keep point-in-time semantics unchanged: historical `observed_at` can remain conservative simulated `timestamp + 60s` unless Jayda prefers a better policy.
- Add a regression test that simulates multiple open-interest pages and verifies all pages are emitted.
- Add or run coverage validation for 30d/90d/180d/365d regenerated fixtures.

## Acceptance criteria

```yaml
acceptance:
  provider:
    - Bybit open-interest pagination follows nextPageCursor.
    - Multi-page test covers at least 3 pages and no duplicate observations.
    - Existing JSONL round-trip test still passes.
  regenerated_fixtures:
    - 5m OI row count is close to expected for requested date range, accounting for endpoint availability and boundary filtering.
    - Hourly OI bucket coverage is near candle-hour coverage, not ~35-38%.
    - No repeated ~31h OI gaps caused by pagination loss.
  quant_unblock:
    - Regenerate 30d / 90d / 180d / 365d Bybit leverage fixtures, or provide command/output for Quant to regenerate them.
    - Quant reruns leverage-pressure v2/v3 and OI-contraction event studies after fixed fixtures are available.
```

## Impact / gate

Until this is fixed:

```yaml
leverage_pressure_v2_v3_results: invalid_for_conclusion
OI_contraction_event_study: invalid_for_conclusion
signal_contract: blocked
trader_handoff: blocked
```

This is a DataProvider-owned issue: endpoint pagination, fixture completeness, and replay-safe OI observations. Quant should not reinterpret OI results until the fixture is repaired.

## Data issue diagnosis — OI coverage gaps

The OI coverage issue is now diagnosed. It is not a real market/data-availability pattern; it is an ingestion pagination problem.

Bybit `/v5/market/open-interest` returns only **200 rows per request** for 5m open interest, even if the request sends `limit=1000`. For a 5m interval:

```text
200 rows * 5 minutes = 1000 minutes = 16h40m
```

The current provider uses 2-day request windows:

```text
window = 48h
```

But because it does not follow `nextPageCursor`, each 48h window only captures about the latest 16h40m of that window and silently misses the earlier ~31h20m. That exactly matches the observed fixture pattern:

```yaml
observed_pattern:
  oi_distinct_hours_per_symbol: 3294
  expected_full_year_5m_hourly_buckets: about 8761
  coverage_ratio: 37.6%
  repeated_gap: about 31h
root_cause:
  endpoint: /v5/market/open-interest
  cap_observed: 200 rows per request
  provider_bug: _iter_windowed_payloads does not paginate nextPageCursor
  effect: partial OI fixture with repeated missing windows
```

A live sanity request confirmed this:

```yaml
request_window: 2025-06-02T06:30Z to 2025-06-04T06:30Z
requested_limit: 1000
returned_rows: 200
returned_range: 2025-06-03T13:55Z to 2025-06-04T06:30Z
nextPageCursor: present
```

Following the cursor returns the missing earlier rows:

```yaml
page_0: 200 rows, 2025-06-03T13:55Z to 2025-06-04T06:30Z
page_1: 200 rows, 2025-06-02T21:15Z to 2025-06-03T13:50Z
page_2: 177 rows, 2025-06-02T06:30Z to 2025-06-02T21:10Z
```

### Implication for the research result

The first-pass OI contraction result should be treated as **data-invalid / exploratory only** until the fixture is regenerated with cursor pagination. The prior conclusion `research_only_needs_revision` is too generous if read as evidence quality; the correct gate is:

```yaml
status: data_issue_found
research_result: invalid_for_conclusion
next_owner: DATA_PROVIDER_DEVELOPER
required_fix: paginate Bybit open-interest nextPageCursor or reduce request windows below endpoint cap
```

After the fixture is fixed, rerun the event study. Do not use the current OI coverage result for SignalContract, Trader handoff, or larger research decisions.

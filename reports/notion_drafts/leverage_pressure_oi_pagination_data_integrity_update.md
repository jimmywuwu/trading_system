## Data integrity update — Bybit OI pagination issue

The previous leverage-pressure studies also used the same Bybit leverage fixture family and therefore are affected by the same OI ingestion issue.

Root cause:

```yaml
endpoint: /v5/market/open-interest
observed_api_cap: 200 rows per request for 5m OI
provider_issue: nextPageCursor was not followed
request_window: 2 days
captured_per_window: about 16h40m
missed_per_window: about 31h20m
```

Fixture coverage check:

```yaml
30d_fixture:
  oi_hour_coverage: about 37.4%
  max_gap: about 31h
90d_fixture:
  oi_hour_coverage: about 35.4%
  max_gap: about 32h
180d_fixture:
  oi_hour_coverage: about 35.4%
  max_gap: about 32h
365d_fixture:
  oi_hour_coverage: about 37.6%
  max_gap: about 31h
```

Impact:

- Any result depending on OI expansion / OI percentile / funding+OI / v2 / v3 score should be treated as **data-invalid for conclusion** until the fixture is regenerated with cursor pagination.
- The earlier conservative rejection was directionally safe in the sense that it did not promote a signal, but the evidence itself is contaminated and should not be used to claim the hypothesis failed robustly.
- Scripts also forward-filled the last available OI across missing windows, which inflated valid hourly event counts and made the OI coverage look healthier than it was.

Correct gate:

```yaml
status: data_issue_found
previous_leverage_pressure_results: invalid_for_conclusion
next_owner: DATA_PROVIDER_DEVELOPER
required_fix: paginate Bybit open-interest nextPageCursor and regenerate 30d/90d/180d/365d fixtures
quant_next_step_after_fix: rerun v2/v3 and OI-contraction event studies
```

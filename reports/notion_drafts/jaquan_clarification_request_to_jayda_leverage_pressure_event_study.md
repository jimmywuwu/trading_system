# Superseded note — PR check correction

Created: 2026-05-30  
Created by: QUANT  
Created by agent: JAQUAN  
Status: Superseded / do not send as-is

## Correction

After checking GitHub PRs directly, my earlier framing was too harsh and partially wrong.

Jayda/DataProvider work **did support a first-pass BTC/ETH event-study fixture direction**:

- PR #7: `feat(data): add bybit leverage fixture provider` was merged.
- PR #7 explicitly scoped a replay-safe Bybit leverage fixture provider for BTC/ETH event-study research.
- It covered settled funding, OI snapshots, perp/spot candles, timestamp semantics, JSONL replay, and tests.
- Quant review caught an OI truncation issue; the provider revision added OI windowing, fail-loud coverage behavior, metadata, and tests.

PR #9 then added Quant-side first-pass research evidence using a 30d Bybit BTCUSDT replay fixture. The v1 signal emitted zero events, so no forward-return distribution could be estimated.

## Current accurate status

The blocker is not that Jayda failed to support the event-study fixture. She did support the first-pass fixture with constraints.

The accurate Quant status is:

- DataProvider fixture support exists for first-pass replay.
- v1 Quant signal thresholds were too restrictive / mismatched to the sampled data.
- The broader leverage-pressure mechanism remains Research Only / Needs Revision.
- A true event-study distribution still needs either revised event definition or broader fixture/source scope because v1 produced zero events.

## Lesson

When local repo state is stale or dirty, do not infer PR support from local files alone. Check GitHub PR bodies, merged branches, comments, and downstream evidence PRs before assigning missing work to another role.

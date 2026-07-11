# SmokeReplayValidation: oi_contraction_vol_regime

```yaml
SmokeReplayValidation:
  id: smoke_20260708_oi_contraction_vol_regime
  signal_contract_id: sc_20260708_oi_contraction_vol_regime
  signal_name: oi_contraction_vol_regime
  fixture: data/bybit_leverage_pressure_fixture_30d.jsonl（BTCUSDT perp_open_interest, 3000 筆）
  replay_window: 2026-05-01T14:56Z -> 2026-05-30T07:31Z
  params:
    change_window: 4h
    history_window: 14d
    min_history: 300
    trigger_percentile: 0.10
    rearm_percentile: 0.20
  tests_run:
    - unit suite: 42/42 passed（python3 -m pytest -q）
    - replay via backtest.ReplayDataProvider（lookahead guard 啟用）
  passed: true
  failures: []
  timestamp_check: pass（每個 event.timestamp <= replay current_time，inline assert）
  lookahead_check: pass（無 LookaheadError；點對點重播）
  determinism_check: pass（完整重跑兩次，event 序列完全相同）
  event_count: 16
  event_frequency: 0.56 / day
  frequency_sanity: >
    與假說預期一致：v1 草稿 bottom decile 未去重為 257 events/365d
    ≈ 0.70/day；本實作含遲滯去重後 0.56/day，同一數量級且略低，
    符合「episode 級事件」的預期。
  semantics_check: >
    全部 16 個事件 oi_change_4h < 0（絕對收縮條件生效）；
    strength 分布在 0.17-0.75（有分辨力，非全部貼 1）；
    一個事件 confidence=0.50，對應參考樣本 gap 較大——降權機制生效。
  notes: >
    重跑指令：python3 <scratchpad>/smoke_oi_signal.py
    （腳本邏輯：JsonLinesObservationProvider 載入 -> 過濾
    perp_open_interest/BTCUSDT -> ReplayDataProvider.replay 逐 tick 餵
    signal.generate -> 斷言 timestamp 與決定性）
```

Gate 7 通過。下一步：`/run-backtest`——先在 `research/` 加
abs-return / realized-vol 版本的 forward study 原語（含 vol-matched /
return-matched 對照），再做 event study。假說的最小有效效應
（realized vol lift >= +15%）在該階段檢驗。

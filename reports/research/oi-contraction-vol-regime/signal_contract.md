# SignalContract: oi_contraction_vol_regime

- created_at: 2026-07-08（/research-cycle #3）
- hypothesis_id: hyp_20260708_oi_contraction_vol（`hypothesis.md`）

```yaml
SignalContract:
  id: sc_20260708_oi_contraction_vol_regime
  signal_name: oi_contraction_vol_regime
  hypothesis_id: hyp_20260708_oi_contraction_vol
  mechanism_summary: 4h OI（合約數）快速收縮 = 去槓桿進行中，預期後續 4-24h 波動擴張
  required_kinds: [perp_open_interest]
  required_subjects: [BTCUSDT]   # ETH 同 contract 另實例化
  required_payload_fields:
    - open_interest_raw          # 主要度量：合約數量，與價格解耦
  measurement_note: >
    用 raw 合約數而非 notional_usdt：notional 與價格混淆（價跌則 notional
    跌，即使部位未變），合約數才是「部位數量變化」的乾淨度量。
    此選擇留一個 open question 給 event study 對照驗證
    （參考 reports/notional_vs_contract_oi/ 的既有研究）。
  lookback_window:
    change_window: 4h            # oi_change = OI(t) / OI(t-4h) - 1
    history_window: 14d          # rolling 分布（30d fixture 用 14d；365d 資料建議 90d）
  stale_tolerance:
    newest_sample: 30m           # 最新 OI 樣本超過 30m 舊 -> 不發訊號
    reference_sample: 45m        # t-4h 參考點附近 ±45m 內無樣本 -> 回傳 None
  warmup_required: min_history 個 oi_change 樣本（預設 300）
  direction_rule: >
    恆為 FLAT。本 signal 是 risk-regime 警示（預期波動擴張、不預測方向），
    不產生 long/short 語意。Trader 端的正確消費方式是 risk throttle /
    sizing 調降 / 停用突破加倉，絕不可解讀為做空訊號。
  strength_rule: >
    事件觸發時 pct_rank <= trigger_percentile（預設 0.10）。
    strength = (trigger_percentile - pct_rank) / trigger_percentile，
    夾在 [0,1]：越深入分布尾部越強。
  confidence_rule: >
    基準 1.0；t-4h 參考樣本偏離目標時間越多，confidence 線性下降
    （偏離 reference_tolerance 時降至 0.5）。
  trigger_rule: >
    edge-triggered + 遲滯：pct_rank 首次 <= 0.10 且 oi_change_4h < 0
    時發事件（絕對收縮條件防止「正漂移分布的 bottom decile 是正變化」
    的退化情況）；之後直到 pct_rank > rearm_percentile（預設 0.20）
    才重新武裝。防止同一去槓桿 episode 的相鄰樣本重複發事件
    （對應假說的非重疊 episode 要求）。
    注意：percentile 定義下，正常時期也會有接近 10% 的樣本進入
    bottom decile——事件頻率高是設計預期，事件的「資訊量」由
    event study 的對照組檢驗，不由稀有度保證。
  reason_codes:
    - code: oi_contraction_bottom_decile
      meaning: 4h OI 變化落入 rolling 分布 bottom decile（去槓桿事件開始）
  metadata_schema:
    oi_change_4h: float          # 觸發時的 4h 變化率
    pct_rank: float              # 在 rolling 分布中的百分位
    history_count: int
    oi_now_raw: float
    oi_ref_raw: float
    reference_gap_seconds: float
  failure_modes:
    - 缺最新樣本 / 樣本過舊 -> None
    - t-4h 參考點缺樣本 -> None
    - warmup 未滿 -> None
    - OI 值 <= 0（資料異常）-> 跳過該樣本
  minimum_tests:
    - warmup 期間無事件
    - 急劇收縮觸發、reason/direction/strength 正確
    - 持續收縮不重複發事件（遲滯）
    - 擴張不觸發
    - 忽略其他 symbol / kind
    - timestamp == 來源 observation 的 observed_at
    - 決定性
    - 資料斷流（gap）時不發事件
  trader_visible_semantics: >
    「未來 4-24h 波動可能高於正常」的警示。用途：降槓桿、放寬停損、
    暫停加倉。無方向含義。strength 高 = 收縮更極端。
```

## Open questions（進 event study 階段驗證）

1. raw 合約數 vs notional 的事件集差異（對照 `reports/notional_vs_contract_oi/`）。
2. trigger_percentile 0.05 / 0.10 / 0.20 的敏感度（參數鄰域檢查）。
3. history_window 14d vs 90d 的穩定性。

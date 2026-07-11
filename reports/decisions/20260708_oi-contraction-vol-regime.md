# DecisionRecord: 否決 oi_contraction_vol_regime（波動 regime 訊號）

```yaml
DecisionRecord:
  id: dec_20260708_oi_contraction_vol_regime
  created_at: 2026-07-08
  created_by: /research-cycle #5（/promote-strategy 流程）
  decision: >
    否決 oi_contraction_vol_regime 作為可行動的波動警示訊號；
    假說走完 Gate 0-11 完整流程後，效應低於預註冊門檻且時間上不穩定。
  status: rejected
  from_grade: research_only（走完 event study 的實際狀態）
  to_grade: reject
  gate_results:
    data_integrity: partial   # fixture 有 source-of-truth 與 preflight 記錄、
                              # OI 分頁 bug 已修（commit c85eb84）；但 observed_at
                              # 為 conservative_simulated，未經 live 驗證。
                              # 本否決不依賴此項——效應不穩定是主因。
    execution_cost: n/a       # 未達可交易評級，無成本模型可審
    sizing_risk: n/a          # 依規未建 strategy（reject 級不准建）
    paper_criteria: n/a
  reason: >
    365d 樣本（BTC 110 / ETH 117 個非重疊事件）：24h vol-matched lift
    BTC +10.5%、ETH +9.8%，低於預註冊的 +15% 門檻；時間切分後效應
    集中於前半年（+21.9% / +18.9%），後半年 ≈ 0（+2.2% / +1.9%）；
    最近 90d 樣本為零或負（BTC 8h 顯著 -16.9%）。
    效應真實存在過（多個 CI 不含零、兩標的兩對照同號）但正在衰減，
    「不知道現在還在不在」的 risk filter 具有負價值。
  evidence:
    - reports/backtests/20260708_oi_contraction_vol_regime_event_study.md
    - reports/research/oi-contraction-vol-regime/vol_event_study_365d.json
    - reports/research/oi-contraction-vol-regime/vol_event_study_90d.json
    - reports/research/oi-contraction-vol-regime/hypothesis.md（預註冊判準）
    - reports/research/oi-contraction-vol-regime/signal_contract.md
    - reports/research/oi-contraction-vol-regime/smoke_replay.md
  owners: [QUANT, TRADER]
  follow_up_tasks:
    - backlog 的 passive-shrink-vol-expansion 已加註：開工前必須先解釋
      為何能倖免於同型效應衰減，否則 defer（已寫入 PIPELINE.md）
    - research/vol_event_study.py 原語保留（有測試），供後續波動假說重用
    - signals/oi_contraction_vol_regime.py 保留：實作正確且過完整測試，
      若重開條件觸發可直接重跑 event study，不需重寫
  do_not_repeat_until: >
    (1) 跨所（>=3 venues）OI 資料可用，能檢驗「全市場同時去槓桿」版本；或
    (2) 任何未來 90d 滾動樣本重新出現 24h vol-matched lift >= +15%
        （重跑指令在報告 §1，成本一個 cycle）。
    換 trigger percentile、horizon、history window 重跑不算新證據。
  related_artifacts:
    - data/bybit_leverage_pressure_fixture_365d.jsonl
    - data/bybit_leverage_pressure_fixture_90d.jsonl
```

## 流程註記

本假說是新流程（DESIGN.md §4）第一個走完 idea → hypothesis → contract →
signal → smoke replay → event study → decision 全鏈路的案例，共花
4 個 cycles（預算 12）。預註冊判準在假說階段就鎖定，event study 結果
出來後無任何調參迴旋空間——這正是流程設計的本意。

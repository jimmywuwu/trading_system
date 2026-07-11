# DecisionRecord: 否決方向性槓桿壓力假說

```yaml
DecisionRecord:
  id: dec_20260708_leverage_pressure_directional
  created_at: 2026-07-08
  created_by: QUANT（/research-cycle #1）
  decision: 否決「高槓桿壓力 -> 下行尾部更差」的方向性假說；固化 v1 三份研究的負面結論
  status: rejected
  from_grade: research_only（v1 非正式狀態）
  to_grade: reject
  reason: >
    365 天樣本、BTC+ETH 兩標的、三個 score 變體（v2 full / v3 / funding+OI）、
    四個 horizon（4h/8h/12h/24h）全部不支持：高壓力分組的 5% 分位數
    沒有比低分組更差（多數情況反而更好）。時間切分 0/2 支持。
    聚類 bootstrap 後方向性效應 CI 幾乎全部含零。
    對照組顯示單純 high_volatility / negative_momentum 的尾部資訊
    優於任何槓桿壓力分數——壓力分數無增量資訊。
  evidence:
    - reports/research/leverage-pressure-revisit/hypothesis.md   # Gate 0-2 對帳
    - reports/notion_drafts/leverage_pressure_v2_event_study_365d.md
    - reports/notion_drafts/eth_leverage_pressure_v3_simplified_score_365d.md
    - reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.md
  owners: [QUANT]
  follow_up_tasks:
    - passive-shrink-vol-expansion 已進 idea backlog（波動假說，非方向性；
      唯一 CI 不含零的 cell：ETH passive_notional_shrink 72h abs_return
      +2.55% CI95=[+0.03%, +5.23%]，僅 15 clusters，證據薄弱）
  do_not_repeat_until: >
    出現以下任一新證據才值得重開方向性版本：
    (1) 清算事件級資料（liquidation feed）可用，讓假說從「壓力狀態」
        改為「壓力 × 觸發」的條件化版本；
    (2) predicted funding（而非 settled）可作為 point-in-time observation
        且通過 data integrity review；
    (3) 跨所（>=3 venues）OI/funding 一致性資料，能區分單所噪音與
        全市場擁擠。
    換 score 權重、換 horizon、換分位數閾值不算新證據。
  related_artifacts:
    - data/bybit_leverage_pressure_fixture_365d.jsonl
    - data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl
```

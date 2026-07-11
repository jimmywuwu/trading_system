# leverage-pressure-revisit — Gate 0-2 Walkthrough

- created_at: 2026-07-08
- created_by: QUANT（/research-idea via /research-cycle #1）
- 結論：**Gate 2 否決（方向性版本）**，衍生一個重定義的 idea 進 backlog
- DecisionRecord: `reports/decisions/20260708_leverage-pressure-directional.md`

## 查重結果

`reports/decisions/`、`reports/research/` 無正式記錄，但 v1 流程留有三份
直接相關的既有證據（本次結論的主要依據）：

1. `reports/notion_drafts/leverage_pressure_v2_event_study_365d.md`
   （365d、BTC+ETH、8534 hourly events/symbol）
2. `reports/notion_drafts/eth_leverage_pressure_v3_simplified_score_365d.md`
   （v3 簡化 score + 時間切分）
3. `reports/leverage_state_classifier_v2/leverage_state_classifier_v2_robustness.md`
   （非重疊聚類 + 1000 次 cluster bootstrap，seed 20260616）

## Gate 0: ResearchIdea

```yaml
ResearchIdea:
  id: idea_20260708_leverage_pressure_revisit
  created_at: 2026-07-08
  created_by: QUANT
  summary: 高槓桿壓力狀態（funding + OI 擴張 + perp/spot 分歧）後，價格出現下行偏移
  suspected_mechanism: 槓桿多頭擁擠時，負向衝擊觸發清算連鎖，被迫賣壓放大下行尾部
  candidate_sources: [bybit perp funding/OI/mark, coinbase spot]
  candidate_symbols: [BTCUSDT, ETHUSDT]
  expected_horizon: 4h-72h
  why_it_might_persist: 清算是強制性的；槓桿部位無法瞬間降槓桿
  known_risks: settled funding 太慢（3 筆/天）；壓力≠觸發時機
  duplicate_of: leverage_pressure_v2 / v3 / leverage_state_classifier_v2（v1 流程）
  next_owner: QUANT
  priority: high（backlog 第 1 項）
```

Gate 0 通過（機制敘事完整、來源與 horizon 明確）——但 duplicate_of 非空，
Gate 2 必須先對帳既有證據。

## Gate 1: MechanismNote

```yaml
MechanismNote:
  id: mech_20260708_leverage_pressure
  research_idea_id: idea_20260708_leverage_pressure_revisit
  mechanism_summary: 擁擠的槓桿多頭 + 負向觸發 -> 清算連鎖 -> 下行尾部變差
  participants:
    forced_traders: 被清算的槓桿多頭
    slow_traders: 被動持倉的現貨多頭
    liquidity_providers: perp 做市商（撤單放大滑價）
    informed_traders: 預判清算價位的獵殺流
  pressure_source: 清算引擎的強制平倉
  expected_observable_footprints:
    - 高 funding + OI 擴張 + perp premium 同時出現（壓力狀態）
    - 壓力狀態後 forward return 的 5% 分位數顯著更差（尾部足跡）
  expected_decay_reason: 壓力被觀察到後套利者提前去槓桿
  why_it_might_persist: 清算的強制性不會消失
  alternative_explanations:
    - 高壓力期多為 risk-on 上行 regime，尾部反而更平靜（樣本選擇偏差）
    - 壓力是「狀態」不是「觸發」——沒有外生衝擊時什麼都不發生
    - OI 擴張主要跟隨價格/波動 regime，非獨立資訊
  invalidation_conditions:
    - 高壓力分組的下行分位數不比低分組差（<- 已發生，見 Gate 2）
```

機制敘事成立、足跡可觀測——Gate 1 形式上通過。問題出在足跡的實證。

## Gate 2: ResearchHypothesis — **否決**

假說的可證偽形式：

```text
當系統在 t 時刻可見高槓桿壓力分數（funding + OI 擴張 + perp/spot 分歧）時，
在 4h-24h 內，forward return 的 5% 分位數應顯著低於低分數時期，
且效應在時間切分下穩定。
```

### 對帳既有證據：falsification tests 實際上已經跑過且全部失敗

| 檢驗 | 來源 | 結果 |
|---|---|---|
| 高-低分組 5% 分位差（BTC，4/8/12/24h） | v2 event study 365d | **全部 supports=False**（diff 為正：高分組尾部反而較好，+0.01% ~ +0.28%） |
| 高-低分組 5% 分位差（ETH，4/8/12/24h） | v2 event study 365d | **全部 supports=False**（+0.50% ~ +0.80%） |
| v3 簡化 score（ETH） | v3 validation 365d | supportive horizons **0/4**；半樣本切分支持 **0/2** |
| 對照組比較 | v2/v3 24h controls | 單純 high_volatility（q05=-6.61%）與 negative_momentum（-6.82%）的尾部都比任何壓力分數（-5.04% ~ -5.47%）更差——壓力分數不含超出 vol/momentum 的尾部資訊 |
| 事件-對照 + 聚類 bootstrap | classifier v2 robustness | 方向性 return diff 的 CI 幾乎全部含零；結論 research-only，no Trader handoff |

替代解釋（Gate 1 alternative_explanations 第 1、2 條）與資料一致：
高壓力狀態多發生在上行 grind 期；壓力是狀態不是觸發，
unconditional 條件化只是採樣到平靜的多頭時段。

### 存活的線索（不屬於本假說，另立 idea）

classifier v2 中唯一 CI 不含零的 cell：**ETH `passive_notional_shrink`
72h abs_return diff=+2.55%，CI95=[+0.03%, +5.23%]**（僅 15 個 event
clusters）。這是**波動擴張**效應（絕對報酬），不是方向性效應。
機制重定義：OI notional 收縮但價格未跌 = 被動去風險，可能先行於
波動 regime 轉換。已作為新 idea 進 backlog（`passive-shrink-vol-expansion`），
明確標注：目標變數是 volatility 不是 return，用途是 risk filter /
vol sizing，非方向性 alpha；樣本極小，需要更長資料或跨所確認才值得開工。

## 結論

- 方向性槓桿壓力假說：**rejected**（詳見 DecisionRecord，含重開條件）
- v1 的三份研究就此固化為正式負面結論，防止換參數重開
- backlog 第 1 項移除，替換為重定義的 `passive-shrink-vol-expansion`（低優先）

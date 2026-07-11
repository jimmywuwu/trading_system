# cross-venue-funding-dispersion — Gate 0-2 Walkthrough

- created_at: 2026-07-08（/research-idea via /research-cycle #6）
- 結論：**兩個變體分流**——
  - 變體 A（事件收斂捕捉）：**Gate 2 否決**（成本算術，見下）
  - 變體 B（持續性 carry）：**Gate 0-2 通過，但資料未就緒** → 下一步 `/new-provider`
- 既有證據：`reports/cross_venue_dispersion/milestone2_btc_funding_dispersion.{md,json}`

## 查重

`reports/decisions/` 無相關記錄。milestone2（2026-06-17）為同一方向的
可行性 first pass，結論 `first_pass_completed_research_only`，其
DataProvider TODO（持久化對齊 funding fixture）未執行。

## 既有證據摘要（30d、BTC、Bybit/OKX/Hyperliquid）

| 統計 | 值 | 來源 |
|---|---|---|
| 對齊 8h 時點 | 90 | milestone2 md |
| 分歧 range 中位數 | 0.59 bps/8h | milestone2 md |
| top-decile 事件門檻 | 0.90 bps/8h | milestone2 md |
| 最大 range | 1.56 bps/8h | milestone2 md |
| 事件後 8h 分歧變化 | −0.47 bps（均值回歸） | milestone2 md |
| 事件後 24h 分歧變化 | −0.55 bps | milestone2 md |
| bybit−okx 配對 gap（n=5 tail 樣本）| mean +0.51 bps/8h、pos_rate 1.00 | `run_pairwise_gap_stats.py`（本目錄，可重跑）|
| hyperliquid−okx 配對 gap（n=5）| mean +0.51 bps/8h、pos_rate 1.00 | 同上 |

⚠️ JSON 只持久化了 5 筆 tail sample；完整 90 筆對齊資料未保存——
配對 gap 統計目前**不構成證據，只構成研究動機**。

## Gate 0/1（兩變體共用）

```yaml
ResearchIdea:
  id: idea_20260708_cross_venue_funding_dispersion
  summary: 跨所 perp funding 分歧的收斂/持續結構
  suspected_mechanism: >
    套利資本在 venue 間移動有摩擦（保證金搬運、venue 風險、
    提幣延遲），且各所結算節奏不同（Hyperliquid 1h vs Bybit/OKX 8h），
    使 funding 差異不會立即被抹平。
  candidate_sources: [bybit, okx, hyperliquid funding history（公開 REST，免 key）]
  candidate_symbols: [BTC perp（先），ETH（後）]
  expected_horizon: 事件收斂 8-24h；持續 carry 數週-數月

MechanismNote:
  participants:
    forced_traders: 各所被 funding 結算強制付費的一方
    slow_traders: 不跨所比價的單一 venue 用戶
    liquidity_providers: 跨所做市商（有限資本，優先大 venue）
    informed_traders: 專業 funding arb 桌（容量門檻高，小分歧不撿）
  pressure_source: funding 結算的強制性 + 跨所資本移動摩擦
  expected_observable_footprints:
    - 配對 funding gap 的符號持續性（carry 變體）
    - 極端分歧事件後的均值回歸（收斂變體，已在 milestone2 觀察到）
  why_it_might_persist: 小分歧低於專業桌的容量/成本門檻，長期留給小資本
  alternative_explanations:
    - gap 反映 venue 結構差異（結算節奏、標的指數構成、費率內嵌），
      不是可捕捉的無效率
    - OKX 系統性偏低可能是指數或 clamp 規則差異（必須先排除）
  invalidation_conditions: 見各變體 Gate 2
```

## Gate 2 — 變體 A：事件收斂捕捉 → **否決**

假說形式：top-decile 分歧事件後做多低 funding 所 / 做空高 funding 所，
收斂時獲利。

成本算術（假設宣告：taker 5.5 bps/leg、maker 2 bps/leg，4 legs 進出）：

```text
可捕獲毛利上限 ≈ 事件分歧 × 收斂期結算次數
  ≈ 0.90~1.56 bps/8h × 1~3 次 ≈ 1~5 bps
往返成本 ≈ 4 legs × 2~5.5 bps = 8~22 bps（未計滑價與兩腿 basis 風險）
=> 毛利上限 < 最低成本，結構性虧損，與參數無關
```

**否決理由不依賴樣本大小**——用 milestone2 的最大分歧值算，上限仍低於
最便宜的成本假設。除非分歧幅度出現一個數量級的放大（危機期），
此變體不值得任何進一步計算。

## Gate 2 — 變體 B：持續性 venue-pair carry → 通過（資料未就緒）

```yaml
ResearchHypothesis:
  id: hyp_20260708_cross_venue_carry
  statement: >
    存在穩定的 venue 配對（候選：OKX vs Bybit/Hyperliquid），其 funding
    gap 符號在數週尺度上持續，delta-neutral 跨所對沖持有可捕獲年化
    數個百分點的 carry，且一次進出成本（8-22 bps）在持有期內可攤銷。
  trigger_condition: 配對 gap 的滾動均值與符號持續性超過門檻（門檻由 90d 資料定）
  target_variable: 持有期內累積 funding 差 − 成本
  horizon: 30-90d 持有
  null_hypothesis: >
    gap 無符號持續性（隨機游走），或 gap 由 venue 結構差異
    （指數構成、clamp、結算規則）完全解釋，扣除後無殘餘。
  minimum_effect_after_cost: >
    90d 樣本上：配對 gap 年化 >= +3%（毛）、符號持續性（週尺度）>= 0.8、
    且扣除進出成本後 90d 持有淨收益 > 0。BTC 與 ETH 至少一個標的成立。
  falsification_tests:
    - 90d+ 三所對齊 funding 序列的配對統計（需新 fixture）
    - venue 結構差異排除：比對各所 funding 公式/clamp/指數文件
    - 子期間切分穩定性
  assumptions_to_verify:
    - Hyperliquid 1h 結算 vs 8h 結算的對齊方法不引入偏差
```

**資料缺口**：需要可重現的 90d+ 三所對齊 funding fixture
（milestone2 的 DataProvider TODO）。來源為公開 REST、免 API key、
免費——**不觸發人核可點**，但涉及網路拉取，執行時如遇環境限制
再升級為 Blocked。

## 下一步

`/new-provider`：建 `providers/` 級的多所 funding history provider
（或先做一次性但**完整持久化**的 90d fixture 導出 + preflight），
交付 Observation JSONL 供變體 B 的 event study 使用。
milestone2 的 TODO 清單（分頁測試、raw payload hash、observed_at 語意）
是驗收標準的起點。

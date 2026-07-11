# oi-contraction-vol-regime — Gate 0-2 Walkthrough

- created_at: 2026-07-08
- created_by: QUANT（/research-idea via /research-cycle #2）
- 結論：**Gate 0-2 通過**，進 Active；下一步 `/new-signal`
- 上游草稿：`reports/notion_drafts/oi_contraction_deleveraging_vol_regime.md`（2026-06-01）

## 查重與邊界檢查

- `reports/decisions/20260708_leverage-pressure-directional.md` 否決的是
  **方向性**槓桿壓力假說（壓力分數 → 下行尾部更差）。本假說目標變數是
  **未來已實現波動與尾部寬度**（雙邊），不預測方向，且事件定義是
  OI **收縮**（去槓桿進行中）而非壓力狀態（去槓桿尚未發生）——
  機制與目標變數均不同，不屬於重開。
- 該否決記錄的教訓已內建到本假說：對照組必須含 recent-volatility 與
  recent-return matching（v1 的壓力分數正是死在「不含超出 vol/momentum
  的增量資訊」）。這是本假說的主要 null。

## Gate 0: ResearchIdea

```yaml
ResearchIdea:
  id: idea_20260708_oi_contraction_vol_regime
  summary: BTC/ETH perp OI 在 4h 窗口快速收縮後，未來 4-24h 已實現波動與尾部寬度高於正常時期
  suspected_mechanism: 去槓桿進行中 -> 被迫重新定位 + 做市商縮手 -> 流動性結構不穩定 -> 波動擴張
  candidate_sources: [bybit linear perp OI/candle（fixture 已有）, bybit spot candle]
  candidate_symbols: [BTCUSDT, ETHUSDT]
  expected_horizon: 4h-24h
  why_it_might_persist: 去槓桿是強制性且分批的；做市商風控是機械性反應，不因被觀察而消失
  known_risks: recent-vol 混淆、事件重疊膨脹、單一交易所 artifact、OI observed_at 語意
  duplicate_of: null（v1 草稿為同一假說的前身，非否決記錄）
  next_owner: QUANT
  priority: high
```

通過：機制敘事、來源、horizon 齊備，且明確不是指標排列組合。

## Gate 1: MechanismNote

```yaml
MechanismNote:
  id: mech_20260708_oi_contraction
  mechanism_summary: OI 快速收縮 = 去槓桿進行中，市場處於不穩定重定位期而非事件結束
  participants:
    forced_traders: 被 margin/清算壓力擠出的槓桿部位
    slow_traders: 未及時調整的被動持倉者
    liquidity_providers: 去槓桿期間擴大價差、降低庫存容忍度的做市商
    informed_traders: 等待重定位完成再進場的機構流
  pressure_source: 保證金機制的強制性 + 做市商庫存風控
  expected_observable_footprints:
    - oi_change_4h 落入歷史 bottom decile（事件）
    - 事件後 4-24h 的 |forward return|、realized vol、q05-q95 寬度高於對照組
    - OI 收縮 vs 擴張（top decile）不對稱：收縮的波動足跡更強
  expected_decay_reason: 若被廣泛交易，做市商會提前擴大價差，效應前移
  why_it_might_persist: 效應本體是風險 regime 而非可直接套利的價差，套利壓力弱
  alternative_explanations:
    - recent-vol 混淆：OI 收縮只是「價格已經在動」的代理
    - direction 混淆：崩跌後的 OI 收縮，波動抬升由價格事件本身解釋
    - 事件重疊：一次去槓桿 episode 產生大量相鄰事件 bar，膨脹統計
    - Bybit 單所 artifact：不代表全市場槓桿
  invalidation_conditions:
    - vol-matched + return-matched 對照後效應消失
    - 非重疊 episode 聚類後 lift 消失
    - BTC 與 ETH 在多個時間窗上實質不一致
```

通過：足跡可觀測、替代解釋與失效條件明確。

## Gate 2: ResearchHypothesis

```yaml
ResearchHypothesis:
  id: hyp_20260708_oi_contraction_vol
  statement: >
    當系統在 t 時刻可見 BTCUSDT/ETHUSDT 的 4h OI 變化落入 rolling 分布
    bottom decile 時，其後 4h-24h 的已實現絕對報酬與尾部寬度（q05-q95）
    應高於 recent-vol 與 recent-return matched 的對照時期。
  trigger_condition: oi_change_4h <= rolling percentile(10%)（rolling 窗另定，非全樣本）
  target_symbol: [BTCUSDT, ETHUSDT]
  target_variable: volatility（abs return / realized vol / tail width）
  horizon: [4h, 8h, 24h]
  expected_direction: 波動高於對照（雙邊，不預測 sign）
  expected_effect_size: 既有初步證據（未驗證，v1 草稿）：BTC 24h abs return
    2.01% vs base 1.54%（+30% relative）；ETH 2.77% vs 2.49%（+11%）
  null_hypothesis: >
    條件化 recent realized vol 與 recent signed return 後，
    OI 收縮對未來 4-24h 波動與尾部無增量資訊。
  minimum_effect_after_cost: >
    本假說產出的是 risk-regime signal（供 sizing/risk filter 用），無直接
    交易成本；最低有用效應定為：非重疊 episode 下，24h realized vol 相對
    vol-matched 對照 lift >= +15%，且 BTC 與 ETH 同號、時間切分兩半皆成立。
    低於此視為不可用並否決。
  assumptions:
    - fixture 的 OI observed_at 語意採 conservative_simulated_observed_at
      （同 classifier v2 的處理），正式回測前需確認
  failure_modes: 見 MechanismNote alternative_explanations
  falsification_tests:
    - vol-matched 對照（主 null）
    - return-matched 對照
    - 非重疊 episode 聚類（參考 classifier v2 的做法）
    - OI top decile（擴張）對照：收縮應顯著強於擴張
    - 時間切分（halves + thirds）穩定性
```

**通過**。假說可證偽、null 明確、資料（365d Bybit fixture）已在
`data/`，最小有效效應已定義。

## 下一步

資料已就緒 → `/new-signal`：定義 OI-contraction vol-regime 的
SignalContract（注意：這是 risk-regime signal，direction 語意為
「波動擴張警示」而非 long/short；contract 需明確 Trader-facing 語意）。
Event study 需要 **abs-return / realized-vol 版本的 forward study 原語**，
屆時先在 `research/` 加函式 + 測試（現有 `forward_return_study` 只算
signed return）。

## Open questions（帶預設答案進下一階段）

- 事件定義用 rolling percentile（預設 90d）而非全樣本 percentile（防前視）。
- 先 BTC/ETH 單所快速驗證；跨所確認留給 robustness 階段。
- primary target 定為 realized vol lift（其次 tail width）。

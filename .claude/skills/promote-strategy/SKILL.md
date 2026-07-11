---
name: promote-strategy
description: 對回測報告做升級審查：四道 review gate（data integrity / execution / sizing risk / paper 標準）、結論評級、DecisionRecord。決定一個策略是否升級（或否決/降級）時使用。
---

# /promote-strategy — 證據到決策

用法：`/promote-strategy <回測報告路徑>`

你輪流扮演四個 reviewer 角色，每一關都在找**否決理由**。升級是例外，
否決與降級是常態。任何一關 fail，最終評級以最低者為準。

## 前置

讀目標報告、`docs/DESIGN.md` §4-5、`ROLES.md` 的 review flow、
`BACKTEST.md` 的 Execution/Fill Model Review 一節。

## Gate A: Data integrity review（DataProvider Developer 視角）

- [ ] 使用的 fixture 有 SourceNote 與品質檢查記錄？
- [ ] `observed_at` 語意正確（candle 是 bucket 結束才可見）？
- [ ] 資料缺口是否落在關鍵事件段？
- [ ] 有無 revision / late-arrival 未建模的風險？

## Gate B: Execution / cost review

- [ ] fill 規則（下一根 open）對該 horizon 合理？高頻訊號要 tick 級驗證
- [ ] fee tier 與滑價假設符合實際交易所？
- [ ] order notional 相對市場成交量可行（capacity）？
- [ ] 成本加倍後 net edge 仍為正？

## Gate C: Sizing / risk review（Trader 視角）

- [ ] sizing 規則明確且與現有 portfolio 不衝突？
- [ ] max drawdown 可承受？連續虧損情境算過？
- [ ] 失效 regime 有對應的減倉/停用規則？
- [ ] `halted` / `max_notional` / kill switch 路徑實測過（測試存在）？

## Gate D: Paper trading 標準（升 paper 時必填）

- 期間與最低樣本數（例如 30 天或 ≥20 筆訊號，取後到者）
- 通過標準：paper 結果 vs 回測預期的容許偏差（fill 價差、訊號頻率）
- 中止標準：最大回撤、連續 N 筆異常 fill、資料斷流
- 負責人與檢查頻率

## 產出：DecisionRecord

寫到 `reports/decisions/<date>_<strategy>.md`：

```yaml
DecisionRecord:
  id:
  created_at:
  decision:            # 一句話
  status: accepted | rejected | deferred | needs_revision
  from_grade:          # 現在評級
  to_grade:            # reject | research_only | paper_trade_candidate | production_candidate
  gate_results:
    data_integrity: pass | fail | partial
    execution_cost: pass | fail | partial
    sizing_risk: pass | fail | partial
    paper_criteria: pass | fail | n/a
  reason:
  evidence:            # 報告與 artifact 路徑列表
  follow_up_tasks:
  do_not_repeat_until: # 否決時：什麼新證據出現才值得重開
```

## 硬性規則

- `production_candidate` 必須四關全 pass **且** 有 paper trading 實績。
  目前系統沒有 paper broker v2 與 RiskManager（見 DESIGN.md §5），
  所以現階段**任何策略最高只能到 `paper_trade_candidate`**。
- 證據不足時的正確動作是 `needs_revision` 並列出缺的檢查，不是通融。
- DecisionRecord 是 append-only：改變結論就寫新的，不改舊的。

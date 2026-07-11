---
name: new-strategy
description: Trader 角色：把已有研究證據的訊號翻譯成可執行策略——StrategyContract、sizing/風控實作、測試、整合回測。訊號評級達 paper_trade_candidate 需要真實策略實作時使用。
---

# /new-strategy — 訊號到受控的交易策略

用法：`/new-strategy <signal 名稱或回測報告路徑>`

你是 **Trader** 角色。你的工作不是判斷訊號好不好（那是 Quant 已完成的），
而是回答：**「假設訊號如報告所述，我怎麼把它變成一筆筆受控、可解釋、
可停止的交易？」** 你的產出會被 `/promote-strategy` 的 Gate C
（sizing/risk review）審查。

## 前置條件（缺一不可，缺了就停）

1. 訊號已實作且過 smoke replay（`reports/research/<id>/smoke_replay.md`）。
2. 回測/event study 報告存在且評級 >= `paper_trade_candidate`，
   或人明確指示為既有訊號建策略。**評級 reject/research_only 的訊號
   不准建策略**——先去修研究，不要用策略工程掩蓋研究缺陷。
3. 讀：`docs/DESIGN.md` §3.3、該訊號的 signal_contract.md 與回測報告、
   `strategies/signal_position_strategy.py`（標準範式）、
   `core/strategy.py`（契約）。
4. 查 `reports/decisions/` 確認訊號未被否決。

## Step 1: StrategyContract（先寫再實作）

寫到 `reports/research/<id>/strategy_contract.md`：

```yaml
StrategyContract:
  id:
  strategy_name:
  input_signals:            # signal name + 消費哪些 reason codes
  signal_interpretation:    # 每個 reason code 對應什麼動作；strength/confidence 如何使用
  entry_rules:              # 什麼條件開倉/加倉
  exit_rules:               # 什麼條件平倉；有無停損/時間出場
  sizing_rules:             # target notional 怎麼算；strength 是 filter 還是乘數（預設 filter，理由見 DESIGN.md §3.3）
  risk_requirements:        # 消費 risk_state 的哪些 key：halted / max_notional / allowed_symbols / 其他
  order_types:              # market / limit；limit 的定價規則
  do_not_trade_conditions:  # 資料過舊、訊號衝突、部位已滿……
  expected_turnover:        # 對照回測報告的事件頻率估算
  expected_max_position:    # 最大部位 notional
  failure_behaviors:        # 訊號斷流、價格缺失時的行為（必須是「不交易」而非「猜」）
  paper_trading_criteria:   # 進 paper 的通過/中止標準（頻率、fill 偏差、最大回撤）
```

Gate（過不了就重寫）：

- 每條 entry/exit 規則都只引用 SignalEvent 欄位、portfolio snapshot、
  risk_state——**沒有任何指標計算**。
- sizing 有明確上限，且 `risk_state.max_notional` 永遠是最終夾板。
- do_not_trade_conditions 涵蓋回測報告列出的失效 regime。

## Step 2: 實作（strategies/<name>.py）

規則（違反任何一條 = 重做）：

- 繼承 `core.Strategy`；只消費 `SignalEvent` + portfolio dict + risk_state
  dict；價格只從 `on_observation` 收到的 Observation 拿。
- **不重算訊號邏輯**：如果你發現需要在 strategy 裡算 SMA/percentile，
  停下來——那是 signal contract 缺欄位，回頭找 Quant（開 open question），
  不是在 strategy 裡補算。
- `risk_state["halted"]` 為真 → `decide()` 回空 list，無例外。
- `allowed_symbols` 存在且不含本 symbol → 空 list。
- 買入部位以 `min(自身 sizing, risk_state.max_notional)` 為上限。
- 每個 `OrderIntent.reason` 串接訊號 reason（`"<strategy>:<signal_reason>"`），
  metadata 帶 signal strength/confidence——這是 attribution 鏈的一環。
- 決定性：同一事件序列 → 同一訂單序列。`decide()` 消費 pending signal
  後必須清空（一個訊號最多觸發一次決策）。
- 長倉 v1：系統目前是 long-only（`backtest.Portfolio` 不支援做空）。
  SHORT 方向的訊號只能映射為平倉/不動作，contract 裡寫明。
- 在 `strategies/__init__.py` export。

## Step 3: 單元測試（tests/test_<name>.py）

最低覆蓋（參考 `tests/test_backtest_engine.py` 的風格）：

- [ ] 無訊號 → 無訂單
- [ ] `halted=True` → 無訂單（即使有 pending 訊號）
- [ ] `allowed_symbols` 排除 → 無訂單
- [ ] 低於 min_strength / min_confidence 的訊號被過濾
- [ ] sizing 數學：目標部位、加倉 delta、`max_notional` 夾板各一例
- [ ] 平倉規則：對應 reason code 觸發全平
- [ ] reason 串接與 metadata 完整
- [ ] 同一訊號不會觸發兩次訂單
- [ ] 決定性

## Step 4: 整合回測（工程驗證，不是研究結論）

用 `backtest.BacktestEngine` 跑兩層：

1. **合成資料**（`tests/conftest.make_candles` 造已知情境）：驗證
   engine 內 order → fill → portfolio 全鏈路行為符合 contract。
   建議直接寫成整合測試放 `tests/`。
2. **真實資料切片**：signal + strategy 跑一段真實 fixture，並排
   buy-and-hold 基準輸出。此步的目的是確認 turnover / exposure /
   fee 與 StrategyContract 的預期一致（數量級對就好）——
   **策略績效結論仍以 /run-backtest 的研究報告為準，本步不得
   宣稱任何 alpha**。發現績效與研究報告矛盾 → 記進 open questions，
   這通常代表 execution 假設或 sizing 放大了研究裡沒有的成本。

結果附在 strategy_contract.md 的「Integration check」一節：
指令、事件數、訂單數、turnover、fees、與預期的偏差。

## 完成後

`python3 -m pytest` 全綠 → 更新看板 → 建議下一步 `/promote-strategy`
（Gate C 會審你的 sizing/risk；Gate D 需要你 contract 裡的
paper_trading_criteria）。

## 禁止

- 為評級不足的訊號建策略。
- 在 strategy 裡藏研究邏輯或「順手優化」訊號參數。
- 繞過或弱化 risk_state 的任何 key。
- 用整合回測的好看數字替代研究報告的結論評級。

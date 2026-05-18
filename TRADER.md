# Trader

Trader 負責把 `SignalEvent`、portfolio state 與 risk state 轉成可執行前檢查的 `OrderIntent`。

本角色的核心不是「看到訊號就下單」，而是把研究訊號放進交易上下文：是否交易、交易哪個標的、交易多少、用什麼訂單類型、是否被風控阻擋。Trader 不直接連交易所，也不重新發明 Quant 的研究邏輯。

## 目標

Trader 的主要目標：

- 把一個或多個 `SignalEvent` 轉成交易決策。
- 根據 portfolio、風控狀態、曝險與倉位規則控制下單意圖。
- Review Quant research report，判斷策略是否能進入 paper trading 或實盤候選。
- 產生穩定、可解釋、可測試的 `OrderIntent`。
- 讓同一個 strategy 可以跑 backtest、paper trading、live trading。
- 把下單意圖交給 execution，不直接處理 broker-specific API。

目前核心資料流：

```text
SignalEvent -> Strategy -> OrderIntent -> Execution
```

## 核心抽象

目前 `Strategy` 抽象是：

```python
class Strategy:
    name: str

    def on_observation(self, observation): ...
    def on_signal(self, signal): ...
    def decide(self, portfolio, risk_state): ...
```

`Strategy` 的輸出應該是：

```python
OrderIntent(
    symbol=...,      # 要交易的標的
    side=...,        # buy / sell
    order_type=...,  # market / limit
    quantity=...,    # 正數
    price=...,       # limit order 必填
    reason=...,      # 穩定、可追蹤的原因
    timestamp=...,
    metadata=...,
)
```

如果不應該交易，`decide()` 應該回傳空 list。

## OrderIntent 設計原則

### `symbol`

`symbol` 是 execution 會看到的交易標的。

如果 signal symbol 是合成標的，例如：

```text
TRIANGLE:BTC-USDT,ETH-BTC,ETH-USDT
```

Strategy 必須把它轉成 execution 可理解的一筆或多筆 order intents。Execution 不應該猜合成訊號要怎麼拆單。

### `side`

`side` 表示買或賣。

- `BUY`: 買入或增加多頭
- `SELL`: 賣出或降低多頭

是否能做空、是否需要借幣、是否有交易所限制，應該由 strategy/risk/execution 合作處理，不應該藏在 Quant signal 裡。

### `order_type`

`order_type` 表示下單意圖類型。

目前支援：

- `MARKET`
- `LIMIT`

若要新增 stop、post-only、IOC、TWAP 等類型，要先確認是否是 execution 能通用支援的語意，而不是單一 broker 的特殊參數。

### `quantity`

`quantity` 必須由 Trader 決定。

Position sizing 可以根據：

- signal strength
- signal confidence
- portfolio equity
- current position
- max exposure
- volatility
- liquidity
- risk state

Quant 不應該直接決定 quantity。

### `price`

`price` 只有在 limit order 時必填。

價格來源可以來自：

- latest observation
- signal metadata
- spread/edge calculation
- execution slippage model

如果 strategy 無法合理決定 limit price，應該先使用 paper validation，不要直接推到 live。

### `reason`

`reason` 是穩定代碼，用於 logs、回測歸因、execution audit。

範例：

- `signal_confirmed`
- `triangular_arbitrage_entry`
- `risk_reduction_exit`
- `rebalance_target_position`

不要把長篇自然語言放在 `reason`。詳細資訊放在 metadata。

### `metadata`

`metadata` 用來記錄決策上下文。

可以放：

- source signal metadata
- sizing calculation
- risk checks
- portfolio snapshot id
- expected edge
- execution notes

Execution 不應該依賴 metadata 才能知道怎麼送出基本訂單。如果某個欄位是 execution 必需的，應該提升成正式模型欄位。

## Strategy 抽象的迭代策略

Strategy 抽象不要一開始就變成完整交易系統。標準做法是：

```text
Signal Contract -> Portfolio/Risk Assumptions -> Minimal Strategy -> Paper Validation -> Execution Handoff
```

每個 strategy 都應該先證明：在固定 signals、portfolio、risk_state 下，能 deterministic 地產生正確 order intents。

### 第 1 階段：定義交易假設

先寫清楚：

```text
當哪些 signal 出現，在什麼風控條件下，要建立、調整或退出什麼部位。
```

範例：

```text
當 triangular_arbitrage_net_profit signal 強度超過門檻，且 risk_state 沒有 halted，產生一組套利 order intents。
```

```text
當 Telegram listing signal 出現，且 confidence 超過門檻，只用固定風險預算建立短期多頭。
```

如果交易假設必須重新計算 signal 才能表達，表示 Quant/Trader 邊界還沒切好。

### 第 2 階段：定義 input contract

明確列出 strategy 需要：

- 哪些 signal names
- 哪些 reason codes
- strength 門檻
- confidence 門檻
- portfolio 欄位
- risk_state 欄位
- 是否需要最新 observation
- 是否支援多標的或合成標的

範例：

```text
ThresholdStrategy
required signals: any SignalEvent
required risk_state: halted
required portfolio: none in first version
position sizing: fixed quantity
```

### 第 3 階段：最小 Strategy

先實作最小可用版本：

- `on_signal()` 收集 signal。
- `decide()` 根據 portfolio/risk_state 產生 order intents。
- risk halted 時回傳空 list。
- 不符合門檻時回傳空 list。
- 每筆 order intent 有清楚 reason。

第一版不要同時塞進：

- broker API
- fill simulation
- performance attribution
- complex portfolio optimization
- raw observation parsing

這些應該分別留給 Execution、Backtest、DataProvider 或 Quant。

### 第 4 階段：position sizing

最小版跑通後，再逐步加入 sizing。

建議迭代順序：

1. fixed quantity
2. fixed notional
3. equity percentage
4. volatility adjusted sizing
5. confidence/strength adjusted sizing
6. portfolio risk budget

每次升級 sizing，都要保留舊邏輯能被測試和比較。

### 第 5 階段：risk integration

Strategy 必須尊重 `risk_state`。

常見 risk_state 欄位：

- `halted`
- `max_position`
- `max_notional`
- `max_order_quantity`
- `allowed_symbols`
- `blocked_symbols`
- `max_daily_loss_reached`
- `reduce_only`

如果風控規則開始變多，應該抽成 RiskManager，而不是讓 Strategy 無限制膨脹。

### 第 6 階段：paper validation

接 live 前，至少要跑 paper validation。

檢查：

- 同一批 signals 是否產生 deterministic order intents。
- risk halted 時是否不交易。
- 資料不足時是否不交易。
- position sizing 是否符合預期。
- limit order 是否都有 price。
- 合成訊號是否正確拆成 execution 可理解的 orders。

### 第 6.0 階段：Research Report Review

Quant 交付 research report 後，Trader 負責交易可行性 review。Trader 不重新證明 signal 假說，但必須判斷它是否能被安全地放進 portfolio context。

Trader 需要回答：

```text
這個 signal / strategy 要怎麼 sizing？
最大倉位與最大曝險是多少？
什麼情況停用或 reduce-only？
和既有部位或其他 signals 會不會衝突？
是否值得進入 paper trading？
```

Trader review 至少包含：

- position sizing rule：fixed notional、equity percentage、volatility adjusted 或其他方法。
- exposure limits：max position、max notional、gross/net exposure。
- risk limits：max daily loss、max drawdown stop、kill switch、reduce-only 條件。
- portfolio impact：和既有策略的相關性、集中度、資金占用。
- benchmark interpretation：若策略輸給 buy-and-hold，但 drawdown 較低，是否定位為 defensive allocation。
- paper trading criteria：paper 期間、成功/失敗門檻、何時升級或停用。
- production readiness：是否還缺 data integrity review、execution cost review 或風控規則。

Trader 不應該只根據 Quant report 的 total return 做交易決策。若 Quant report 結論是 `Research Only`，Trader 不應升級成 production candidate。

### 第 6.1 階段：Backtest Strategy Replay

Strategy 進入 paper/live 前，應該先在 BacktestEngine 裡跑 historical replay。

回測中的 strategy 流程：

```text
SignalEvent
-> strategy.on_signal()
-> strategy.decide(portfolio_snapshot, risk_state)
-> list[OrderIntent]
-> SimulatedExecution
-> Portfolio update
```

Trader 在這個階段負責：

- 定義 strategy 需要的 portfolio fields。
- 定義 strategy 需要的 risk_state fields。
- 確認 no-signal / weak-signal / risk-halted 都不產生 orders。
- 確認 normal signal 產生 expected order intents。
- 確認 position sizing deterministic。
- 確認 order reason 可以回溯到 signal reason。

Trader 不負責：

- historical observations replay
- signal 計算
- fill simulation internals
- portfolio accounting internals

這些分別屬於 DataProvider、Quant、Execution simulation、Portfolio。

### 第 7 階段：execution handoff

交給 execution 前，Strategy 要明確定義：

- order intent schema
- order reason codes
- broker 是否支援該 order_type
- 是否允許 partial fill
- 是否需要 cancel/replace
- 是否需要 reduce-only 或 post-only 類參數

如果某些 execution 參數是通用需求，應該考慮擴充 `OrderIntent`。如果只是單一 broker 特性，先放 metadata 或 execution adapter config。

## 新增 Strategy 標準流程

每次新增一個 strategy，都按照以下流程。

### 1. Trading Note

先寫清楚：

- 使用哪些 signals？
- 什麼條件進場？
- 什麼條件不交易？
- 什麼條件退出或減倉？
- position sizing 怎麼算？
- 風控假設是什麼？
- 預期交易標的是單一標的還是多腿交易？

輸出：一段簡短 trading note。

### 2. Input Contract

定義 strategy 的輸入要求：

- required signal names
- required signal metadata
- required portfolio fields
- required risk_state fields
- optional observations
- supported symbols

如果 strategy 長期依賴某個 signal metadata 欄位，應該回頭和 Quant 討論是否要提升成正式 signal contract。

### 3. Minimal Implementation

在 `strategies/` 新增 strategy。

要求：

- `name` 穩定。
- `decide()` 回傳 list of `OrderIntent`。
- 無交易時回傳空 list。
- 不直接呼叫 broker。
- 不重新解析 raw observations。
- 不重新計算 signal 內部研究邏輯。

### 4. Sizing and Risk Rules

定義：

- base quantity
- max quantity
- max notional
- symbol allowlist/blocklist
- reduce-only mode
- confidence/strength scaling

Sizing 和 risk rule 必須可測試，不要只寫在 comments 裡。

### 5. Validation

至少驗證：

- no-signal case
- weak-signal case
- risk-halted case
- normal-entry case
- sizing boundary case
- limit-order price requirement
- deterministic output
- backtest replay with simulated execution
- orders can be attributed to signal reason

### 6. Handoff to Execution

交給 execution 前，提供：

- strategy name
- order reason codes
- expected order types
- supported symbols
- metadata schema
- known failure modes
- paper validation result

## `on_observation()` 使用準則

`on_observation()` 是給 Strategy 使用最新市場上下文，不是讓 Strategy 變成 Signal。

適合使用 `on_observation()` 的情況：

- 取得最新價格做 limit price。
- 檢查流動性或 bid/ask spread。
- 判斷資料是否 stale。
- 估算粗略 slippage。

不適合使用 `on_observation()` 的情況：

- 重新計算 RSI。
- 做 sentiment parsing。
- 判斷 Telegram keyword。
- 重新計算套利 spread。

這些應該留在 Quant 的 Signal。

## Strategy 驗收清單

一個 strategy 可以被視為可用，至少要滿足：

- [ ] 有穩定 `name`。
- [ ] 有清楚 trading note。
- [ ] 明確列出 required signals。
- [ ] 明確列出 required portfolio/risk_state 欄位。
- [ ] 無交易時回傳空 list。
- [ ] 不直接呼叫 broker API。
- [ ] 不重新計算 signal 內部邏輯。
- [ ] 不解析 raw source payload。
- [ ] `OrderIntent.quantity` 永遠為正數。
- [ ] limit order 永遠有 price。
- [ ] risk halted 時不產生新倉 orders。
- [ ] 相同輸入產生 deterministic output。
- [ ] 有 smoke example 或測試。
- [ ] 通過 historical replay。
- [ ] 回測中的 orders 可追到 signal reason。

## 什麼時候要改 Strategy 抽象

不要因為單一 strategy 特殊，就立刻改 `Strategy` 或 `OrderIntent`。

只有以下情況才考慮改核心抽象：

- 兩個以上 strategies 都需要同一個新 order 欄位。
- Execution 長期需要解析同一個 metadata 欄位。
- 多腿交易無法安全用多個 `OrderIntent` 表達。
- 多個 strategies 都需要共同的 position sizing helper。
- risk_state dict 已經讓常見規則難以安全表達。
- `decide()` 無法表達必要的 state transition。

## 近期迭代路線

建議按這個順序迭代：

1. 為 `ThresholdStrategy` 補上 signal confidence 門檻。
2. 把 fixed quantity 擴充成 fixed notional sizing。
3. 定義最小 `risk_state` schema，例如 `halted`、`allowed_symbols`、`max_notional`。
4. 新增 strategy smoke example，覆蓋 no-signal、weak-signal、risk-halted、normal-entry。
5. 建立 paper execution validation，確認 `OrderIntent` 能被 `PaperBroker` 接收。
6. 若多個 strategies 共用 sizing，抽出 sizing helper。
7. 接上 BacktestEngine，先用 market order、fixed fee、simple long-only portfolio 驗證完整 loop。

## 設計取捨

Strategy 應該專注於「交易決策」，不是資料接入、研究訊號或實際下單。

這表示：

- Strategy 可以決定是否交易。
- Strategy 可以決定交易多少。
- Strategy 可以根據風控阻擋交易。
- Strategy 可以把合成 signal 拆成多筆 order intents。
- Strategy 不應該接外部 API。
- Strategy 不應該重新做 Quant 的研究計算。
- Strategy 不應該處理 broker 下單細節。

這樣 DataProvider、Quant、Trader、Execution 的邊界會保持清楚，系統也比較容易測試與迭代。

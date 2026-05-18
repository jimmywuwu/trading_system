# Backtest Architecture

Backtest 的目標是用 historical observations 重建某段時間內系統實際可見的資訊，依序驅動 Signal、Strategy、Execution simulation 與 Portfolio accounting。

核心原則：

```text
只用 observed_at <= current_time 的資料做決策
```

不要用 `occurred_at` 判斷可見性。`occurred_at` 是事件發生時間，`observed_at` 才是系統知道這件事的時間。

## 核心資料流

```text
Historical Observations
-> ReplayDataProvider
-> BacktestClock
-> Signal.generate()
-> Strategy.on_signal()
-> Strategy.decide()
-> SimulatedExecution
-> Portfolio
-> Metrics
```

## 元件分工

### ReplayDataProvider

負責提供 historical observations。

責任：

- 載入 historical observations。
- 依 `observed_at` 排序。
- 支援時間窗查詢。
- 支援逐步 replay。
- 保證不回傳 `observed_at > current_time` 的資料。

建議介面：

```python
class ReplayDataProvider(DataProvider):
    def get_observations(self, start=None, end=None, kinds=None, subjects=None): ...
    def replay(self, start, end): ...
```

`replay()` 可以逐筆或逐 bucket 產生 observations：

```python
for current_time, observations in provider.replay(start, end):
    ...
```

### BacktestClock

負責回測時間推進。

兩種模式：

- event-driven：每次推進到下一個 observation 的 `observed_at`
- bar-driven：每次推進固定間隔，例如 1 minute

第一版建議使用 event-driven，因為和 `Observation` 抽象最一致。

### SignalRunner

負責把目前可見資料交給 signals。

責任：

- 管理 signal warmup。
- 在每個 current_time 呼叫 `generate()`。
- 收集非 `None` 的 `SignalEvent`。
- 確認 signal timestamp 不晚於 current_time。

SignalRunner 不應該做 position sizing，也不應該修改 portfolio。

### StrategyRunner

負責把 signals 交給 strategy。

責任：

- 呼叫 `strategy.on_observation()`。
- 呼叫 `strategy.on_signal()`。
- 呼叫 `strategy.decide(portfolio, risk_state)`。
- 收集 `OrderIntent`。

StrategyRunner 不應該模擬成交，也不應該直接改 portfolio。

### SimulatedExecution

負責把 `OrderIntent` 轉成 simulated fills。

第一版可以很簡單：

- market order 用下一個可用 candle open 成交。
- limit order 如果 candle high/low 觸及 price 則成交。
- fee 用固定 rate。
- slippage 先用固定 bps 或 0。

後續再擴充：

- bid/ask fill model
- partial fill
- volume cap
- latency
- maker/taker fee
- cancel/replace

### Execution / Fill Model Review

Quant report 可以先使用簡化 execution assumptions，但進入 paper trading 或 production 前，必須由 Execution / Broker owner review fill model 與成本假設。

Execution review 需要回答：

```text
回測成交假設是否接近實盤？
market order 是否會有 spread / slippage / latency？
limit / stop order 的觸價與成交規則是否合理？
交易所 API、最小下單量、費率與流動性限制是否已反映？
```

最低檢查項目：

- fill timing：same close、next open、next close 或 tick/quote fill 的假設是否明確。
- spread/slippage：是否有固定 bps、bid/ask model、volume-based model 或保守 haircut。
- fees：maker/taker、tier、交易所與商品是否一致。
- liquidity：order notional 相對成交量是否合理，是否需要 volume cap。
- partial fill：是否允許 partial fill，未成交部分如何處理。
- order type semantics：market、limit、stop、post-only、IOC 等是否和 broker 行為一致。
- latency：signal 生成到送單是否有延遲假設。
- failure behavior：rejection、cancel、rate limit、disconnect 是否有模擬或 paper 檢查。

若 execution review 未通過，策略不得被標記為 production candidate。回測報告必須清楚標示 execution assumptions 與尚未驗證的成本項目。

### Signal Price / Fill Price / Equity Price

Bar backtest 裡要把三種價格分清楚：

- `signal price`：策略判斷訊號用的價格。SMA、RSI、MACD 這類收盤確認策略通常用 candle close。
- `fill price`：訂單實際成交用的價格。若第 N 根 candle close 產生 market order，第一版假設第 N+1 根 candle open 成交。
- `equity price`：帳面估值用的價格。每根 candle 結束時，用最新 close 做 mark-to-market。

因此 SMA 類策略的預設流程是：

```text
第 N 根 candle close
-> 用 close 更新 SMA 並產生 signal/order intent
-> order 放進 pending_orders

第 N+1 根 candle open
-> pending market order 用 open 成交

第 N+1 根 candle close
-> 用 close 更新 signal state
-> 用 close 計算 portfolio equity
```

這個約定避免用同一根 candle close 同時產生訊號和成交，也比「下一根 close 成交」更接近一般 bar backtest 的 market order 假設。

### Portfolio

負責帳務與部位。

責任：

- cash balance
- positions
- average cost
- realized PnL
- unrealized PnL
- fees
- equity curve
- exposure

Portfolio 不應該知道 Signal 的研究邏輯。

### RiskState

負責提供當下風控狀態給 Strategy。

第一版可以是 dict：

```python
risk_state = {
    "halted": False,
    "max_notional": 1000,
    "allowed_symbols": ["BTC-USD"],
}
```

當規則變多，再抽成 `RiskManager`。

### Metrics

負責回測結果統計。

第一版至少包含：

- total return
- max drawdown
- number of trades
- win rate
- average trade PnL
- fees
- exposure

後續再加入：

- Sharpe
- Sortino
- turnover
- capacity
- slippage attribution
- signal attribution

## 最小回測 Loop

第一版 BacktestEngine 可以長這樣：

```python
class BacktestEngine:
    def run(self):
        pending_orders = []

        for current_time, new_observations in provider.replay(start, end):
            visible_observations.extend(new_observations)

            fills = execution.simulate(pending_orders, new_observations, current_time)
            portfolio.apply(fills)
            pending_orders = execution.remaining_orders()

            for observation in new_observations:
                strategy.on_observation(observation)

            generated_events = []
            for signal in configured_signals:
                event = signal.generate(visible_observations)
                if event is not None:
                    generated_events.append(event)

            for event in generated_events:
                strategy.on_signal(event)

            new_orders = strategy.decide(portfolio.snapshot(), risk_state)
            pending_orders.extend(new_orders)
            metrics.record(current_time, portfolio, generated_events, new_orders, fills)
```

這個 loop 刻意讓新產生的 orders 進入 `pending_orders`，由後續 observations 觸發成交模擬。這樣可以避免同一個 current_time 產生 signal 後，立刻使用同一批尚未可交易的價格成交。

若資料是 candle，第一版 execution 規則應該把價格拆開：

```python
fill_price = candle.open      # pending order 成交
signal_price = candle.close   # strategy / signal 更新
equity_price = candle.close   # portfolio mark-to-market
```

## Backtest 階段設計

### 第 1 階段：Observation Replay

先完成：

- historical observations 載入
- `observed_at` 排序
- event-driven replay
- point-in-time query

不急著做完整 portfolio。

驗收：

- replay 順序 deterministic
- 不會回傳未來資料
- `start/end/kinds/subjects` filter 正確

### 第 2 階段：Signal Replay

加入 Quant signals。

驗收：

- signal 只使用 current_time 可見資料
- missing data 回傳 `None`
- signal timestamp 不晚於 current_time
- signal metadata 足以 debug

### 第 3 階段：Strategy Replay

加入 Strategy。

驗收：

- no signal 時無 orders
- weak signal 時無 orders
- risk halted 時無 orders
- normal signal 時有 expected order intents
- 相同輸入 deterministic

### 第 4 階段：Execution Simulation

加入 simulated fills。

驗收：

- market order 成交規則明確
- limit order 觸價規則明確
- fee/slippage 可設定
- 無法成交時保留或取消規則明確

### 第 5 階段：Portfolio Accounting

加入 portfolio update。

驗收：

- cash 正確扣款
- position 正確更新
- fee 正確入帳
- realized/unrealized PnL 可重算
- equity curve deterministic

### 第 6 階段：Metrics and Attribution

加入回測報告。

驗收：

- trades 可追到 order reason
- orders 可追到 signal reason
- signal metadata 可追到 observations
- performance 可按 strategy/signal/reason 分解

## Lookahead Bias 防線

BacktestEngine 必須強制以下規則：

- provider replay 只能產生 `observed_at <= current_time` 的 observations。
- signal timestamp 不得晚於 current_time。
- strategy 不得查詢 current_time 之後的資料。
- execution fill 不得使用同一時間點尚不可知的價格。
- macro/news/message revisions 必須用 revision observed time 建模。

如果需要用 candle 成交，要明確定義該 candle 何時可見：

- candle open 在 bucket 開始時可見
- candle close/high/low/volume 通常在 bucket 結束後才可見

分鐘 K 線回測常見錯誤是：在 10:00 直接使用 10:00-10:01 candle 的 close 做決策。正確做法是 10:01 之後才能用該 close。

## 第一版建議範圍

第一版 backtest 不需要做完整交易平台。

建議只做：

- `ReplayDataProvider`
- event-driven replay
- one signal
- one strategy
- market order only
- fixed fee rate
- close-price fill after candle becomes visible
- simple long-only portfolio
- basic metrics

先把 point-in-time loop 做對，再擴充成交模型與 portfolio。

## 不該放進 BacktestEngine 的事

BacktestEngine 不應該：

- 解析 raw exchange API response
- 重新計算 signal 內部邏輯
- 決定 position sizing
- 硬寫某個 broker API
- 修改 signal 或 strategy 的 contract

BacktestEngine 只負責 orchestration。

# 研發角色分工

本專案先拆成三個研發角色：

1. DataProvider Developer
2. Quant
3. Trader

另有 Execution / Broker owner 負責實際成交、模擬成交與 broker-specific 行為。Execution 目前主要在 backtest / paper / live broker 元件中體現，不直接產生研究訊號或交易決策。

共用資料流是：

```text
DataProvider -> Observation -> Signal -> Strategy -> OrderIntent
```

核心原則是：所有資料都先變成某個時間點可見的 `Observation`，Quant 再把 observations 轉成 `SignalEvent`，Trader 最後根據訊號、部位與風控狀態產生 `OrderIntent`。

## DataProvider Developer

DataProvider Developer 負責資料接入與 point-in-time visibility。

### 責任

- 接外部資料源，例如交易所、檔案、資料庫、Telegram、新聞、總經 API。
- 把不同來源的資料統一轉成 `Observation`。
- 保留 `occurred_at` 與 `observed_at`。
- 確保回測只能看到當時系統已經可見的資料。
- 把來源特定資料轉成 typed payload，例如 `PricePayload`、`MessagePayload`、`MacroPayload`。
- 處理缺資料、重複資料、延遲到達、重連、格式錯誤。
- Review Quant research 使用的資料品質、時間語意與 point-in-time 正確性。

### 核心抽象

```python
class DataProvider:
    source: str

    def get_latest(self, subject, kind=None): ...
    def get_observations(self, start=None, end=None, kinds=None, subjects=None): ...
    def subscribe(self, kinds=None, subjects=None): ...
```

### 交付物

- `providers/` 底下的 provider 實作。
- 資料解析與標準化邏輯。
- 來源資料的基本驗證。
- 查詢 observations 的簡單範例。
- research data integrity review。

### 邊界

- 不判斷要不要交易。
- 不產生買賣訊號。
- 不決定倉位大小。
- 不送出訂單。

### 成功標準

- Quant 可以讀 `Observation`，不需要知道原始 API 格式。
- 回測可以重建某個時間點系統實際知道的資訊。
- 新資料源可以加入，不需要改既有 signals 或 strategies。

## Quant

Quant 負責研究邏輯，把 observations 轉成交易訊號。

### 責任

- 在 `signals/` 底下設計與實作 signal。
- 使用價格、Telegram、新聞、總經或其他 observations。
- 產生 `SignalEvent`，包含 direction、strength、confidence、reason。
- 定義 signal 是否需要 `warmup()`。
- 驗證 signal 在缺資料、資料過期、異常資料下的行為。
- 避免 lookahead bias，判斷可見性時使用 `observed_at`，不是只看 `occurred_at`。
- 主責產出完整 research report 與 benchmark report。

### 核心抽象

```python
class Signal:
    name: str

    def warmup(self, provider): ...
    def generate(self, observations): ...
```

### 交付物

- `signals/` 底下的 signal 實作。
- Signal metadata，說明訊號原因、輸入資料、假設。
- 研究範例、測試或簡單驗證腳本。
- 對缺資料與 stale data 的安全處理。
- 完整研究報告，包含 train/test、walk-forward、benchmark、regime attribution、參數穩定性與失效條件。

### 邊界

- 不直接連交易所或 Telegram。
- 不送出訂單。
- 不管理 portfolio。
- 不把風控規則藏在 signal 裡。

### 成功標準

- Trader 可以從 `SignalEvent.reason` 與 metadata 理解訊號為什麼出現。
- 同一個 signal 可以跑回測，也可以跑 live。
- 資料不足或資料過期時，signal 應該安全地不產生訊號。

## Trader

Trader 負責策略決策，把 signals 轉成 order intents。

### 責任

- 在 `strategies/` 底下實作 strategy。
- 組合一個或多個 signals。
- 根據 portfolio、風控狀態、曝險限制與倉位規則做交易決策。
- 產生 `OrderIntent`。
- 讓每筆交易意圖都能透過 reason 與 metadata 解釋。
- 與 paper broker 或 live broker 等 execution 元件協作。
- Review Quant research report，決定策略是否值得進入 paper trading 或 production readiness review。

### 核心抽象

```python
class Strategy:
    name: str

    def on_observation(self, observation): ...
    def on_signal(self, signal): ...
    def decide(self, portfolio, risk_state): ...
```

### 交付物

- `strategies/` 底下的 strategy 實作。
- 進場、出場、加減倉規則。
- position sizing 規則。
- risk state 整合方式。
- 產生 `OrderIntent` 的範例。
- trading feasibility review，包含 sizing、risk limits、portfolio impact 與 paper trading criteria。

### 邊界

- 不解析原始資料源格式。
- 不直接實作應該屬於 Quant 的研究指標。
- 不直接呼叫交易所 API。
- 不繞過風控狀態。

### 成功標準

- Strategy 輸出清楚的 `OrderIntent` list。
- 相同輸入會得到 deterministic 的決策結果。
- 風控可以在 execution 前阻擋或調整訂單。
- 策略可以先跑 paper execution，再接 live execution。

## 協作契約

### DataProvider Developer -> Quant

提供：

- point-in-time `Observation`
- typed payload
- 清楚的 source / subject 命名
- 資料品質與延遲假設

Quant 不應該依賴交易所、Telegram、總經 API 的原始格式。原始 payload 可以放在 metadata 裡做 debug，但不應該變成主要依賴。

### Quant -> Trader

提供：

- `SignalEvent.direction`
- `SignalEvent.strength`
- `SignalEvent.confidence`
- `SignalEvent.reason`
- 解釋 signal 所需的 metadata

Trader 不應該在 strategy code 裡重新計算 signal 內部邏輯。

### Trader -> Execution

提供：

- `OrderIntent.symbol`
- `OrderIntent.side`
- `OrderIntent.order_type`
- `OrderIntent.quantity`
- optional price
- order metadata

Execution 負責實際下單、模擬成交、成交回報與 broker-specific 行為。

### Quant Report Review Flow

完整策略研究不應由單一角色直接推到 production。標準 review flow：

```text
1. Quant 出完整 research report / benchmark report
2. DataProvider Developer 做 data integrity review
3. Execution / Broker owner 做 fill model / cost review
4. Trader 做 sizing / risk / portfolio review
5. Paper trading
6. Production decision
```

各角色核心問題：

- Quant：這個 signal / strategy 是否有研究價值，是否通過樣本外與 benchmark 檢查？
- DataProvider Developer：資料是否 point-in-time、完整且沒有 lookahead bias？
- Execution / Broker owner：成交與成本假設是否接近實盤？
- Trader：是否能安全 sizing、控風險並放進 portfolio？

若 Quant report 只達到 `Research Only`，Trader 不應直接升級為 production candidate。

## 權責總表

| 角色 | 擁有 | 產出 | 消費 |
| --- | --- | --- | --- |
| DataProvider Developer | 資料可見性 | `Observation`, data integrity review | 外部 API / 檔案 / stream |
| Quant | 研究訊號 | `SignalEvent`, research report, benchmark report | `Observation` |
| Trader | 交易決策 | `OrderIntent`, trading feasibility review | `SignalEvent`, portfolio, risk state |
| Execution / Broker owner | 成交與 broker 行為 | fills, execution cost review, broker adapters | `OrderIntent` |

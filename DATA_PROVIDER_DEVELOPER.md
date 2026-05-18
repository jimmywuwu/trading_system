# DataProvider Developer

DataProvider Developer 負責把任何外部資訊轉成系統在某個時間點可見的 `Observation`。

本角色的核心不是「接 API」而已，而是保證資料語意、時間可見性與格式穩定。價格、Telegram 訊息、新聞、總經數據、鏈上事件，都應該先被轉成 observations，Quant 才能在同一個時間軸上使用它們。

## 目標

DataProvider Developer 的主要目標：

- 建立可靠的資料接入層。
- 統一不同資料源的輸出格式。
- 保留 point-in-time visibility。
- Review Quant research 使用的資料品質與時間語意。
- 避免回測使用未來資料。
- 讓 Quant 不需要依賴原始 API 格式。
- 讓新資料源可以逐步加入，而不破壞既有 signals。

目前核心資料流：

```text
External Source -> DataProvider -> Observation -> Signal
```

## 核心抽象

目前 `DataProvider` 抽象是：

```python
class DataProvider:
    source: str

    def get_latest(self, subject, kind=None): ...
    def get_observations(self, start=None, end=None, kinds=None, subjects=None): ...
    def subscribe(self, kinds=None, subjects=None): ...
```

`DataProvider` 的輸出應該是：

```python
Observation(
    observed_at=...,   # 系統實際看到資料的時間
    occurred_at=...,   # 事件本身發生的時間
    source=...,        # coinbase / telegram / macro_api
    kind=...,          # price / trade / message / macro / orderbook
    symbol=...,        # BTC-USDT / telegram channel / US_CPI
    payload=...,       # typed payload
    metadata=...,
)
```

## Observation 設計原則

### `observed_at`

`observed_at` 是策略在 live 或 backtest 中能看見這筆資料的時間。

這是回測最重要的欄位。任何查詢某個時間點可見資料的邏輯，都應該以 `observed_at <= t` 為準。

### `occurred_at`

`occurred_at` 是事件本身發生的時間。

例如：

- 交易所成交時間。
- Telegram 訊息發送時間。
- CPI 公布時間。
- 新聞發布時間。

`occurred_at` 不代表系統當時一定已經知道這件事。

### `kind`

`kind` 描述 observation 類型，目前包含：

- `PRICE`
- `CANDLE`
- `TRADE`
- `MESSAGE`
- `MACRO`
- `ORDERBOOK`

新增 `kind` 前要先確認：既有 kind 搭配新的 typed payload 是否已足夠。

### `symbol`

`symbol` 是 observation 的主要 subject。

範例：

- `BTC-USDT`
- `ETH-BTC`
- `telegram:binance_announcements`
- `macro:US_CPI`

命名要穩定，不能直接使用來源 API 中容易變動或不一致的名稱。

### `payload`

`payload` 必須是 typed model，不要把主要資料只塞進 dict。

目前已有：

- `PricePayload`
- `CandlePayload`
- `MessagePayload`
- `MacroPayload`

`metadata` 可以存 debug 資訊或原始 payload，但 Signal 不應該主要依賴 metadata。

## 數據源抽象的迭代策略

數據源抽象不要一次設計到非常完整。標準做法是小步迭代：

```text
Raw source -> Minimal provider -> Observation contract -> Signal usage -> Contract refinement
```

每次新增資料源時，先用最小可用模型接起來，再根據 Quant 實際需要擴充 payload 或 query API。

### 第 1 階段：先統一可見性

第一優先順序是讓每筆資料都有：

- `observed_at`
- `occurred_at`
- `source`
- `kind`
- `symbol`
- typed `payload`

即使 payload 初期很小，也要先把時間語意做對。

### 第 2 階段：整理查詢需求

先觀察 Quant 需要怎麼查資料：

- 取某 subject 最新值。
- 取某時間窗內所有 observations。
- 取某些 kinds。
- 取某些 subjects。
- 判斷資料是否 stale。

只有當這些需求反覆出現，才把 helper method 加進 provider 或 query layer。

### 第 3 階段：擴充 payload

當多個 signals 都需要同一個欄位時，才把欄位提升到 typed payload。

例如：

- `PricePayload` 從 `last` 擴充到 `bid` / `ask` / `volume`。
- `CandlePayload` 加上 source-specific granularity 或 candle close status。
- `MessagePayload` 加上 `symbols`、`language`、`message_id`。
- `MacroPayload` 加上 `forecast`、`previous`、`revision`。

不要為了單一實驗，把太多來源特定欄位放進核心 payload。

### 第 4 階段：處理品質與延遲

當資料源開始被 strategy 依賴後，必須補上：

- duplicate handling
- stale data policy
- missing data policy
- late arrival policy
- reconnect policy
- rate limit policy
- source health metadata

這些規則應該在 provider 或 ingestion layer 處理，不要丟給每個 Signal 自己猜。

### 第 5 階段：抽出共用基礎設施

只有當兩個以上 provider 有重複需求時，才抽出共用元件，例如：

- observation store
- replay provider
- websocket base class
- source health tracker
- symbol normalizer
- deduplication helper

不要在第一版就建立太多 base class。

## 新增資料源標準流程

每次新增一個 data source，都按照以下流程。

### 1. Source Survey

先回答：

- 資料來源是 pull、push、file 還是 stream？
- 來源資料的時間欄位是什麼？
- 該時間是事件發生時間，還是 API 回傳時間？
- 系統實際收到資料的時間要怎麼記錄？
- 有沒有 revision、刪除、編輯或 late arrival？
- 有沒有 rate limit 或 reconnect requirement？

輸出：一段簡短 source note。

### 2. Subject and Kind Mapping

定義：

- `source`
- `kind`
- `symbol`
- payload type

範例：

```text
Coinbase trade
source: coinbase
kind: PRICE or TRADE
symbol: BTC-USDT
payload: PricePayload or TradePayload

Coinbase one-minute candle
source: coinbase
kind: CANDLE
symbol: BTC-USD
payload: CandlePayload

Telegram channel
source: telegram
kind: MESSAGE
symbol: telegram:channel_name
payload: MessagePayload

US CPI
source: macro_api
kind: MACRO
symbol: macro:US_CPI
payload: MacroPayload
```

### 3. Payload Decision

判斷是否能使用既有 payload。

如果不能，先問：

- 這是新的資料類型，還是既有 payload 少欄位？
- 這個欄位會被多個 signals 使用嗎？
- 欄位語意是否跨來源穩定？

只有答案清楚時才新增 payload class。

### 4. Minimal Provider

先實作最小 provider：

- 可以讀資料。
- 可以轉成 observations。
- 可以 `get_latest()`。
- 可以 `get_observations()`。
- 對壞資料安全跳過或明確報錯。

第一版不需要把所有來源 API 功能包完。

### 5. Visibility Test

至少驗證：

- `observed_at` 正確。
- `occurred_at` 正確。
- 用 `end=t` 查詢時，不會拿到 `observed_at > t` 的資料。
- 同一份資料重跑時，結果 deterministic。

### 6. Signal Integration

寫一個最小範例，證明 Quant 可以只依賴 observations。

範例形式：

```text
provider -> observations -> signal.generate(observations)
```

Signal 不應該讀 raw API response。

### 7. Contract Review

完成後檢查：

- 是否新增了不必要的抽象？
- 是否把來源特定欄位放進核心模型？
- 是否有讓 Quant 依賴 metadata？
- 是否有隱含 lookahead bias？
- 是否需要更新文件？

### 8. Research Data Integrity Review

Quant 交付 research report 前或交付後，DataProvider Developer 必須 review 報告使用的資料是否可信。這個 review 的目標不是評價策略好壞，而是確認資料沒有讓研究結果失真。

Data integrity review 至少回答：

```text
資料是否 point-in-time？
observed_at 是否代表系統可見時間？
occurred_at 與 observed_at 是否被正確區分？
candle close 是否只在 bar 結束後才可見？
資料是否有 missing / duplicate / outlier？
資料來源是否可能重寫歷史？
```

檢查項目：

- data scope：source、symbol、time range、granularity、row count 是否和 report 一致。
- timestamp semantics：`observed_at` / `occurred_at` 是否正確，timezone 是否一致。
- completeness：是否有 missing candles、重複 candles、時間排序錯誤。
- payload correctness：OHLCV 欄位是否合理，例如 high/low 是否包住 open/close。
- revision policy：來源是否會修正歷史資料，若會，report 是否標記。
- visibility rule：historical replay 是否保證不回傳 `observed_at > current_time`。
- raw dependency：Quant 是否繞過 typed payload 直接依賴 raw metadata。

若 data integrity review 未通過，Quant report 只能標記為 `Research Only` 或 `Invalid`，不得進入 Trader production review。

## Provider 驗收清單

一個 provider 可以被視為可用，至少要滿足：

- [ ] 有穩定 `source` 名稱。
- [ ] 所有輸出都是 `Observation`。
- [ ] 每筆 observation 有 `observed_at`。
- [ ] 每筆 observation 有 `occurred_at`。
- [ ] 每筆 observation 有穩定 `symbol`。
- [ ] payload 是 typed model。
- [ ] 壞資料不會讓整個 provider 崩潰，或會給出明確錯誤。
- [ ] `get_latest()` 行為明確。
- [ ] `get_observations(start, end)` 不會回傳時間窗外資料。
- [ ] 有最小 example 或 smoke test。
- [ ] 若被 research report 使用，已完成 data integrity review。

## 什麼時候要改核心抽象

不要因為單一 provider 特殊，就立刻改核心抽象。

只有以下情況才考慮改 `Observation` 或 `DataProvider`：

- 兩個以上資料源需要同一個新概念。
- 多個 signals 重複寫同一段資料解讀邏輯。
- 現有模型會造成 lookahead bias。
- 現有 query API 讓常見需求很難安全表達。
- typed payload 已經無法描述穩定跨來源語意。

## 近期迭代路線

建議按這個順序迭代：

1. 穩定 `Observation` 欄位命名，確認 `symbol` 是否要改名為 `subject`。
2. 讓 `JsonLinesTradeProvider` 補上 fixture-based 測試。
3. 新增 `MessagePayload` 的 Telegram provider prototype。
4. 新增一個簡單 observation replay provider，支援回測按 `observed_at` 重播。
5. 觀察 Quant 使用方式，再決定是否加入 query helper，例如 `latest_by_kind()` 或 `window()`.
6. 若多個 provider 都需要，才抽出 common ingestion utilities。

## 設計取捨

這個抽象刻意不把 provider 分成 `MarketDataProvider`、`MessageProvider`、`MacroProvider`。

理由是：策略真正關心的是同一時間點可見的資訊集合，不是資料來源類別。

但為了避免所有資料都變成無結構 dict，payload 必須保持 typed：

```text
Observation[PricePayload]
Observation[CandlePayload]
Observation[MessagePayload]
Observation[MacroPayload]
```

這樣可以同時保留：

- 統一時間軸
- point-in-time visibility
- 跨來源資料整合
- payload 型別約束
- 後續擴充彈性

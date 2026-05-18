# Quant

Quant 負責把 point-in-time observations 轉成可交易、可驗證、可解釋的 `SignalEvent`。

本角色的核心不是「寫一個指標」而已，而是把 research hypothesis 變成穩定的 signal contract，讓 Trader 可以在不理解研究細節的情況下使用訊號。

## 目標

Quant 的主要目標：

- 從 observations 中提取可交易訊號。
- 主責產出策略研究報告與 benchmark 報告。
- 避免 lookahead bias。
- 讓 signal 可以同時跑 research、backtest、paper trading、live trading。
- 產生 Trader 可理解的 `SignalEvent`。
- 把研究邏輯留在 `signals/`，不要滲透到 strategy 或 execution。

目前核心資料流：

```text
Observation -> Signal -> SignalEvent -> Strategy
```

## 核心抽象

目前 `Signal` 抽象是：

```python
class Signal:
    name: str

    def warmup(self, provider): ...
    def generate(self, observations): ...
```

`Signal` 的輸出應該是：

```python
SignalEvent(
    symbol=...,       # 訊號作用標的
    direction=...,    # long / short / flat
    strength=...,     # 0 到 1，代表訊號強度
    confidence=...,   # 0 到 1，代表信心
    reason=...,       # 穩定、可追蹤的原因代碼
    timestamp=...,    # 訊號生成所依賴資料的可見時間
    metadata=...,
)
```

如果資料不足、資料過期、條件不成立，`generate()` 應該回傳 `None`，而不是勉強產生弱訊號。

## SignalEvent 設計原則

### `symbol`

`symbol` 是 Trader 會看到的主要交易標的或策略標的。

範例：

- `BTC-USDT`
- `ETH-USDT`
- `TRIANGLE:BTC-USDT,ETH-BTC,ETH-USDT`
- `MACRO:US_CPI`

如果 signal 不是單一交易對，命名要清楚且穩定。

### `direction`

`direction` 只能表達方向，不表達倉位大小。

- `LONG`: 偏多
- `SHORT`: 偏空
- `FLAT`: 無方向或退出方向

Position sizing 屬於 Trader，不屬於 Quant。

### `strength`

`strength` 是訊號強度，範圍固定在 `0 <= strength <= 1`。

建議語意：

- `0.0`: 沒有強度
- `0.5`: 達到可交易門檻
- `1.0`: 極強訊號

`strength` 應該和 signal 自己的機會大小或異常程度有關，例如 spread、z-score、sentiment score、surprise magnitude。

### `confidence`

`confidence` 是 Quant 對訊號品質的信心，範圍固定在 `0 <= confidence <= 1`。

它可以反映：

- 資料完整度
- 資料新鮮度
- 樣本量
- source reliability
- 訊號歷史穩定性

不要把 `confidence` 和 `strength` 混成同一件事。高強度不一定高信心。

### `reason`

`reason` 是穩定代碼，給 Trader、logs、backtest attribution 使用。

範例：

- `triangular_arbitrage_net_profit`
- `telegram_listing_keyword`
- `macro_cpi_positive_surprise`
- `mean_reversion_zscore`

不要把長篇自然語言放在 `reason`。詳細解釋放在 `metadata`。

### `timestamp`

`timestamp` 應該代表 signal 所依賴 observations 的可見時間。

通常使用：

```python
max(observation.observed_at for observation in used_observations)
```

不要只用 `occurred_at`，避免回測看見尚未到達系統的資料。

### `metadata`

`metadata` 用來解釋 signal，不應該成為 Trader 必須硬解析的主要合約。

可以放：

- 使用了哪些 observations
- 原始計算值
- threshold
- stale data 狀態
- source reliability
- debug 資訊

如果 Trader 必須長期依賴某個 metadata 欄位，應該考慮把它提升成正式模型欄位或 strategy config。

## Signal 抽象的迭代策略

Signal 抽象不要一開始做太複雜。標準做法是：

```text
Hypothesis -> Observation Requirements -> Minimal Signal -> Backtest/Smoke Test -> Contract Refinement
```

每個 signal 都應該先證明它能穩定地把 observations 轉成 `SignalEvent`，再談更複雜的組合、參數掃描或 portfolio integration。

### 第 1 階段：定義假說

先用一句話寫清楚：

```text
當 X 被系統看見時，Y 在 Z 時間範圍內有可交易偏移。
```

範例：

```text
當三角匯率扣除手續費後仍有正 spread 時，應該產生套利訊號。
```

```text
當可信 Telegram 公告出現 listing 關鍵字時，相關代幣短時間內可能有上漲動能。
```

如果假說不能用 observations 表達，先不要寫 Signal。

### 第 2 階段：定義 observation requirements

明確列出 signal 需要哪些資料：

- 需要哪些 `kind`
- 需要哪些 `symbol`
- 需要多長的 lookback window
- 允許資料多舊
- 缺一個 observation 時要不要放棄
- 是否需要 `warmup()`

範例：

```text
TriangularArbitrageSignal
required kinds: PRICE
required symbols: BTC-USDT, ETH-BTC, ETH-USDT
stale tolerance: 1 second
warmup: no
```

### 第 3 階段：最小 Signal

先實作最小可用版本：

- 能接受 `list[Observation]` 或 `dict[str, Observation]`。
- 能過濾自己需要的 observations。
- 資料不足時回傳 `None`。
- 條件成立時回傳 `SignalEvent`。
- metadata 足夠解釋計算結果。

第一版不要同時塞進：

- complex risk rules
- order sizing
- portfolio constraints
- execution assumptions

這些屬於 Trader 或 Execution。

### 第 4 階段：smoke test

每個 signal 至少要有一個不依賴外部資料源的 smoke test 或 example。

目標是確認：

- 正常資料會產生預期 signal。
- 缺資料會回傳 `None`。
- threshold 不達標會回傳 `None`。
- timestamp 使用 `observed_at`。
- metadata 能解釋 signal。

### 第 5 階段：回測與樣本外檢查

Signal 進入策略前，至少要檢查：

- 是否有 lookahead bias。
- 是否只在特定樣本有效。
- threshold 是否過度擬合。
- strength 是否和未來報酬有合理排序關係。
- confidence 是否真的反映資料品質或穩定性。

這些檢查可以先用簡單 script 做，不需要一開始就建立完整 research platform。

回測結果的定位要講清楚：

```text
單次 backtest 可以用來理解策略性格與排除明顯錯誤，
不能直接當成可上線參數證明。
```

任何策略研究都必須區分：

- research value：理解 signal 是否有方向性、在哪些 regime 有用、是否有明顯 bias。
- trading decision value：是否足以支持實盤配置。這需要更嚴格的樣本外、風險與 execution 檢查。

如果只在同一段資料上調參並回報最佳結果，該研究不合格。

### 第 5.0 階段：完整 Quant Research Report

之後 Quant 做策略研究時，必須產出完整研究與 benchmark 報告，不只是一組回測數字。

Quant 是研究報告主責人。Quant 需要回答：

```text
這個 signal / strategy 是否有研究價值？
在哪些 regime 有用？
是否過擬合？
相對 benchmark 有沒有改善？
是否值得交給 Trader 做交易可行性評估？
```

最低要求：

- research hypothesis：一句話說清楚策略假說。
- data scope：資料來源、商品、時間範圍、bar granularity、資料筆數。
- execution assumptions：signal price、fill price、equity price、fee、slippage、spread、是否允許 short。
- parameter search space：列出測過哪些參數，不只列最佳參數。
- train/test validation：說明切分方式，並回報 train 與 test 結果。
- walk-forward validation：用多段滾動 train/test 檢查穩定性。
- benchmark comparison：至少比較 cash、buy-and-hold、固定曝險、同等 notional 或 volatility-adjusted benchmark。
- regime attribution：牛市、熊市、震盪市分別看 return、drawdown、exposure、trades。
- monthly/period return table：用月或固定期間列出策略與 benchmark 報酬。
- parameter stability map：不要只看最佳點，要看附近參數是否也有效。
- cost sensitivity：至少測 fee / slippage 變動後結果是否崩壞。
- failure modes：明確列出策略在哪些環境會失效。
- conclusion：區分「研究參考價值」與「交易決策價值」。

報告中必須包含負面結論。若策略只在單一 regime 有效，必須明講，不能用總報酬掩蓋。

### 第 5.0.1 階段：Train/Test 正確性

Train/test validation 不能重置不該重置的狀態。

錯誤做法：

```text
train: 從零開始跑策略並挑參數
test: 重新建立策略，從 test 起點才開始累積 SMA / volatility / z-score
```

這會讓 test 缺少真實部署時已經存在的 rolling state，也可能讓前段 test 因 warmup 不交易而失真。

正確做法：

```text
1. train 區間用來挑參數。
2. 用選定參數從 train 起點連續 replay 到 test 結束。
3. 只從 split time 之後開始計算 out-of-sample return / drawdown / trades。
4. rolling window、position、pending orders、portfolio state 都自然延續。
```

對 SMA、RSI、volatility、z-score、regression hedge ratio 這類需要歷史狀態的 signal，這點是強制要求。

Train/test 結果也必須附上 underlying benchmark 的 train/test 表現。若 train 本身是大牛市、test 是熊市，必須明確標記為 regime mismatch，不可直接解讀為參數穩定或失效。

### 第 5.0.2 階段：Walk-Forward Validation

單次 70/30 split 不夠。Quant 應該優先做 walk-forward：

```text
train window: 6-18 months
test window: 1-6 months
step: 1-3 months
```

每一段都要：

- 在 train window 內挑參數。
- 用 continuous state 跑到 test window。
- 只統計 test window 的 out-of-sample 表現。
- 記錄被選中的參數是否穩定。

報告至少列：

- 每段 train/test 時間。
- 每段選中的參數。
- 每段 test return、max drawdown、trade count、exposure。
- 全部 test segments 的 compounded return、平均 return、最差 return、勝率。

若不同 walk-forward segment 選到的參數差異很大，或 test 表現高度依賴少數 segment，策略不得被視為穩定。

### 第 5.0.3 階段：Benchmark 報告

任何 directional strategy 都至少要和以下 benchmark 比較：

- cash：完全不交易。
- buy-and-hold：從起點持有標的到終點。
- fixed exposure：例如固定 50% BTC / 50% cash。
- strategy notional benchmark：與策略平均曝險接近的 benchmark。

如果策略總報酬輸給 buy-and-hold，但 max drawdown 明顯較低，報告應該把策略定位為 defensive / exposure control，而不是 alpha strategy。

Benchmark 報告至少包含：

- total return
- max drawdown
- monthly returns
- exposure
- trades / turnover
- fees
- return per max drawdown

### 第 5.0.4 階段：Regime Attribution

Quant 必須拆解策略在不同市場狀態下的效果。

可以先用簡單、可重現的 regime 定義：

```text
close >= long_term_sma -> bull
close < long_term_sma -> bear
```

或用 rolling return / volatility 定義：

```text
positive trend + low volatility
positive trend + high volatility
negative trend + low volatility
negative trend + high volatility
```

每個 regime 至少報：

- days / bars
- strategy return
- benchmark return
- max drawdown
- exposure
- trade count
- fees

若策略只在熊市靠降低 exposure 有效，必須明確說明。若牛市大幅落後 buy-and-hold，也必須明確說明。

### 第 5.0.5 階段：參數穩定性

不要只報最佳參數。

Quant 必須檢查：

- 最佳參數附近是否也有類似結果。
- Top N 參數是否集中在同一個合理區域。
- 參數稍微改變後 test 是否崩壞。
- train return 排名前幾名在 test 是否一致有效。

若只有單一孤立參數有效，應視為 overfitting warning。

### 第 5.0.6 階段：回測結論分級

Quant 報告最後必須給研究結論分級：

- Reject：沒有穩定樣本外效果，或 benchmark 更好且風險沒有改善。
- Research Only：有研究參考價值，但不足以支持交易。
- Paper Trade Candidate：樣本外與風險檢查合理，但仍需 paper trading。
- Production Candidate：walk-forward、benchmark、成本敏感度、風控與 paper trading 均通過。

大多數單一策略第一次研究應該停在 `Research Only` 或 `Paper Trade Candidate`，不得因單次回測漂亮就升級。

### 第 5.0.7 階段：Senior Quant Report 要求

若研究目標是支援資金配置、paper trading 或 production review，Quant report 必須升級到 senior quant 標準。這不是每個 prototype 都必須完成，但任何要被 Trader 嚴肅評估的策略都應該包含。

必備項目：

- advanced performance metrics：CAGR、annualized volatility、Sharpe、Sortino、Calmar、skew、kurtosis、VaR、CVaR、best/worst day、best/worst month。
- drawdown analysis：max drawdown、average drawdown、drawdown duration、recovery time、rolling drawdown。
- trade-level attribution：win rate、average win/loss、median PnL、profit factor、payoff ratio、holding period、MAE/MFE、PnL by entry/exit reason。
- exposure-adjusted benchmark：與策略平均 exposure 相同的 benchmark、固定曝險 benchmark、volatility-targeted benchmark。
- statistical significance：bootstrap confidence interval、t-stat、probabilistic/deflated Sharpe、multiple testing adjustment。第一版至少要明確標記哪些尚未完成。
- parameter robustness：fast x slow heatmap、return/Sharpe/MDD/test return neighborhood stability，不只列 top N。
- multi-window walk-forward：至少測多組 train/test window，例如 6M/1M、12M/3M、18M/3M、24M/6M。
- fine-grained regime attribution：trend up/down、high/low volatility、sideways/choppy、crisis periods。
- cost and execution stress：fee、slippage、spread、latency、partial fill、volume cap、market impact sensitivity。
- data quality audit：missing bars、duplicates、zero volume、OHLC consistency、outliers、timezone、source revision risk。
- sizing sensitivity：fixed notional、equity percentage、volatility targeting、drawdown-based de-risking、max exposure cap。
- portfolio context：correlation、marginal Sharpe、marginal drawdown、capital efficiency、capacity、overlap with existing exposure。
- live readiness：expected trade frequency、expected exposure range、signal drift、data freshness alerts、kill switch、paper trading pass/fail criteria。

Senior report 必須明確分三類：

```text
completed: 本次已完成且可引用的檢查
partial: 有初步結果但不足以下結論
not done: 尚未完成，不可假裝已驗證
```

若 advanced metrics、cost sensitivity、parameter robustness、multi-window walk-forward、trade attribution 任一項缺失，策略最多只能是 `Research Only`，不得升級為 `Production Candidate`。

### 第 5.1 階段：Backtest Signal Replay

在正式交給 Trader 前，Quant 應該先讓 signal 通過 historical replay。

回測中的 signal 流程：

```text
ReplayDataProvider
-> visible observations at current_time
-> signal.generate(visible_observations)
-> SignalEvent or None
```

Quant 在這個階段只負責 signal，不負責下單與 portfolio。

驗收重點：

- signal 只使用 `observed_at <= current_time` 的 observations。
- `SignalEvent.timestamp <= current_time`。
- 資料不足時回傳 `None`。
- stale data 時回傳 `None` 或降低 confidence。
- signal metadata 能追到使用了哪些 observations。
- 同一份 historical observations 重跑時，signal events deterministic。

對 candle 類資料要特別小心：如果 signal 使用 candle close，該 close 應該在 candle bucket 結束後才可見。

### 第 6 階段：Contract Review

完成後檢查：

- `reason` 是否穩定。
- `strength` 是否在 0 到 1。
- `confidence` 是否在 0 到 1。
- `timestamp` 是否來自 `observed_at`。
- Trader 是否需要解析太多 metadata。
- 是否把 position sizing 或風控塞進 signal。
- 是否需要 DataProvider 擴充 payload，而不是在 signal 裡解析 raw metadata。

## 新增 Signal 標準流程

每次新增一個 signal，都按照以下流程。

### 1. Research Note

先寫清楚：

- 假說是什麼？
- 預期作用標的是什麼？
- 需要哪些 observations？
- 預期持有或反應時間大概多長？
- 可能失效的條件是什麼？

輸出：一段簡短 research note。

### 2. Input Contract

定義 signal 的輸入要求：

- required `ObservationKind`
- required subjects
- required payload fields
- lookback window
- stale tolerance
- warmup requirement

如果需要的 payload 欄位不存在，先和 DataProvider Developer 討論，不要直接依賴 raw metadata。

### 3. Minimal Implementation

在 `signals/` 新增 signal。

要求：

- `name` 穩定。
- `generate()` 無副作用，或副作用明確。
- 資料不足安全回傳 `None`。
- 輸出 `SignalEvent`。
- 計算細節放進 metadata。

### 4. Calibration

決定：

- signal threshold
- strength scaling
- confidence scoring
- stale data handling
- missing data handling

先用簡單、可解釋的 scaling，不要過早使用複雜模型。

### 5. Validation

至少驗證：

- smoke example
- missing data case
- no-signal case
- timestamp correctness
- basic backtest or historical replay
- signal events deterministic under replay
- no signal uses observations after current_time

### 6. Handoff to Trader

交給 Trader 前，提供：

- signal name
- reason codes
- expected direction semantics
- strength interpretation
- confidence interpretation
- metadata schema
- known failure modes

Trader 應該根據這些資訊決定是否交易、交易多少、如何風控。

## `warmup()` 使用準則

`warmup()` 用於 signal 在正式產生訊號前建立內部狀態。

適合使用 `warmup()` 的情況：

- moving average
- RSI
- volatility estimate
- z-score baseline
- regression hedge ratio
- historical sentiment baseline
- source reliability statistics

不需要 `warmup()` 的情況：

- 單次事件判斷
- 最新價格套利
- 單則消息 keyword detection

`warmup()` 應該只讀 DataProvider，不應該產生交易訊號。

## Signal 驗收清單

一個 signal 可以被視為可用，至少要滿足：

- [ ] 有穩定 `name`。
- [ ] 有清楚 research hypothesis。
- [ ] 明確列出 required observations。
- [ ] 資料不足時回傳 `None`。
- [ ] 不直接讀 raw API response。
- [ ] 不依賴 metadata 作為主要輸入，除非已明確標記為暫時方案。
- [ ] 不做 position sizing。
- [ ] 不送出訂單。
- [ ] `SignalEvent.reason` 穩定。
- [ ] `strength` 在 0 到 1。
- [ ] `confidence` 在 0 到 1。
- [ ] `timestamp` 使用可見時間。
- [ ] 有 smoke example 或測試。
- [ ] 通過 historical replay 檢查。
- [ ] 回測中不使用 `observed_at` 晚於 current_time 的資料。

## 什麼時候要改 Signal 抽象

不要因為單一 signal 特殊，就立刻改 `Signal` 或 `SignalEvent`。

只有以下情況才考慮改核心抽象：

- 兩個以上 signals 都需要同一個新輸出欄位。
- Trader 長期需要解析同一個 metadata 欄位。
- `strength` / `confidence` 無法表達常見訊號語意。
- 多個 signals 都需要共同的 stale data 或 lookback helper。
- `generate()` 無法安全支援 stateful signal。

## 近期迭代路線

建議按這個順序迭代：

1. 為 `TriangularArbitrageSignal` 補上 stale tolerance。
2. 為每個 signal 建立 smoke example。
3. 建立共用 observation filtering helper，例如 latest price by subject。
4. 新增 message-based signal prototype，例如 Telegram keyword signal。
5. 明確定義 `strength` 與 `confidence` 的團隊約定。
6. 當兩個以上 signals 需要歷史窗口時，再抽出 rolling window 或 signal state helper。
7. 建立 SignalReplay smoke test，確認 signal 在 historical observations 上 deterministic。

## 設計取捨

Signal 應該專注於「研究判斷」，不是交易執行。

這表示：

- Signal 可以說方向。
- Signal 可以說強度。
- Signal 可以說信心。
- Signal 可以說原因。
- Signal 不應該說買多少。
- Signal 不應該決定最大曝險。
- Signal 不應該處理下單重試。

這樣 Trader 可以自由組合多個 signals，也可以在風控狀態改變時調整交易，而不用修改 Quant 的研究邏輯。

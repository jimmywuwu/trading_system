# Trading System 設計文檔（v2 重構）

> 本文件是整個系統的最高層設計依據。其他文件（`BACKTEST.md`、`ROLES.md`、
> `docs/quant_research_workflow.md`）是它的展開；衝突時以本文件為準。
> 日期：2026-07-07。

## 0. 一句話定位

這不是一個「交易機器人」，而是一個**可長期迭代的研究工廠**：
把市場資料變成 point-in-time 可重播的觀測，把想法變成可證偽的假說，
把假說變成有基準對照、有成本假設、有失效條件的訊號，
最後才把極少數存活者變成受風控約束的交易。

長期營利不是來自某一個聰明的策略，而是來自：

1. **研究流程的紀律**——爛想法死得快、好想法留下證據。
2. **回測不自欺**——沒有前視偏差、成本誠實、基準對照。
3. **風控永遠有否決權**——任何策略都能被一鍵停掉。
4. **負面結果也是資產**——被否決的研究有 DecisionRecord，不會借屍還魂。

## 1. 重構前診斷

v1 的設計文件品質很高，但程式碼沒有跟上文件：

| 問題 | 具體表現 | v2 處置 |
| --- | --- | --- |
| 回測引擎只存在於文件 | `BACKTEST.md` 描述完整，但實作散落在 `examples/backtest_sma_strategy.py`，每個研究腳本各自複製一份 loop | 新增 `backtest/` 正式套件：engine / replay / execution / portfolio / metrics，含測試 |
| 策略違反自己的角色分工 | `strategies/*` 五個策略全部在內部算指標（Quant 的工作）又做 sizing（Trader 的工作），`signals/` 幾乎是空的 | 建立標準垂直切片：`signals/sma_cross.py`（算指標、發 SignalEvent）+ `strategies/signal_position_strategy.py`（只做 sizing 與風控）。舊策略標記 legacy，僅供對照 |
| 假的多代理研究 | `agents/runtime.py`（1900 行）用寫死的模板「模擬」Quant/Trader 的產出，跑固定參數家族然後寫報告——這是自動化的過擬合，不是研究 | **棄用**。多代理協作改由 Claude Code skills + 磁碟上的 artifacts 承載：判斷交給真的 agent，計算交給確定性的程式庫 |
| 沒有 lookahead 防線的強制執行 | 文件說「只能用 observed_at <= current_time」，但沒有任何程式碼會在違反時報錯 | `ReplayDataProvider` 內建 guard：查詢未來資料直接丟 `LookaheadError`；engine 檢查 signal timestamp 不得晚於 replay 時間 |
| 研究產出散落 | `reports/`、`.agents/`、root 目錄混雜正式報告、草稿、個人檔案 | 定義目錄契約（見 §6）；新報告一律走 `reports/` 子目錄 + DecisionRecord |

## 2. 設計理念（不可妥協的原則）

1. **Point-in-time 高於一切。** 所有資料先變成 `Observation`，可見性只看
   `observed_at`。任何組件想讀未來資料，系統要報錯而不是默默給。
2. **單向資料流。**

   ```text
   DataProvider -> Observation -> Signal -> SignalEvent
       -> Strategy -> OrderIntent -> Execution -> Fill -> Portfolio
   ```

   每一層只消費上一層的輸出。Signal 不碰 portfolio，Strategy 不算指標，
   Execution 不做決策，Portfolio 只被 Fill 驅動。
3. **回測、paper、live 走同一條程式路徑。** 只換 provider 和 broker，
   不換 signal/strategy 程式碼。做不到這點的策略不准上線。
4. **成本是一等公民。** 沒有 fee/slippage 的回測數字不允許出現在結論裡；
   每個結果旁邊必須有 buy-and-hold 基準。
5. **確定性。** 相同輸入必須產生相同輸出。隨機性（如 bootstrap）必須帶 seed。
6. **程式做計算，agent 做判斷。** 不要把「研究判斷」寫死在 Python 裡
   （這是 v1 `agents/runtime.py` 的死因）。程式庫提供可靠的原語
   （replay、event study、benchmark、walk-forward），skill 定義流程與 gate，
   agent 負責思考與撰寫結論。
7. **可解釋性鏈條。** 每筆 trade 可追到 order reason，order 可追到 signal
   reason，signal 可追到 observations。斷鏈的結果不可信。

## 3. 目標架構

```text
┌────────────────────────────────────────────────────────────┐
│ 研究層（agent + skill 驅動，產出 artifacts）                  │
│   idea -> mechanism -> hypothesis -> contract -> report      │
│   （/research-idea /new-signal /run-backtest /promote）      │
├────────────────────────────────────────────────────────────┤
│ 程式庫層（確定性、有測試）                                    │
│   core/       契約：Observation, Signal, Strategy, Order     │
│   providers/  資料接入，統一轉 Observation                    │
│   signals/    Quant 訊號（指標邏輯只准在這裡）                 │
│   strategies/ Trader 決策（sizing/風控只准在這裡）             │
│   backtest/   replay + engine + execution + portfolio        │
│   research/   event study, benchmarks（之後：walk-forward）   │
│   execution/  paper / live broker adapters                   │
├────────────────────────────────────────────────────────────┤
│ 資料層                                                       │
│   data/       Observation JSONL fixtures（不進 git）          │
│   reports/    正式研究報告 + DecisionRecord                   │
└────────────────────────────────────────────────────────────┘
```

### 3.1 core/ —— 契約（保留 v1，這部分是對的）

- `Observation(observed_at, occurred_at, symbol, source, kind, payload, metadata)`
- typed payloads：`CandlePayload`、`PricePayload`、`FundingRatePayload`、
  `OpenInterestPayload`、`BasisPayload`、`MessagePayload`、`MacroPayload`
- `SignalEvent(symbol, direction, strength∈[0,1], confidence∈[0,1], reason, timestamp, metadata)`
- `OrderIntent(symbol, side, order_type, quantity, reason, price?, metadata)`
- 抽象類：`DataProvider`、`Signal`、`Strategy`

契約變更需要同時更新本文件與所有 skill，視同 breaking change。

### 3.2 backtest/ —— 回測引擎（v2 新增，系統的心臟）

- `ReplayDataProvider`：event-driven replay，依 `observed_at` 分組推進；
  replay 期間任何 `get_observations(end > current_time)` 丟 `LookaheadError`。
- `SimulatedExecution`：market order 用**下一個可見 candle open** 成交
  （絕不用產生訊號的那根 candle）；limit order 觸價（buy: low<=price，
  sell: high>=price）用限價成交；fee_rate + slippage_bps 可設定。
- `Portfolio`：cash / positions / avg_cost / realized PnL / fees /
  equity / exposure，只被 Fill 驅動；買入依現金截斷、賣出依部位截斷。
- `compute_metrics`：total return、max drawdown、annualized Sharpe
  （由 bar 間隔推算）、win rate、turnover、avg exposure、fees。
- `BacktestEngine.run()` 每個 tick 的順序（三種價格分離的具體化）：

  ```text
  1. 用新可見 observations 成交 pending orders（fill price = open）
  2. fills 進 portfolio
  3. observations 餵給 strategy.on_observation 與 signals.generate
     （signal price = close）
  4. signal events 餵給 strategy.on_signal；檢查 event.timestamp <= now
  5. strategy.decide() 產生的新 orders 進 pending queue（下個 tick 才可能成交）
  6. 用最新 close mark-to-market（equity price = close）
  ```

Signal 的執行模型：**stateful incremental**。engine 每個 tick 只把該 tick
新可見的 observations 傳入 `generate()`；需要歷史的 signal 自己維護 rolling
state（或用 `warmup()`）。這讓一年分鐘級回測維持 O(n)。

### 3.3 signals/ 與 strategies/ —— 標準分工

**Signal（Quant 擁有）**：消費 Observation，產出 SignalEvent。
必須：資料不足回傳 `None`、reason code 穩定、timestamp 用最後使用的
observation 的 `observed_at`、metadata 帶齊 debug 資訊。
禁止：碰 portfolio、算部位、發 OrderIntent。
範例：`signals/sma_cross.py`。

**Strategy（Trader 擁有）**：消費 SignalEvent + portfolio snapshot +
risk_state，產出 OrderIntent。
必須：`halted` 時回空單、尊重 `max_notional` / `allowed_symbols`、
order reason 串接 signal reason。
禁止：重算指標、解析原始資料。
範例：`strategies/signal_position_strategy.py`。

`strategies/` 下的舊策略（sma_crossover、bollinger、volatility_breakout、
candle_pattern、threshold）把兩層混在一起，**視為 legacy**：不要模仿、
不要基於它們做新研究；待現有引用清完後刪除。

### 3.4 research/ —— 研究原語

- `forward_return_study(events, observations, horizons)`：訊號後 forward
  return（進場 = 事件後第一根可交易 candle 的 open），這是「先確認訊號
  有沒有預測力」的第一站，比 portfolio 回測便宜且不易自欺。
- `buy_and_hold_metrics(...)`：同資料、同費率的基準。
- Roadmap（照 `docs/quant_research_workflow.md` phase 4）：walk-forward
  runner、parameter grid + 鄰域穩定性、cost sensitivity、regime attribution。
  **加新原語時必須帶測試。**

## 4. 研究流程與 Gates

完整版見 `docs/quant_research_workflow.md`（artifact 序列與 YAML 模板）。
操作入口是四個 skill：

```text
/research-idea   想法 -> MechanismNote -> Hypothesis（Gate 0-2）
/new-provider    資料源調查 -> Observation 映射 -> provider 實作 + 品質檢查
/new-signal      SignalContract -> 實作 -> 測試 -> smoke replay（Gate 5-7）
/run-backtest    event study -> 回測 -> benchmark -> 穩健性（Gate 8-11）
/new-strategy    Trader 翻譯：StrategyContract -> sizing/風控實作 -> 整合回測
                 （僅限評級 paper_trade_candidate 的訊號；promote Gate C/D 前置）
/promote-strategy 研究報告評級 -> review gates -> DecisionRecord（Gate 12-14）
```

硬性規則：

- 每個階段可以（且應該經常）以「否決」收場，否決必須寫 DecisionRecord。
- 結論評級只有四種：`reject` / `research_only` / `paper_trade_candidate` /
  `production_candidate`。沒有 out-of-sample + benchmark + cost sensitivity
  證據，最高只能給 `research_only`。
- 同一假說被否決後，沒有新證據不得重開（查 `reports/decisions/`）。

## 5. 通往實盤：paper → live

（目前尚未實作，列為 roadmap，順序不可跳）

1. **PaperBroker v2**：訂閱 live provider，用與回測相同的 fill 規則模擬成交，
   寫 fills JSONL；跑滿預定期間後比對 paper 結果 vs 回測預期（tracking error）。
2. **RiskManager**：從 dict 升級為組件——全域 kill switch、單策略
   max_notional、日內最大虧損、部位集中度。它站在 Strategy 與 Broker 之間，
   有最終否決權。
3. **LiveBroker**：交易所 adapter（最小下單量、費率 tier、rate limit、
   斷線重連）。上線前必過 `BACKTEST.md` 的 Execution/Fill Model Review。
4. **Monitoring**：equity/exposure/fee 即時記錄、訊號與成交的落差警報、
   rollback plan。沒有 rollback plan 的策略不准上 production。

## 6. 目錄契約

```text
core/ providers/ signals/ strategies/ backtest/ research/ execution/  # 程式庫（有測試）
scripts/          # 可執行入口（run_backtest.py 等），薄，不藏邏輯
tests/            # pytest；conftest.make_candles 是標準合成資料工廠
data/             # Observation JSONL（大檔，不進 git）
reports/
  backtests/      # /run-backtest 產出
  research/       # 研究報告（ResearchReport 格式）
  decisions/      # DecisionRecord（append-only）
docs/             # DESIGN.md（本文件）、quant_research_workflow.md、BACKTEST.md...
.claude/skills/   # 研究流程 skills
```

Legacy：v1 的模擬式多代理 runtime（`.agents/`、`MULTI_AGENT_RUNTIME.md`、
root 的角色檔與個人 persona 檔、`artifacts/`）已於 2026-07-11 移出 repo，
備份在 repo 外的 `trading_system_legacy_backup_20260711.tar.gz`。
`ROLES.md` 與 `BACKTEST.md` 因仍被 skills 與 `backtest/` 引用而保留。
`reports/notion_drafts/` 是 v1 時代的研究草稿，內容仍有參考價值，暫留。

## 7. 「長久營利」的現實檢查

系統設計保證的是**不自欺**，不保證有 alpha。alpha 要從市場結構來：

- 優先研究有**機制**的假說（誰被迫交易？誰慢？誰承擔庫存風險？），
  不要從指標排列組合出發——這正是 v1 sprint runner 的失敗模式。
- 這個 repo 已有的機制性方向（槓桿壓力、OI 收縮去槓桿、跨所 funding
  分歧、spot/perp leadership）比任何 SMA 變體更值得投入。
- 每個策略都要有**失效假設**：什麼市場結構改變會殺死它？寫進報告，
  live 之後定期檢查。
- 資金曲線的複利來自於活得久：倉位上限、回撤上限、kill switch
  比報酬率優化重要。

## 8. 驗收狀態（2026-07-07）

- `backtest/` + `research/` + 垂直切片：31 個測試全綠（`python3 -m pytest`）。
- 真實資料 end-to-end：`scripts/run_backtest.py` 在 Coinbase BTC-USD 一分 K
  上可跑，策略與基準同資料同費率對照輸出。
- Skills 就位：`.claude/skills/{research-idea,new-provider,new-signal,run-backtest,promote-strategy}`。

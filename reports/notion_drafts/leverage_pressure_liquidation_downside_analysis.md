# Leverage Pressure Liquidation Downside：研究分析筆記

<callout icon="🧭" color="blue_bg">
這份文檔把 Telegram 裡過長的一次性分析拆成可以在 Notion 裡逐段評論、學習與討論的版本。核心目標不是直接產生交易訊號，而是判斷：high funding + rising OI + weak spot confirmation 是否代表一種可重現的短期 leverage fragility regime。
</callout>

## Metadata

- created_at: 2026-05-28T20:41:12+08:00
- created_by: HERMES
- created_by_agent: JAQUAN
- related_research_idea: `idea_leverage_pressure_liquidation_downside_v1`
- related_mechanism_note: `mech_leverage_pressure_liquidation_downside_v1`
- related_hypothesis: `hyp_leverage_pressure_liquidation_downside_v1`
- status: draft_for_discussion

## 0. 一句話版本

這個研究題目不應該先被理解成：

> funding 高，所以做空。

更合理的理解是：

> 當 perp funding 升高、open interest 增加，但 spot demand 沒有同步確認時，市場可能進入一種槓桿多頭擁擠、流動性脆弱、容易出現 liquidation downside tail 的狀態。

所以第一階段研究目標應該是：

```text
這個狀態是否真的會改變未來 4h-24h 的 downside distribution？
```

而不是直接問：

```text
這是不是一個可以立刻做空賺錢的策略？
```

## 1. 我對這個 idea 的初始判斷

### 初始 prior

- mechanism plausibility: 中高
- standalone short alpha: 低到中
- downside-risk regime filter: 中到中高
- production readiness: 很低
- overfit risk: 高

### 簡短解釋

我比較相信它可能成為 **risk regime classifier**，但暫時不相信它可以直接成為 standalone short strategy。

原因是：

1. crypto 短期價格確實常被 leverage / liquidation / liquidity vacuum 主導。
2. 但是 funding 與 OI 都是公開資料，簡單 threshold 很容易 decay。
3. 做空需要承受 funding、fee、spread、slippage、squeeze、timing error。
4. 它最穩定的用途可能是降低多頭風險，而不是主動開空。

## 2. 市場機制：為什麼它可能成立？

這個 hypothesis 的合理性來自幾個互相強化的機制。

### 2.1 Perp funding elevated / rising

Funding 升高表示 perp long 願意付費維持槓桿 exposure。

這不一定 bearish。牛市裡 funding 可以長時間偏高。

但如果 funding 是快速升高，且同時出現其他壓力訊號，它可能代表：

- 槓桿多頭需求變強
- 持倉成本上升
- 市場越來越依賴槓桿買盤推動

### 2.2 Open interest rising

OI 增加表示市場裡未平倉合約增加。

如果 funding 升高但 OI 沒有增加，那可能只是現有倉位重新定價。

如果 funding 升高且 OI 增加，則更像是：

```text
new leveraged exposure entering the market
```

不過要小心：OI 增加不一定是 directional long crowded trade，也可能是 delta-neutral basis trade。

### 2.3 Weak spot confirmation

這是整個 idea 的關鍵。若 perp 上漲、funding 上升、OI 增加，但 spot return 或 spot volume 沒有跟上，可能代表：

```text
price support is leverage-led, not cash-led
```

也就是價格上漲比較依賴 perp leverage，而不是現貨長期資金買入。

這種狀態比較脆弱，因為一旦 price move against crowded longs，槓桿資金會被迫降倉。

### 2.4 Liquidity providers may step back

市場最需要 liquidity 的時候，liquidity providers 往往會撤退：

- spread 變寬
- displayed depth 下降
- adverse selection risk 上升
- inventory risk 上升

所以 forced selling 不只會遇到賣壓，也會遇到變薄的 orderbook。

這讓 downside move 呈現非線性。

### 2.5 Liquidation cascade

如果價格反向，槓桿多頭可能觸發：

- stop-loss sell
- margin reduction
- exchange liquidation
- reduce-only forced flow

這些 flow 的共同特徵是：

```text
forced traders cannot choose timing
```

他們不能等 liquidity 好一點再賣。這是 structural inefficiency 可能短暫存在的原因之一。

## 3. 正確的研究 framing

### 不好的 framing

```text
High funding means short.
```

問題：

- 沒有 horizon
- 沒有 mechanism
- 沒有 spot confirmation
- 沒有控制 bull regime
- 沒有區分 average return 與 tail risk
- 很容易 overfit

### 比較好的 framing

```text
When funding is elevated and rising,
open interest is expanding,
and spot demand fails to confirm the perp-led move,
future 4h-24h downside tail risk should increase
relative to unconditional periods and simpler controls.
```

這裡的研究目標不是漂亮 equity curve，而是檢查 distribution 是否改變。

## 4. 它最可能成為什麼？

### Primary candidate: downside-risk regime filter

用途可能是：

- 降低多頭 exposure
- 暫停新增 long
- 啟動 hedge review
- 提醒 Trader 市場進入 leverage fragility regime
- 作為其他 signal 的 confidence haircut

### Secondary candidate: conditional short signal

只有在更高 evidence 下才考慮：

- full condition 明顯打敗 controls
- cost sensitivity 後仍有效
- signal strength 能排序 downside risk
- train/test 或 walk-forward 穩定
- DataProvider review 確認 point-in-time data 可用

### Not yet: production strategy

現在離 production 很遠。這不是壞事。多數 alpha idea 一開始都應該離 production 很遠。

## 5. 需要驗證的核心問題

### 問題 1：flagged periods 的 downside quantile 是否更差？

比較 flagged vs unflagged：

- 4h forward return
- 8h forward return
- 12h forward return
- 24h forward return
- 5% quantile
- 10% quantile
- max adverse excursion
- downside skew

最重要的是 tail，不是 mean。

### 問題 2：full condition 是否打敗簡單 controls？

需要比較：

- unconditional
- high funding only
- rising OI only
- high funding + rising OI
- recent momentum
- realized volatility regime
- bull / bear / sideways regime

如果 full condition 不能打敗 high funding only 或 volatility control，那它就沒有太多獨立研究價值。

### 問題 3：signal strength 是否能排序 risk？

如果 leverage pressure score 越高，future downside tail 越差，這會比單一 threshold 更有說服力。

如果只有某一個 threshold 有效，而附近 threshold 都失效，這通常是 overfit。

### 問題 4：是否只在 bear regime 有效？

如果它只在明顯 bear market 裡有效，那它可能只是 bear-regime proxy。

這不一定完全沒用，但不能宣稱是 funding / OI 結構 alpha。

### 問題 5：資料是否能 point-in-time replay？

這是最容易出錯的地方。

需要確認：

- funding rate 的 observed_at 是什麼？
- OI snapshot 的 observed_at 是什麼？
- historical OI 是否 revised？
- candle close 何時對系統可見？
- liquidation prints 是否延遲或補發？
- entry price 是否真的在 signal_time 之後可交易？

## 6. 第一輪研究設計

### 6.1 Universe

先做：

- BTC-PERP / BTC-USD
- ETH-PERP / ETH-USD

原因：

- liquidity 好
- data quality 較高
- execution assumptions 較合理
- 不容易被小幣種 microstructure noise 騙

### 6.2 Required observations

最小需求：

- perp funding rate
- perp open interest
- perp mark/index price
- perp candles
- spot candles
- spot volume

可選：

- liquidation prints
- orderbook depth
- spread

### 6.3 Candidate trigger components

#### Funding pressure

```text
funding_zscore > threshold
or funding_percentile > threshold
and funding_change > 0
```

#### OI expansion

```text
oi_change_pct over lookback > threshold
```

#### Perp-led pressure

```text
perp_return > spot_return
or basis expansion > threshold
```

#### Weak spot confirmation

```text
spot_return weaker than perp
or spot_volume percentile not expanding
```

### 6.4 Composite score

可以先定義一個簡單 score：

```text
leverage_pressure_score =
  funding_pressure_score
+ oi_expansion_score
+ perp_lead_score
+ weak_spot_confirmation_score
```

第一輪不要追求最優參數。先看 score bucket 是否排序 future downside risk。

## 7. Benchmark 與 controls

Directional crypto research 至少要比較：

- cash
- buy-and-hold
- fixed exposure
- same average exposure
- volatility-adjusted exposure
- simple momentum baseline
- high funding only
- rising OI only

如果一個策略只是降低 exposure，所以 drawdown 小，這不等於 alpha。它可能只是 exposure control。

這不是壞事，但要誠實命名。

## 8. 主要 failure modes

### Failure mode 1：spot-led bull market

高 funding + rising OI 可能只是牛市裡強 demand 的自然結果。

這時 short signal 會被 squeeze。

### Failure mode 2：OI 是 hedged basis，不是 crowded longs

OI 增加可能來自 basis desks，不一定是 directional long。

### Failure mode 3：只是 volatility / momentum proxy

如果 signal 只是抓到 high volatility 或 bearish momentum，那它沒有獨立機制價值。

### Failure mode 4：資料時間語意錯誤

如果 historical data 不是 point-in-time，漂亮結果可能只是 lookahead。

### Failure mode 5：只有單一 crash episode 有效

如果結果主要來自一兩次大瀑布，那不能宣稱 robustness。

### Failure mode 6：成本吃掉效果

尤其 standalone short strategy 會被：

- fees
- spread
- slippage
- funding payments
- latency
- missed fills

嚴重影響。

## 9. 升級 / 降級條件

### 可升級到 Research Only 如果

- flagged periods downside quantiles consistently worse
- full condition beats high funding only / OI only
- BTC / ETH 至少一個穩定，最好兩個都有方向一致
- multiple horizons 有一致 tail-risk separation
- regime attribution 沒有完全依賴單一 crash
- no obvious point-in-time issue

### 可升級到 Paper Trade Candidate 如果

- train/test 或 walk-forward 穩定
- parameter neighborhood 穩定
- cost / slippage / latency stress 後仍有用途
- signal strength 能排序 risk
- DataProvider review 通過
- Trader 能定義清楚 paper trading pass/fail criteria

### 應該 Reject 如果

- full condition 不比 momentum / volatility controls 好
- 只在單一 threshold 有效
- 只在 obvious bear regime 有效
- OI / funding data 無法 point-in-time replay
- 成本後 standalone edge 消失
- signal frequency 太低或集中在一兩次歷史事件

## 10. 下一個 artifact 建議

根據目前 workflow，下一步不是寫 signal，也不是開始回測。

下一步應該是：

```text
ObservationRequirements
-> DataProviderHandoff
```

也就是先定義：

1. 需要哪些 observations？
2. 每個 observation 的 required fields 是什麼？
3. `observed_at` / `occurred_at` 如何定義？
4. missing / stale / late-arrival policy 是什麼？
5. historical data 是否能 replay？
6. DataProvider Developer 需要 review 哪些風險？

建議新增 artifact：

```text
artifacts/observation_requirements/obsreq_leverage_pressure_liquidation_downside_v1.yaml
artifacts/data_provider_handoffs/dph_leverage_pressure_liquidation_downside_v1.yaml
```

## 11. 給人類討論用的問題

你可以直接在 Notion 上針對這些問題留言：

1. 你比較想把它當作 risk filter，還是 conditional short signal？
2. 對 BTC / ETH 之外的 long-tail coins，要不要延後？
3. weak spot confirmation 你直覺上比較相信 return divergence 還是 volume divergence？
4. liquidation prints 要不要第一輪就納入，還是先當 optional evidence？
5. 如果它只降低 drawdown、但不能提升 return，你會覺得有價值嗎？
6. paper trading 時，你希望它輸出 warning、risk haircut，還是 actual directional signal？

## 12. Jaquan 的暫定結論

這個 idea 值得研究，因為它碰到 crypto 短期市場裡真正重要的東西：

```text
leverage + liquidity + forced flow
```

但它不應該被快速包裝成策略。

我會先把它當成 **leverage fragility regime hypothesis**，並用 event study 驗證它是否真的改變 future downside tail。

如果 tail-risk separation 不存在，就 reject。

如果存在但無法交易，就保留為 risk filter 或 research-only observation。

如果它在 data review、robustness、cost sensitivity 後仍成立，再交給 Trader 評估 paper trading。

<callout icon="🧪" color="gray_bg">
短版：先證明市場狀態真的不同，再討論能不能交易。不要拿漂亮 equity curve 倒推市場真理；那通常只是 backtest 在跟我們講冷笑話。
</callout>

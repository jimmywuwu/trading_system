# Quant 黑話辭典

<callout icon="🧠" color="purple_bg">
這頁是給 trading_system / Jaquan Research Wiki 用的 Quant 概念辭典。目的不是炫技，而是把研究文件裡常見但容易卡住的詞，用人話、例子、反例和本專案語境整理起來。
</callout>

## 使用方式

- 看不懂某個詞，直接在該詞旁邊或頁面底部 comment。
- 我會把回答補成正式條目，而不是只在 comment 裡短回。
- 條目會盡量包含：
  - 一句話定義
  - Quant 語境下的意思
  - 在 crypto / trading_system 裡的例子
  - 常見誤解
  - 相關詞

## 條目模板

```text
### 詞彙

一句話：

Quant 語境：

Trading system / crypto 例子：

常見誤解：

相關詞：
```

---

## 1. Alpha

一句話：

> 扣掉市場 beta、成本與風險後，仍可能存在的可交易資訊優勢或結構性收益來源。

Quant 語境：

Alpha 不是「會漲」或「回測賺錢」。比較嚴格地說，它應該表示某個訊號對未來報酬、風險、波動、流動性或 tail event 有額外資訊，而且這個資訊不能完全被簡單 benchmark 解釋。

Trading system / crypto 例子：

如果 high funding + rising OI + weak spot confirmation 在控制 momentum / volatility 後，仍能穩定預測未來 downside tail，那它可能有 alpha 成分。

常見誤解：

- 漂亮 equity curve ≠ alpha
- 高 Sharpe ≠ alpha
- 避開下跌可能是 alpha，也可能只是降低 exposure

相關詞：beta、edge、benchmark、overfit

---

## 2. Beta

一句話：

> 對大盤或主要風險因子的暴露。

Quant 語境：

如果策略賺錢只是因為長期持有 BTC 或承擔市場方向風險，那它比較像 beta，不是 alpha。

Trading system / crypto 例子：

一個策略在 BTC 牛市賺很多，但熊市全部吐回去，可能只是 long BTC beta。

常見誤解：

- beta 不一定不好；但要誠實命名。
- 很多策略其實是 beta timing，不是獨立 alpha。

相關詞：alpha、benchmark、exposure

---

## 3. Edge

一句話：

> 某個決策相對於不做或簡單 baseline 的可重複優勢。

Quant 語境：

Edge 可以是更高 return，也可以是更低 drawdown、更好 tail risk、更低 turnover、更好 risk-adjusted return。

Trading system / crypto 例子：

如果 leverage pressure filter 不能提高收益，但能穩定降低 liquidation periods 裡的 max drawdown，它可能有 risk-management edge。

常見誤解：

- edge 不一定等於「每次都贏」。
- edge 必須在成本和 slippage 後仍有意義。

相關詞：alpha、cost sensitivity、benchmark

---

## 4. Signal

一句話：

> 從 observation 轉換出的、對未來市場狀態有資訊的事件或分數。

Quant 語境：

Signal 不等於 trade。Signal 只描述方向、強度、信心與原因；要不要交易、怎麼 sizing，是 Trader / Strategy 的責任。

Trading system / crypto 例子：

`leverage_pressure_short_signal` 可能輸出：方向 SHORT、strength 0.7、confidence 0.5、reason `leverage_pressure_short`。

常見誤解：

- Signal 不是 order。
- Signal 不應該包含 position size 或 leverage。

相關詞：SignalEvent、Strategy、OrderIntent、TraderHandoff

---

## 5. Regime

一句話：

> 市場所處的一種狀態，例如 bull、bear、high volatility、low liquidity。

Quant 語境：

同一個 signal 在不同 regime 可能表現完全不同。因此研究不能只看 aggregate return，要拆 regime attribution。

Trading system / crypto 例子：

High funding 在 bull regime 可能代表強 demand；在 fragile leverage regime 可能代表 crowded longs。

常見誤解：

- regime 不是事後貼標籤就好；要能在當時被觀察或近似分類。
- 一個策略只在單一 regime 有效，不一定是壞事，但要明確說明。

相關詞：regime attribution、market state、volatility regime

---

## 6. Tail Risk

一句話：

> 分布尾端的小機率大損失風險。

Quant 語境：

很多策略平均報酬看起來正常，但在少數極端狀態會出現很大的損失。Tail risk 研究關心的不是平均，而是 5% / 1% quantile、max adverse excursion、crash behavior。

Trading system / crypto 例子：

Leverage pressure idea 的第一目標不是預測平均 return，而是看 flagged periods 的 downside tail 是否更差。

常見誤解：

- 平均 return 沒變，不代表 tail risk 沒變。
- 小機率事件如果損失很大，仍然可以決定策略生死。

相關詞：downside quantile、max adverse excursion、liquidation cascade

---

## 7. Point-in-Time

一句話：

> 回測在每個歷史時間點只能使用當時真的已經可見的資料。

Quant 語境：

Point-in-time 是避免 lookahead bias 的基本要求。資料不只要有事件發生時間 `occurred_at`，還要知道系統何時觀察到它 `observed_at`。

Trading system / crypto 例子：

如果 1h candle 到 11:00 才完整，但回測在 10:30 就用它的 close / volume，這不是 point-in-time。

常見誤解：

- 有 timestamp 不代表 point-in-time 正確。
- 事後整理過的 historical data 可能包含 live 當時不可見的資訊。

相關詞：lookahead、observed_at、occurred_at、ReplayDataProvider

---

## 8. Lookahead Bias

一句話：

> 回測不小心用了未來資訊。

Quant 語境：

Lookahead bias 會讓策略看起來異常準確，但 live trading 時無法複現。

Trading system / crypto 例子：

用同一根 candle 的 close 產生 signal，又假設可以用那個 close 成交，通常就有 lookahead 或 execution timing 問題。

常見誤解：

- 不是故意作弊才叫 lookahead；很多是資料對齊錯誤。
- 最危險的是「看起來很合理」的 lookahead。

相關詞：point-in-time、replay、observed_at

---

## 9. Overfit

一句話：

> 策略太貼合歷史樣本，導致未來失效。

Quant 語境：

如果只有一個參數、一次市場事件、或一段期間有效，而附近參數和其他期間都失效，通常是 overfit warning。

Trading system / crypto 例子：

只靠 2021 或 2022 某幾次 liquidation crash 找出的 funding/OI threshold，很可能 overfit。

常見誤解：

- 測很多參數後挑最好的，不是 discovery；常常只是資料挖礦。
- 高 Sharpe 也可能是 overfit。

相關詞：parameter stability、walk-forward、train/test split

---

## 10. Full Condition

一句話：

> 一個 hypothesis 裡完整的組合條件，而不是單一指標。

Quant 語境：

Full condition 用來測完整機制是否比 simpler controls 有額外資訊。

Trading system / crypto 例子：

在 leverage pressure 研究中，full condition 是：

```text
funding elevated / rising
+ open interest rising
+ perp-led pressure 或 basis pressure
+ weak spot confirmation
```

常見誤解：

- 如果 funding only 就一樣有效，那 full condition 可能沒有額外價值。
- 如果 full condition 只是在抓 volatility，那不是 leverage-specific alpha。

相關詞：control、benchmark、ablation

---

## 11. Candidate

一句話：

> 候選者，值得研究但還不是結論。

Quant 語境：

Quant 常用 candidate 表示某個 idea / signal / source / strategy 還在研究或審查階段。

Trading system / crypto 例子：

`paper trade candidate` 表示可能值得紙上交易觀察，不代表可以 production。

常見誤解：

- candidate 不是 approval。
- candidate 不是已證明有效。

相關詞：research_only、paper_trade_candidate、production_candidate

---

## 待補條目

- Benchmark
- Control
- Ablation
- Walk-forward
- Parameter stability
- Cost sensitivity
- Slippage
- Liquidity
- Funding rate
- Open interest
- Basis
- Crowded trade
- Hedged basis
- Forced flow
- Max adverse excursion
- Downside quantile
- Confidence
- Strength
- Observation
- SignalContract
- DataProviderHandoff

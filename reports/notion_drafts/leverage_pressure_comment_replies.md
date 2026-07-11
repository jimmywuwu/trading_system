---

## Comment 回覆與概念補充

<callout icon="💬" color="yellow_bg">
這一節是回覆 Jimmy 在文件上的 comments。之後如果有更多問題，我會優先在這裡補概念，而不是只在聊天裡回覆，方便同事一起讀。
</callout>

### A. 初始 prior 裡那些詞是什麼？我怎麼區分？

這裡的幾個詞不是精確模型分數，而是 **研究前的主觀分層**。用途是幫我們決定下一步要怎麼驗證，不是宣稱結論。

#### mechanism plausibility：機制合理性

意思是：這個市場故事在結構上是否說得通。

我問的是：

```text
如果這個現象真的存在，它背後是否有合理的市場參與者、約束、forced flow、liquidity behavior 可以解釋？
```

在這個題目裡，我給「中高」，因為 crypto 裡槓桿、清算、流動性撤退確實常造成短期非線性波動。

但注意：**機制合理不等於可以賺錢。**

#### standalone short alpha：獨立做空 alpha

意思是：只靠這個訊號，是否有可能直接產生一個做空策略，扣掉成本後仍有正期望值。

我給「低到中」，因為做空比 risk filter 難很多，需要克服：

- funding payment
- fee / spread / slippage
- bull market squeeze
- timing error
- signal 太早或太晚

所以即使它能預測 downside risk，也不代表它適合直接開空。

#### downside-risk regime filter：下行風險狀態過濾器

意思是：它不一定告訴我們「現在做空會賺」，但可能告訴我們：

```text
現在市場進入比較容易發生下行尾部風險的狀態。
```

這種訊號可以用來：

- 降低 long exposure
- 暫停新增多單
- 提醒 Trader 檢查 hedge
- 對其他 bullish signal 降低 confidence

我給「中到中高」，因為這比 standalone short alpha 要求低，而且更符合 liquidation-fragility 的機制。

#### production readiness：離上線交易有多近

意思是：這個想法距離 production / live trading 還差多少 evidence。

我給「很低」，不是否定 idea，而是因為它還缺：

- DataProvider point-in-time review
- observation requirements
- event study
- benchmark comparison
- robustness checks
- cost sensitivity
- regime attribution
- Trader handoff
- paper trading evidence

在我們的 workflow 裡，大多數初始 idea 的 production readiness 都應該很低。這是健康的。

#### overfit risk：過度擬合風險

意思是：我們是否很容易在少數歷史事件、少數 threshold、少數參數上找到漂亮但不穩定的結果。

這題我給「高」，因為 liquidation 類研究很容易被幾次大瀑布主導。只要掃很多 threshold，就很容易找到看似有效的組合。

判斷 overfit risk 時，我會看：

- 是否只有一個 threshold 有效？
- 附近參數是否也有效？
- 是否只靠一兩次 crash 撐起結果？
- train/test 是否穩定？
- BTC / ETH 是否方向一致？
- 控制 momentum / volatility 後是否還存在？

---

### B. candidate 是什麼意思？Quant 通常怎麼用？

`candidate` 可以理解成：**候選者，還不是結論。**

在 quant research 裡，它通常用在「還需要驗證，但值得列入下一步研究」的東西。

例如：

- candidate signal：候選訊號，還沒證明有效
- candidate feature：候選特徵，可能有資訊量
- candidate source：候選資料源，還沒通過 data review
- paper trade candidate：可能值得紙上交易，但還不是 production
- production candidate：可能值得上線前審查，但仍不是已上線策略

所以我寫 `Primary candidate: downside-risk regime filter` 的意思是：

```text
目前最值得驗證的用途，是把它當成下行風險 regime filter。
```

不是說它已經是有效 filter。

---

### C. full condition 是什麼？

`full condition` 指的是完整組合條件，而不是單一指標。

在這個研究裡，full condition 大概是：

```text
funding elevated / rising
+ open interest rising
+ perp-led pressure 或 basis pressure
+ weak spot confirmation
```

對比：

```text
high funding only
rising OI only
high funding + rising OI only
```

我們需要比較 full condition 和 simpler controls，原因是：

- 如果 high funding only 就一樣有效，那 weak spot confirmation 可能沒加資訊。
- 如果 realized volatility control 就一樣有效，那它可能只是 volatility proxy。
- 如果 momentum control 就一樣有效，那它可能只是 momentum / reversal proxy。

所以 `full condition` 是用來測：

```text
這個完整市場機制是否比單一指標更有資訊量？
```

---

### D. OI 是 hedged basis，不是 crowded longs，這有辦法確認嗎？

可以部分確認，但通常不能完美確認。

Open interest 本身只告訴我們：

```text
未平倉合約增加了。
```

它不直接告訴我們：

```text
增加的是 directional longs，還是 delta-neutral basis trades。
```

可以用幾個間接方法提高信心：

#### 1. 看 funding 與 basis

如果 OI 增加，同時 funding 很高、basis 擴大，代表 long demand 可能比較強。

但 basis trade 也會在這種時候進場，所以不能單靠這點。

#### 2. 看 perp vs spot lead-lag

如果 perp return 明顯領先 spot，且 spot volume 沒跟上，比較像 perp-led leverage demand。

如果 spot 同步強勢放量，則比較像現貨真需求。

#### 3. 看 liquidation / long-short imbalance 資料

如果可取得 point-in-time liquidation prints、long/short ratio、top trader positioning，可以輔助判斷。

但這些資料常有品質問題，不能無腦信。

#### 4. 看 funding arb 行為痕跡

如果 OI 增加但 price impact 小、basis 被壓回、spot borrow / lend 或 stablecoin flow 支持 basis arb，可能更像 hedged positioning。

#### 5. 最務實的做法

我們不需要完美知道每一筆 OI 是誰開的。研究上可以問：

```text
在 OI rising 的狀態裡，加入 weak spot confirmation 後，是否能區分出更脆弱的那一群？
```

也就是用 outcome 和 controls 檢查這個 interpretation 是否有用。

---

### E. historical data 不是 point-in-time，漂亮結果可能只是 lookahead，這句話是什麼意思？

`point-in-time` 的意思是：

```text
在歷史回放的每一個時間點，策略只能看到當時真的已經可見的資料。
```

`lookahead` 的意思是：

```text
回測不小心用了當時還不知道的未來資訊。
```

例子：

假設 10:00-11:00 的 1h candle，要到 11:00 之後才完整知道 high/low/close/volume。

如果回測在 10:30 就使用這根 1h candle 的 close 或 full volume，那就是偷看未來。

再舉這個題目的例子：

- funding API 歷史資料可能有 funding rate timestamp
- 但我們需要知道系統在當時什麼時間可以觀察到它
- 如果 historical dataset 是事後整理過的，我們可能拿到當時 live system 還看不到的資料

這會讓回測看起來很準，因為它其實拿了未來資料。

比較簡單的比喻：

```text
你在考試前說自己會預測題目，
但其實你拿到的是考後整理過的答案卷。
```

這就是 lookahead。漂亮，但不誠實。市場不會在 live trading 時給我們答案卷。

所以這個研究一定要確認：

- 每個 observation 的 `occurred_at` 是什麼？
- 每個 observation 的 `observed_at` 是什麼？
- replay 時 current_time 只能看到 `observed_at <= current_time` 的資料。

這也是為什麼下一步應該先做 `ObservationRequirements` 和 `DataProviderHandoff`，而不是直接 backtest。

# Quant / 投資研究 7 天入門專案 TODO

> 目的：在正式進入 Quant / 投資研究工作前，先透過一個 7 天專案建立共同語言。這不是為了追求漂亮回測，而是讓研究輸出能服務兩件事：**資產增長**與**更深的世界洞見**。

## 專案定位

- **專案類型**：Quant 入門 + 投資研究系統建立
- **主軸**：美股 Market Regime & Fragility Dashboard
- **方法**：質性 + 量化混合
- **第一原則**：用質性理解世界，用量化避免被故事騙，用風險框架保護資產。
- **預期成果**：建立一套可重複使用的市場狀態判斷與主題研究流程。

## 成功標準

完成 7 天後，我們應該得到：

- [ ] 一套共同語言：alpha、edge、signal、strategy、regime、risk premium、valuation、liquidity、breadth、credit、volatility。
- [ ] 一張 Market Regime Dashboard v1。
- [ ] 一份當前美股市場狀態 memo。
- [ ] 一份主題研究 mini-project。
- [ ] 一張研究審查卡：用來判斷 Jaquan 的研究是否真的有價值。
- [ ] 一個下一階段研究 backlog。

---

# Day 1 — 建立投資研究與 Quant 的共同語言

## 今日目標

理解 Quant / 投資研究的本質：不是用數學包裝交易，而是把市場直覺變成可檢查、可反駁、可服務決策的研究流程。

## TODO

- [ ] 定義 Quant 在我們合作中的角色。
- [ ] 區分：alpha、edge、signal、strategy、portfolio decision。
- [ ] 區分：質性 thesis、量化 proxy、可交易 signal。
- [ ] 建立「好研究 vs 壞研究」標準。
- [ ] 寫出第一版《研究審查卡 v1》。

## 今日輸出

- [ ] `Quant / 投資研究本質地圖 v1`
- [ ] `研究審查卡 v1`

## Jaquan 回報格式

- 今天學了什麼概念？
- 這個概念如何幫助資產增長或世界洞見？
- 之後你應該如何用它審查我的工作？

---

# Day 2 — 市場 Regime：先判斷環境，再談標的

## 今日目標

建立市場狀態框架，理解為什麼投資不是只選公司，也要判斷環境是否允許承擔風險。

## TODO

- [ ] 定義四種市場狀態：
  - [ ] Broad Risk-On Expansion
  - [ ] Narrow Leadership / Melt-Up
  - [ ] Defensive / Slowdown
  - [ ] Fragility / De-risking
- [ ] 為每種 regime 寫出 portfolio implication。
- [ ] 定義 regime 轉換時應該觀察的證據。
- [ ] 建立「不是預測明天漲跌，而是判斷風險補償」的工作語言。

## 今日輸出

- [ ] `Market Regime Map v1`
- [ ] `Regime → Portfolio Implication 對照表`

## Jaquan 回報格式

- 目前我們在學哪種市場判斷？
- 它避免哪種投資錯誤？
- 如果判斷錯了，會在哪裡先看到？

---

# Day 3 — 建立 Market Regime Dashboard v1

## 今日目標

選出第一版核心指標，不追求複雜，而是追求能解釋「市場是否值得承擔風險」。

## TODO

- [ ] 選定 8–10 個核心指標。
- [ ] 為每個指標定義：
  - [ ] 它回答什麼問題？
  - [ ] 它偏向 trend、breadth、credit、volatility、rates、leadership 哪一類？
  - [ ] 它的常見誤讀是什麼？
- [ ] 建立初版 scoring / interpretation，不急著自動化。

## 初始指標池

- [ ] SPY trend / drawdown
- [ ] QQQ vs SPY relative strength
- [ ] Equal-weight S&P vs cap-weight S&P
- [ ] Market breadth proxy
- [ ] High yield credit spread / HYG proxy
- [ ] VIX level and term structure
- [ ] 10Y yield / real yield
- [ ] USD / liquidity proxy
- [ ] Semiconductors vs broad market
- [ ] Cyclicals vs defensives

## 今日輸出

- [ ] `Market Regime Dashboard 指標清單 v1`
- [ ] `每個指標的解釋與誤讀風險`

## Jaquan 回報格式

- 每個指標的用途是什麼？
- 哪些指標比較可靠？哪些容易誤導？
- 這個 dashboard 目前不能回答什麼？

---

# Day 4 — 用 Dashboard 讀一次當前美股市場

## 今日目標

把框架用在真實市場上，產出第一份 regime memo。重點不是精準預測，而是建立可審查的市場判斷。

## TODO

- [ ] 拉取或整理當前市場資料。
- [ ] 按照 dashboard 分類填入證據：
  - [ ] Trend
  - [ ] Breadth
  - [ ] Credit
  - [ ] Volatility
  - [ ] Rates / Liquidity
  - [ ] Leadership
- [ ] 給出當前 regime 判斷。
- [ ] 寫出支持證據、反證風險、投資含義。

## 今日輸出

- [ ] `Current U.S. Market Regime Memo v1`

## Memo 固定格式

```text
Market Regime:
Evidence:
- Trend:
- Breadth:
- Credit:
- Volatility:
- Rates / Liquidity:
- Leadership:
Interpretation:
Portfolio Implication:
Key Risk / Falsification:
Confidence:
```

## Jaquan 回報格式

- 目前市場真正獎勵的是什麼？
- 這對倉位、風險、觀察清單有什麼含義？
- 哪個證據最可能推翻判斷？

---

# Day 5 — 選一個有趣且可能影響資產的主題

## 今日目標

從「市場環境」進入「主題研究」。選一個既能加深世界洞見，也可能影響資產配置或選股的題目。

## 候選題目

- [ ] AI Capex Cycle：真實生產力週期，還是資本開支泡沫？
- [ ] 高品質大型股是否仍優於小型股？
- [ ] Data Center / Power Bottleneck：AI 的瓶頸是否轉向電力與基礎設施？
- [ ] Defense / Reindustrialization：地緣政治是否重塑長期資本支出？
- [ ] GLP-1 / Healthcare Productivity：醫療創新是否改變消費與保險經濟？
- [ ] Japan Corporate Reform：日本市場改革是否仍有結構性機會？

## TODO

- [ ] 為每個候選題寫一句 thesis。
- [ ] 評估：資產相關性、世界洞見價值、資料可得性、可反駁性。
- [ ] 選出第一個 mini-project 題目。
- [ ] 寫出為什麼選它、為什麼暫不選其他題。

## 今日輸出

- [ ] `Theme Selection Memo v1`
- [ ] `下一個主題研究題目`

## Jaquan 回報格式

- 這個題目為什麼值得研究？
- 它如何可能影響資產增長？
- 什麼證據會讓我們放棄它？

---

# Day 6 — 主題研究 Mini-Project

## 今日目標

對 Day 5 選出的主題做第一輪研究：不是下交易結論，而是建立 thesis、proxy、反證條件與觀察清單。

## TODO

- [ ] 寫出 qualitative thesis。
- [ ] 定義 market mechanism / economic mechanism。
- [ ] 選出 quantitative proxies。
- [ ] 建立 key companies / ETFs / value chain map。
- [ ] 初步檢查 valuation、growth、margin、revision、risk。
- [ ] 寫出 falsification criteria。
- [ ] 判斷目前用途：Watch / Research More / Position / Hedge / Avoid。

## 今日輸出

- [ ] `Theme Research Mini-Report v1`

## Report 固定格式

```text
Theme:
One-sentence thesis:
Why it matters:
Mechanism:
Key assets / companies / ETFs:
Qualitative evidence:
Quantitative proxies:
Valuation question:
Falsification criteria:
Portfolio implication:
Confidence:
Next research step:
```

## Jaquan 回報格式

- 這是敘事、事實，還是可投資假設？
- 哪些證據支持？哪些證據削弱？
- 現在最合理的行動是什麼？

---

# Day 7 — 整合成可重複使用的研究系統

## 今日目標

把 7 天內容整理成可長期使用的研究系統，而不是一次性課程。

## TODO

- [ ] 整理 `Market Regime Dashboard v1`。
- [ ] 整理 `Theme Research Template v1`。
- [ ] 更新 `研究審查卡 v2`。
- [ ] 建立下一階段 research backlog。
- [ ] 決定週期：每週 market regime memo？每月主題研究？事件觸發更新？
- [ ] 定義 Jaquan 之後每次研究輸出的固定標籤。

## 固定標籤

```text
用途：資產增長 / 世界洞見 / 風險控制 / 純探索
投資相關性：High / Medium / Low
可行動性：Watch / Research More / Position / Hedge / Avoid
證據類型：質性 / 量化 / 混合
信心：Low / Medium / High
主要反證：
下一步：
```

## 今日輸出

- [ ] `Market Regime Dashboard v1`
- [ ] `Theme Research Template v1`
- [ ] `研究審查卡 v2`
- [ ] `Research Backlog v1`
- [ ] `後續運作節奏`

---

# 專案原則

## 1. 先建立語言，再追求複雜度

如果我們還不能清楚說明一個研究在檢驗什麼，就不應該急著做 backtest。

## 2. 每個輸出都要說清楚用途

研究必須標明：它服務資產增長、世界洞見、風險控制，還是只是探索。

## 3. 質性與量化互相制衡

質性研究防止數據盲；量化研究防止故事癮。

## 4. 弱結果也要保留

如果一個想法被削弱，這本身就是價值：它幫我們少犯錯。

## 5. 不把專業感誤認成價值

漂亮圖表、複雜模型、術語密度，都不是研究品質。真正的品質是：是否改善決策。

---

# 第一個正式專案主線

## Market Regime & Fragility Dashboard

核心問題：

> 現在的美股市場環境，是否值得承擔更多風險？

這個 dashboard 不追求預測明天漲跌，而是幫助判斷：

- 市場目前處於什麼 regime？
- 風險補償是否足夠？
- 脆弱性是否上升？
- 哪些證據會推翻目前判斷？
- 對倉位、風險、主題研究有什麼含義？

---

# 下一步

- [ ] Day 1 開始：建立《Quant / 投資研究本質地圖 v1》。
- [ ] Jaquan 每次回報時都必須說清楚：本次輸出如何幫助資產增長或世界洞見。

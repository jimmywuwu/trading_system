# Jaquan Trading Research Wiki

<callout icon="📚" color="blue_bg">
這個 Wiki 用來集中 Jaquan / HERMES 對 trading_system 的研究筆記、market mechanism 分析、artifact handoff、以及決策紀錄。目標是讓同事可以在 Notion 上閱讀、評論、追問，而不是把長分析塞在 Telegram 裡一次消化完。
</callout>

## Wiki 使用方式

- Telegram / chat：只放摘要、結論、下一步。
- Notion Wiki：放完整推理、假設、反例、研究設計與討論問題。
- Repo artifacts：放 machine-readable YAML、tests、validation output。

## 目前分類

### 1. Research Ideas

模糊想法的初步整理，包含 suspected mechanism、candidate sources、known risks、priority。

### 2. Market Mechanism Notes

市場機制分析：誰被迫交易、誰提供 liquidity、壓力來源、observable footprints、alternative explanations、invalidation conditions。

### 3. Research Hypotheses

把 mechanism 轉成可以 falsify 的研究假說：trigger condition、target variable、horizon、null hypothesis、failure modes。

### 4. Data / Observation Requirements

資料需求與 point-in-time 語意：observed_at、occurred_at、missing/stale/late policy、replay requirements。

### 5. Research Reports

完整研究報告：event study、benchmark、robustness、regime attribution、cost sensitivity、conclusion grade。

### 6. Decision Records

Hermes 決策紀錄：accepted / rejected / deferred / needs_revision，避免重複研究與過度升級。

## 已收錄文件

### Leverage Pressure Liquidation Downside：研究分析筆記

- local draft: `reports/notion_drafts/leverage_pressure_liquidation_downside_analysis.md`
- related idea: `idea_leverage_pressure_liquidation_downside_v1`
- related mechanism note: `mech_leverage_pressure_liquidation_downside_v1`
- related hypothesis: `hyp_leverage_pressure_liquidation_downside_v1`
- status: draft_for_discussion

## Wiki 維護原則

1. **Chat 不承載完整研究。** 長推理寫到 Notion。
2. **每篇文件要有討論問題。** 方便同事評論，不只是閱讀。
3. **保留 uncertainty。** 不把 preliminary thought 寫成結論。
4. **角色邊界要清楚。** HERMES 負責 coordination；QUANT 負責 hypothesis / evidence；DataProvider Developer 負責 point-in-time source review；Trader 負責 sizing / risk / portfolio feasibility。
5. **避免漂亮回測直接升級。** 所有 trading candidate 都需要 benchmark、cost、robustness、regime、data integrity review。

## 下一步

建立 Notion parent page 後，將本頁作為 Wiki Home，並將各研究筆記作為子頁。第一批頁面：

1. Wiki Home
2. Leverage Pressure Liquidation Downside：研究分析筆記

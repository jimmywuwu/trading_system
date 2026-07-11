---
name: research-idea
description: 把一個交易想法走過 Gate 0-2（ResearchIdea -> MechanismNote -> ResearchHypothesis），產出可證偽的研究假說或明確否決。任何新策略研究的唯一入口。
---

# /research-idea — 想法到可證偽假說

用法：`/research-idea <一句話描述想法>`

你是 Quant 角色。目標不是讓想法通過，而是**盡快找到否決它的理由**；
通不過就寫 DecisionRecord 否決，這是有價值的產出。

## 前置

1. 讀 `docs/DESIGN.md` §2（設計理念）與 `docs/quant_research_workflow.md` §0-2。
2. **查重**：搜尋 `reports/decisions/` 與 `reports/research/` 是否已有相同
   或相似假說。若已被否決且無新證據，直接停止並告知使用者先前的結論。

## Gate 0: ResearchIdea

回答不出以下任一項就否決：

- 一句話 summary
- 懷疑的市場機制（不是「SMA 交叉可能有用」，是「誰被迫在什麼時候做什麼」）
- 候選資料源與標的
- 預期 horizon（分鐘/小時/天）
- 為什麼這個效應不會立刻被套利掉

## Gate 1: MechanismNote

必答問題（answers 寫進 artifact）：

- 誰被迫交易？（清算、對沖、資金費結算、指數再平衡…）
- 誰是慢的、受限制的、結構性劣勢的一方？
- 誰承擔庫存或流動性風險？
- 機制應該在資料上留下什麼**可觀測的足跡**？
- 有哪些替代解釋可以否定它？
- 什麼條件下機制失效？

寫不出「可觀測足跡」的機制 = 無法研究 = 否決。

## Gate 2: ResearchHypothesis

假說必須長這樣：

```text
當系統在時間 t 可見 X observation 時，
在 horizon H 內，
Y 應該出現方向/分布上的偏移 Z，
且扣除合理成本後效應仍存在。
```

必填：trigger_condition、target_variable、horizon、expected_direction、
null_hypothesis、minimum_effect_after_cost、falsification_tests。

## 產出

寫到 `reports/research/<idea-slug>/hypothesis.md`，包含三個 gate 的
YAML artifacts（模板在 `docs/quant_research_workflow.md`）。

結尾必須明確給出下一步之一：

- **否決** → 寫 `reports/decisions/<date>_<idea-slug>.md`（DecisionRecord，
  含 reason、evidence、do_not_repeat_until 條件）
- **需要新資料** → 建議使用者跑 `/new-provider`
- **資料已就緒** → 建議使用者跑 `/new-signal`

## 禁止

- 跳過機制直接寫 signal 程式碼。
- 用「回測看看就知道」代替 null hypothesis。
- 對已否決假說換個參數重開。

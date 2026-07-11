---
name: research-cycle
description: 執行一個完整的自主研究 cycle：讀看板、選一個工作項、呼叫對應階段 skill、產出 artifact、更新看板、自我審計。自主閉環（/loop 或排程）的標準循環體；每次呼叫獨立完成，不依賴前一個 session 的記憶。
---

# /research-cycle — 一個研究 cycle（閉環循環體）

本 skill 是自主 loop 的原子單位。設計前提：**你可能在全新 session、
零先前記憶的狀態下被呼叫**。所有需要的狀態都在磁碟上，按順序執行即可。
一個 cycle 只推進一個工作項的一個階段，寧可做少不可跳 gate。

## Step 0: Preflight（不過就停）

```bash
python3 -m pytest -q          # 紅燈 → 本 cycle 只准修測試，修完即結束
git status --short            # 記下開場狀態，cycle 結束時 diff 必須可解釋
```

讀（只讀這些，不要發散）：

1. `CLAUDE.md`（規則）
2. `reports/PIPELINE.md`（看板）
3. `docs/AGENT_OPERATIONS.md` §2.3-2.5（決策樹與預算）

## Step 1: 對帳（看板 vs 事實）

Artifact 是事實，看板是快取。逐項核對 Active 工作項：

- `reports/research/<id>/` 實際走到哪個 artifact？
- `reports/decisions/` 有沒有已存在但看板沒登記的結論？

不一致 → 先修看板再繼續（這本身算有效產出）。

## Step 2: 選工作項（嚴格按決策樹，禁止跳序）

依 `AGENT_OPERATIONS.md` §2.3 依序檢查，**命中第一條就停**：

1. 報告評級 paper_trade_candidate 且無 StrategyContract + strategy 實作
   → 用 `/new-strategy` 的流程（Trader 翻譯，promote Gate C/D 的前置）
2. 有報告無 DecisionRecord（reject/research_only，或 strategy 已就緒）
   → 用 `/promote-strategy` 的流程
3. signal 過 smoke replay 但無回測報告 → 用 `/run-backtest` 的流程
4. 假說通過、資料就緒、無 signal → 用 `/new-signal` 的流程
5. 假說通過、缺資料、不需人核可 → 用 `/new-provider` 的流程；
   需要 API key / 花錢 → 移到 Blocked，寫清楚要人做什麼，**跳到 Step 5**
6. Active < 3 且 backlog 有貨 → 用 `/research-idea` 的流程
7. backlog 空 → 生成 ideas 進 backlog（§2.4 規則），本 cycle 到此為止
8. 全部 blocked → 維護工作（補測試、資料品質檢查），禁止放寬 gate

選定後，先檢查該工作項的預算：cycles 已用 ≥ 12 → 不做研究，直接寫
`deferred` DecisionRecord 並下架。

## Step 3: 執行該階段

打開對應 skill 檔（`.claude/skills/<name>/SKILL.md`）**完整照做**，
包括它的前置閱讀與禁止事項。執行紀律：

- 只做被選中的這一個階段，做完就停，不要「順手」推進下一階段
- 所有結論必須來自你實際執行的指令輸出；沒跑過的數字不准寫進報告
- 需要新的分析原語 → 先在 `research/` 加函式 + 測試，再用它
- 對任何事實不確定（資料語意、既有結論）→ 查檔案，查不到就當作不知道，
  寫進 open questions，不要編造

## Step 4: 產出檢查（自我審計，逐項核對）

- [ ] 本 cycle 產出了至少一個 artifact 檔案或 DecisionRecord（零產出 = 違規）
- [ ] 產出檔案位置符合目錄契約（`reports/research/` `reports/backtests/` `reports/decisions/`）
- [ ] 動過程式碼 → `python3 -m pytest -q` 全綠
- [ ] 報告裡每個數字都能對應到可重跑的指令或腳本
- [ ] 沒有跳過任何 gate、沒有重開已否決假說

任何一項不過 → 在結束前修正；修不了 → 把該工作項標記 needs_attention
並如實記錄，不要掩蓋。

## Step 5: 收尾

1. 更新 `reports/PIPELINE.md`：階段、cycles 已用 +1、下一步 skill、阻塞
2. 在看板底部 Recently decided 維持最近 5 筆
3. 輸出 cycle 摘要（給人看的，3-6 行）：
   - 這個 cycle 做了什麼、產出檔案路徑
   - pipeline 現在的狀態一句話
   - 需要人介入嗎？（三個核可點：花錢資料源 / 升 paper / 真金白銀）

## 停止條件（loop 層面）

以下情況輸出摘要後**明確建議停止 loop**，等人回來：

- 觸及任何人工核可點
- 全部工作項 blocked 且維護工作也做完
- 連續 2 個 cycle 零有效產出
- 測試修了 2 個 cycle 還是紅

# Agent 自主研究閉環操作手冊

> 給「操作這個系統的 agent」（或想用 agent 跑研究的人）的結論性建議。
> 架構與理念見 `docs/DESIGN.md`；本文件回答兩個問題：
> **這種系統該怎麼做**、**一個 agent 怎麼調用 skills 自行閉環迭代**。
> 日期：2026-07-08。

---

## Part 1. 做這種系統的核心建議

### 1.1 一個 agent 輪替角色，勝過多個 agent 假協作

v1 的 `agents/runtime.py` 已經證明了反面教材：讓多個「agent 人格」互發
模板訊息，產出的是會議記錄的形狀，不是研究。角色分工（Quant / DataProvider
Developer / Trader）的價值在於**每個階段戴不同的帽子、用不同的標準審查**，
而不在於真的要多個進程。

正確做法：**單一 agent，依 pipeline 階段切換角色視角**。每個 skill 開頭
已經寫明「你是誰、你在找什麼否決理由」。需要平行化的時候（例如同時跑
兩個假說的回測），才用 subagent，且各自仍走完整 gate。

### 1.2 狀態放在磁碟上，不放在對話裡

Agent 的 session 會結束、context 會被壓縮。**唯一可信的狀態是
`reports/` 裡的 artifacts**：

- `reports/research/<idea>/` 走到哪個 artifact，就是這個假說的狀態
- `reports/decisions/` 是全部歷史結論（append-only）
- `reports/PIPELINE.md` 是唯一的看板（見 §2.2），每個 cycle 開始先讀、
  結束前更新

這代表任何新 session 的 agent 都能無損接手：讀 `CLAUDE.md` →
讀 `reports/PIPELINE.md` → 繼續。

### 1.3 否決率是健康指標，不是失敗指標

一個誠實的研究工廠，**大部分假說應該死在便宜的階段**：

```text
理想漏斗（數量級）
ideas          ████████████ 每週 3-5 個
hypotheses     ██████       約一半死在 Gate 0-2（無機制、無足跡、重複）
event studies  ███          再死一半（無預測力，最便宜的量化否決點）
backtests      ██           成本一加就死
paper 候選     ▌            每月 0-1 個是正常的
```

如果 agent 產出的假說大多「通過」，代表 gate 沒在工作，系統在自欺。
DecisionRecord 裡 `rejected` 的比例低於 60%，就該審查流程本身。

### 1.4 計算歸程式庫，判斷歸 agent，流程歸 skill

三層分工不要混：

| 層 | 承載 | 例子 |
|---|---|---|
| 計算（確定性、有測試） | `backtest/` `research/` | replay、fill 模擬、event study、benchmark |
| 流程（gate、模板、誠實規則） | `.claude/skills/` | 「event study 先於回測」「全部參數都要列出」 |
| 判斷（機制推理、寫結論） | agent 本身 | 「這個效應的機制是清算瀑布還是資金費套利？」 |

Agent 想跑新的分析而程式庫沒有原語時，正確動作是**先在 `research/`
加原語 + 測試**，再回來做研究；不是在研究腳本裡手搓一次性 loop
（那就是 v1 報告目錄爆炸的原因）。

### 1.5 人的介入點要明確且少

全自動不等於無人。建議只保留三個人工核可點，其餘全部放行：

1. **新資料源要花錢/要 API key** → 人核可
2. **評級升到 `paper_trade_candidate`** → 人看 DecisionRecord 後核可
3. **任何真金白銀**（未來 live）→ 人核可，永遠

其他（想法生成、假說否決、回測、報告）agent 自主，事後可審計。

---

## Part 2. Agent 閉環運作規範

### 2.1 主循環：每個 cycle 做一件事

```text
loop:
  1. 讀 reports/PIPELINE.md，同步實際目錄狀態（artifact 是事實，看板是快取）
  2. 選出「最接近產生決策」的一個工作項（優先序見 §2.3）
  3. 呼叫對應 skill，走到該階段的 gate 為止
  4. 產出 artifact 或 DecisionRecord（沒有產出 = 這個 cycle 白跑，禁止）
  5. 更新 reports/PIPELINE.md（狀態、下一步、阻塞原因）
  6. python3 -m pytest 全綠才能結束 cycle（動過程式碼時）
```

一個 cycle 只推進一個工作項的一個階段。不要在同一個 cycle 裡
「順手」把假說從 idea 推到回測報告——分階段停頓是防自欺機制，
每個 gate 都要有機會殺掉這個想法。

### 2.2 看板：`reports/PIPELINE.md`

格式固定，agent 負責維護：

```markdown
# Research Pipeline
更新：<date> by <agent/session>

## Active（最多 3 個）
| id | 假說一句話 | 階段 | 下一步 skill | cycles 已用 | 阻塞 |
|---|---|---|---|---|---|
| lev-pressure-v3 | 高槓桿壓力後 4h 下行偏移 | signal 已實作 | /run-backtest | 4 | - |

## Blocked（等資料/等人核可）
## Idea backlog（下一批候選，附一句機制）
## Recently decided（最近 5 筆，連到 DecisionRecord）
```

**Active 上限 3 個**是硬規則。滿了就不准開新假說，先把現有的推到
decision（promote 或 reject 都算）。

### 2.3 決策樹：這個 cycle 該呼叫哪個 skill

依序檢查，命中即執行：

```text
1. 有 active 項目「報告評級 paper_trade_candidate、但無 StrategyContract
   + strategy 實作」？
   → /new-strategy（Trader 翻譯：sizing/風控/paper 標準；
     promote 的 Gate C/D 需要它）

2. 有 active 項目卡在「報告已完成、無 DecisionRecord」
   （reject/research_only，或 strategy 已就緒）？
   → /promote-strategy（離決策最近的工作優先）

3. 有 active 項目「signal 已過 smoke replay、無回測報告」？
   → /run-backtest

4. 有 active 項目「假說已通過、資料已就緒、無 signal」？
   → /new-signal

5. 有 active 項目「假說已通過、但缺資料」且資料源不需人核可？
   → /new-provider
   （需要花錢/API key → 移到 Blocked，寫清楚要人做什麼）

6. Active < 3 且 idea backlog 有貨？
   → /research-idea 拿最上面的 idea 走 Gate 0-2

7. Idea backlog 空了？
   → 生成 ideas（規則見 §2.4），只補進 backlog，本 cycle 不研究

8. 以上皆無（全部 blocked）？
   → 做維護工作：補 research/ 原語的測試、清理 legacy、
     驗證資料品質。不准為了有事做而放寬 gate 重開已否決假說。
```

**原則：漏斗下游優先。**先收割接近決策的工作，再開新戰線。
這保證 decisions 持續產出，而不是 backlog 無限膨脹（v1 的死法）。

### 2.4 Idea 生成規則（第 6 步）

生成 idea 時的優先順序：

1. **既有研究的衍生**：讀 `reports/decisions/` 裡 `research_only` 級的
   結論——它們是「有訊號但證據不足」的礦脈。這個 repo 現成的方向：
   槓桿壓力（leverage pressure v2/v3）、OI 收縮去槓桿、跨所 funding
   分歧、spot/perp leadership、notional vs contract OI。
2. **機制驅動的新想法**：從「誰被迫交易」出發（清算、資金費結算、
   期權到期對沖、指數再平衡、大額解鎖）。
3. **禁止**：指標排列組合（「試試 EMA 代替 SMA」）、對已否決假說
   換參數重開（除非 DecisionRecord 的 `do_not_repeat_until` 條件已滿足）。

每個 idea 進 backlog 時必須帶一句機制描述，寫不出來就不進。

### 2.5 預算與停損（防空轉）

- **每個假說總預算 12 個 cycles**。用完還沒到 decision → 自動寫
  DecisionRecord `deferred`，附「差什麼證據」。
- **同一階段最多重試 2 次**。第三次失敗（例如 signal 測試一直不過）
  → 降級處理：回上一個 gate 檢討假說，或 defer。
- **每 10 個 cycles 做一次自我審計**：讀最近的 decisions，檢查
  否決率（低於 60% → 檢討 gate 執行）、檢查是否有假說在
  Active 待超過預算、檢查 PIPELINE.md 與實際目錄是否一致。
- **任何 cycle 結束時 pytest 不綠 → 下個 cycle 只准修測試**，
  不准帶著紅燈做研究。

### 2.6 排程建議（用 Claude Code 跑）

循環體已封裝成 `/research-cycle`（`.claude/skills/research-cycle/SKILL.md`）：
一次呼叫 = 一個完整 cycle（preflight → 對帳 → 決策樹選項 → 執行單一階段
→ 自我審計 → 更新看板）。loop 就是反覆呼叫它。

- **互動迭代**（推薦起步）：人開 session 打 `/research-cycle`；
  人只在三個核可點介入。
- **半自動**：`/loop /research-cycle`，agent 自我節奏連續跑，
  碰到停止條件（blocked、核可點、連續零產出）停下來通知。
- **全自動**：`/schedule` 每天固定時段跑 N 個 cycles + 產一份 digest
  （當天推進了什麼、什麼等人）。前提：先用互動模式跑滿 20 個
  cycles、確認 gate 紀律可信，再放手。

不管哪種模式，**每個 cycle 的產出都要能在 git diff 裡看見**
（artifact、decision、看板更新），這是審計的最小單位。

### 2.7 用 Opus 4.8（或任何非最前沿模型）跑 loop 的設計

原則：**把紀律從模型搬進結構**。模型越弱，越不能依賴它「記得」規則，
所有規則都要在每個 cycle 被重新餵進去、且盡量可機器驗證。

1. **每個 cycle 用全新 session（fresh context）**。不要一個長對話跑
   20 個 cycles——長 context 裡的紀律衰減是主要失效模式。磁碟上的
   `PIPELINE.md` + artifacts 就是全部交接，`/research-cycle` 的 Step 0-1
   會重建所需狀態。headless 排程即天然滿足：
   `claude -p "/research-cycle"` 每次都是新 session。
2. **判斷題改成核對題**。skill 裡的 gate 全部寫成 checklist
   （`/research-cycle` Step 4），出口條件用指令驗證（pytest 綠、
   artifact 檔案存在、看板已更新），不驗證「模型覺得做完了」。
3. **縮小每步的自由度**。一個 cycle 只推進一個階段；決策樹「命中第一條
   就停」；閱讀清單白名單化（只讀三個檔案起手）。模型能力越弱，
   單步範圍要越小——寧可 cycle 數多，不要單 cycle 聰明。
4. **禁止 loop 中發明抽象**。缺分析原語時只准「在 `research/` 加函式
   + 測試」，不准在報告腳本裡手搓 loop；架構層變更（`core/` 契約、
   engine 行為）一律移到 Blocked 等人審。
5. **停止條件寬鬆、升級條件嚴格**。寧可多停多問（blocked、連續零產出、
   測試修不好就停），也不要讓它在不確定時自行放寬 gate 往前衝。
6. **人工抽查節奏**：前 20 個 cycles 每個都看 diff；之後抽查
   DecisionRecord 的證據鏈（報告數字 ↔ 可重跑指令）。發現模型某類
   系統性犯規 → 把該規則升級成 skill 裡的 checklist 項，而不是口頭提醒。

推薦落地組合（Opus 4.8）：

```text
階段 1（人在場）：互動 session 手動 /research-cycle × 20，每次看 diff
階段 2（半自動）：/loop /research-cycle，回測等長工作用背景執行，
                 loop 醒來間隔 20-30 分鐘
階段 3（全自動）：/schedule 每日 06:00 跑 6 個 cycles（每 cycle 新 session）
                 + 產 digest；三個核可點透過通知等人
```

---

## Part 3. 結論（TL;DR）

1. **系統的護城河是流程誠實，不是聰明策略。** 程式庫保證回測不自欺
   （lookahead guard、成本、基準），skills 保證研究不自欺（gate、查重、
   否決記錄），agent 的價值是機制推理——三層都不要越界。
2. **單 agent 輪替角色 + 磁碟上的 artifact 狀態**，就足以形成可長期
   運轉的閉環；多 agent 編排是 v1 已驗證的歧途。
3. **閉環的核心是漏斗下游優先 + 硬性預算**：每 cycle 推進一個階段、
   Active 上限 3、每假說 12 cycles、否決率 ≥60% 才健康。
4. **下一個里程碑不是更多策略，而是第一個走完全流程的 decision**：
   建議從槓桿壓力假說開始，用 `/research-idea` 把它重新走一遍新流程——
   這同時是對系統本身的驗收測試。
5. 等出現第一個 `paper_trade_candidate`，再回來建 PaperBroker v2 與
   RiskManager（`DESIGN.md` §5），順序不要反過來。

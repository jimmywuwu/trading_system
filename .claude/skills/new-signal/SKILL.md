---
name: new-signal
description: 從已通過的 ResearchHypothesis 實作訊號：SignalContract、最小實作、單元測試、smoke replay 驗證（Gate 5-7）。實作任何新 Signal 時使用。
---

# /new-signal — 假說到可重播的訊號

用法：`/new-signal <hypothesis 路徑或訊號描述>`

你是 Quant 角色。前提：假說已通過 `/research-idea`（Gate 0-2），且所需
observations 已存在或已由 `/new-provider` 交付。沒有假說先跑 `/research-idea`。

## 前置

讀 `docs/DESIGN.md` §3.3、`core/signal.py`、`signals/sma_cross.py`
（標準範式：stateful incremental、reason codes、timestamp 規則）。

## Step 1: SignalContract（先寫再實作）

模板見 `docs/quant_research_workflow.md` §5。關鍵欄位：

- `required_kinds` / `required_subjects` / `lookback_window` / `stale_tolerance`
- `direction_rule` / `strength_rule` / `confidence_rule`——strength 與
  confidence 都必須是 [0,1] 且有明確語意（strength = 效應強度，
  confidence = 資料品質/新鮮度），不要拍腦袋填 1.0
- `reason_codes`：穩定的字串枚舉，Trader 靠它做 attribution
- `failure_modes`：缺資料、stale、極端值時的行為

Contract 存到 `reports/research/<idea-slug>/signal_contract.md`。

## Step 2: 實作（signals/<name>.py）

規則（違反任何一條 = 重做）：

- 只消費 `Observation` / typed payload，不碰原始 API 格式
- 資料不足或不安全 → 回傳 `None`，絕不猜
- stateful incremental：engine 每 tick 只傳新 observations，
  歷史狀態自己維護；需要預熱用 `warmup()`
- `SignalEvent.timestamp` = 最後使用的 observation 的 `observed_at`
- 決定性：相同輸入序列 → 相同事件序列
- 不 import strategy / portfolio / broker / provider 實作
- 在 `signals/__init__.py` export

## Step 3: 單元測試（tests/test_<name>.py）

用 `tests/conftest.py` 的 `make_candles`（或自建 fixture factory）。
最低覆蓋（參考 `tests/test_sma_cross_signal.py`）：

- [ ] warmup 期間不出事件
- [ ] 正常觸發：方向、reason code 正確
- [ ] 不觸發情境：無事件
- [ ] timestamp == 來源 observation 的 observed_at
- [ ] 忽略其他 symbol / kind
- [ ] 兩次執行結果完全相同（決定性）
- [ ] 缺資料 / stale 資料回傳 None

## Step 4: Smoke replay（Gate 7）

用真實資料跑一小段：

```python
from backtest import ReplayDataProvider
provider = ReplayDataProvider(observations)
for current_time, batch in provider.replay():
    event = signal.generate(batch)
    if event: assert event.timestamp <= current_time
```

檢查：無 LookaheadError、事件數量級合理（每天幾個 vs 每分鐘幾個要對得上
假說的 expected frequency）、重跑一次結果相同。
結果記到 `reports/research/<idea-slug>/smoke_replay.md`。

## 完成後

`python3 -m pytest` 全綠，然後建議使用者跑 `/run-backtest` 做 event study
與回測。**不要**自己順手寫 strategy 或跑大回測下結論——分階段是防自欺機制。

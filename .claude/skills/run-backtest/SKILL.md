---
name: run-backtest
description: 對一個訊號做完整研究評估：event study、point-in-time 回測、benchmark 對照、穩健性檢查（Gate 8-11），產出回測報告。評估任何訊號/策略表現時使用。
---

# /run-backtest — 訊號到有證據的結論

用法：`/run-backtest <signal 名稱與資料範圍>`

你是 Quant 角色。輸出不是一條 equity curve，而是**一組可以否決假說的
證據**。順序不可跳：event study 先於回測，benchmark 先於調參。

## 前置

讀 `docs/DESIGN.md` §3.2、§3.4。工具：

- 引擎：`backtest.BacktestEngine` / `ReplayDataProvider` / `BacktestConfig`
- Event study：`research.forward_return_study`
- 基準：`research.buy_and_hold_metrics`
- CLI 範例：`scripts/run_backtest.py`（SMA 切片；新訊號仿照它寫薄腳本）

## Step 1: Event study（先問「訊號有沒有預測力」）

```python
from datetime import timedelta
from research import forward_return_study
study = forward_return_study(events, observations,
    horizons=[timedelta(hours=1), timedelta(hours=4), timedelta(days=1)])
```

看：事件數（<30 個就別談統計）、各 horizon 的 mean/median/positive_rate、
strength 分桶是否單調（strength 高的事件 forward return 應該更好，
不單調表示 strength 定義有問題）。
**Event study 就死掉的假說，到此為止，直接寫報告否決。**

## Step 2: 回測（含成本）

- `fee_rate` 至少 0.001（taker），加 `slippage_bps`（BTC 主流所 1-5bps，
  小幣更高）；成本假設寫進報告。
- Strategy 用 `strategies.SignalPositionStrategy`（或依 TraderHandoff 客製，
  但 sizing 邏輯不准塞回 signal）。
- 同資料同費率跑 `buy_and_hold_metrics` 對照。

## Step 3: 穩健性（paper candidate 必備，research_only 可部分省略）

- **Train/test**：時間切分（如前 70% / 後 30%），rolling state 不重置。
- **參數鄰域**：最佳參數 ±30% 內至少 4 組；只有一個參數島好 = 過擬合警報。
- **成本敏感度**：fee/slippage 加倍後 net edge 是否還在。
- **Regime 拆分**：至少 trend（漲/跌/盤整）× volatility（高/低），
  指出失效 regime。

## Step 4: 報告

寫到 `reports/backtests/<date>_<signal>_<scope>.md`，必含：

1. 資料範圍與來源（含 fixture 路徑，結果要可重現）
2. Event study 摘要
3. 策略 vs benchmark 表格（return / max_dd / sharpe / turnover / fees / exposure）
4. 穩健性結果與**失效條件**
5. Execution assumptions（fill 規則、費率、滑價）與尚未驗證項
6. 結論評級：`reject` / `research_only` / `paper_trade_candidate`
   —— 本 skill 最高只能給 `paper_trade_candidate`；升級走 `/promote-strategy`

## 誠實規則

- 輸給 buy-and-hold 就明說；「exposure 更低所以其實不錯」要有
  same-average-exposure 基準支持才能講。
- 不准為了讓結果好看而事後改資料範圍或費率。
- 跑了 10 組參數只報告最好的 1 組 = 造假；全部列出。

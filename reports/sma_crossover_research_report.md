# SMA Crossover Research Report

Date: 2026-05-17

## Executive Summary

本研究測試 BTC-USD 1 分鐘資料上的 SMA crossover directional strategy。

目前最穩健的候選參數仍是：

```text
fast_window = 4,320   # 約 3 天
slow_window = 20,160  # 約 14 天
```

完整 3 年回測結果：

```text
period: 2023-05-18T06:32:00+00:00 -> 2026-05-17T06:31:00+00:00
strategy return: +57.58%
max drawdown: -14.54%
trades: 100
fees: 5,062.62
average exposure: 54.71%
final equity: 157,582.65
```

Benchmark:

```text
BTC buy-and-hold return: +187.15%
BTC buy-and-hold max drawdown: -52.34%

50% BTC / 50% cash return: +93.57%
50% BTC / 50% cash max drawdown: -43.06%
```

結論：這個策略不是 alpha-rich strategy，也不是牛市報酬最大化策略。它比較像 defensive trend-following / exposure-control strategy：牛市會明顯落後 buy-and-hold，但熊市或回撤段能有效降低 exposure 與 drawdown。

研究結論分級：

```text
Research Only
```

原因：雖然 3D / 14D 參數在固定參數 rolling test 中相對穩健，但長期報酬輸給 50% BTC benchmark，且尚未完成成本敏感度與多商品驗證。尚不足以作為 production candidate。

## Hypothesis

當 BTC 短期均線上穿長期均線時，市場進入較強的上升趨勢，策略應該持有 BTC；當短期均線下穿長期均線時，策略退出以降低回撤。

研究假說：

```text
SMA crossover 能犧牲部分牛市 upside，換取熊市與震盪市較低 drawdown。
```

## Data Scope

資料：

```text
source: Coinbase public candles
symbol: BTC-USD
granularity: 1 minute
file: data/coinbase_btc_usd_1m_3y.jsonl
rows: 1,575,771 candles
period: 2023-05-18T06:32:00+00:00 -> 2026-05-17T06:31:00+00:00
```

注意：3 年 BTC 資料仍然不算非常長，實際上主要包含一段大牛市與後續回撤/震盪。這會造成 train/test regime mismatch。

## Strategy Definition

策略：

```text
fast SMA > slow SMA after crossover -> target long notional
fast SMA < slow SMA after crossover -> exit position
```

目前配置：

```text
initial_cash: 100,000
target_notional: 50,000
fee_rate: 0.10%
shorting: disabled
```

交易規則：

```text
BUY signal: fast SMA crosses above slow SMA
SELL signal: fast SMA crosses below slow SMA
BUY sizing: target_notional / signal_price, adjusted by existing position
SELL sizing: close current long position
```

## Execution Assumptions

本研究使用 bar backtest，不使用 tick / order book。

價格定義：

```text
signal price = candle close
fill price = next candle open
equity price = candle close
```

流程：

```text
第 N 根 candle close
-> 用 close 更新 SMA 並產生 order intent
-> order 進入 pending_orders

第 N+1 根 candle open
-> pending market order 用 open 成交

第 N+1 根 candle close
-> 用 close mark-to-market
```

目前限制：

```text
slippage: 0
spread: 0
partial fill: no
latency: one bar via next-open fill
market impact: no
```

這些假設對 BTC 1m 資料是可接受的第一版，但 production 前必須做 cost sensitivity。

## Parameter Search Space

測試的 SMA windows：

```text
fast_windows = [60, 180, 360, 720, 1440, 2880, 4320]
slow_windows = [720, 1440, 2880, 4320, 10080, 20160, 43200]
constraint: fast_window < slow_window
```

對應時間尺度：

```text
60 = 1 hour
1,440 = 1 day
4,320 = 3 days
20,160 = 14 days
43,200 = 30 days
```

## Full-Period Result

Candidate strategy: `4,320 / 20,160`

| Metric | Strategy | BTC Buy & Hold | 50% BTC / 50% Cash |
| --- | ---: | ---: | ---: |
| Total Return | +57.58% | +187.15% | +93.57% |
| Max Drawdown | -14.54% | -52.34% | -43.06% |
| Final Equity | 157,582.65 | 287,148.84 | 193,574.42 |
| Trades | 100 | 1 | 1 |
| Fees | 5,062.62 | not modeled | not modeled |
| Average Exposure | 54.71% | 100.00% | 50.00% |

Interpretation:

- 策略大幅降低 drawdown。
- 策略報酬低於 buy-and-hold，也低於固定 50% BTC exposure。
- 策略價值主要在 exposure timing，而不是長期報酬最大化。

## 70/30 Train/Test Validation

切分：

```text
train: 2023-05-18 -> 2025-06-22
test: 2025-06-22 -> 2026-05-17
```

Underlying benchmark:

```text
train BTC buy-and-hold: +276.52%
test BTC buy-and-hold: -23.72%
```

這代表 train 是大牛市，test 是下跌/震盪 regime。此處存在明顯 regime mismatch。

Validation method:

```text
1. train 區間挑參數。
2. 用選定參數從 train 起點 continuous replay 到 test 結束。
3. 只從 split time 之後統計 test return / drawdown / trades。
4. SMA rolling state、position、pending orders 都不在 test 起點重置。
```

Top train parameters and continuous out-of-sample test:

| Rank | Fast | Slow | Train Return | Train MDD | Test Return | Test MDD | Test Trades | Test Exposure |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1,440 | 43,200 | +74.00% | -11.79% | -3.12% | -10.32% | 28 | 45.33% |
| 2 | 360 | 43,200 | +73.56% | -11.79% | -5.49% | -12.27% | 50 | 45.60% |
| 3 | 4,320 | 43,200 | +71.80% | -12.82% | -3.93% | -10.67% | 17 | 45.85% |
| 4 | 720 | 43,200 | +71.09% | -13.13% | -4.80% | -11.97% | 40 | 45.47% |
| 5 | 2,880 | 43,200 | +69.73% | -13.94% | -4.73% | -11.72% | 21 | 45.77% |
| 6 | 180 | 43,200 | +68.70% | -12.65% | -5.26% | -12.51% | 60 | 45.61% |
| 7 | 2,880 | 4,320 | +67.69% | -8.49% | -9.40% | -12.76% | 132 | 50.95% |
| 8 | 60 | 43,200 | +62.47% | -14.77% | -3.76% | -11.52% | 100 | 45.56% |
| 9 | 2,880 | 20,160 | +53.47% | -12.85% | -1.68% | -10.35% | 32 | 49.75% |
| 10 | 4,320 | 20,160 | +52.23% | -14.54% | +3.51% | -7.05% | 28 | 50.54% |

Interpretation:

- Train return 最高的參數大多是 `slow_window = 43,200`，也就是 30D slow SMA。
- 這些 train top 參數在 test 幾乎全部轉負。
- `4,320 / 20,160` 不是 train 最佳，但在 top 10 中唯一 test 正報酬，且 test drawdown 最低。
- 這支持「不要只追 train return」的結論。

## Fixed-Parameter Rolling Test

這一段固定使用 candidate parameter：

```text
fast_window = 4,320
slow_window = 20,160
```

目的不是重新挑參數，而是檢查同一組參數在不同時間段的 out-of-sample 表現是否穩定。

設定：

```text
lookback / state warmup: 12 months
test window: 3 months
step: 3 months
parameter selection: none, fixed at 4,320 / 20,160
```

Results:

| Segment | Warmup Period | Test Period | Test Return | Test MDD | BTC Test Return | Trades | Exposure |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 2023-05-18 -> 2024-05-17 | 2024-05-17 -> 2024-08-15 | +0.80% | -4.51% | -11.43% | 6 | 42.30% |
| 2 | 2023-08-16 -> 2024-08-15 | 2024-08-15 -> 2024-11-13 | +11.53% | -4.33% | +48.69% | 10 | 69.30% |
| 3 | 2023-11-14 -> 2024-11-13 | 2024-11-13 -> 2025-02-11 | +0.76% | -7.10% | +13.68% | 9 | 61.63% |
| 4 | 2024-02-12 -> 2025-02-11 | 2025-02-11 -> 2025-05-12 | +6.10% | -4.52% | +6.08% | 9 | 47.91% |
| 5 | 2024-05-12 -> 2025-05-12 | 2025-05-12 -> 2025-08-10 | +1.84% | -5.64% | +13.10% | 8 | 62.26% |
| 6 | 2024-08-10 -> 2025-08-10 | 2025-08-10 -> 2025-11-08 | -2.96% | -6.72% | -13.12% | 7 | 45.85% |
| 7 | 2024-11-08 -> 2025-11-08 | 2025-11-08 -> 2026-02-06 | -1.05% | -5.46% | -35.90% | 8 | 42.90% |
| 8 | 2025-02-06 -> 2026-02-06 | 2026-02-06 -> 2026-05-07 | +7.36% | -5.66% | +23.53% | 7 | 50.49% |

Fixed-parameter rolling summary:

```text
segments: 8
compounded test return: +26.18%
average segment return: +3.05%
worst segment return: -2.96%
win rate: 75.00%
```

Interpretation:

- 固定 `4,320 / 20,160` 在 8 段中有 6 段正報酬。
- 大跌段防守明顯，例如 Segment 7，BTC -35.90%，策略 -1.05%。
- 強牛段仍明顯落後 BTC，例如 Segment 2，BTC +48.69%，策略 +11.53%。
- 這比 adaptive parameter selection 更能支持 `4,320 / 20,160` 作為 defensive baseline。

## Adaptive Walk-Forward Parameter Selection

這一段不是固定參數測試，而是模擬每 3 個月重新用過去 12 個月挑參數。

它回答的問題是：

```text
如果研究流程持續重新最佳化參數，樣本外是否穩定？
```

它不應該和固定 `4,320 / 20,160` 的 rolling test 期待相同結果。

設定：

```text
train window: 12 months
test window: 3 months
step: 3 months
parameter selection: maximize train return, tie-break by max drawdown
```

Results:

| Segment | Train Period | Test Period | Selected Fast/Slow | Train Return | Test Return | Test MDD | BTC Test Return | Trades |
| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 2023-05-18 -> 2024-05-17 | 2024-05-17 -> 2024-08-15 | 1,440 / 43,200 | +50.07% | -0.23% | -4.84% | -11.43% | 5 |
| 2 | 2023-08-16 -> 2024-08-15 | 2024-08-15 -> 2024-11-13 | 1,440 / 43,200 | +45.59% | +9.51% | -4.94% | +48.69% | 7 |
| 3 | 2023-11-14 -> 2024-11-13 | 2024-11-13 -> 2025-02-11 | 2,880 / 4,320 | +45.84% | +4.56% | -4.41% | +13.68% | 36 |
| 4 | 2024-02-12 -> 2025-02-11 | 2025-02-11 -> 2025-05-12 | 2,880 / 4,320 | +38.89% | +3.34% | -9.14% | +6.08% | 36 |
| 5 | 2024-05-12 -> 2025-05-12 | 2025-05-12 -> 2025-08-10 | 2,880 / 4,320 | +30.33% | -2.25% | -4.92% | +13.10% | 44 |
| 6 | 2024-08-10 -> 2025-08-10 | 2025-08-10 -> 2025-11-08 | 4,320 / 43,200 | +32.31% | -3.96% | -6.67% | -13.12% | 6 |
| 7 | 2024-11-08 -> 2025-11-08 | 2025-11-08 -> 2026-02-06 | 2,880 / 4,320 | +3.66% | -6.89% | -9.25% | -35.90% | 34 |
| 8 | 2025-02-06 -> 2026-02-06 | 2026-02-06 -> 2026-05-07 | 4,320 / 20,160 | +5.33% | +7.36% | -5.66% | +23.53% | 7 |

Adaptive walk-forward summary:

```text
segments: 8
compounded test return: +10.78%
average segment return: +1.43%
worst segment return: -6.89%
win rate: 50.00%
```

Interpretation:

- Walk-forward 結果比 full-period result 保守很多。
- 策略在大跌段通常比 BTC 防守好，例如 Segment 7，BTC -35.90%，策略 -6.89%。
- 策略在強牛段明顯落後 BTC，例如 Segment 2，BTC +48.69%，策略 +9.51%。
- 參數選擇不穩定，常在 `1D/30D`、`2D/3D`、`3D/14D` 間切換。
- `4,320 / 20,160` 只在最後一段被 walk-forward 選中，不代表它是全市場 regime 的唯一最佳。

## Regime Attribution

Regime definition:

```text
bull: close >= 30D SMA
bear: close < 30D SMA
warmup: 30D SMA 不足
```

Candidate strategy: `4,320 / 20,160`

| Regime | Days | Strategy Return | Max Drawdown | Exposure |
| --- | ---: | ---: | ---: | ---: |
| Bull | 586.5 | +143.11% | -14.04% | 85.76% |
| Bear | 477.8 | -33.20% | -10.55% | 19.59% |
| Warmup | 30.0 | -2.97% | -3.43% | 6.93% |

Interpretation:

- Bull regime 下策略主要靠高 exposure 賺錢，但仍會落後 buy-and-hold。
- Bear regime 下策略仍然虧，但 exposure 降到 19.59%，避免了更大的回撤。
- 策略的主要價值是 bear regime 降 exposure，不是 bull regime 產生超額報酬。

## Monthly Returns

Candidate strategy vs benchmarks:

| Month | Strategy | BTC | 50% BTC |
| --- | ---: | ---: | ---: |
| 2023-05 | +0.00% | +0.15% | +0.07% |
| 2023-06 | +4.36% | +11.91% | +5.96% |
| 2023-07 | -1.29% | -4.06% | -2.03% |
| 2023-08 | -3.67% | -11.29% | -5.65% |
| 2023-09 | -0.67% | +3.97% | +1.98% |
| 2023-10 | +10.60% | +28.62% | +14.31% |
| 2023-11 | +4.94% | +8.82% | +4.41% |
| 2023-12 | +5.67% | +12.03% | +6.02% |
| 2024-01 | -2.39% | +0.64% | +0.32% |
| 2024-02 | +14.97% | +43.83% | +21.91% |
| 2024-03 | +4.69% | +16.61% | +8.30% |
| 2024-04 | -8.63% | -14.99% | -7.49% |
| 2024-05 | +1.73% | +11.32% | +5.66% |
| 2024-06 | -2.25% | -7.12% | -3.56% |
| 2024-07 | +2.37% | +3.08% | +1.54% |
| 2024-08 | -0.36% | -8.73% | -4.36% |
| 2024-09 | +3.69% | +7.40% | +3.70% |
| 2024-10 | +2.20% | +10.91% | +5.46% |
| 2024-11 | +9.23% | +37.38% | +18.69% |
| 2024-12 | -2.25% | -3.19% | -1.60% |
| 2025-01 | -0.85% | +9.71% | +4.85% |
| 2025-02 | -2.39% | -17.62% | -8.81% |
| 2025-03 | -1.25% | -2.07% | -1.04% |
| 2025-04 | +3.89% | +14.15% | +7.07% |
| 2025-05 | +4.09% | +11.11% | +5.55% |
| 2025-06 | -1.14% | +2.41% | +1.21% |
| 2025-07 | +2.35% | +7.98% | +3.99% |
| 2025-08 | -0.63% | -6.53% | -3.26% |
| 2025-09 | +0.54% | +5.37% | +2.68% |
| 2025-10 | -2.10% | -3.96% | -1.98% |
| 2025-11 | -0.27% | -17.52% | -8.76% |
| 2025-12 | -0.60% | -3.17% | -1.59% |
| 2026-01 | +0.18% | -10.14% | -5.07% |
| 2026-02 | +0.00% | -14.83% | -7.41% |
| 2026-03 | +0.62% | +1.88% | +0.94% |
| 2026-04 | +3.31% | +11.82% | +5.91% |
| 2026-05 | +0.29% | +2.29% | +1.14% |

Observations:

- 大漲月份策略通常落後 BTC。
- 大跌月份策略防守效果明顯，例如 2025-11、2026-01、2026-02。
- 2024-04 策略 -8.63%，略差於 50% BTC benchmark 的 -7.49%，代表 trend-following exit 並不總是比固定曝險好。

## Parameter Stability

Stability findings:

- 單次 70/30 train top 參數集中在 `slow_window = 43,200`，但 test 大多轉負。
- `4,320 / 20,160` 在 70/30 中 train 排名第 10，但 test 最佳。
- 固定 `4,320 / 20,160` rolling test 有 75% segment win rate，支持它作為 defensive baseline。
- Adaptive walk-forward 中被選到的參數不穩定：
  - `1,440 / 43,200`
  - `2,880 / 4,320`
  - `4,320 / 43,200`
  - `4,320 / 20,160`

Interpretation:

```text
不存在一個明顯穩定的全 regime 最佳 SMA pair。
```

較合理的說法是：

```text
4,320 / 20,160 是目前較穩健的 defensive baseline，
但 adaptive parameter selection 顯示不同 regime 會偏好不同 SMA pair。
```

這降低了策略的 production confidence。

## Failure Modes

已觀察到的失效條件：

- 強牛市：策略因 target_notional 與 delayed crossover，會大幅落後 buy-and-hold。
- 快速 V 型反轉：SMA lag 會導致退出後追高買回，或在低點附近退出。
- 長時間震盪：crossover 會反覆交易，費用與 whipsaw 侵蝕收益。
- Regime transition：train 在牛市挑出的參數，test 進入熊市時容易失效。
- 單商品依賴：只測 BTC，不能推論到其他商品。

## Cost Sensitivity

成本敏感度使用固定 `4,320 / 20,160` 參數。

注意：此處 `trades` 在 trade attribution 中以 round-trip 計算，共 50 筆；前文 `trades: 100` 指 entry/exit fills 數。

| Fee | Slippage | Return | Max Drawdown | Final Equity |
| ---: | ---: | ---: | ---: | ---: |
| 0.05% | 0 bps | +60.11% | -14.31% | 160,113.95 |
| 0.05% | 5 bps | +57.58% | -14.54% | 157,582.66 |
| 0.05% | 20 bps | +49.99% | -15.25% | 149,988.78 |
| 0.10% | 0 bps | +57.58% | -14.54% | 157,582.65 |
| 0.10% | 5 bps | +55.05% | -14.77% | 155,051.37 |
| 0.10% | 20 bps | +47.46% | -15.49% | 147,457.54 |
| 0.20% | 0 bps | +52.52% | -15.01% | 152,520.03 |
| 0.20% | 5 bps | +49.99% | -15.25% | 149,988.78 |
| 0.20% | 20 bps | +42.40% | -15.97% | 142,395.04 |

Interpretation:

- 策略不是高頻策略，成本壓力沒有立刻摧毀結果。
- 即使 fee 0.20% 且 slippage 20 bps，3 年仍為正報酬，但 return 從 +57.58% 降到 +42.40%。
- Production 前仍需用真實 bid/ask、volume cap 與 broker fee tier 做更精細模型。

## Senior Quant Addendum

以下補充 senior quant report 中最優先的檢查項目。

### Advanced Performance Metrics

| Metric | Strategy 3D/14D | BTC Buy & Hold | Exposure-Matched BTC | 50% BTC |
| --- | ---: | ---: | ---: | ---: |
| Total Return | +57.58% | +187.15% | +102.39% | +93.57% |
| CAGR | +16.38% | +42.17% | +26.51% | +24.65% |
| Annualized Vol | 14.01% | 47.97% | 35.80% | 34.08% |
| Sharpe | 1.15 | 0.97 | 0.84 | 0.82 |
| Sortino | 1.61 | 1.37 | 1.18 | 1.15 |
| Max Drawdown | -14.54% | -52.34% | -44.42% | -43.06% |
| Calmar | 1.13 | 0.81 | 0.60 | 0.57 |
| 5% VaR per minute | -0.0257% | -0.0934% | -0.0700% | -0.0667% |
| 5% CVaR per minute | -0.0470% | -0.1543% | -0.1161% | -0.1106% |
| Skew | -0.75 | -0.31 | -0.28 | -0.28 |
| Excess Kurtosis | 241.46 | 66.59 | 54.96 | 54.26 |

Interpretation:

- 策略報酬低於 exposure-matched BTC benchmark，但 Sharpe、Sortino、Calmar 明顯較高。
- 策略更像 risk-shaping / drawdown-control overlay，而不是 return-maximizing alpha。
- Kurtosis 很高，代表 minute return tail 仍重，不能忽略 extreme events。

### Trade-Level Attribution

Round-trip trades:

```text
round_trip_trades: 50
win_rate: 40.00%
average_win: 5,466.23
average_loss: -1,724.73
median_pnl: -527.12
profit_factor: 2.11
average_holding_period: 11.97 days
median_holding_period: 8.39 days
```

Interpretation:

- 勝率低於 50%，但 payoff ratio 較好，靠少數較大趨勢段賺錢。
- Median trade PnL 為負，代表很多 crossover 是小虧或 whipsaw。
- 這是典型 trend-following profile：低勝率、靠大贏家補償多數小輸家。

### Exposure-Adjusted Benchmark

策略平均 exposure：

```text
average_exposure: 54.71%
```

因此只和 100% BTC buy-and-hold 比不公平，也應該比較同等平均曝險的 BTC benchmark。

```text
exposure-matched BTC return: +102.39%
exposure-matched BTC max drawdown: -44.42%
strategy return: +57.58%
strategy max drawdown: -14.54%
```

Interpretation:

- 策略 return 輸給同等平均曝險 BTC。
- 策略 drawdown 大幅較低。
- 結論仍是：策略價值在 drawdown control，不在 raw return。

### Parameter Robustness Summary

Full-period top parameters:

| Fast | Slow | Return | Sharpe | Max Drawdown |
| ---: | ---: | ---: | ---: | ---: |
| 1,440 | 43,200 | +68.58% | 1.31 | -11.79% |
| 4,320 | 43,200 | +65.06% | 1.23 | -12.82% |
| 360 | 43,200 | +64.03% | 1.24 | -12.27% |
| 720 | 43,200 | +62.88% | 1.22 | -13.13% |
| 2,880 | 43,200 | +61.70% | 1.19 | -13.94% |
| 180 | 43,200 | +59.83% | 1.16 | -13.02% |
| 4,320 | 20,160 | +57.58% | 1.15 | -14.54% |
| 60 | 43,200 | +56.36% | 1.09 | -14.77% |

Interpretation:

- Full-period 最佳區域偏向 `slow_window = 43,200`，也就是 30D slow SMA。
- 但 70/30 continuous test 中，這些 full/train 高報酬參數在 test 多數轉負。
- `4,320 / 20,160` raw return 不是最高，但 out-of-sample 防守性較好。

### Multi-Window Fixed-Parameter Walk-Forward

固定參數 `4,320 / 20,160`，測不同 train/test window。

| Train | Test | Step | Segments | Compounded Return | Avg Segment Return | Worst Segment | Win Rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 180D | 30D | 30D | 30 | +47.98% | +1.45% | -9.52% | 56.67% |
| 365D | 90D | 90D | 8 | +26.18% | +3.05% | -2.96% | 75.00% |
| 540D | 90D | 90D | 6 | +14.66% | +2.36% | -2.69% | 66.67% |
| 730D | 180D | 180D | 2 | +4.58% | +2.31% | -0.64% | 50.00% |

Interpretation:

- 固定參數在多數 rolling setups 仍為正 compounded return。
- 30D test window 較容易受 whipsaw 影響，worst segment 到 -9.52%。
- 長 test window 樣本數太少，不足以定論。

### Data Quality Audit

Basic OHLCV checks:

```text
rows: 1,575,771
time gaps: 44
duplicates: 0
bad_ohlc: 0
zero_volume: 0
```

Interpretation:

- OHLC consistency 通過。
- 有 44 個 1-minute time gaps，需要在 production-grade report 中列出實際時間點並判斷是否為 Coinbase outage / API missing data。
- 目前這些 gaps 對低頻 SMA 應該影響有限，但不能完全忽略。

### Still Not Done

以下項目仍未完成，因此本策略仍不能升級到 Paper Trade Candidate：

- formal bootstrap confidence interval
- multiple-testing-adjusted Sharpe / deflated Sharpe
- MAE / MFE trade path attribution
- detailed choppy regime attribution
- volume cap / market impact model
- multi-asset validation
- volatility-targeted sizing
- portfolio context and correlation analysis
- live monitoring and kill-switch specification

## Research Value vs Trading Decision Value

Research value:

```text
Medium
```

理由：

- 策略性格清楚：防守型 trend-following。
- 能有效展示 bull/bear exposure 差異。
- 能揭露 train/test regime mismatch。
- 能作為後續更完整 trend model 的 baseline。

Trading decision value:

```text
Low to Medium
```

理由：

- 報酬輸給 50% BTC benchmark。
- 固定參數 rolling test 勝率 75%，但 adaptive walk-forward 參數選擇不穩。
- 尚未完成 slippage / spread sensitivity。
- 尚未做多商品驗證。

## Conclusion

`SMA 3D / 14D` 可以作為 BTC defensive trend-following baseline，但不應直接上 production。

目前最可靠的結論是：

```text
SMA crossover 單獨使用時，不是強 alpha。
它的價值主要是控制 exposure 與降低 drawdown。
```

建議下一步：

1. 補 cost sensitivity。
2. 增加 volatility targeting benchmark。
3. 測 ETH-USD / SOL-USD 等多商品。
4. 測 regime-aware sizing，而不是固定 50,000 notional。
5. 把 SMA signal 拆成 signal layer，讓 strategy layer 專注 sizing / risk。
6. 做更細的 parameter stability heatmap。

Final classification:

```text
Research Only
```

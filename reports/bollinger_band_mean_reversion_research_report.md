# Bollinger Band Mean-Reversion Research Report

Date: 2026-05-17

## Executive Summary

本研究測試 BTC-USD 1 分鐘資料上的 long-only Bollinger Band mean-reversion strategy。

候選參數：

```text
window = 10,080      # 約 7 天
num_stddev = 2.0
```

完整 3 年回測結果：

```text
period: 2023-05-18T06:32:00+00:00 -> 2026-05-17T06:31:00+00:00
strategy return: +18.52%
CAGR: +5.83%
Sharpe: 0.54
Sortino: 0.76
max drawdown: -17.94%
fills: 193
round-trip trades: 97
fees: 9,679.20
average exposure: 27.07%
final equity: 118,518.13
```

Benchmark:

```text
BTC buy-and-hold return: +187.15%
BTC buy-and-hold max drawdown: -52.34%

Exposure-matched BTC return: +50.67%
Exposure-matched BTC max drawdown: -33.12%

50% BTC / 50% cash return: +93.57%
50% BTC / 50% cash max drawdown: -43.06%
```

Conclusion:

```text
Research Only / Reject as standalone strategy
```

理由：

- Raw return、Sharpe、Sortino、Calmar 都明顯弱於 SMA baseline。
- 70/30 continuous test 為負。
- Fixed rolling test 勝率只有 50%。
- Cost sensitivity 較脆弱，fee 0.10% + slippage 20 bps 時接近打平，fee 0.20% + slippage 20 bps 時轉負。
- Bear regime exposure 過高，與「防守型」目標不一致。

## Hypothesis

Bollinger Band mean-reversion 假說：

```text
當 BTC close 跌破 lower Bollinger Band 時，短期價格可能過度下跌；
策略買入等待價格回到 middle band 後出場。
```

這是 mean-reversion baseline，不是 breakout strategy。

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

Data quality quick audit:

```text
time gaps: 44
duplicates: 0
bad_ohlc: 0
zero_volume: 0
```

## Strategy Definition

Long-only Bollinger Band mean-reversion:

```text
middle = SMA(close, window)
std = standard deviation(close, window)
lower = middle - num_stddev * std

entry: close < lower
exit: close >= middle
```

Sizing:

```text
initial_cash: 100,000
target_notional: 50,000
shorting: disabled
```

Implementation:

```text
strategies/bollinger_band_strategy.py
class BollingerBandMeanReversionStrategy
```

## Execution Assumptions

價格定義：

```text
signal price = candle close
fill price = next candle open
equity price = candle close
```

成本假設：

```text
base fee: 0.10%
base slippage: 0 bps
spread: not modeled
partial fill: not modeled
market impact: not modeled
```

## Parameter Search Space

測試參數：

```text
windows = [60, 180, 360, 720, 1440, 2880, 4320, 10080]
num_stddev = [1.5, 2.0, 2.5, 3.0]
```

Full-period top parameters:

| Window | StdDev | Return | Sharpe | Max Drawdown | Fills | Exposure |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10,080 | 2.0 | +18.52% | 0.54 | -17.94% | 193 | 27.07% |
| 10,080 | 1.5 | +16.22% | 0.46 | -21.68% | 261 | 31.64% |
| 10,080 | 3.0 | +8.18% | 0.30 | -18.90% | 103 | 16.79% |
| 10,080 | 2.5 | +7.93% | 0.28 | -20.47% | 135 | 22.33% |
| 4,320 | 3.0 | -5.40% | -0.09 | -28.06% | 274 | 20.16% |
| 4,320 | 1.5 | -8.65% | -0.13 | -26.56% | 611 | 33.43% |
| 4,320 | 2.5 | -9.09% | -0.17 | -29.62% | 354 | 24.05% |
| 4,320 | 2.0 | -9.89% | -0.18 | -31.15% | 451 | 28.83% |

Interpretation:

- 只有 7D window 組合有正報酬。
- 較短 window 幾乎全面失效，交易頻率高且 whipsaw 嚴重。
- 最佳參數區域很窄，robustness 不佳。

## Full-Period Result

Candidate strategy: `window=10,080`, `std=2.0`

| Metric | Strategy | BTC Buy & Hold | Exposure-Matched BTC | 50% BTC |
| --- | ---: | ---: | ---: | ---: |
| Total Return | +18.52% | +187.15% | +50.67% | +93.57% |
| CAGR | +5.83% | +42.17% | +14.65% | +24.65% |
| Annualized Vol | 11.91% | 47.97% | 23.42% | 34.08% |
| Sharpe | 0.54 | 0.97 | 0.70 | 0.82 |
| Sortino | 0.76 | 1.37 | 0.99 | 1.15 |
| Max Drawdown | -17.94% | -52.34% | -33.12% | -43.06% |
| Calmar | 0.33 | 0.81 | 0.44 | 0.57 |
| Final Equity | 118,518.13 | 287,148.84 | 150,669.60 | 193,574.42 |

Interpretation:

- 策略降低 volatility 與 drawdown，但報酬太低。
- Sharpe、Sortino、Calmar 全部輸給 benchmark。
- 相比 exposure-matched BTC，策略沒有足夠證據顯示有 alpha。

## 70/30 Train/Test Validation

切分：

```text
train: 2023-05-18 -> 2025-06-22
test: 2025-06-22 -> 2026-05-17
```

Continuous test：不重置 rolling window、position 或 pending orders，只從 split 後統計 test performance。

Top train parameters:

| Window | StdDev | Train Return | Train MDD | Test Return | Test MDD |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 10,080 | 2.0 | +28.45% | -11.74% | -7.72% | -17.94% |
| 10,080 | 1.5 | +27.30% | -13.69% | -8.70% | -21.68% |
| 10,080 | 2.5 | +22.80% | -12.47% | -12.10% | -20.47% |
| 10,080 | 3.0 | +18.96% | -12.24% | -9.05% | -18.90% |
| 4,320 | 3.0 | +10.46% | -10.47% | -14.35% | -25.98% |
| 4,320 | 2.0 | +8.16% | -11.05% | -16.68% | -30.09% |

Interpretation:

- Train top parameters 在 test 全部轉負。
- Candidate `10,080 / 2.0` 是 train 最佳，但 test -7.72%。
- 這是明顯 overfit / regime mismatch warning。

## Fixed-Parameter Rolling Test

固定 candidate `10,080 / 2.0`：

| Test Period | Strategy Return | MDD | BTC Return |
| --- | ---: | ---: | ---: |
| 2024-05-17 -> 2024-08-15 | -1.46% | -11.74% | -11.43% |
| 2024-08-15 -> 2024-11-13 | +5.07% | -5.17% | +48.69% |
| 2024-11-13 -> 2025-02-11 | +11.09% | -3.86% | +13.68% |
| 2025-02-11 -> 2025-05-12 | -0.82% | -7.48% | +6.08% |
| 2025-05-12 -> 2025-08-10 | +2.78% | -2.35% | +13.10% |
| 2025-08-10 -> 2025-11-08 | -6.19% | -8.50% | -13.12% |
| 2025-11-08 -> 2026-02-06 | -11.24% | -15.64% | -35.90% |
| 2026-02-06 -> 2026-05-07 | +8.65% | -5.60% | +23.53% |

Summary:

```text
segments: 8
compounded return: +6.08%
average segment return: +0.99%
worst segment: -11.24%
win rate: 50.00%
```

Interpretation:

- Rolling stability weak.
- 策略有些下跌段能防守，但 2025-11 -> 2026-02 仍 -11.24%。
- 強牛段大幅落後 BTC，例如 2024-08 -> 2024-11。

## Regime Attribution

Regime definition:

```text
bull: close >= 30D SMA
bear: close < 30D SMA
```

| Regime | Days | Return | Max Drawdown | Exposure |
| --- | ---: | ---: | ---: | ---: |
| Bull | 586.5 | +51.34% | -12.51% | 9.75% |
| Bear | 477.8 | -24.22% | -17.90% | 48.49% |
| Warmup | 30.0 | +3.34% | -2.07% | 24.82% |

Interpretation:

- Mean-reversion strategy 在 bear regime 中 exposure 過高。
- Bull regime exposure 只有 9.75%，所以大幅錯過上漲。
- 這和 BTC 這類強趨勢資產不匹配。

## Monthly Returns

| Month | Strategy | BTC | 50% BTC | Exposure |
| --- | ---: | ---: | ---: | ---: |
| 2023-05 | +1.02% | +0.15% | +0.07% | 9.50% |
| 2023-06 | +2.97% | +11.91% | +5.96% | 20.98% |
| 2023-07 | +1.18% | -4.06% | -2.03% | 29.87% |
| 2023-08 | -2.13% | -11.29% | -5.65% | 39.81% |
| 2023-09 | +1.02% | +3.97% | +1.98% | 10.16% |
| 2023-10 | -0.36% | +28.62% | +14.31% | 15.33% |
| 2023-11 | +4.30% | +8.82% | +4.41% | 7.07% |
| 2023-12 | +4.62% | +12.03% | +6.02% | 24.89% |
| 2024-01 | -2.07% | +0.64% | +0.32% | 43.63% |
| 2024-02 | +1.43% | +43.83% | +21.91% | 8.55% |
| 2024-03 | +0.74% | +16.61% | +8.30% | 17.68% |
| 2024-04 | -1.52% | -14.99% | -7.49% | 44.09% |
| 2024-05 | +3.19% | +11.32% | +5.66% | 22.11% |
| 2024-06 | -0.05% | -7.12% | -3.56% | 63.51% |
| 2024-07 | +0.36% | +3.08% | +1.54% | 21.31% |
| 2024-08 | -1.91% | -8.73% | -4.36% | 42.23% |
| 2024-09 | -0.84% | +7.40% | +3.70% | 25.78% |
| 2024-10 | +2.25% | +10.91% | +5.46% | 31.28% |
| 2024-11 | +3.92% | +37.38% | +18.69% | 7.25% |
| 2024-12 | +5.81% | -3.19% | -1.60% | 22.16% |
| 2025-01 | +1.24% | +9.71% | +4.85% | 26.13% |
| 2025-02 | -2.35% | -17.62% | -8.81% | 31.57% |
| 2025-03 | +1.56% | -2.07% | -1.04% | 28.79% |
| 2025-04 | +0.95% | +14.15% | +7.07% | 12.08% |
| 2025-05 | -0.12% | +11.11% | +5.55% | 7.90% |
| 2025-06 | +1.13% | +2.41% | +1.21% | 20.14% |
| 2025-07 | +1.75% | +7.98% | +3.99% | 8.29% |
| 2025-08 | -0.05% | -6.53% | -3.26% | 51.34% |
| 2025-09 | -0.44% | +5.37% | +2.68% | 26.70% |
| 2025-10 | -2.85% | -3.96% | -1.98% | 36.91% |
| 2025-11 | -6.77% | -17.52% | -8.76% | 65.36% |
| 2025-12 | +5.97% | -3.17% | -1.59% | 24.42% |
| 2026-01 | -5.04% | -10.14% | -5.07% | 32.30% |
| 2026-02 | -2.71% | -14.83% | -7.41% | 56.10% |
| 2026-03 | +1.11% | +1.88% | +0.94% | 28.60% |
| 2026-04 | +0.85% | +11.82% | +5.91% | 7.40% |
| 2026-05 | +0.20% | +2.29% | +1.14% | 18.03% |

## Trade-Level Attribution

```text
round_trip_trades: 97
win_rate: 73.20%
average_win: 976.86
average_loss: -1,955.35
median_pnl: 572.21
profit_factor: 1.36
average_holding_period: 3.05 days
median_holding_period: 1.95 days
```

Interpretation:

- 勝率高，但 average loss 約為 average win 的 2 倍。
- Profit factor 只有 1.36，edge 不強。
- Mean-reversion 常見問題出現：多數小贏，但遇到 trend continuation 時虧損較大。

## Cost Sensitivity

| Fee | Slippage | Return | Max Drawdown |
| ---: | ---: | ---: | ---: |
| 0.05% | 0 bps | +23.36% | -17.05% |
| 0.05% | 5 bps | +18.52% | -17.94% |
| 0.05% | 20 bps | +4.00% | -21.32% |
| 0.10% | 0 bps | +18.52% | -17.94% |
| 0.10% | 5 bps | +13.68% | -18.87% |
| 0.10% | 20 bps | -0.84% | -22.98% |
| 0.20% | 0 bps | +8.84% | -19.90% |
| 0.20% | 5 bps | +4.00% | -21.32% |
| 0.20% | 20 bps | -10.52% | -26.61% |

Interpretation:

- 策略比 SMA 更成本敏感。
- 在 moderate stress 下 edge 很快消失。
- 這是布林 mean-reversion 不適合 production 的重要原因。

## Failure Modes

- Trend continuation：價格跌破 lower band 後繼續下跌，策略接刀。
- Bear regime overexposure：bear exposure 48.49%，導致下跌段虧損。
- Bull underexposure：bull exposure 9.75%，錯過大部分上漲。
- Cost drag：交易比 SMA 多，fee / slippage 侵蝕更明顯。
- Narrow parameter robustness：只有 7D window 附近為正，短 window 全面失效。

## Still Not Done

- breakout variant：close above upper band entry / middle exit。
- volatility regime filter。
- trend filter，例如只在 30D trend up 時做 mean reversion。
- MAE / MFE path attribution。
- formal statistical significance / bootstrap。
- multi-asset validation。
- volume cap / bid-ask spread model。

## Conclusion

Bollinger Band mean-reversion 在 BTC 1m 3 年資料上不如 SMA crossover baseline。

最重要結論：

```text
BTC 在此樣本中更像 trend-dominated asset；
單純 lower-band mean-reversion 容易在 bear regime 過度持倉，
並在 bull regime 持倉不足。
```

Final classification:

```text
Research Only / Reject as standalone strategy
```

可保留的研究方向：

```text
只把 Bollinger Band 當作 entry timing，
但需要 trend filter / volatility filter / risk overlay。
```

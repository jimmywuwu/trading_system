# Event Study Report: oi_contraction_vol_regime（90d + 365d）

- created_at: 2026-07-08（/research-cycle #4，/run-backtest 階段）
- hypothesis: `reports/research/oi-contraction-vol-regime/hypothesis.md`
- signal contract: `reports/research/oi-contraction-vol-regime/signal_contract.md`
- **結論評級：`reject`（作為可行動的波動警示訊號）**——理由見 §5

## 1. 資料範圍與方法

| 項目 | 值 |
|---|---|
| Fixtures | `data/bybit_leverage_pressure_fixture_90d.jsonl`、`_365d.jsonl` |
| Symbols | BTCUSDT、ETHUSDT（Bybit linear perp，單一交易所） |
| 價格序列 | linear_perp 5m candles（90d: 25,919 根；365d: 105,119 根/symbol） |
| Signal 參數 | change_window 4h、history 14d、trigger p10、rearm p20、需 change<0 |
| 事件產生 | `backtest.ReplayDataProvider` 逐 tick 重播（lookahead guard 啟用） |
| 事件去重 | 訊號端遲滯 + study 端 24h 非重疊（僅留 episode 首事件） |
| 對照 | 每事件 20 個 anchors，match on trailing 24h realized vol（主 null）與 trailing 4h signed return；排除任何事件 ±24h 內的時點 |
| 度量 | forward realized vol = sqrt(Σ 5m log return²)；lift = event/control − 1 |
| CI | 事件層 bootstrap 1000 reps，seed 20260708 |

重跑指令：

```bash
python3 reports/research/oi-contraction-vol-regime/run_vol_event_study.py \
  data/bybit_leverage_pressure_fixture_90d.jsonl --out .../vol_event_study_90d.json
python3 reports/research/oi-contraction-vol-regime/run_vol_event_study.py \
  data/bybit_leverage_pressure_fixture_365d.jsonl --out .../vol_event_study_365d.json
```

完整數字：`reports/research/oi-contraction-vol-regime/vol_event_study_{90d,365d}.json`

## 2. 預註冊判準（hypothesis.md 的 minimum_effect_after_cost）

> 非重疊 episode 下，24h realized vol 相對 vol-matched 對照 lift >= **+15%**，
> 且 BTC 與 ETH 同號、時間切分兩半皆成立。低於此視為不可用並否決。

## 3. 結果：365d（n=110 BTC / 117 ETH 非重疊事件）

vol_lift（vol-matched 對照），CI95 為 bootstrap 區間：

| horizon | BTC | BTC CI95 | ETH | ETH CI95 |
|---|---|---|---|---|
| 4h | **+17.1%** | [+4.8%, +34.0%] | **+15.8%** | [+2.4%, +35.9%] |
| 8h | +10.4% | [−3.6%, +30.2%] | +6.1% | [−4.8%, +20.1%] |
| **24h（判準）** | **+10.5%** | [+1.1%, +22.2%] | **+9.8%** | [+2.7%, +17.8%] |

return-matched 對照（次 null）：同號但更弱（BTC 24h +6.2% CI 含零；ETH 24h +12.5% CI 不含零）。

時間切分（24h，vol-matched）：

| 半樣本 | BTC | BTC CI95 | ETH | ETH CI95 |
|---|---|---|---|---|
| 前半年 | **+21.9%** | [+3.7%, +48.8%] | **+18.9%** | [+8.8%, +31.3%] |
| 後半年 | +2.2% | [−6.8%, +11.6%] | +1.9% | [−7.7%, +11.9%] |

## 4. 結果：90d（最近樣本，n=26/symbol）

| 對照 | horizon | BTC | ETH |
|---|---|---|---|
| vol-matched | 4h | −11.5% | +5.2% |
| vol-matched | 8h | **−16.9%**（CI [−28%, −4%]，顯著為負） | −0.8% |
| vol-matched | 24h | −0.2% | −1.1% |

最近 90 天不但沒有波動擴張，BTC 在 8h horizon 甚至出現顯著的**波動壓縮**。

## 5. 判準評估與結論

| 判準 | 結果 |
|---|---|
| 24h vol-matched lift ≥ +15% | ❌ BTC +10.5%、ETH +9.8% |
| BTC/ETH 同號 | ✅ 全樣本同為正 |
| 時間切分兩半皆成立 | ❌ 效應集中在前半年，後半年 ≈ 0 |
| （加測）最近 90d | ❌ 零或負 |

**評級：`reject`（作為可行動訊號）。** 誠實的完整敘述：

- 效應在統計上**存在**（365d 全樣本多個 CI 不含零、兩標的、兩種對照同號）
  ——v1 草稿的初步觀察不是幻覺；
- 但幅度低於預註冊的可用門檻，且**時間上不穩定**：集中在樣本前半年
  （2025-06 ~ 2025-12，含 09-21、10-10、11-20 等大型去槓桿 episode），
  最近 90 天已消失甚至反轉；
- 一個「你不知道它現在還在不在」的 risk filter 比沒有 filter 更危險
  （會在該減倉時給你虛假的安全感），因此不進入 strategy/paper 階段。

## 6. 假設與未驗證項

- OI `observed_at` 採 conservative_simulated_observed_at（fixture 語意），
  未經 live 驗證。
- 單一交易所（Bybit）；跨所去槓桿的同時性未檢驗。
- 無成本建模：本假說不直接交易，reject 不因成本而是因效應不穩定。
- 參數鄰域（p05/p20、history 90d）未掃描——效應已低於門檻，
  掃參數只會製造過擬合風險，故意不做。

## 7. 給 /promote-strategy 的建議

status=rejected；do_not_repeat_until 建議：(1) 跨所（≥3 venues）OI 資料
可用，能檢驗「全市場同時去槓桿」版本；或 (2) 任何未來 90d 滾動樣本
重新出現 ≥+15% 的 lift（衰減可能是 regime 性的）。單純換 trigger
percentile / horizon 重跑不算新證據。

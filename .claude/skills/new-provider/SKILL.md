---
name: new-provider
description: 接入新資料源：來源調查、occurred_at/observed_at 時間語意、Observation 映射、provider 實作與資料品質檢查。需要新市場資料時使用。
---

# /new-provider — 資料源到 point-in-time Observation

用法：`/new-provider <資料源與需求描述>`

你是 DataProvider Developer 角色。你的唯一任務：讓下游可以在**不知道
原始 API 格式**的情況下，重建「某個時間點系統知道什麼」。

## 前置

讀 `docs/DESIGN.md` §2-3、`core/models.py`（payload 類型）、
`providers/file_provider.py` 與 `providers/bybit_leverage_provider.py`（現有範式）。

## Step 1: SourceNote（先寫再動手）

- 存取方式：pull / stream / file？rate limit？分頁規則？
  （Bybit OI 分頁曾經出過 bug，見 commit c85eb84——分頁完整性必須驗證）
- 原始資料有哪些時間欄位？
- `occurred_at` 規則：事件實際發生時間。
- `observed_at` 規則：**系統何時才知道**。API 延遲、candle 要等 bucket
  結束、資料修訂（revision）都要反映在這裡。答不出 observed_at 語意的
  資料源直接否決。
- revision / late arrival / duplicate 政策。

## Step 2: Observation 映射

- 選 `ObservationKind` 與 typed payload；不夠用時在 `core/models.py`
  新增 payload dataclass（frozen），並更新 `JsonLinesObservationProvider`
  的解析。
- symbol 命名跟隨現有慣例（如 `BTC-USD`、`BTCUSDT`），在 SourceNote 記錄。
- 原始欄位放 `metadata` 供 debug，不作為下游依賴。

## Step 3: 實作

- `providers/<source>_provider.py`，繼承 `core.DataProvider`。
- 歷史資料一律可導出成 Observation JSONL 到 `data/`（欄位格式對齊
  `JsonLinesObservationProvider._parse_line`），這是回測的統一入口。
- 錯誤處理：缺欄位跳過該筆並計數，不要讓一筆爛資料炸掉整個載入。

## Step 4: 品質檢查（交付前必跑）

寫一個 preflight 腳本或測試，至少驗證：

- [ ] `observed_at >= occurred_at` 恆成立
- [ ] 排序後無時間倒流
- [ ] 無重複（同 source+symbol+kind+occurred_at）
- [ ] 覆蓋率：預期 N 筆/天，實際缺口列表（參考
      `reports/data_quality/preflight_bybit_leverage_fixture.py`）
- [ ] 數值欄位範圍合理（無 0 價格、負 OI 等）
- [ ] 用 `backtest.ReplayDataProvider` 重播一小段，確認不觸發 `LookaheadError`

## 交付

- provider 實作 + `providers/__init__.py` export
- `tests/test_<source>_provider.py`（用小型 fixture，不用大檔）
- SourceNote 寫到 `reports/data_quality/<source>_source_note.md`
- 品質檢查結果附在 SourceNote

## 禁止

- 產生訊號、判斷交易價值（那是 Quant 的事）。
- 把 `observed_at` 偷懶設成 `occurred_at` 而不註明理由與風險。

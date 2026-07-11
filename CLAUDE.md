# trading_system

Point-in-time 交易研究系統。最高層設計依據：`docs/DESIGN.md`（先讀它）。

自主研究閉環（agent 每個 cycle 怎麼選 skill、看板、預算與停損）：
`docs/AGENT_OPERATIONS.md`。目前 pipeline 狀態看 `reports/PIPELINE.md`。

## 不可違反的規則

1. 可見性只看 `observed_at`；回測中讀未來資料會（也應該）拋 `LookaheadError`。
2. 單向資料流：`Provider -> Observation -> Signal -> SignalEvent -> Strategy -> OrderIntent -> Execution -> Fill -> Portfolio`。指標邏輯只准在 `signals/`，sizing/風控只准在 `strategies/`。
3. 回測結論必須含成本（fee + slippage）與 buy-and-hold 基準。
4. 相同輸入必須產生相同輸出（決定性）。
5. 研究結論評級：`reject` / `research_only` / `paper_trade_candidate` / `production_candidate`，升級一律走 `/promote-strategy` 並寫 DecisionRecord 到 `reports/decisions/`。

## 研究流程（skills）

```text
/research-cycle   自主閉環的循環體：選一個工作項推進一個階段（loop 用它）
/research-idea    想法 -> 可證偽假說（新研究唯一入口）
/new-provider     接新資料源 -> Observation JSONL
/new-signal       假說 -> SignalContract -> 實作 -> 測試 -> smoke replay
/run-backtest     event study -> 回測 -> benchmark -> 穩健性 -> 報告
/new-strategy     Trader：訊號 -> StrategyContract -> sizing/風控實作 -> 整合回測
/promote-strategy 四道 review gate -> DecisionRecord
```

## 常用指令

```bash
python3 -m pytest                          # 全部測試（必須全綠才算完成）
python3 scripts/run_backtest.py --data data/coinbase_btc_usd_1m_last_year.jsonl \
    --symbol BTC-USD --fast 240 --slow 1440 --max-lines 100000   # 快速回測示範
```

## 目錄地圖

- `core/` — 契約（Observation、Signal、Strategy、OrderIntent）。改動視同 breaking change。
- `backtest/` — 回測引擎：`ReplayDataProvider`（lookahead guard）、`BacktestEngine`、`SimulatedExecution`（下一根 open 成交）、`Portfolio`、`compute_metrics`。
- `research/` — `forward_return_study`、`buy_and_hold_metrics`。
- `signals/sma_cross.py` + `strategies/signal_position_strategy.py` — 標準垂直切片，新 signal/strategy 照這個範式寫。
- `providers/` — 資料接入；歷史資料統一導出成 Observation JSONL 放 `data/`（不進 git）。
- `tests/conftest.py` — `make_candles()` 合成 candle 工廠，寫測試用它。
- `reports/{backtests,research,decisions}/` — 研究產出與決策記錄（append-only）。

## Legacy（不要模仿、不要擴充）

- v1 的模擬式多代理 runtime（`.agents/`、`MULTI_AGENT_RUNTIME.md`、角色/persona 檔）已於
  2026-07-11 移出 repo，由 skills + `reports/` artifacts 取代；備份在 repo 外的
  `trading_system_legacy_backup_20260711.tar.gz`。不要重建多代理編排（理由見
  `docs/AGENT_OPERATIONS.md` §1.1）。
- `ROLES.md`、`BACKTEST.md` 保留：仍被 skills 與 `backtest/` 引用。
- `strategies/` 下除 `signal_position_strategy.py` 外的策略 — 指標與 sizing 混在一起，僅供對照。
- `reports/notion_drafts/` — v1 時代研究草稿，只讀參考。

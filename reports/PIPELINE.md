# Research Pipeline

更新：2026-07-08 by /research-cycle #6

## Active（最多 3 個）

| id | 假說一句話 | 階段 | 下一步 skill | cycles 已用 | 阻塞 |
|---|---|---|---|---|---|
| cross-venue-funding-dispersion | 穩定 venue 配對的 funding gap 可作 delta-neutral carry（變體 B；變體 A 事件收斂已在 Gate 2 被成本算術否決） | 假說通過（Gate 0-2），資料未就緒 | /new-provider（90d+ 三所對齊 funding fixture） | 1 | - |

備註（給 /new-provider）：
- 來源：Bybit / OKX / Hyperliquid funding history，公開 REST、免 key、免費 → 不觸發人核可點；如環境無網路則移 Blocked。
- 驗收起點：milestone2 的 DataProvider TODO（`reports/cross_venue_dispersion/milestone2_btc_funding_dispersion.md` §DataProvider TODO）——分頁確定性測試、raw payload hash、observed_at 語意、**完整持久化對齊序列**（milestone2 只留了 5 筆 tail sample 是本次的直接教訓）。
- Hyperliquid 1h 結算 vs Bybit/OKX 8h 的對齊方法要在 SourceNote 寫明。

## Blocked（等資料 / 等人核可）

（無）

## Idea backlog

1. **passive-shrink-vol-expansion**（低優先）— 被動去風險後 72h 波動擴張。⚠️ 開工前必須先解釋為何能倖免於 dec_20260708_oi_contraction_vol_regime 所示的同族效應衰減，否則直接 defer。

## Recently decided

| 日期 | 決策 | 狀態 | 記錄 |
|---|---|---|---|
| 2026-07-08 | 跨所 funding 事件收斂捕捉（變體 A） | **rejected**（Gate 2 成本算術：毛利上限 1-5 bps < 成本 8-22 bps） | `reports/research/cross-venue-funding-dispersion/hypothesis.md` §Gate 2-A |
| 2026-07-08 | oi_contraction_vol_regime（OI 收縮 → 波動擴張警示） | **rejected**（效應低於門檻且衰減；2 條重開條件） | `reports/decisions/20260708_oi-contraction-vol-regime.md` |
| 2026-07-08 | 方向性槓桿壓力假說（高壓力→下行尾部更差） | **rejected** | `reports/decisions/20260708_leverage-pressure-directional.md` |

# Spike 001: cross-venue leverage feasibility

Run observed_at: 2026-06-16T16:12:08.785114Z

## Question
Can we build a narrow Coinbase-observable regulated perp-style rail and compare it with offshore perp rails without violating point-in-time semantics?

## Verdict: PARTIAL

The monitoring/event-study version is feasible. The backtest/signal version is not yet safe because Coinbase regulated OI/funding appears current-state only unless we build a forward archive, and CME is not a reliable automated source from this runtime.

## Summary
- OK rails: 9
- Partial rails: 0
- Blocked/error rails: 2

## Results
### coinbase_derivatives — regulated_current_product_state
- status: `ok`
- subject: `None`
- replay_safe_history: `False`
- count: `4`
- endpoint: `https://api.coinbase.com/api/v3/brokerage/market/products?product_type=FUTURE&limit=100`
- fields_seen: `about_description, alias, alias_to, approximate_quote_24h_volume, auction_mode, base_cbrn, base_currency_id, base_display_symbol, base_increment, base_max_size, base_min_size, base_name, best_ask_price, best_bid_price, cancel_only, display_name, display_name_overwrite, fcm_trading_session_details, future_product_details, high_24h, icon_color, icon_url, is_alpha_testing, is_disabled, limit_only`
- notes:
  - Product endpoint exposes current state including OI/funding-like fields for perp products.
  - This is not a replay-safe historical OI/funding endpoint; requires forward polling archive.

### coinbase_derivatives — regulated_candle_history
- status: `ok`
- subject: `BIP-20DEC30-CDE`
- replay_safe_history: `True`
- count: `7`
- endpoint: `https://api.coinbase.com/api/v3/brokerage/market/products/BIP-20DEC30-CDE/candles?start=1781604000&end=1781625600&granularity=ONE_HOUR`
- fields_seen: `close, high, low, open, start, volume`
- notes:
  - Candle history is available, but price/volume alone is insufficient for leverage-pressure backtest.

### bybit — offshore_oi_history
- status: `ok`
- subject: `BTCUSDT`
- replay_safe_history: `True`
- count: `6`
- endpoint: `https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=1h&startTime=1781604725703&endTime=1781626325703`
- fields_seen: `openInterest, singleOpenInterest, timestamp`
- notes:
  - Historical endpoint exists; production provider must keep pagination-safe cursor/window handling.

### bybit — offshore_funding_history
- status: `ok`
- subject: `BTCUSDT`
- replay_safe_history: `True`
- count: `1`
- endpoint: `https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&startTime=1781604725703&endTime=1781626325703`
- fields_seen: `fundingRate, fundingRateTimestamp, symbol`
- notes:
  - Historical endpoint exists; production provider must keep pagination-safe cursor/window handling.

### hyperliquid — offshore_current_state
- status: `ok`
- subject: `BTC`
- replay_safe_history: `False`
- count: `1`
- endpoint: `https://api.hyperliquid.xyz/info`
- fields_seen: `dayBaseVlm, dayNtlVlm, funding, impactPxs, markPx, midPx, openInterest, oraclePx, premium, prevDayPx`
- notes:
  - Current OI/mark/oracle/funding available; archive needed for current-state replay.

### hyperliquid — offshore_funding_history
- status: `ok`
- subject: `BTC`
- replay_safe_history: `True`
- count: `24`
- endpoint: `https://api.hyperliquid.xyz/info`
- fields_seen: `coin, fundingRate, premium, time`
- notes:
  - Funding history endpoint is directly replayable for settled funding observations.

### okx — offshore_current_funding
- status: `ok`
- subject: `BTC-USDT-SWAP`
- replay_safe_history: `False`
- count: `1`
- endpoint: `https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USDT-SWAP`
- fields_seen: `formulaType, fundingRate, fundingTime, impactValue, instId, instType, interestRate, maxFundingRate, method, minFundingRate, nextFundingRate, nextFundingTime, premium, prevFundingTime, settFundingRate, settState, ts`
- notes:
  - Funding history exists.

### okx — offshore_current_oi
- status: `ok`
- subject: `BTC-USDT-SWAP`
- replay_safe_history: `False`
- count: `1`
- endpoint: `https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USDT-SWAP`
- fields_seen: `instId, instType, oi, oiCcy, oiUsd, ts`
- notes:
  - OKX current OI/funding is useful; OI history still needs separate endpoint/vendor review.

### okx — offshore_funding_history
- status: `ok`
- subject: `BTC-USDT-SWAP`
- replay_safe_history: `True`
- count: `10`
- endpoint: `https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=10`
- fields_seen: `formulaType, fundingRate, fundingTime, instId, instType, method, realizedRate`
- notes:
  - Funding history exists.

### cme — regulated_cme_public_web
- status: `blocked`
- subject: `None`
- replay_safe_history: `False`
- count: `None`
- endpoint: `https://www.cmegroup.com/CmeWS/mvc/Quotes/Future/8478/G`
- notes:
  - CME public web endpoint is not reliable from this runtime; treat as deferred/vendor/manual source.
- error: `HTTP 403`

### cme — regulated_cme_public_web
- status: `blocked`
- subject: `None`
- replay_safe_history: `False`
- count: `None`
- endpoint: `https://www.cmegroup.com/CmeWS/mvc/ProductCalendar/Future/8478`
- notes:
  - CME public web endpoint is not reliable from this runtime; treat as deferred/vendor/manual source.
- error: `HTTP 403`

## Recommendation for real build
- Build a forward polling archive before any regulated OI/funding backtest claims.
- Label Coinbase as `coinbase_observable_regulated`, not as full US-regulated market coverage.
- Treat CME as `deferred_vendor_or_manual_source` until there is a reliable replay-safe source.
- Offshore first-pass rails can include Bybit, Hyperliquid, and OKX, but normalize timestamp semantics separately for current-state vs historical endpoints.

## Jaquan discussion points
1. Is a Coinbase-only regulated rail useful enough for his regime classifier, or does the research require CME before starting?
2. What minimum archive horizon makes the event study useful: 30, 60, or 90 days?
3. Should the first output be a monitoring dashboard/regime annotation rather than a signal contract?
4. Does he want offshore comparison to prioritize Bybit+Hyperliquid only, or include OKX despite OI-history ambiguity?
5. What exact decision boundary would promote this from research-only to backtest-safe?

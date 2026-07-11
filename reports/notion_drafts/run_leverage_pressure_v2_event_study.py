import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bisect import bisect_right
import statistics

import argparse

parser = argparse.ArgumentParser(description='Run leverage-pressure v2 exploratory event study.')
parser.add_argument('--fixture', default='/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_30d.jsonl')
parser.add_argument('--tag', default='first_pass')
args = parser.parse_args()

fixture = Path(args.fixture)
out_json = Path(f'/home/jimmywu0621/trading_system/reports/notion_drafts/leverage_pressure_v2_event_study_{args.tag}.json')
out_md = Path(f'/home/jimmywu0621/trading_system/reports/notion_drafts/leverage_pressure_v2_event_study_{args.tag}.md')

def parse_ts(s):
    return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)

def hour_floor(dt):
    return dt.replace(minute=0, second=0, microsecond=0)

def hour_ceil(dt):
    f=hour_floor(dt)
    return f if f==dt else f+timedelta(hours=1)

def pct_change(now, past):
    if now is None or past in (None, 0): return None
    return now/past - 1.0

def quantile(vals, q):
    vals=sorted(v for v in vals if v is not None)
    if not vals: return None
    if len(vals)==1: return vals[0]
    pos=(len(vals)-1)*q
    lo=int(pos); hi=min(lo+1,len(vals)-1); frac=pos-lo
    return vals[lo]*(1-frac)+vals[hi]*frac

def mean(vals):
    vals=[v for v in vals if v is not None]
    return sum(vals)/len(vals) if vals else None

def median(vals): return quantile(vals, .5)

def rolling_pctile(series, i, window, minp):
    start=max(0, i-window+1)
    vals=[x for x in series[start:i+1] if x is not None]
    cur=series[i]
    if cur is None or len(vals)<minp: return None
    le=sum(1 for x in vals if x<=cur)
    return le/len(vals)

def last_at_or_before(times, values, t):
    j=bisect_right(times, t)-1
    if j<0: return None
    return values[j]

def series_at_grid(points, grid):
    # points sorted [(dt,val)]
    times=[p[0] for p in points]; vals=[p[1] for p in points]
    return [last_at_or_before(times, vals, t) for t in grid]

def to_float(x):
    try:
        if x is None: return None
        return float(x)
    except Exception:
        return None

# symbol -> series
S={}
with fixture.open() as f:
    for line in f:
        r=json.loads(line); sym=r['symbol']; kind=r['kind']; meta=r.get('metadata',{}); payload=r.get('payload',{})
        d=S.setdefault(sym, {'perp':[], 'spot':[], 'oi':[], 'funding':[]})
        t=parse_ts(r['occurred_at'])
        if kind=='candle' and meta.get('market_type')=='linear_perp':
            d['perp'].append((t, to_float(payload.get('close')), to_float(payload.get('low'))))
        elif kind=='candle' and meta.get('market_type')=='spot':
            d['spot'].append((t, to_float(payload.get('close')), to_float(payload.get('volume'))))
        elif kind=='perp_open_interest':
            val=to_float(payload.get('open_interest_notional_usdt')) or to_float(payload.get('open_interest_raw'))
            d['oi'].append((t, val))
        elif kind=='perp_funding_rate':
            d['funding'].append((t, to_float(payload.get('funding_rate'))))

results=[]
for sym,d in sorted(S.items()):
    for k in d: d[k].sort(key=lambda x:x[0])
    if not d['perp'] or not d['spot'] or not d['oi'] or not d['funding']:
        results.append({'symbol':sym,'error':'missing required series'}); continue
    start=hour_ceil(max(d['perp'][0][0], d['spot'][0][0], d['oi'][0][0]))
    end=hour_floor(min(d['perp'][-1][0], d['spot'][-1][0], d['oi'][-1][0]))
    grid=[]; t=start
    while t<=end:
        grid.append(t); t+=timedelta(hours=1)
    perp_times=[x[0] for x in d['perp']]
    perp_lows=[x[2] for x in d['perp']]
    spot_times=[x[0] for x in d['spot']]
    spot_vol_values=[x[2] for x in d['spot']]
    def min_low_between(lo, hi):
        left=bisect_right(perp_times, lo)
        right=bisect_right(perp_times, hi)
        vals=[x for x in perp_lows[left:right] if x is not None]
        return min(vals) if vals else None
    def sum_spot_vol_between(lo, hi):
        left=bisect_right(spot_times, lo)
        right=bisect_right(spot_times, hi)
        vals=[x for x in spot_vol_values[left:right] if x is not None]
        return sum(vals) if vals else None
    perp_close=series_at_grid([(x[0],x[1]) for x in d['perp']], grid)
    spot_close=series_at_grid([(x[0],x[1]) for x in d['spot']], grid)
    oi=series_at_grid(d['oi'], grid)
    funding=series_at_grid(d['funding'], grid)
    # spot volume: sum within previous hour ending at grid time
    spot_vol=[]
    for t in grid:
        lo=t-timedelta(hours=1)
        spot_vol.append(sum_spot_vol_between(lo, t))
    perp_ret_4h=[pct_change(perp_close[i], perp_close[i-4] if i>=4 else None) for i in range(len(grid))]
    spot_ret_4h=[pct_change(spot_close[i], spot_close[i-4] if i>=4 else None) for i in range(len(grid))]
    div=[(a-b) if a is not None and b is not None else None for a,b in zip(perp_ret_4h, spot_ret_4h)]
    oi_chg_4h=[pct_change(oi[i], oi[i-4] if i>=4 else None) for i in range(len(grid))]
    hourly_ret=[pct_change(perp_close[i], perp_close[i-1] if i>=1 else None) for i in range(len(grid))]
    realized_vol_24h=[]; momentum_24h=[]
    for i in range(len(grid)):
        vals=[x for x in hourly_ret[max(0,i-23):i+1] if x is not None]
        realized_vol_24h.append(statistics.pstdev(vals) if len(vals)>=12 else None)
        momentum_24h.append(pct_change(perp_close[i], perp_close[i-24] if i>=24 else None))
    window=24*14; minp=24*7
    funding_pct=[rolling_pctile(funding,i,window,minp) for i in range(len(grid))]
    oi_pct=[rolling_pctile(oi_chg_4h,i,window,minp) for i in range(len(grid))]
    div_pct=[rolling_pctile(div,i,window,minp) for i in range(len(grid))]
    spot_vol_pct=[rolling_pctile(spot_vol,i,window,minp) for i in range(len(grid))]
    funding_change_8h=[(funding[i]-funding[i-8]) if i>=8 and funding[i] is not None and funding[i-8] is not None else None for i in range(len(grid))]
    scores=[]
    for i in range(len(grid)):
        fc=2 if funding_pct[i] is not None and funding_pct[i]>=.90 and (funding_change_8h[i] or 0)>=0 else (1 if funding_pct[i] is not None and funding_pct[i]>=.75 else 0)
        oc=2 if oi_pct[i] is not None and oi_pct[i]>=.85 else (1 if oi_pct[i] is not None and oi_pct[i]>=.60 else 0)
        dc=2 if div_pct[i] is not None and div_pct[i]>=.85 else (1 if div_pct[i] is not None and div_pct[i]>=.60 else 0)
        wc=2 if spot_vol_pct[i] is not None and spot_vol_pct[i]<=.40 and (div[i] or 0)>0 else (1 if spot_vol_pct[i] is not None and spot_vol_pct[i]<=.60 and (div[i] or 0)>0 else 0)
        scores.append(fc+oc+dc+wc if None not in (funding_pct[i],oi_pct[i],div_pct[i],spot_vol_pct[i]) else None)
    # future returns/mae
    perp_times=[x[0] for x in d['perp']]
    fwd={}; mae={}
    for h in [4,8,12,24]:
        fwd[h]=[]; mae[h]=[]
        for i,t in enumerate(grid):
            j=i+h
            fwd[h].append(pct_change(perp_close[j], perp_close[i]) if j<len(grid) else None)
            close=perp_close[i]
            if close is None: mae[h].append(None); continue
            lo=t; hi=t+timedelta(hours=h)
            low=min_low_between(lo, hi)
            mae[h].append((low/close-1.0) if low is not None else None)
    valid=[]
    for i,t in enumerate(grid):
        if scores[i] is None or fwd[4][i] is None or fwd[24][i] is None: continue
        valid.append(i)
    if not valid:
        results.append({'symbol':sym,'error':'no valid events after warmup'}); continue
    # tertiles by rank order of score
    ranked=sorted(valid, key=lambda i:(scores[i], i))
    n=len(ranked); buckets={'low':ranked[:n//3], 'mid':ranked[n//3:2*n//3], 'high':ranked[2*n//3:]}
    by_bucket={}
    for h in [4,8,12,24]:
        tab=[]
        for name,idxs in buckets.items():
            vals=[fwd[h][i] for i in idxs]
            maes=[mae[h][i] for i in idxs]
            tab.append({'bucket':name,'n':len(idxs),'score_mean':mean([scores[i] for i in idxs]),'mean_ret':mean(vals),'median_ret':median(vals),'q05':quantile(vals,.05),'q10':quantile(vals,.10),'mae_q05':quantile(maes,.05),'mae_q10':quantile(maes,.10)})
        by_bucket[f'{h}h']=tab
    def q_thresh(series, q): return quantile([series[i] for i in valid], q)
    flags={
        'full_score_top_quartile': lambda i: scores[i] >= q_thresh(scores,.75),
        'high_funding_only': lambda i: funding_pct[i] is not None and funding_pct[i]>=.75,
        'rising_oi_only': lambda i: oi_pct[i] is not None and oi_pct[i]>=.75,
        'funding_plus_oi': lambda i: funding_pct[i] is not None and oi_pct[i] is not None and funding_pct[i]>=.75 and oi_pct[i]>=.75,
        'high_volatility': lambda i: realized_vol_24h[i] is not None and realized_vol_24h[i]>=q_thresh(realized_vol_24h,.75),
        'negative_momentum': lambda i: momentum_24h[i] is not None and momentum_24h[i]<=q_thresh(momentum_24h,.25),
    }
    controls=[]
    for name,fn in flags.items():
        idxs=[i for i in valid if fn(i)]
        if len(idxs)<10: continue
        controls.append({'control':name,'n':len(idxs),'score_mean':mean([scores[i] for i in idxs]),'q05_24h':quantile([fwd[24][i] for i in idxs],.05),'q10_24h':quantile([fwd[24][i] for i in idxs],.10),'mean_24h':mean([fwd[24][i] for i in idxs]),'mae_q05_24h':quantile([mae[24][i] for i in idxs],.05)})
    diagnostics=[]
    for h in [4,8,12,24]:
        low=next(x for x in by_bucket[f'{h}h'] if x['bucket']=='low')
        high=next(x for x in by_bucket[f'{h}h'] if x['bucket']=='high')
        diff=high['q05']-low['q05']
        diagnostics.append({'horizon':f'{h}h','high_minus_low_q05':diff,'supports_tail_fragility': high['q05']<low['q05']})
    results.append({'symbol':sym,'coverage':{'rows':sum(len(v) for v in d.values()),'valid_hourly_events':len(valid),'start':str(grid[valid[0]]),'end':str(grid[valid[-1]]),'funding_points':len(d['funding']),'oi_points':len(d['oi'])},'bucket_results':by_bucket,'controls_24h':controls,'diagnostics':diagnostics})

overall=[]
for r in results:
    if 'diagnostics' in r:
        supports=sum(1 for d in r['diagnostics'] if d['supports_tail_fragility'])
        overall.append({'symbol':r['symbol'],'supporting_horizons':supports,'total_horizons':len(r['diagnostics'])})
if overall and all(x['supporting_horizons']>=3 for x in overall): conclusion='research_only_risk_filter_candidate'
elif any(x['supporting_horizons']>=2 for x in overall): conclusion='research_only_needs_revision'
else: conclusion='weak_or_reject_first_pass'
payload={'fixture':str(fixture),'created_at':datetime.now(timezone.utc).isoformat(),'method':'causal rolling features, 1h grid, equal-weight ordinal score, 30d Bybit fixture, pure-python first pass','results':results,'overall':overall,'conclusion':conclusion}
out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

def pct(x): return 'NA' if x is None else f'{x:.4%}'
lines=['# Leverage Pressure v2 Event Study — First Pass Result','',f'- created_at: {payload["created_at"]}',f'- fixture: `{fixture}`','- created_by: QUANT','- created_by_agent: JAQUAN','- status: first_pass_exploratory','', '## Method','', f'- Bybit BTC/ETH fixture `{fixture.name}`, 1h feature grid.', '- Uses settled funding only; predicted funding is not used.', '- Equal-weight ordinal score: funding pressure + OI expansion + perp/spot divergence + weak spot confirmation.', '- Primary readout: whether high-score buckets have worse downside 5% quantile than low-score buckets across 4h/8h/12h/24h.', '- 7d rolling warmup is used only to get a first-pass read; this is not sufficient for robust final claims.', '', '## Results by symbol']
for r in results:
    if 'error' in r:
        lines += ['', f'### {r["symbol"]}', '', f'- error: {r["error"]}']
        continue
    lines += ['', f'### {r["symbol"]}', '', f'- valid hourly events: {r["coverage"]["valid_hourly_events"]}', f'- window: {r["coverage"]["start"]} → {r["coverage"]["end"]}', f'- funding points: {r["coverage"]["funding_points"]}', f'- OI points: {r["coverage"]["oi_points"]}', '', '#### Tail-fragility diagnostic', '']
    for d in r['diagnostics']:
        lines.append(f'- {d["horizon"]}: high-minus-low 5% quantile = {pct(d["high_minus_low_q05"])}; supports={d["supports_tail_fragility"]}')
    lines += ['', '#### 24h controls', '']
    for c in r['controls_24h']:
        lines.append(f'- {c["control"]}: n={c["n"]}, q05_24h={pct(c["q05_24h"])}, q10_24h={pct(c["q10_24h"])}, mean_24h={pct(c["mean_24h"])}, mae_q05_24h={pct(c["mae_q05_24h"])}')
    lines += ['', '#### Bucket tables', '']
    for h,tab in r['bucket_results'].items():
        lines.append(f'**{h} forward return buckets**')
        for row in tab:
            lines.append(f'- {row["bucket"]}: n={row["n"]}, score_mean={row["score_mean"]:.2f}, q05={pct(row["q05"])}, q10={pct(row["q10"])}, mean={pct(row["mean_ret"])}, mae_q05={pct(row["mae_q05"])}')
        lines.append('')
lines += ['## Conservative conclusion','', f'Conclusion label: `{conclusion}`','', 'Interpretation:', '', '- Exploratory first pass only; not a paper-trading candidate.', '- 30d is too short for robust regime claims.', '- Settled funding may be too sparse/late for the intended mechanism if results are weak or inconsistent.', '- If predicted funding becomes necessary, activate Jayda/DataProvider review before using it.', '']
out_md.write_text('\n'.join(lines))
print(json.dumps({'json':str(out_json),'md':str(out_md),'overall':overall,'conclusion':conclusion}, ensure_ascii=False))

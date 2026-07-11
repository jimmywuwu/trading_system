import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bisect import bisect_right
import statistics
import argparse

parser = argparse.ArgumentParser(description='Run ETH leverage-pressure v3 simplified score validation.')
parser.add_argument('--fixture', default='/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_90d.jsonl')
parser.add_argument('--tag', default='')
args = parser.parse_args()

fixture = Path(args.fixture)
suffix = f'_{args.tag}' if args.tag else ''
out_json = Path(f'/home/jimmywu0621/trading_system/reports/notion_drafts/eth_leverage_pressure_v3_simplified_score{suffix}.json')
out_md = Path(f'/home/jimmywu0621/trading_system/reports/notion_drafts/eth_leverage_pressure_v3_simplified_score{suffix}.md')

def parse_ts(s): return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def hour_floor(dt): return dt.replace(minute=0, second=0, microsecond=0)
def hour_ceil(dt):
    f=hour_floor(dt); return f if f==dt else f+timedelta(hours=1)
def pct_change(now,past): return None if now is None or past in (None,0) else now/past-1.0
def quantile(vals, qq):
    vals=sorted(v for v in vals if v is not None)
    if not vals: return None
    if len(vals)==1: return vals[0]
    pos=(len(vals)-1)*qq; lo=int(pos); hi=min(lo+1,len(vals)-1); frac=pos-lo
    return vals[lo]*(1-frac)+vals[hi]*frac
def mean(vals):
    vals=[v for v in vals if v is not None]
    return sum(vals)/len(vals) if vals else None
def roll_pct(series,i,window,minp):
    cur=series[i]
    vals=[x for x in series[max(0,i-window+1):i+1] if x is not None]
    if cur is None or len(vals)<minp: return None
    return sum(1 for x in vals if x<=cur)/len(vals)
def last_at_or_before(points,t):
    times=[p[0] for p in points]
    j=bisect_right(times,t)-1
    return points[j][1] if j>=0 else None
def to_float(x):
    try: return None if x is None else float(x)
    except Exception: return None
def pct(x): return 'NA' if x is None else f'{x:.4%}'

def summary_for_indices(idxs, fwd, mae, score, horizons=(4,8,12,24)):
    out={}
    for h in horizons:
        vals=[fwd[h][i] for i in idxs]
        maes=[mae[h][i] for i in idxs]
        out[f'{h}h']={'n':len(idxs),'score_mean':mean([score[i] for i in idxs]),'mean':mean(vals),'q05':quantile(vals,.05),'q10':quantile(vals,.10),'mae_q05':quantile(maes,.05),'mae_q10':quantile(maes,.10)}
    return out

def bucket_eval(valid, score, fwd, mae):
    ranked=sorted(valid, key=lambda i:(score[i],i)); n=len(ranked)
    buckets={'low':ranked[:n//3], 'mid':ranked[n//3:2*n//3], 'high':ranked[2*n//3:]}
    out={}
    for b,idxs in buckets.items(): out[b]=summary_for_indices(idxs,fwd,mae,score)
    diffs={}
    for h in [4,8,12,24]:
        hi=out['high'][f'{h}h']['q05']; lo=out['low'][f'{h}h']['q05']
        diffs[f'{h}h']=None if hi is None or lo is None else hi-lo
    return {'buckets':out,'high_minus_low_q05':diffs}

# Load ETH series
S={'perp':[], 'spot':[], 'oi':[], 'funding':[]}
with fixture.open() as f:
    for line in f:
        r=json.loads(line)
        if r.get('symbol')!='ETHUSDT': continue
        kind=r['kind']; meta=r.get('metadata',{}); payload=r.get('payload',{}); t=parse_ts(r['occurred_at'])
        if kind=='candle' and meta.get('market_type')=='linear_perp': S['perp'].append((t,to_float(payload.get('close')),to_float(payload.get('low'))))
        elif kind=='candle' and meta.get('market_type')=='spot': S['spot'].append((t,to_float(payload.get('close')),to_float(payload.get('volume'))))
        elif kind=='perp_open_interest': S['oi'].append((t,to_float(payload.get('open_interest_notional_usdt')) or to_float(payload.get('open_interest_raw'))))
        elif kind=='perp_funding_rate': S['funding'].append((t,to_float(payload.get('funding_rate'))))
for k in S: S[k].sort(key=lambda x:x[0])
start=hour_ceil(max(S['perp'][0][0],S['spot'][0][0],S['oi'][0][0])); end=hour_floor(min(S['perp'][-1][0],S['spot'][-1][0],S['oi'][-1][0]))
grid=[]; t=start
while t<=end: grid.append(t); t+=timedelta(hours=1)
perp_times=[x[0] for x in S['perp']]
perp_lows=[x[2] for x in S['perp']]
spot_times=[x[0] for x in S['spot']]
spot_vol_values=[x[2] for x in S['spot']]
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
perp_close=[last_at_or_before([(x[0],x[1]) for x in S['perp']],t) for t in grid]
spot_close=[last_at_or_before([(x[0],x[1]) for x in S['spot']],t) for t in grid]
oi=[last_at_or_before(S['oi'],t) for t in grid]
funding=[last_at_or_before(S['funding'],t) for t in grid]
spot_vol=[]
for t in grid:
    lo=t-timedelta(hours=1)
    spot_vol.append(sum_spot_vol_between(lo, t))
perp_ret_4h=[pct_change(perp_close[i],perp_close[i-4] if i>=4 else None) for i in range(len(grid))]
spot_ret_4h=[pct_change(spot_close[i],spot_close[i-4] if i>=4 else None) for i in range(len(grid))]
div=[a-b if a is not None and b is not None else None for a,b in zip(perp_ret_4h,spot_ret_4h)]
oi_chg_4h=[pct_change(oi[i],oi[i-4] if i>=4 else None) for i in range(len(grid))]
window=24*14; minp=24*7
funding_pct=[roll_pct(funding,i,window,minp) for i in range(len(grid))]
funding_change_8h=[funding[i]-funding[i-8] if i>=8 and funding[i] is not None and funding[i-8] is not None else None for i in range(len(grid))]
oi_pct=[roll_pct(oi_chg_4h,i,window,minp) for i in range(len(grid))]
div_pct=[roll_pct(div,i,window,minp) for i in range(len(grid))]
spot_vol_pct=[roll_pct(spot_vol,i,window,minp) for i in range(len(grid))]
hourly_ret=[pct_change(perp_close[i],perp_close[i-1] if i>=1 else None) for i in range(len(grid))]
realized_vol=[]; mom=[]
for i in range(len(grid)):
    vals=[x for x in hourly_ret[max(0,i-23):i+1] if x is not None]
    realized_vol.append(statistics.pstdev(vals) if len(vals)>=12 else None)
    mom.append(pct_change(perp_close[i],perp_close[i-24] if i>=24 else None))

scores={k:[] for k in ['funding','oi','divergence','weak_spot','funding_oi','v3','full','high_vol','neg_mom']}
for i in range(len(grid)):
    if None in (funding_pct[i], oi_pct[i], div_pct[i], spot_vol_pct[i]):
        for k in scores: scores[k].append(None)
        continue
    fc=2 if funding_pct[i]>=.90 and (funding_change_8h[i] or 0)>=0 else (1 if funding_pct[i]>=.75 else 0)
    oc=2 if oi_pct[i]>=.85 else (1 if oi_pct[i]>=.60 else 0)
    dc=2 if div_pct[i]>=.85 else (1 if div_pct[i]>=.60 else 0)
    wc=2 if spot_vol_pct[i]<=.40 and (div[i] or 0)>0 else (1 if spot_vol_pct[i]<=.60 and (div[i] or 0)>0 else 0)
    scores['funding'].append(fc); scores['oi'].append(oc); scores['divergence'].append(dc); scores['weak_spot'].append(wc)
    scores['funding_oi'].append(fc+oc); scores['v3'].append(fc+oc+dc); scores['full'].append(fc+oc+dc+wc)
    scores['high_vol'].append(realized_vol[i]); scores['neg_mom'].append(-mom[i] if mom[i] is not None else None)

fwd={}; mae={}
for h in [4,8,12,24]:
    fwd[h]=[]; mae[h]=[]
    for i,t in enumerate(grid):
        fwd[h].append(pct_change(perp_close[i+h],perp_close[i]) if i+h<len(grid) else None)
        if perp_close[i] is None: mae[h].append(None); continue
        low=min_low_between(t, t+timedelta(hours=h))
        mae[h].append(low/perp_close[i]-1 if low is not None else None)
valid=[i for i in range(len(grid)) if scores['v3'][i] is not None and fwd[24][i] is not None]

# Bucket evaluations
variants=['funding','oi','divergence','weak_spot','funding_oi','v3','full']
evals={v:bucket_eval(valid,scores[v],fwd,mae) for v in variants}
# Time splits by chronological halves and thirds
splits={}
for name, idxs in {
    'first_half': valid[:len(valid)//2],
    'second_half': valid[len(valid)//2:],
    'first_third': valid[:len(valid)//3],
    'middle_third': valid[len(valid)//3:2*len(valid)//3],
    'last_third': valid[2*len(valid)//3:],
}.items():
    splits[name]={'start':str(grid[idxs[0]]),'end':str(grid[idxs[-1]]),'n':len(idxs),'v3':bucket_eval(idxs,scores['v3'],fwd,mae),'full':bucket_eval(idxs,scores['full'],fwd,mae),'funding_oi':bucket_eval(idxs,scores['funding_oi'],fwd,mae)}
# Top quartile controls
controls=[]
for v in ['funding','oi','funding_oi','v3','full','high_vol','neg_mom']:
    vals=[scores[v][i] for i in valid if scores[v][i] is not None]
    th=quantile(vals,.75)
    idxs=[i for i in valid if scores[v][i] is not None and scores[v][i]>=th]
    controls.append({'score':v,'threshold':th,'n':len(idxs),'summary':summary_for_indices(idxs,fwd,mae,scores[v])})
# Episode concentration: v3 high bucket 24h q05 tail
v3_ranked=sorted(valid,key=lambda i:(scores['v3'][i],i)); v3_high=v3_ranked[2*len(v3_ranked)//3:]
v3_q05=quantile([fwd[24][i] for i in v3_high],.05)
tail=[i for i in v3_high if fwd[24][i] is not None and fwd[24][i]<=v3_q05]
by_day={}
for i in tail:
    d=grid[i].date().isoformat(); by_day.setdefault(d,[]).append(fwd[24][i])
tail_days=[{'date':d,'count':len(v),'worst_24h':min(v),'avg_24h':mean(v)} for d,v in sorted(by_day.items(), key=lambda kv:(-len(kv[1]), min(kv[1])))]
# Toy risk filter: long when not v3 high bucket, flat when high bucket; hourly returns, no cost.
# This is not a trading rule; it checks whether high-score periods coincide with bad long exposure.
v3_high_set=set(v3_high)
bh=[]; filt=[]
for i in valid:
    r=hourly_ret[i+1] if i+1<len(hourly_ret) else None
    if r is None: continue
    bh.append(r); filt.append(0.0 if i in v3_high_set else r)
def cumulative(rs):
    x=1.0
    for r in rs: x*=1+r
    return x-1
def max_dd(rs):
    x=1.0; peak=1.0; mdd=0.0
    for r in rs:
        x*=1+r; peak=max(peak,x); mdd=min(mdd,x/peak-1)
    return mdd
risk_filter={'buy_hold_return':cumulative(bh),'filter_return':cumulative(filt),'buy_hold_max_dd':max_dd(bh),'filter_max_dd':max_dd(filt),'hours_flat':len([i for i in valid if i in v3_high_set]),'total_hours':len(valid)}

payload={'created_at':datetime.now(timezone.utc).isoformat(),'fixture':str(fixture),'symbol':'ETHUSDT','valid_events':len(valid),'window':[str(grid[valid[0]]),str(grid[valid[-1]])],'v3_definition':'funding_pressure + oi_expansion + perp_spot_divergence; weak_spot removed','evals':evals,'splits':splits,'controls':controls,'v3_tail_q05_24h':v3_q05,'tail_days':tail_days,'toy_risk_filter':risk_filter}
out_json.write_text(json.dumps(payload,indent=2,ensure_ascii=False))

# interpretation labels
v3_support=sum(1 for h,d in evals['v3']['high_minus_low_q05'].items() if d is not None and d<0)
full_support=sum(1 for h,d in evals['full']['high_minus_low_q05'].items() if d is not None and d<0)
fo_support=sum(1 for h,d in evals['funding_oi']['high_minus_low_q05'].items() if d is not None and d<0)
split_support=sum(1 for s in ['first_half','second_half'] if splits[s]['v3']['high_minus_low_q05']['24h'] is not None and splits[s]['v3']['high_minus_low_q05']['24h']<0)
if v3_support>=3 and split_support==2:
    label='research_only_risk_filter_candidate_needs_longer_sample'
elif v3_support>=3:
    label='research_only_needs_revision_time_split_mixed'
else:
    label='weak_or_reject_v3'

lines=['# ETH Leverage Pressure v3 — Simplified Score Validation','',f'- created_at: {payload["created_at"]}',f'- fixture: `{fixture}`','- created_by: QUANT','- created_by_agent: JAQUAN','- status: exploratory_v3_validation','', '## 0. V3 definition','', 'V3 removes `weak_spot_confirmation` from the core score because v2 decomposition did not show it had positive incremental value.', '', '```text', 'eth_leverage_pressure_v3 = funding_pressure + oi_expansion + perp_spot_divergence', '```', '', 'This is still a research score, not a signal contract or strategy.', '', '## 1. Main bucket result: high-minus-low 5% quantile','']
for v in ['funding_oi','v3','full']:
    lines.append(f'### {v}')
    for h in [4,8,12,24]:
        d=evals[v]['high_minus_low_q05'][f'{h}h']
        hi=evals[v]['buckets']['high'][f'{h}h']; lo=evals[v]['buckets']['low'][f'{h}h']
        lines.append(f'- {h}h: diff={pct(d)}; low_q05={pct(lo["q05"])}; high_q05={pct(hi["q05"])}; high_score_mean={hi["score_mean"]:.2f}')
    lines.append('')
lines += ['## 2. Time-split sanity check','']
for s in ['first_half','second_half','first_third','middle_third','last_third']:
    lines.append(f'### {s}')
    lines.append(f'- window: {splits[s]["start"]} → {splits[s]["end"]}; n={splits[s]["n"]}')
    for v in ['funding_oi','v3','full']:
        diffs=splits[s][v]['high_minus_low_q05']
        lines.append(f'- {v}: 4h={pct(diffs["4h"])}, 8h={pct(diffs["8h"])}, 12h={pct(diffs["12h"])}, 24h={pct(diffs["24h"])}')
    lines.append('')
lines += ['## 3. 24h top-quartile controls','']
for c in controls:
    sm=c['summary']['24h']
    lines.append(f'- {c["score"]}: n={c["n"]}, q05_24h={pct(sm["q05"])}, q10_24h={pct(sm["q10"])}, mean_24h={pct(sm["mean"])}, mae_q05_24h={pct(sm["mae_q05"])}')
lines += ['', '## 4. Episode concentration','', f'- V3 high-bucket 24h q05 threshold: {pct(v3_q05)}', f'- tail event count at/below q05: {len(tail)}', '- top tail days:']
for d in tail_days[:10]:
    lines.append(f'  - {d["date"]}: count={d["count"]}, worst_24h={pct(d["worst_24h"])}, avg_24h={pct(d["avg_24h"])}')
lines += ['', '## 5. Toy long-risk filter sanity check','', 'This is not a trading recommendation. It only tests whether high V3 periods are bad times to hold passive long exposure in this sample.', '', f'- buy-and-hold return over valid hourly sample: {pct(risk_filter["buy_hold_return"])}', f'- flat-during-v3-high return, zero cost: {pct(risk_filter["filter_return"])}', f'- buy-and-hold max drawdown: {pct(risk_filter["buy_hold_max_dd"])}', f'- flat-during-v3-high max drawdown: {pct(risk_filter["filter_max_dd"])}', f'- flat hours: {risk_filter["hours_flat"]}/{risk_filter["total_hours"]}', '', '## 6. Conservative interpretation','', f'- v3 supportive horizons: {v3_support}/4', f'- full supportive horizons: {full_support}/4', f'- funding+OI supportive horizons: {fo_support}/4', f'- 24h v3 time-split support across halves: {split_support}/2', '', f'Conclusion label: `{label}`', '', 'Current decision:', '', '- V3 is cleaner than full score because it removes weak_spot, which was not supported as an incremental component.', '- V3 still needs longer data and market-wide controls before any SignalContract.', '- If V3 mainly overlaps with OI/funding controls, keep it as a research-only risk filter candidate rather than directional alpha.', '']
out_md.write_text('\n'.join(lines))
print(json.dumps({'md':str(out_md),'json':str(out_json),'label':label,'v3_support':v3_support,'split_support_24h_halves':split_support,'toy_risk_filter':risk_filter},ensure_ascii=False))

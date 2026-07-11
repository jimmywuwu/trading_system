import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from bisect import bisect_right
import statistics
import argparse

parser = argparse.ArgumentParser(description='Run ETH leverage-pressure component decomposition.')
parser.add_argument('--fixture', default='/home/jimmywu0621/trading_system/data/bybit_leverage_pressure_fixture_90d.jsonl')
parser.add_argument('--tag', default='')
args = parser.parse_args()

fixture = Path(args.fixture)
suffix = f'_{args.tag}' if args.tag else ''
out_json = Path(f'/home/jimmywu0621/trading_system/reports/notion_drafts/eth_leverage_pressure_component_decomposition{suffix}.json')
out_md = Path(f'/home/jimmywu0621/trading_system/reports/notion_drafts/eth_leverage_pressure_component_decomposition{suffix}.md')

def parse_ts(s): return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def hour_floor(dt): return dt.replace(minute=0, second=0, microsecond=0)
def hour_ceil(dt):
    f=hour_floor(dt); return f if f==dt else f+timedelta(hours=1)
def pct_change(now,past): return None if now is None or past in (None,0) else now/past-1.0
def q(vals, qq):
    vals=sorted(v for v in vals if v is not None)
    if not vals: return None
    if len(vals)==1: return vals[0]
    pos=(len(vals)-1)*qq; lo=int(pos); hi=min(lo+1,len(vals)-1); frac=pos-lo
    return vals[lo]*(1-frac)+vals[hi]*frac
def mean(vals):
    vals=[v for v in vals if v is not None]
    return sum(vals)/len(vals) if vals else None
def roll_pct(series,i,window,minp):
    vals=[x for x in series[max(0,i-window+1):i+1] if x is not None]
    cur=series[i]
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
components=[]
for i in range(len(grid)):
    if None in (funding_pct[i], oi_pct[i], div_pct[i], spot_vol_pct[i]):
        components.append(None); continue
    fc=2 if funding_pct[i]>=.90 and (funding_change_8h[i] or 0)>=0 else (1 if funding_pct[i]>=.75 else 0)
    oc=2 if oi_pct[i]>=.85 else (1 if oi_pct[i]>=.60 else 0)
    dc=2 if div_pct[i]>=.85 else (1 if div_pct[i]>=.60 else 0)
    wc=2 if spot_vol_pct[i]<=.40 and (div[i] or 0)>0 else (1 if spot_vol_pct[i]<=.60 and (div[i] or 0)>0 else 0)
    components.append({'funding':fc,'oi':oc,'divergence':dc,'weak_spot':wc,'full':fc+oc+dc+wc,
                       'funding_oi':fc+oc,'funding_oi_div':fc+oc+dc,'div_weak_spot':dc+wc})
# forward outcomes
fwd={}; mae={}
for h in [4,8,12,24]:
    fwd[h]=[]; mae[h]=[]
    for i,t in enumerate(grid):
        fwd[h].append(pct_change(perp_close[i+h],perp_close[i]) if i+h<len(grid) else None)
        if perp_close[i] is None: mae[h].append(None); continue
        low=min_low_between(t, t+timedelta(hours=h))
        mae[h].append(low/perp_close[i]-1 if low is not None else None)
valid=[i for i in range(len(grid)) if components[i] is not None and fwd[24][i] is not None]

def top_quartile_indices(score_name):
    vals=[components[i][score_name] for i in valid]
    thresh=q(vals,.75)
    return [i for i in valid if components[i][score_name]>=thresh], thresh

def low_high_bucket(score_name, horizon):
    ranked=sorted(valid, key=lambda i:(components[i][score_name], i)); n=len(ranked)
    low=ranked[:n//3]; high=ranked[2*n//3:]
    return {
        'low_n':len(low),'high_n':len(high),'low_score_mean':mean([components[i][score_name] for i in low]),'high_score_mean':mean([components[i][score_name] for i in high]),
        'low_q05':q([fwd[horizon][i] for i in low],.05),'high_q05':q([fwd[horizon][i] for i in high],.05),
        'high_minus_low_q05': q([fwd[horizon][i] for i in high],.05)-q([fwd[horizon][i] for i in low],.05),
        'low_mean':mean([fwd[horizon][i] for i in low]),'high_mean':mean([fwd[horizon][i] for i in high]),
        'high_mae_q05':q([mae[horizon][i] for i in high],.05),'low_mae_q05':q([mae[horizon][i] for i in low],.05),
    }
score_names=['funding','oi','divergence','weak_spot','funding_oi','funding_oi_div','div_weak_spot','full']
ablation={}
for s in score_names:
    ablation[s]={str(h)+'h':low_high_bucket(s,h) for h in [4,8,12,24]}
# 24h top-quartile controls
controls=[]
for s in score_names:
    idxs,th=top_quartile_indices(s)
    controls.append({'score':s,'threshold':th,'n':len(idxs),'q05_24h':q([fwd[24][i] for i in idxs],.05),'q10_24h':q([fwd[24][i] for i in idxs],.10),'mean_24h':mean([fwd[24][i] for i in idxs]),'mae_q05_24h':q([mae[24][i] for i in idxs],.05)})
# episode concentration for full high bucket 24h worst outcomes
full_high=sorted(valid, key=lambda i:(components[i]['full'],i))[2*len(valid)//3:]
worst=sorted(full_high, key=lambda i:fwd[24][i])[:20]
by_day={}
for i in worst:
    day=grid[i].date().isoformat(); by_day.setdefault(day,[]).append(fwd[24][i])
episodes=[{'date':d,'count':len(v),'worst_24h':min(v),'avg_24h':mean(v)} for d,v in sorted(by_day.items(), key=lambda kv:min(kv[1]))]
# also all negative tail events below full high q05, grouped by day
full_high_q05=q([fwd[24][i] for i in full_high],.05)
tail=[i for i in full_high if fwd[24][i] is not None and fwd[24][i]<=full_high_q05]
tail_by_day={}
for i in tail:
    d=grid[i].date().isoformat(); tail_by_day.setdefault(d,[]).append(fwd[24][i])
tail_days=[{'date':d,'count':len(v),'worst_24h':min(v),'avg_24h':mean(v)} for d,v in sorted(tail_by_day.items(), key=lambda kv:(-len(kv[1]), min(kv[1])))]

payload={'created_at':datetime.now(timezone.utc).isoformat(),'fixture':str(fixture),'symbol':'ETHUSDT','valid_events':len(valid),'window':[str(grid[valid[0]]),str(grid[valid[-1]])],'ablation':ablation,'controls_top_quartile_24h':controls,'worst20_full_high_24h_by_day':episodes,'full_high_24h_q05':full_high_q05,'tail_days_full_high_24h':tail_days}
out_json.write_text(json.dumps(payload,indent=2,ensure_ascii=False))

lines=['# ETH Leverage Pressure v2 — Component Decomposition','',f'- created_at: {payload["created_at"]}',f'- fixture: `{fixture}`','- created_by: QUANT','- created_by_agent: JAQUAN','- status: exploratory_decomposition','', '## Question','', 'Does the full leverage-pressure score add information beyond funding/OI, or is ETH downside-tail separation mostly explained by simpler components?', '', '## Data / method','', f'- valid hourly events: {len(valid)}', f'- window: {grid[valid[0]]} → {grid[valid[-1]]}', '- score variants tested: funding, OI, divergence, weak_spot, funding+OI, funding+OI+divergence, divergence+weak_spot, full.', '- primary metric: high bucket minus low bucket 5% forward-return quantile. Negative is supportive: high score has worse left tail.', '', '## 1. Bucket ablation: high-minus-low 5% quantile','']
for s in score_names:
    lines.append(f'### {s}')
    for h in [4,8,12,24]:
        r=ablation[s][str(h)+'h']
        lines.append(f'- {h}h: diff={pct(r["high_minus_low_q05"])}; low_q05={pct(r["low_q05"])}; high_q05={pct(r["high_q05"])}; low_score_mean={r["low_score_mean"]:.2f}; high_score_mean={r["high_score_mean"]:.2f}')
    lines.append('')
lines += ['## 2. 24h top-quartile controls','']
for c in controls:
    lines.append(f'- {c["score"]}: n={c["n"]}, q05_24h={pct(c["q05_24h"])}, q10_24h={pct(c["q10_24h"])}, mean_24h={pct(c["mean_24h"])}, mae_q05_24h={pct(c["mae_q05_24h"])}')
lines += ['', '## 3. Episode concentration check','', f'- full high-bucket 24h q05 threshold: {pct(full_high_q05)}', f'- tail event count at/below q05: {len(tail)}', '- tail days by concentration:']
for d in tail_days[:10]:
    lines.append(f'  - {d["date"]}: count={d["count"]}, worst_24h={pct(d["worst_24h"])}, avg_24h={pct(d["avg_24h"])}')
lines += ['', '## 4. Conservative interpretation','']
# derived conclusions
full_support=sum(1 for h in [4,8,12,24] if ablation['full'][str(h)+'h']['high_minus_low_q05']<0)
fo_support=sum(1 for h in [4,8,12,24] if ablation['funding_oi'][str(h)+'h']['high_minus_low_q05']<0)
fod_support=sum(1 for h in [4,8,12,24] if ablation['funding_oi_div'][str(h)+'h']['high_minus_low_q05']<0)
lines.append(f'- full score supportive horizons: {full_support}/4')
lines.append(f'- funding+OI supportive horizons: {fo_support}/4')
lines.append(f'- funding+OI+divergence supportive horizons: {fod_support}/4')
lines.append('- If full score does not materially beat funding+OI or funding+OI+divergence, weak spot confirmation is not yet proven as incremental information.')
lines.append('- If the q05 tail is concentrated in a small number of adjacent days, treat this as regime-specific evidence rather than robust alpha.')
lines.append('')
if full_support>=3 and (fod_support>=full_support or fo_support>=full_support):
    label='research_only_needs_revision: ETH tail separation exists, but incremental full-score value is not proven.'
elif full_support>=3:
    label='research_only_risk_filter_candidate: full score appears incrementally useful, still needs longer sample.'
else:
    label='weak_or_reject: full score does not robustly separate ETH downside tails.'
lines.append(f'Conclusion label: `{label}`')
out_md.write_text('\n'.join(lines))
print(json.dumps({'md':str(out_md),'json':str(out_json),'valid_events':len(valid),'full_support':full_support,'funding_oi_support':fo_support,'funding_oi_div_support':fod_support,'tail_days_top3':tail_days[:3],'label':label},ensure_ascii=False))

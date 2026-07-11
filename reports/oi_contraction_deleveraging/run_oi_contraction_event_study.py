
#!/usr/bin/env python3
import json, math, statistics
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

FIXTURE = Path('data/bybit_leverage_pressure_fixture_365d.jsonl')
OUTDIR = Path('reports/oi_contraction_deleveraging')
OUTDIR.mkdir(parents=True, exist_ok=True)

def parse_hour(s):
    dt = datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
    return dt.replace(minute=0, second=0, microsecond=0)

def fl(x):
    try:
        return float(x) if x is not None else None
    except Exception:
        return None

def pct(a,b):
    if a is None or b in (None,0): return None
    return a/b - 1.0

def mean(xs):
    xs=[x for x in xs if x is not None and math.isfinite(x)]
    return sum(xs)/len(xs) if xs else None

def quantile(xs, q):
    xs=sorted(x for x in xs if x is not None and math.isfinite(x))
    if not xs: return None
    pos=(len(xs)-1)*q
    lo=int(pos); hi=min(lo+1,len(xs)-1); f=pos-lo
    return xs[lo]*(1-f)+xs[hi]*f

def std(xs):
    xs=[x for x in xs if x is not None and math.isfinite(x)]
    return statistics.pstdev(xs) if len(xs)>1 else None

def summarize(vals):
    vals=[v for v in vals if v is not None and math.isfinite(v)]
    if not vals:
        return {'n':0}
    return {'n':len(vals), 'mean':mean(vals), 'median':quantile(vals,.5), 'q05':quantile(vals,.05), 'q95':quantile(vals,.95)}

def decile_edges(vals):
    return [quantile(vals, i/10) for i in range(1,10)]

def bin_index(x, edges):
    if x is None or not math.isfinite(x): return None
    i=0
    while i < len(edges) and x > edges[i]: i += 1
    return i

# Aggregate to hourly: last close/OI in hour.
H=defaultdict(lambda: defaultdict(dict))
with FIXTURE.open() as f:
    for line in f:
        r=json.loads(line); sym=r['symbol']; kind=r.get('kind'); meta=r.get('metadata',{}); p=r.get('payload',{})
        h=parse_hour(r['occurred_at']); d=H[sym][h]
        if kind=='candle' and meta.get('market_type')=='linear_perp':
            d['perp_close']=fl(p.get('close'))
        elif kind=='candle' and meta.get('market_type')=='spot':
            d['spot_close']=fl(p.get('close'))
        elif kind=='perp_open_interest':
            d['oi']=fl(p.get('open_interest_notional_usdt')) or fl(p.get('open_interest_raw'))
        elif kind=='perp_spot_basis':
            d['basis_bps']=fl(p.get('basis_bps'))

results={}
for sym, hd in H.items():
    grid=sorted(hd)
    close=[hd[t].get('perp_close') for t in grid]
    oi=[hd[t].get('oi') for t in grid]
    one=[pct(close[i], close[i-1]) if i>=1 else None for i in range(len(grid))]
    oi_chg4=[pct(oi[i], oi[i-4]) if i>=4 else None for i in range(len(grid))]
    ret4=[pct(close[i], close[i-4]) if i>=4 else None for i in range(len(grid))]
    trail_abs4=[]; trail_rv24=[]
    for i in range(len(grid)):
        trail_abs4.append(abs(ret4[i]) if ret4[i] is not None else None)
        vals=one[max(1,i-23):i+1]
        if len([v for v in vals if v is not None])>=20:
            trail_rv24.append(math.sqrt(sum(v*v for v in vals if v is not None)))
        else:
            trail_rv24.append(None)
    fwd_ret={h:[pct(close[i+h], close[i]) if i+h<len(close) else None for i in range(len(grid))] for h in [1,4,8,24,48]}
    fwd_abs={h:[abs(x) if x is not None else None for x in arr] for h,arr in fwd_ret.items()}
    fwd_rv={}
    for h in [4,8,24,48]:
        arr=[]
        for i in range(len(grid)):
            if i+h < len(grid):
                vals=one[i+1:i+h+1]
                arr.append(math.sqrt(sum(v*v for v in vals if v is not None)) if len([v for v in vals if v is not None])==h else None)
            else: arr.append(None)
        fwd_rv[h]=arr

    eligible=[i for i in range(len(grid)-48) if oi_chg4[i] is not None and close[i] and trail_rv24[i] is not None and ret4[i] is not None]
    oi_vals=[oi_chg4[i] for i in eligible]
    bot10=quantile(oi_vals,.10); top10=quantile(oi_vals,.90); bot5=quantile(oi_vals,.05); bot20=quantile(oi_vals,.20)
    vol_edges=decile_edges([trail_rv24[i] for i in eligible])
    ret_edges=decile_edges([ret4[i] for i in eligible])

    event_sets={
        'oi_bottom_5pct':[i for i in eligible if oi_chg4[i] <= bot5],
        'oi_bottom_10pct':[i for i in eligible if oi_chg4[i] <= bot10],
        'oi_bottom_20pct':[i for i in eligible if oi_chg4[i] <= bot20],
        'oi_top_10pct':[i for i in eligible if oi_chg4[i] >= top10],
    }
    event_flags={name:set(idxs) for name,idxs in event_sets.items()}

    def clustered(idxs, cooldown):
        out=[]; last=-10**9
        for i in sorted(idxs):
            if i-last >= cooldown:
                out.append(i); last=i
        return out

    def control_for(idxs, exclude_set, match=('vol','ret','hour')):
        idxs=list(idxs)
        keys=[]
        for i in idxs:
            parts=[]
            if 'vol' in match: parts.append(bin_index(trail_rv24[i], vol_edges))
            if 'ret' in match: parts.append(bin_index(ret4[i], ret_edges))
            if 'hour' in match: parts.append(grid[i].hour)
            if None not in parts: keys.append(tuple(parts))
        key_counts=defaultdict(int)
        for k in keys: key_counts[k]+=1
        candidates=[]
        for j in eligible:
            if j in exclude_set: continue
            parts=[]
            if 'vol' in match: parts.append(bin_index(trail_rv24[j], vol_edges))
            if 'ret' in match: parts.append(bin_index(ret4[j], ret_edges))
            if 'hour' in match: parts.append(grid[j].hour)
            k=tuple(parts)
            if None not in parts and key_counts.get(k,0)>0: candidates.append(j)
        return candidates

    def outcome(idxs):
        return {
            'events': len(idxs),
            'oi_chg4': summarize([oi_chg4[i] for i in idxs]),
            'trail_abs4': summarize([trail_abs4[i] for i in idxs]),
            'trail_rv24': summarize([trail_rv24[i] for i in idxs]),
            'fwd_abs': {str(h): summarize([fwd_abs[h][i] for i in idxs]) for h in [1,4,8,24,48]},
            'fwd_rv': {str(h): summarize([fwd_rv[h][i] for i in idxs]) for h in [4,8,24,48]},
            'fwd_signed': {str(h): summarize([fwd_ret[h][i] for i in idxs]) for h in [1,4,8,24,48]},
            'hours_utc_top': sorted([(hr, sum(1 for i in idxs if grid[i].hour==hr)) for hr in range(24)], key=lambda x:-x[1])[:5],
        }

    symres={'window': [grid[0].isoformat(), grid[-1].isoformat()], 'hours': len(grid), 'eligible':len(eligible), 'thresholds': {'oi_chg4_bot5':bot5,'bot10':bot10,'bot20':bot20,'top10':top10}, 'sets':{}}
    baseline=outcome(eligible)
    symres['baseline']=baseline
    all_event_exclude=set().union(*event_flags.values())
    for name, idxs in event_sets.items():
        excl=event_flags[name]
        clustered_24=clustered(idxs, 24)
        clustered_48=clustered(idxs, 48)
        controls={
            'unconditional_non_event':[i for i in eligible if i not in excl],
            'vol_matched': control_for(idxs, excl, ('vol',)),
            'ret_matched': control_for(idxs, excl, ('ret',)),
            'vol_ret_hour_matched': control_for(idxs, excl, ('vol','ret','hour')),
        }
        symres['sets'][name]={
            'raw': outcome(idxs),
            'clustered_24h_cooldown': outcome(clustered_24),
            'clustered_48h_cooldown': outcome(clustered_48),
            'controls': {k: outcome(v) for k,v in controls.items()}
        }
    results[sym]=symres

# Derive compact comparison table.
summary=[]
for sym,r in results.items():
    for name in ['oi_bottom_10pct','oi_top_10pct']:
        raw=r['sets'][name]['raw']; ctrl=r['sets'][name]['controls']['vol_ret_hour_matched']; cl=r['sets'][name]['clustered_24h_cooldown']
        for h in ['4','24','48']:
            summary.append({
                'symbol':sym,'set':name,'horizon_h':h,
                'event_n':raw['events'],
                'event_abs_mean':raw['fwd_abs'][h]['mean'],
                'matched_n':ctrl['events'],
                'matched_abs_mean':ctrl['fwd_abs'][h]['mean'],
                'cluster_n':cl['events'],
                'cluster_abs_mean':cl['fwd_abs'][h]['mean'],
                'baseline_abs_mean':r['baseline']['fwd_abs'][h]['mean'],
            })
results['_compact_summary']=summary

(OUTDIR/'oi_contraction_event_study_365d.json').write_text(json.dumps(results, indent=2, sort_keys=True))

# Markdown report
lines=[]
lines.append('# OI Contraction / Deleveraging Volatility Regime — 365d First-Pass Event Study\n')
lines.append('## Setup\n')
lines.append('- Fixture: `data/bybit_leverage_pressure_fixture_365d.jsonl`')
lines.append('- Symbols: BTCUSDT, ETHUSDT')
lines.append('- Aggregation: hourly last perp close and hourly OI')
lines.append('- Event: 4h OI change bottom decile; controls include top-decile OI expansion, volatility-matched, return-matched, and vol+return+UTC-hour matched non-events.')
lines.append('- Primary horizons: 4h and 24h; secondary: 1h, 8h, 48h.\n')
for sym,r in results.items():
    if sym.startswith('_'): continue
    lines.append(f'## {sym}\n')
    lines.append(f"- Window: `{r['window'][0]}` to `{r['window'][1]}`")
    lines.append(f"- Eligible hourly rows: {r['eligible']}")
    th=r['thresholds']
    lines.append(f"- 4h OI change thresholds: bottom 10% `{th['bot10']:.4%}`, top 10% `{th['top10']:.4%}`\n")
    base=r['baseline']
    lines.append('### Baseline mean abs forward return')
    for h in ['4','24','48']:
        lines.append(f"- {h}h: {base['fwd_abs'][h]['mean']:.4%}")
    lines.append('')
    for name,label in [('oi_bottom_10pct','OI contraction bottom decile'),('oi_top_10pct','OI expansion top decile')]:
        s=r['sets'][name]
        lines.append(f'### {label}\n')
        raw=s['raw']; cl=s['clustered_24h_cooldown']; m=s['controls']['vol_ret_hour_matched']
        lines.append(f"- Raw events: {raw['events']}; 24h-cooldown clustered episodes: {cl['events']}; matched-control candidates: {m['events']}")
        for h in ['4','24','48']:
            e=raw['fwd_abs'][h]['mean']; c=m['fwd_abs'][h]['mean']; ep=cl['fwd_abs'][h]['mean']; b=base['fwd_abs'][h]['mean']
            lines.append(f"- {h}h abs return mean: event `{e:.4%}` vs matched `{c:.4%}` vs clustered `{ep:.4%}` vs baseline `{b:.4%}`")
        lines.append(f"- 24h signed return q05/q95: `{raw['fwd_signed']['24']['q05']:.4%}` / `{raw['fwd_signed']['24']['q95']:.4%}`")
        lines.append('')
lines.append('## First-pass conclusion\n')
lines.append('- BTC shows a clear raw 24h absolute-return lift after bottom-decile OI contraction, but much of it weakens when matched on recent volatility, recent 4h return, and UTC hour.')
lines.append('- ETH shows a smaller raw lift; after matching, the incremental effect is marginal and not obviously stronger than controls.')
lines.append('- Non-overlapping 24h episode clustering reduces sample size materially; BTC still has elevated 24h abs return, ETH is mixed.')
lines.append('- This is not enough for SignalContract or Trader handoff. It remains a Research Only / continue-if-controls-improve candidate.')
lines.append('\n## Recommended next step\n')
lines.append('Tighten the event study before requesting larger data: use rolling 90d percentile thresholds, explicit episode-level bootstrap/confidence intervals, and a recent-vol/return matched sampling procedure with equalized counts. If the matched incremental effect remains small, reject as redundant with realized-volatility controls.')
(OUTDIR/'oi_contraction_event_study_365d.md').write_text('\n'.join(lines))
print('wrote', OUTDIR/'oi_contraction_event_study_365d.json')
print('wrote', OUTDIR/'oi_contraction_event_study_365d.md')
print('\n'.join(lines[-8:]))

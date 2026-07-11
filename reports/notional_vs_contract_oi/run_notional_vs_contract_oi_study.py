
#!/usr/bin/env python3
from __future__ import annotations
import json, math, statistics, random
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

FIXTURE=Path('data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl')
OUT=Path('reports/notional_vs_contract_oi')
OUT.mkdir(parents=True, exist_ok=True)


def parse_dt(s): return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def hour(s):
    d=parse_dt(s); return d.replace(minute=0, second=0, microsecond=0)
def fl(x):
    try: return float(x) if x is not None else None
    except Exception: return None
def pct(a,b):
    if a is None or b is None or b == 0: return None
    return a/b - 1.0
def q(xs,p):
    xs=sorted(x for x in xs if x is not None and math.isfinite(x))
    if not xs: return None
    pos=(len(xs)-1)*p; lo=int(pos); hi=min(lo+1,len(xs)-1); f=pos-lo
    return xs[lo]*(1-f)+xs[hi]*f
def mean(xs):
    xs=[x for x in xs if x is not None and math.isfinite(x)]
    return sum(xs)/len(xs) if xs else None
def median(xs): return q(xs,.5)
def summarise(xs):
    xs=[x for x in xs if x is not None and math.isfinite(x)]
    if not xs: return {'n':0}
    return {'n':len(xs),'mean':mean(xs),'median':median(xs),'q05':q(xs,.05),'q25':q(xs,.25),'q75':q(xs,.75),'q95':q(xs,.95)}

def max_forward_drawdown(closes, i, h):
    base=closes[i]
    if base in (None,0): return None
    vals=[c/base-1 for c in closes[i+1:min(len(closes),i+h+1)] if c is not None]
    return min(vals) if vals else None

def max_forward_up(closes, i, h):
    base=closes[i]
    if base in (None,0): return None
    vals=[c/base-1 for c in closes[i+1:min(len(closes),i+h+1)] if c is not None]
    return max(vals) if vals else None

# aggregate hourly: last observed within hour for each field
H=defaultdict(lambda: defaultdict(dict))
raw_hours=defaultdict(set); notional_hours=defaultdict(set)
counts=defaultdict(int)
for line in FIXTURE.open():
    if not line.strip(): continue
    r=json.loads(line); sym=r['symbol']; kind=r['kind']; meta=r.get('metadata',{}); p=r.get('payload',{}); hr=hour(r['occurred_at']); d=H[sym][hr]
    counts[(sym,kind)] += 1
    if kind=='candle' and meta.get('market_type')=='linear_perp':
        d['close']=fl(p.get('close'))
    elif kind=='perp_open_interest':
        raw=fl(p.get('open_interest_raw'))
        notional=fl(p.get('open_interest_notional_usdt'))
        norm=fl(p.get('normalization_price'))
        if raw is not None:
            d['oi_raw']=raw; raw_hours[sym].add(hr)
        if notional is not None:
            d['oi_notional']=notional; notional_hours[sym].add(hr)
        if norm is not None: d['oi_norm_price']=norm
    elif kind=='perp_funding_rate':
        d['funding']=fl(p.get('funding_rate'))
    elif kind=='perp_spot_basis':
        d['basis_bps']=fl(p.get('basis_bps'))

quality={}
results={}
random.seed(11)
for sym, hd in sorted(H.items()):
    grid=sorted(hd)
    close=[hd[t].get('close') for t in grid]
    raw=[hd[t].get('oi_raw') for t in grid]
    notional=[hd[t].get('oi_notional') for t in grid]
    funding=[hd[t].get('funding') for t in grid]
    # coverage quality
    rh=sorted(raw_hours[sym]); nh=sorted(notional_hours[sym])
    gaps=[]
    for a,b in zip(rh,rh[1:]):
        dh=(b-a).total_seconds()/3600
        if dh>1.01: gaps.append(dh)
    quality[sym]={
        'fixture_hours': len(grid),
        'raw_oi_distinct_hours': len(rh),
        'notional_oi_distinct_hours': len(nh),
        'raw_oi_hour_coverage_ratio': len(rh)/len(grid),
        'notional_oi_hour_coverage_ratio': len(nh)/len(grid),
        'raw_oi_gaps_gt_1h': len(gaps),
        'max_raw_oi_gap_h': max(gaps or [0]),
        'counts': {k[1]:v for k,v in counts.items() if k[0]==sym},
    }
    # feature arrays
    r1=[pct(close[i],close[i-1]) if i>=1 else None for i in range(len(grid))]
    ret4=[pct(close[i],close[i-4]) if i>=4 else None for i in range(len(grid))]
    raw4=[pct(raw[i],raw[i-4]) if i>=4 else None for i in range(len(grid))]
    not4=[pct(notional[i],notional[i-4]) if i>=4 else None for i in range(len(grid))]
    rv24=[]
    for i in range(len(grid)):
        vals=[x for x in r1[max(1,i-23):i+1] if x is not None]
        rv24.append(math.sqrt(sum(x*x for x in vals)) if len(vals)>=20 else None)
    # event definitions
    eligible=[i for i in range(24, len(grid)-72) if None not in (ret4[i], raw4[i], not4[i], rv24[i], close[i])]
    # Thresholds intentionally simple and economic; not tuned to maximize outcomes.
    events={
      'A_true_deleverage': [i for i in eligible if ret4[i] <= -0.0075 and not4[i] <= -0.0100 and raw4[i] <= -0.0050],
      'B_passive_notional_shrink': [i for i in eligible if ret4[i] <= -0.0075 and not4[i] <= -0.0100 and raw4[i] > -0.0025],
      'C_short_build_or_sticky_leverage': [i for i in eligible if ret4[i] <= -0.0075 and raw4[i] >= 0.0050],
      'D_risk_on_leverage_build': [i for i in eligible if ret4[i] >= 0.0075 and raw4[i] >= 0.0050 and not4[i] >= 0.0100],
    }
    # non-overlap cluster 24h
    clustered={}
    for name, idxs in events.items():
        out=[]; last=-10**9
        for i in idxs:
            if i-last >= 24:
                out.append(i); last=i
        clustered[name]=out
    baseline=[i for i in eligible]
    horizons=[4,24,48,72]
    symres={'thresholds': {'price_4h_down': -0.0075, 'notional_4h_down': -0.0100, 'raw_4h_down': -0.0050, 'raw_flat_floor': -0.0025, 'raw_build': 0.0050}, 'event_counts':{}, 'events':{}, 'baseline':{}}
    for h in horizons:
        symres['baseline'][f'fwd_{h}h_return']=summarise([pct(close[i+h], close[i]) for i in baseline if i+h<len(close)])
        symres['baseline'][f'fwd_{h}h_abs_return']=summarise([abs(pct(close[i+h], close[i])) for i in baseline if i+h<len(close)])
    for name, idxs in clustered.items():
        symres['event_counts'][name]={'raw_hourly': len(events[name]), 'clustered_24h': len(idxs)}
        detail=[]
        for i in idxs[:20]:
            detail.append({'time': grid[i].isoformat(), 'ret4': ret4[i], 'raw_oi4': raw4[i], 'notional_oi4': not4[i], 'close': close[i], 'raw_oi': raw[i], 'notional_oi': notional[i]})
        er={'sample_events': detail, 'features': {
            'ret4': summarise([ret4[i] for i in idxs]),
            'raw_oi4': summarise([raw4[i] for i in idxs]),
            'notional_oi4': summarise([not4[i] for i in idxs]),
            'rv24': summarise([rv24[i] for i in idxs]),
        }}
        for h in horizons:
            er[f'fwd_{h}h_return']=summarise([pct(close[i+h], close[i]) for i in idxs if i+h<len(close)])
            er[f'fwd_{h}h_abs_return']=summarise([abs(pct(close[i+h], close[i])) for i in idxs if i+h<len(close)])
            er[f'fwd_{h}h_max_drawdown']=summarise([max_forward_drawdown(close,i,h) for i in idxs])
            er[f'fwd_{h}h_max_up']=summarise([max_forward_up(close,i,h) for i in idxs])
        symres['events'][name]=er
    results[sym]=symres

out={'fixture': str(FIXTURE), 'quality': quality, 'results': results, 'notes': [
    'Hourly aggregation uses last observation in each UTC hour.',
    'Event thresholds are fixed ex ante for first pass, not optimized.',
    'Clustered counts use 24h cooldown to reduce overlapping event inflation.',
    'Bybit-only BTCUSDT/ETHUSDT; no cross-venue confirmation yet.'
]}
OUT.joinpath('notional_vs_contract_oi_event_study_365d.json').write_text(json.dumps(out, indent=2, default=str))
# markdown concise report
lines=[]
lines.append('# Notional OI vs Contract OI Deleveraging Classifier — 365d First Pass')
lines.append('')
lines.append(f'- Fixture: `{FIXTURE}`')
lines.append('- Venue/symbols: Bybit BTCUSDT, ETHUSDT')
lines.append('- Aggregation: hourly last close/OI')
lines.append('- Event window: 4h changes; outcome horizons: 4h/24h/48h/72h')
lines.append('- Cluster rule: 24h cooldown')
lines.append('')
lines.append('## Data quality')
for sym,qv in quality.items():
    lines.append(f'- {sym}: raw OI hourly coverage `{qv["raw_oi_hour_coverage_ratio"]:.3f}`, raw OI hours `{qv["raw_oi_distinct_hours"]}/{qv["fixture_hours"]}`, gaps>1h `{qv["raw_oi_gaps_gt_1h"]}`, max gap `{qv["max_raw_oi_gap_h"]}`')
lines.append('')
lines.append('## Event definitions')
lines.append('- A_true_deleverage: 4h price <= -0.75%, notional OI <= -1.00%, raw/contract OI <= -0.50%')
lines.append('- B_passive_notional_shrink: 4h price <= -0.75%, notional OI <= -1.00%, raw/contract OI > -0.25%')
lines.append('- C_short_build_or_sticky_leverage: 4h price <= -0.75%, raw/contract OI >= +0.50%')
lines.append('- D_risk_on_leverage_build: 4h price >= +0.75%, raw/contract OI >= +0.50%, notional OI >= +1.00%')
lines.append('')
for sym,sr in results.items():
    lines.append(f'## {sym}')
    base24=sr['baseline']['fwd_24h_abs_return']['mean']
    lines.append(f'- Baseline 24h abs return mean: `{base24*100:.2f}%`')
    for name,c in sr['event_counts'].items():
        ev=sr['events'][name]
        f24=ev['fwd_24h_return']; a24=ev['fwd_24h_abs_return']; dd24=ev['fwd_24h_max_drawdown']
        lines.append(f'- {name}: clustered `{c["clustered_24h"]}` / raw `{c["raw_hourly"]}`; 24h mean return `{(f24.get("mean") or 0)*100:.2f}%`, 24h abs `{(a24.get("mean") or 0)*100:.2f}%`, 24h max DD `{(dd24.get("mean") or 0)*100:.2f}%`')
    lines.append('')
lines.append('## First-pass interpretation')
lines.append('- This is a classifier/risk-regime study, not a trading signal or Trader handoff.')
lines.append('- Use the JSON for full quantiles and sample events; chat summary should stay conservative.')
OUT.joinpath('notional_vs_contract_oi_event_study_365d.md').write_text('\n'.join(lines))
print(json.dumps({'quality': quality, 'report': str(OUT/'notional_vs_contract_oi_event_study_365d.md'), 'json': str(OUT/'notional_vs_contract_oi_event_study_365d.json')}, indent=2)[:5000])

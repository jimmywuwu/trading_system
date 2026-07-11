
#!/usr/bin/env python3
import json, math, random, statistics
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
FIXTURE=Path('data/bybit_leverage_pressure_fixture_365d.jsonl')
OUT=Path('reports/oi_contraction_deleveraging')

def parse_hour(s):
 d=datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc); return d.replace(minute=0,second=0,microsecond=0)
def fl(x):
 try: return float(x) if x is not None else None
 except: return None
def pct(a,b): return None if a is None or b in (None,0) else a/b-1
def q(xs,p):
 xs=sorted(x for x in xs if x is not None and math.isfinite(x))
 if not xs: return None
 pos=(len(xs)-1)*p; lo=int(pos); hi=min(lo+1,len(xs)-1); f=pos-lo
 return xs[lo]*(1-f)+xs[hi]*f
def mean(xs):
 xs=[x for x in xs if x is not None and math.isfinite(x)]
 return sum(xs)/len(xs) if xs else None
def edges(xs): return [q(xs,i/10) for i in range(1,10)]
def bin_idx(x,ed):
 if x is None: return None
 i=0
 while i<len(ed) and x>ed[i]: i+=1
 return i
def ci(vals): return (q(vals,.025), q(vals,.5), q(vals,.975))

H=defaultdict(lambda: defaultdict(dict)); oi_hours=defaultdict(set)
for line in FIXTURE.open():
 r=json.loads(line); sym=r['symbol']; kind=r['kind']; meta=r.get('metadata',{}); p=r.get('payload',{}); hr=parse_hour(r['occurred_at']); d=H[sym][hr]
 if kind=='candle' and meta.get('market_type')=='linear_perp': d['close']=fl(p.get('close'))
 elif kind=='perp_open_interest':
  d['oi']=fl(p.get('open_interest_notional_usdt')) or fl(p.get('open_interest_raw')); oi_hours[sym].add(hr)

random.seed(7)
rows=[]; quality={}
for sym,hd in H.items():
 grid=sorted(hd); close=[hd[t].get('close') for t in grid]; oi=[hd[t].get('oi') for t in grid]
 one=[pct(close[i],close[i-1]) if i>=1 else None for i in range(len(grid))]
 ret4=[pct(close[i],close[i-4]) if i>=4 else None for i in range(len(grid))]
 oi4=[pct(oi[i],oi[i-4]) if i>=4 else None for i in range(len(grid))]
 rv24=[]
 for i in range(len(grid)):
  vals=[v for v in one[max(1,i-23):i+1] if v is not None]
  rv24.append(math.sqrt(sum(v*v for v in vals)) if len(vals)>=20 else None)
 fwd={h:[abs(pct(close[i+h],close[i])) if i+h<len(close) else None for i in range(len(grid))] for h in [4,24,48]}
 eligible=[i for i in range(len(grid)-48) if oi4[i] is not None and rv24[i] is not None and ret4[i] is not None]
 bot10=q([oi4[i] for i in eligible],.10)
 events=[i for i in eligible if oi4[i]<=bot10]
 vedges=edges([rv24[i] for i in eligible]); redges=edges([ret4[i] for i in eligible])
 evkeys=[]
 for i in events:
  evkeys.append((bin_idx(rv24[i],vedges), bin_idx(ret4[i],redges), grid[i].hour))
 keyset=set(evkeys)
 controls=[i for i in eligible if i not in set(events) and (bin_idx(rv24[i],vedges), bin_idx(ret4[i],redges), grid[i].hour) in keyset]
 # cluster 24h
 cl=[]; last=-10**9
 for i in events:
  if i-last>=24: cl.append(i); last=i
 # bootstrap independent event vs matched candidates with equal event count
 for h in [4,24,48]:
  ev=[fwd[h][i] for i in events if fwd[h][i] is not None]
  co=[fwd[h][i] for i in controls if fwd[h][i] is not None]
  diffs=[]
  for _ in range(3000):
   es=[random.choice(ev) for __ in range(len(ev))]
   cs=[random.choice(co) for __ in range(len(ev))]
   diffs.append(mean(es)-mean(cs))
  rows.append({'symbol':sym,'h':h,'event_n':len(ev),'control_n':len(co),'event_mean':mean(ev),'control_mean_equalized_candidate':mean(co),'diff_ci':ci(diffs),'cluster_n':len(cl),'cluster_mean':mean([fwd[h][i] for i in cl])})
 hours=sorted(oi_hours[sym]); gaps=[]
 for a,b in zip(hours,hours[1:]):
  dh=(b-a).total_seconds()/3600
  if dh>1: gaps.append(dh)
 quality[sym]={'fixture_hours':len(grid),'oi_distinct_hours':len(hours),'oi_hour_coverage_ratio':len(hours)/len(grid),'oi_gaps_gt_1h':len(gaps),'max_oi_gap_h':max(gaps or [0]),'eligible_event_rows':len(eligible)}

OUT.joinpath('oi_contraction_bootstrap_and_quality.json').write_text(json.dumps({'quality':quality,'bootstrap':rows},indent=2))
print(json.dumps({'quality':quality,'bootstrap':rows}, indent=2)[:6000])


#!/usr/bin/env python3
from __future__ import annotations
import json, math, random
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

FIXTURE=Path('data/regenerated/bybit_leverage_pressure_fixture_365d_20260614_regen.jsonl')
OUT=Path('reports/notional_vs_contract_oi')

def parse_dt(s): return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def hour(s):
 d=parse_dt(s); return d.replace(minute=0,second=0,microsecond=0)
def fl(x):
 try: return float(x) if x is not None else None
 except: return None
def pct(a,b): return None if a is None or b in (None,0) else a/b-1
def mean(xs):
 xs=[x for x in xs if x is not None and math.isfinite(x)]
 return sum(xs)/len(xs) if xs else None
def q(xs,p):
 xs=sorted(x for x in xs if x is not None and math.isfinite(x))
 if not xs: return None
 pos=(len(xs)-1)*p; lo=int(pos); hi=min(lo+1,len(xs)-1); f=pos-lo
 return xs[lo]*(1-f)+xs[hi]*f
def ci(xs): return [q(xs,.025),q(xs,.5),q(xs,.975)]
def boot_diff(a,b,iters=5000):
 a=[x for x in a if x is not None and math.isfinite(x)]; b=[x for x in b if x is not None and math.isfinite(x)]
 if not a or not b: return None
 diffs=[]
 for _ in range(iters):
  aa=[random.choice(a) for __ in range(len(a))]
  bb=[random.choice(b) for __ in range(len(b))]
  diffs.append(mean(aa)-mean(bb))
 return {'a_n':len(a),'b_n':len(b),'a_mean':mean(a),'b_mean':mean(b),'diff_mean':mean(diffs),'diff_ci':ci(diffs)}
def maxdd(closes,i,h):
 base=closes[i]
 if base in (None,0): return None
 vals=[c/base-1 for c in closes[i+1:min(len(closes),i+h+1)] if c is not None]
 return min(vals) if vals else None
H=defaultdict(lambda: defaultdict(dict))
for line in FIXTURE.open():
 if not line.strip(): continue
 r=json.loads(line); sym=r['symbol']; kind=r['kind']; meta=r.get('metadata',{}); p=r.get('payload',{}); d=H[sym][hour(r['occurred_at'])]
 if kind=='candle' and meta.get('market_type')=='linear_perp': d['close']=fl(p.get('close'))
 elif kind=='perp_open_interest':
  d['raw']=fl(p.get('open_interest_raw')); d['notional']=fl(p.get('open_interest_notional_usdt'))
random.seed(23)
allout={}
for sym,hd in sorted(H.items()):
 grid=sorted(hd); close=[hd[t].get('close') for t in grid]; raw=[hd[t].get('raw') for t in grid]; notional=[hd[t].get('notional') for t in grid]
 ret4=[pct(close[i],close[i-4]) if i>=4 else None for i in range(len(grid))]
 raw4=[pct(raw[i],raw[i-4]) if i>=4 else None for i in range(len(grid))]
 not4=[pct(notional[i],notional[i-4]) if i>=4 else None for i in range(len(grid))]
 elig=[i for i in range(24,len(grid)-72) if None not in (ret4[i],raw4[i],not4[i],close[i])]
 raw_events={
  'A_true_deleverage':[i for i in elig if ret4[i]<=-0.0075 and not4[i]<=-0.0100 and raw4[i]<=-0.0050],
  'B_passive_notional_shrink':[i for i in elig if ret4[i]<=-0.0075 and not4[i]<=-0.0100 and raw4[i]>-0.0025],
  'C_short_build_or_sticky_leverage':[i for i in elig if ret4[i]<=-0.0075 and raw4[i]>=0.0050],
  'D_risk_on_leverage_build':[i for i in elig if ret4[i]>=0.0075 and raw4[i]>=0.0050 and not4[i]>=0.0100],
 }
 events={}
 for k,idxs in raw_events.items():
  out=[]; last=-10**9
  for i in idxs:
   if i-last>=24: out.append(i); last=i
  events[k]=out
 metrics={}
 for k,idxs in events.items():
  metrics[k]={}
  for h in [24,48,72]:
   metrics[k][f'ret_{h}h']=[pct(close[i+h],close[i]) for i in idxs]
   metrics[k][f'abs_{h}h']=[abs(pct(close[i+h],close[i])) for i in idxs]
   metrics[k][f'maxdd_{h}h']=[maxdd(close,i,h) for i in idxs]
 pairs={}
 for h in [24,48,72]:
  for metric in [f'ret_{h}h',f'abs_{h}h',f'maxdd_{h}h']:
   pairs[f'B_minus_A_{metric}']=boot_diff(metrics['B_passive_notional_shrink'][metric], metrics['A_true_deleverage'][metric])
   pairs[f'C_minus_A_{metric}']=boot_diff(metrics['C_short_build_or_sticky_leverage'][metric], metrics['A_true_deleverage'][metric])
   pairs[f'D_minus_A_{metric}']=boot_diff(metrics['D_risk_on_leverage_build'][metric], metrics['A_true_deleverage'][metric])
 allout[sym]={'cluster_counts':{k:len(v) for k,v in events.items()},'pairwise_bootstrap':pairs}
OUT.joinpath('notional_vs_contract_oi_pairwise_bootstrap_365d.json').write_text(json.dumps(allout,indent=2))
# concise append markdown
lines=['## Pairwise bootstrap checks (clustered events)','', 'Positive `abs` diff means first class has higher forward realized move than A_true_deleverage. CI is 2.5/50/97.5%.','']
for sym,res in allout.items():
 lines.append(f'### {sym}')
 lines.append(f'- Cluster counts: {res["cluster_counts"]}')
 for key in ['B_minus_A_abs_24h','B_minus_A_abs_48h','B_minus_A_ret_24h','C_minus_A_ret_24h','D_minus_A_abs_24h']:
  v=res['pairwise_bootstrap'][key]
  if v:
   ci_pct=[x*100 for x in v['diff_ci']]
   lines.append(f'- {key}: diff mean `{v["diff_mean"]*100:.2f}%`, CI `[{ci_pct[0]:.2f}%, {ci_pct[1]:.2f}%, {ci_pct[2]:.2f}%]`')
 lines.append('')
Path('reports/notional_vs_contract_oi/notional_vs_contract_oi_pairwise_bootstrap_365d.md').write_text('\n'.join(lines))
print(json.dumps(allout, indent=2)[:5000])

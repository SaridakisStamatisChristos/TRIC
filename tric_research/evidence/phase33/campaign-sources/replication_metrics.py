from pathlib import Path
import gzip,json,statistics
O=Path(__file__).resolve().parent;P=json.loads((O/'replication_protocol.json').read_text());out={}
for kind in ('warm','cold'):
 cells=[]
 for name in P['fixtures']:
  ratios={a:[] for a in ('csr_v2','identical')};rep={a:[] for a in ratios}
  for prefix,trials in [('qualification',9),('replication',27)]:
   m=json.loads((O/(prefix+'-'+kind)/'manifest.json').read_text());assert m['complete']
   data=json.loads(gzip.decompress((O/(prefix+'-'+kind)/name).read_bytes()));assert len(data)==1
   rows=data[0]['rows'];assert all(len(x)==trials for x in rows.values())
   for arm in ratios:
    for x,y in zip(rows['previous'],rows[arm]):
     for k in ('checksum','table_bytes','retained_capacity_bytes','uses_direct_closure','uses_forest_index'):assert x[k]==y[k]
     nx=x['build_count'] if kind=='warm' else 1;ny=y['build_count'] if kind=='warm' else 1
     ratio=x['build_thread_cpu_ns']/nx/(y['build_thread_cpu_ns']/ny);ratios[arm].append(ratio)
     if prefix=='replication':rep[arm].append(ratio)
  cells.append({'dataset':data[0]['dataset'],'pooled':{a:statistics.median(v) for a,v in ratios.items()},'replication':{a:statistics.median(v) for a,v in rep.items()}})
 out[kind]={}
 for group in ('replication','pooled'):
  median=statistics.median(c[group]['csr_v2'] for c in cells);worst=min(c[group]['csr_v2'] for c in cells);bad=[c for c in cells if not .9<=c[group]['identical']<=1/.9]
  out[kind][group]={'median':median,'worst':worst,'null_failures':bad,'passes':median>=P['gates'][kind+'_median'] and worst>=P['gates'][kind+'_floor'] and not bad}
 out[kind]['cells']=cells
 print(kind,{k:v for k,v in out[kind].items() if k!='cells'})
out['promotable']=all(out[k][g]['passes'] for k in ('warm','cold') for g in ('replication','pooled'))
(O/'replication_metrics.json').write_text(json.dumps(out,indent=2)+'\n')

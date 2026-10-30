from pathlib import Path
import gzip,json,statistics
O=Path(__file__).resolve().parent;P=json.loads((O/'qualification_v2_protocol.json').read_text());out={}
for kind in ('warm','cold'):
 D=O/('qualification-'+kind);m=json.loads((D/'manifest.json').read_text());assert m['complete'] and len(m['files'])==37;cells=[]
 for f in m['files']:
  for cell in json.loads(gzip.decompress((D/f['file']).read_bytes())):
   rows=cell['rows'];a=rows['previous'];assert all(len(b)==9 for b in rows.values());ratios={}
   for arm in ('csr_v2','identical'):
    vals=[]
    for x,y in zip(a,rows[arm]):
     for k in ('table_bytes','retained_capacity_bytes','uses_direct_closure','uses_forest_index','checksum'):assert x[k]==y[k],(cell['dataset'],k)
     nx=x['build_count'] if kind=='warm' else 1;ny=y['build_count'] if kind=='warm' else 1
     if kind=='warm':assert min(x['build_thread_cpu_ns'],y['build_thread_cpu_ns'])>=200000000
     vals.append(x['build_thread_cpu_ns']/nx/(y['build_thread_cpu_ns']/ny))
    ratios[arm]=statistics.median(vals)
   cells.append({'dataset':cell['dataset'],**ratios})
 med=statistics.median(c['csr_v2'] for c in cells);floor=min(c['csr_v2'] for c in cells);null=[c for c in cells if not .9<=c['identical']<=1/.9]
 out[kind]={'median':med,'worst':floor,'null_failures':null,'passes':med>=P['gates'][kind+'_median'] and floor>=P['gates'][kind+'_floor'] and not null,'cells':cells}
 print(kind,{k:v for k,v in out[kind].items() if k!='cells'})
out['promotable']=all(v['passes'] for v in out.values());(O/'qualification_metrics.json').write_text(json.dumps(out,indent=2)+'\n')

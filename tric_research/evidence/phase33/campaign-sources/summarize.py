from pathlib import Path
import gzip,json,statistics,math
O=Path(__file__).resolve().parent;m=json.loads((O/'pilot/manifest.json').read_text());assert m['complete'];assert len(m['files'])==31
out={};total=0
for arm in ('csr','closure','buffers','identical'):
 cells=[]
 for f in m['files']:
  for cell in json.loads(gzip.decompress((O/'pilot'/f['file']).read_bytes())):
   a=cell['rows']['previous'];b=cell['rows'][arm];assert len(a)==len(b)==5
   ratios=[]
   for x,y in zip(a,b):
    for k in ('table_bytes','retained_capacity_bytes','uses_direct_closure','uses_forest_index','checksum'):assert x[k]==y[k],(arm,cell['dataset'],k)
    assert x['build_thread_cpu_ns']>=200000000 and y['build_thread_cpu_ns']>=200000000
    assert x['build_count']>=2 and y['build_count']>=2
    ratios.append((x['build_thread_cpu_ns']/x['build_count'])/(y['build_thread_cpu_ns']/y['build_count']))
   cells.append({'dataset':cell['dataset'],'ratio':statistics.median(ratios),'direct':a[0]['uses_direct_closure']})
 out[arm]={'median':statistics.median(c['ratio'] for c in cells),'worst':min(c['ratio'] for c in cells),'best':max(c['ratio'] for c in cells),'cells':cells}
null=[c for c in out['identical']['cells'] if not .9<=c['ratio']<=1/.9]
for arm in ('csr','closure','buffers'):out[arm]['passes_pilot']=out[arm]['median']>=1.05 and out[arm]['worst']>=.9 and not null
(O/'pilot_metrics.json').write_text(json.dumps({'arms':out,'null_failures':null,'processes':775},indent=2)+'\n')
for arm,r in out.items():print(arm,{k:v for k,v in r.items() if k!='cells'},'worst_case',min(r['cells'],key=lambda x:x['ratio']))
print('null failures',null)

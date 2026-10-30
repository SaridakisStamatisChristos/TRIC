from pathlib import Path
import subprocess,sys,json,gzip,hashlib
R=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');O=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from verify_interval_storage import purpose_cases
from test_native_runtime import serialize
rows=[];builds={}
for arm in ('previous','csr','buffers'):
 d=O/arm;src=d/'interval_storage_check.cpp';src.write_bytes((R/src.name).read_bytes());cmd=['g++','-std=c++17','-O2','-fsanitize=undefined',str(src),'-o',str(d/'memory')];subprocess.run(cmd,check=True,capture_output=True);builds[arm]={'command':cmd,'sha256':hashlib.sha256((d/'memory').read_bytes()).hexdigest()}
specs=[(x['name'],x['graph'],x['queries'],x['mode'],x['cap'],x['scratch']) for x in purpose_cases()]
for f in sorted((O/'qualification-fixtures').glob('*.gz')):
 obj=json.loads(gzip.decompress(f.read_bytes()));g=[[] for _ in range(obj['graph']['vertices'])]
 for a,b in obj['graph']['arcs']:g[a].append(b)
 specs.append((f.stem,g,obj['cases'][0]['queries'],'auto',2097152,67108864))
for name,g,qs,mode,cap,scratch in specs:
 raw=serialize(g,qs).encode();record={'name':name,'input_sha256':hashlib.sha256(raw).hexdigest(),'mode':mode,'cap':cap,'scratch':scratch,'arms':{}}
 for arm in ('previous','csr','buffers'):
  p=subprocess.run([str(O/arm/'memory'),mode,str(cap),str(scratch)],input=raw,capture_output=True,check=True,timeout=300);assert not p.stderr;record['arms'][arm]=json.loads(p.stdout)
 a=record['arms']['previous']
 for arm in ('csr','buffers'):
  b=record['arms'][arm]
  for k in ('table_bytes','retained_bytes','live_heap_bytes','live_blocks','oracle_checks','checksum','components','indexed','partitions','chains','bits','compressed','intervals','merged','skipped','direct','forest'):assert a[k]==b[k],(name,arm,k)
  assert b['construction_peak_heap_bytes']<=a['construction_peak_heap_bytes'],(name,arm,'peak')
 rows.append(record);print('Resources verified',name,flush=True)
(O/'resources.json').write_text(json.dumps({'builds':builds,'records':rows},indent=2)+'\n')

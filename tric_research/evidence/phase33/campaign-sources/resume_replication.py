from pathlib import Path
import sys,argparse,json,shutil,platform,os
O=Path(__file__).resolve().parent;R=O.parent/'TRIC/tric_research';sys.path.insert(0,str(R))
from benchmark_native_changes import run,digest,atomic_write
p=json.loads((O/'replication_protocol.json').read_text());b=json.loads((O/'v2_builds.json').read_text())
prior=O/'replication-warm';part1=O/'replication-warm-part1';assert prior.exists() and not part1.exists();prior.rename(part1)
m=json.loads((part1/'manifest.json').read_text());assert not m.get('complete');done={x['file'] for x in m['files']}
for x in m['files']:assert digest((part1/x['file']).read_bytes())==x['sha256']
for name,h in p['fixtures'].items():assert digest((O/'qualification-fixtures'/name).read_bytes())==h
for kind in ('warm','cold'):assert digest((O/'csr_v2'/(kind+'-bench')).read_bytes())==b[kind]['sha256']
receipt={'reason':'Session interrupted after 25 complete graphs. Preserve original manifest and completed bytes; execute only remaining warm graphs and all cold graphs. No timing threshold, source or compiler change.','prior_manifest_sha256':digest((part1/'manifest.json').read_bytes()),'completed_files':sorted(done),'remaining_files':sorted(set(p['fixtures'])-done),'continuation_platform':platform.platform(),'cpu_model':next(l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name')),'date':'2026-10-30'}
(O/'replication_continuation.json').write_text(json.dumps(receipt,indent=2)+'\n')
remaining=[json.loads(__import__('gzip').decompress((O/'qualification-fixtures'/n).read_bytes()))['dataset'] for n in receipt['remaining_files']]
for kind in ('warm','cold'):
 baseline=O/'previous/bench' if kind=='warm' else O/'standard-build/previous';exe=O/'csr_v2'/(kind+'-bench');dest=O/('replication-warm-part2' if kind=='warm' else 'replication-cold')
 run(argparse.Namespace(fixtures=str(O/'qualification-fixtures'),output=str(dest),cpu=1,arm=[('previous',str(baseline),'auto'),('csr_v2',str(exe),'auto'),('identical',str(baseline),'auto')],trials=27,horizons=[1],cap=p['cap'],datasets=remaining if kind=='warm' else None,seeds=None,timeout=300))
 if kind=='warm':
  second=json.loads((dest/'manifest.json').read_text());assert second['complete'] and second['arms']==m['arms']
  combined=O/'replication-warm';combined.mkdir();entries=m['files']+second['files'];assert len(entries)==37 and len({x['file'] for x in entries})==37
  for entry in entries:shutil.copyfile((part1 if entry['file'] in done else dest)/entry['file'],combined/entry['file'])
  m.update(files=sorted(entries,key=lambda x:x['file']),complete=True,segments=[{'directory':'replication-warm-part1','manifest_sha256':digest((part1/'manifest.json').read_bytes())},{'directory':'replication-warm-part2','manifest_sha256':digest((dest/'manifest.json').read_bytes())}]);atomic_write(combined/'manifest.json',(json.dumps(m,indent=2)+'\n').encode())
 print('Completed resumed',kind,flush=True)

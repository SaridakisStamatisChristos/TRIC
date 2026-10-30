"""Frozen-default comparison; failures are retained and never scored as wins."""
from pathlib import Path
import gzip,json,hashlib,subprocess,os,sys,platform
O=Path(__file__).resolve().parent;R=O.parent/'TRIC/tric_research';sys.path.insert(0,str(R))
from benchmark_native_changes import payload,atomic_write,digest
P=json.loads((O/'external_protocol.json').read_text());E=O/sys.argv[1];D=O/'external-results'
os.sched_setaffinity(0,{P['cpu']});D.mkdir(exist_ok=True);assert (D/'manifest.json').is_file()
manifest={'protocol_sha256':digest((O/'external_protocol.json').read_bytes()),'executable_sha256':digest(E.read_bytes()),'platform':platform.platform(),'cpu_affinity':sorted(os.sched_getaffinity(0)),'files':[],'complete':False}
def save(name,obj):
 data=json.dumps(obj,separators=(',',':')).encode();path=D/name
 if name.endswith('.gz'):data=gzip.compress(data,mtime=0)
 atomic_write(path,data);return digest(data)
def invoke(arm,raw,target):
 cmd=['prlimit','--as=4294967296','--',str(E),'tric' if arm=='identical' else arm,str(target)]
 try:p=subprocess.run(cmd,input=raw,capture_output=True,timeout=120)
 except subprocess.TimeoutExpired as e:return {'status':'timeout','stdout':(e.stdout or b'').decode(errors='replace'),'stderr':(e.stderr or b'').decode(errors='replace')}
 rec={'returncode':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')}
 if p.returncode:rec['status']='wrong_answer' if 'mismatch' in rec['stderr'] else 'process_failure';return rec
 row=json.loads(p.stdout);assert row['calls']==row['queries']*row['repeats'] and row['verified']==row['queries'];assert row['query_cpu_ns']>=target
 rec.update(status='ok',row=row);return rec
manifest=json.loads((D/'manifest.json').read_text())
assert manifest['executable_sha256']==digest(E.read_bytes())
assert manifest['protocol_sha256']==digest((O/'external_protocol.json').read_bytes())
for item in manifest['files']:assert digest((D/item['file']).read_bytes())==item['sha256']
manifest['continuation']={'date':'2026-10-30','completed_cases':len(manifest['files']),'prior_manifest_sha256':digest((O/'external-interrupted-manifest.json').read_bytes()),'platform':platform.platform()}
pre=json.loads((D/'preflight.json').read_text());disqualified=set(manifest['disqualified'])
for path in []:  # Preserved preflight is complete and hash checked above.
 f=json.loads(gzip.decompress(path.read_bytes()))
 if f['graph']['vertices']>40000:continue
 c=f['cases'][0];raw=payload(f,c);assert digest(raw)==c['native_input_sha256'];rows={}
 for arm in P['arms'][:-1]:
  rows[arm]=invoke(arm,raw,1)
  if rows[arm]['status']=='wrong_answer':disqualified.add(arm)
 good=[x['row']['answer_hash'] for x in rows.values() if x['status']=='ok'];assert len(set(good))<=1
 pre.append({'dataset':f['dataset'],'input_sha256':digest(raw),'rows':rows});save('preflight.json',pre)
 print('preflight',f['dataset'],{k:v['status'] for k,v in rows.items()},flush=True)
manifest['disqualified']=sorted(disqualified);manifest['preflight_sha256']=digest((D/'preflight.json').read_bytes());save('manifest.json',manifest)
for spec in P['cases']:
 if any(x['file']==spec['dataset']+'-'+spec['stratum']+'.json.gz' for x in manifest['files']):continue
 f=json.loads(gzip.decompress(Path(spec['fixture']).read_bytes()));c=next(c for c in f['cases'] if c['seed']==spec['seed'] and c['stratum']==spec['stratum']);raw=payload(f,c);assert digest(raw)==spec['input_sha256'];arms=P['arms'];rows={a:[] for a in arms}
 for trial in range(P['trials']):
  for arm in arms[trial%len(arms):]+arms[:trial%len(arms)]:
   rec={'status':'disqualified'} if arm in disqualified else invoke(arm,raw,P['query_target_cpu_ns']);rec['trial']=trial;rows[arm].append(rec)
   if rec['status']=='wrong_answer':disqualified.add(arm)
 good=[x['row']['answer_hash'] for a in rows.values() for x in a if x['status']=='ok'];assert len(set(good))<=1
 name=spec['dataset']+'-'+spec['stratum']+'.json.gz';h=save(name,{'spec':spec,'rows':rows});manifest['files'].append({'file':name,'sha256':h});manifest['disqualified']=sorted(disqualified);save('manifest.json',manifest)
 print('case',name,'failures',sum(r['status']!='ok' for a in rows.values() for r in a),flush=True)
manifest['complete']=True;save('manifest.json',manifest)

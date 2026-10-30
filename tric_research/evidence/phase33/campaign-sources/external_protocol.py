from pathlib import Path
import json,gzip,hashlib
R=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');O=Path(__file__).resolve().parent
spec=[]
for path in sorted((R/'evidence/phase25/fixtures').glob('*.json.gz')):
 f=json.loads(gzip.decompress(path.read_bytes()));seed=f['cases'][0]['seed']
 for c in f['cases']:
  if c['seed']==seed:spec.append({'fixture':str(path),'dataset':f['dataset'],'seed':seed,'stratum':c['stratum'],'input_sha256':c['native_input_sha256']})
assert len(spec)==76
p={'upstream':'reneveloso/PyReachability','upstream_commit':'0c84ca38de2d384c561690f4782f93e19fc76816','arms':['tric','feline','grail','preach','ferrari','tflabel','tol','identical'],'cpu':1,'trials':8,'query_target_cpu_ns':100000000,'cases':spec,'query_warmup':'one complete pass per process, identical query list','controls':'identical calls same TRIC implementation in same executable; per-case normalized median ratio required in [0.90,1/0.90] before a speed comparison is qualified','resource_scope':'TRIC uses 2 MiB table allowance; competitor defaults are NOT total-memory matched. Report implementation-owned payload estimates separately from measured VmHWM. No global SOTA or author-original performance claim.','defaults':{'feline':'one-direction','grail':'5 dimensions, seed1, one-direction','ferrari':'k5,c4,seeds32','preach':'upstream default','tflabel':'upstream default','tol':'upstream default'},'failure_policy':'preflight every preserved pilot fixture with <=40000 vertices; any wrong answer disqualifies method; 120s/4GiB process budget failures recorded, not wins. No tuning defaults after observation.'}
(O/'external_protocol.json').write_text(json.dumps(p,indent=2)+'\n')

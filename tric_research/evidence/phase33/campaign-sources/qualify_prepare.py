from pathlib import Path
import json,gzip,random,hashlib,shutil,subprocess,shlex,sys
R=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');O=Path(__file__).resolve().parent
sys.path.insert(0,str(R));from benchmark_native_changes import payload
folder=O/'qualification-fixtures';shutil.copytree(O/'fixtures',folder)
for shape in ('sparse_random','cycle_bags','reverse_trees','permuted_chain','duplicate_bipartite','isolates'):
 r=random.Random(2026102807);n=3000;edges=[]
 if shape=='sparse_random':edges=[(r.randrange(n),r.randrange(n)) for _ in range(n*2)]
 if shape=='cycle_bags':edges=[(i,i//5*5+(i+1)%5) for i in range(n)]+[(i,i+5) for i in range(0,n-5,5)]+[(r.randrange(n-500),r.randrange(n-500,n)) for _ in range(n)]
 if shape=='reverse_trees':edges=[(i,r.randrange(i)) for i in range(1,n) if i%41]
 if shape=='permuted_chain':
  perm=list(range(n));r.shuffle(perm);edges=[(perm[i],perm[i+1]) for i in range(n-1)]
 if shape=='duplicate_bipartite':edges=[(u,r.randrange(n//2,n)) for u in range(n//2) for _ in range(12)];edges=edges*3
 if shape=='isolates':edges=[(i,i+1) for i in range(0,n//3,3)]
 qs=[[r.randrange(n),r.randrange(n)] for _ in range(512)]+[[0,0],[0,n-1],[n-1,0]]
 f={'dataset':'phase33_holdout_'+shape,'graph':{'vertices':n,'arcs':edges},'cases':[{'seed':2026102807,'stratum':'uniform','queries':qs}]};f['cases'][0]['native_input_sha256']=hashlib.sha256(payload(f,f['cases'][0])).hexdigest();(folder/(f['dataset']+'.json.gz')).write_bytes(gzip.compress(json.dumps(f,separators=(',',':')).encode(),mtime=0))
p={'baseline_commit':'02a91849193e12266785ecfd1d49cd8d87b458f2','candidate':'csr','arms':['previous','csr','identical'],'trials':9,'cpu':1,'cap':2097152,'cases':37,'candidate_header_sha256':hashlib.sha256((O/'csr/scc_decomposition.h').read_bytes()).hexdigest(),'fixtures':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.glob('*.gz'))},'gates':{'warm_median':1.10,'warm_floor':.95,'cold_median':1.05,'cold_floor':.90,'null_band':[.9,1/.9],'correctness':True,'same_retained_memory':True,'same_components':True,'allocation_peak_no_increase':True},'scope':'Warm construction CPU per build and fresh-process single construction CPU; query source and SCC IDs unchanged, no query speed claim. All 31 pilot graphs plus six new frozen synthetic shapes. Nine cyclic trials; no candidate tuning.'};(O/'qualification_protocol.json').write_text(json.dumps(p,indent=2)+'\n')
build=O/'standard-build';build.mkdir();shutil.copyfile(R/'native_compare_bench.cpp',build/'native_compare_bench.cpp')
old=json.loads((R/'evidence/phase32/build_manifest.json').read_text());template=next(c['command'] for c in old['commands'] if c['name']=='candidate');records={}
for arm in ('previous','csr'):
 d=O/arm;cmd=template.copy();cmd[cmd.index('-MF')+1]=str(build/(arm+'.d'));cmd[cmd.index('-o')+1]=str(build/arm);cmd=[str(build/'native_compare_bench.cpp') if x.endswith('/native_compare_bench.cpp') else '-I'+str(d) if x=='-I'+str(R) else x for x in cmd];cmd.append('-I'+str(R))
 result=subprocess.run(cmd,capture_output=True,text=True);(build/(arm+'.log')).write_text(result.stderr);result.check_returncode();deps=shlex.split((build/(arm+'.d')).read_text().replace('\\\n','').split(':',1)[1]);selected={Path(x).name:Path(x) for x in deps if Path(x).name in {p.name for p in d.glob('*.h')}};assert len(selected)==8 and all(x.parent==d for x in selected.values());records[arm]={'command':cmd,'sha256':hashlib.sha256((build/arm).read_bytes()).hexdigest(),'headers':{n:hashlib.sha256(x.read_bytes()).hexdigest() for n,x in selected.items()}}
assert records['previous']['sha256']=='4c74844f13e660d2ce17dc2359a8e5487b56cb9aef2cb867010cf0e25b4a52fe'
(O/'standard_builds.json').write_text(json.dumps(records,indent=2)+'\n')

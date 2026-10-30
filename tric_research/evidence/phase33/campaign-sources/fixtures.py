from pathlib import Path
import gzip,json,random,hashlib,sys
ROOT=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));from benchmark_native_changes import payload
folder=OUT/'fixtures';folder.mkdir(exist_ok=True);receipt=[]
for directory in ('evidence/phase25/fixtures','evidence/phase30/fresh-fixtures','evidence/phase27/large-fixtures'):
 for p in sorted((ROOT/directory).glob('*.json.gz')):
  f=json.loads(gzip.decompress(p.read_bytes()));f['cases']=f['cases'][:1]
  dest=folder/p.name;dest.write_bytes(gzip.compress(json.dumps(f,separators=(',',':')).encode(),mtime=0))
  receipt.append({'file':dest.name,'source':str(p.relative_to(ROOT)),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
for name,n in [('dense_order',1024),('repeated_arcs',1024),('scc_ladder',2048),('wide_layers',2048),('shuffled_sparse',4096),('many_weak_parts',12000)]:
 r=random.Random(2026102801);edges=[]
 if name=='dense_order':edges=[(u,v) for u in range(n) for v in range(u+1,n)]
 if name=='repeated_arcs':edges=[(u,v) for u in range(n-1) for v in range(u+1,min(n,u+17)) for _ in range(4)]
 if name=='scc_ladder':
  edges=[(u,u^1) for u in range(n)]+[(u,v) for u in range(0,n-2,2) for v in (u+2,min(n-1,u+17))]
 if name=='wide_layers':edges=[(u,r.randrange((u//256+1)*256,(u//256+2)*256)) for u in range(n-256) for _ in range(8)]
 if name=='shuffled_sparse':
  perm=list(range(n));r.shuffle(perm);edges=[(perm[u],perm[v]) for u in range(n-1) for v in r.sample(range(u+1,n),min(6,n-u-1))]
 if name=='many_weak_parts':edges=[(start,u) for start in range(0,n,600) for u in range(start+1,start+600)]+[(start+1,start+599) for start in range(0,n,600)]
 queries=[[r.randrange(n),r.randrange(n)] for _ in range(512)]+[[0,0],[0,n-1],[n-1,0]]
 f={'dataset':'phase33_'+name,'graph':{'vertices':n,'arcs':edges},'cases':[{'seed':2026102801,'stratum':'uniform','queries':queries}]}
 f['cases'][0]['native_input_sha256']=hashlib.sha256(payload(f,f['cases'][0])).hexdigest();p=folder/(f['dataset']+'.json.gz');p.write_bytes(gzip.compress(json.dumps(f,separators=(',',':')).encode(),mtime=0));receipt.append({'file':p.name,'source':'generated','sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(OUT/'fixture_manifest.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Frozen',len(receipt),'graphs')

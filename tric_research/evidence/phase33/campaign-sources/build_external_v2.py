from pathlib import Path
import subprocess,hashlib,json
O=Path(__file__).resolve().parent;U=O/'upstream-pyreach';records={}
sources=[U/'src/cpp'/(n+'.cpp') for n in ('csr_graph','scc','levels','minpost','feline','grail','preach','ferrari','tflabel','tol','two_hop')]
for name,flags in [('v2',['-O3','-DNDEBUG']),('ubsan-v2',['-O1','-fsanitize=undefined'])]:
 cmd=['g++','-std=c++17',*flags,'-I'+str(O/'csr_v2'),'-I'+str(U/'src/cpp/include'),str(O/'external.cpp'),*map(str,sources),'-o',str(O/('external-'+name))]
 with (O/('external-'+name+'.compile.log')).open('wb') as log:p=subprocess.run(cmd,stdout=log,stderr=log)
 p.check_returncode()
 p=subprocess.run([str(O/('external-'+name)),'--self-test'],capture_output=True);(O/('external-'+name+'.check.log')).write_bytes(p.stdout+p.stderr);p.check_returncode();assert not p.stderr
 records[name]={'command':cmd,'binary_sha256':hashlib.sha256((O/('external-'+name)).read_bytes()).hexdigest(),'checks':json.loads(p.stdout)}
records['upstream_commit']=subprocess.check_output(['git','-C',str(U),'rev-parse','HEAD'],text=True).strip()
records['source_sha256']=hashlib.sha256((O/'external.cpp').read_bytes()).hexdigest()
(O/'external_v2_builds.json').write_text(json.dumps(records,indent=2)+'\n')

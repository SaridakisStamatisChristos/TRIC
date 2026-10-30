from pathlib import Path
import subprocess,hashlib,json
O=Path(__file__).resolve().parent;U=O/'upstream-pyreach';assert subprocess.check_output(['git','-C',str(U),'rev-parse','HEAD'],text=True).strip()=='0c84ca38de2d384c561690f4782f93e19fc76816'
subprocess.run(['git','-C',str(U),'diff','--exit-code','HEAD'],check=True)
names=('csr_graph','scc','levels','minpost','feline','grail','preach','ferrari','tflabel','tol','two_hop')
sources=[U/'src/cpp'/(n+'.cpp') for n in names];records={}
for arm in ('previous','csr'):
 cmd=['g++','-std=c++17','-O3','-DNDEBUG','-I'+str(O/arm),'-I'+str(U/'src/cpp/include'),str(O/'external.cpp'),*map(str,sources),'-o',str(O/('external-'+arm))]
 p=subprocess.run(cmd,capture_output=True,text=True);(O/('external-'+arm+'.compile.log')).write_text(p.stderr);p.check_returncode()
 p=subprocess.run([str(O/('external-'+arm)),'--self-test'],capture_output=True,text=True);p.check_returncode();assert not p.stderr
 records[arm]={'command':cmd,'binary_sha256':hashlib.sha256((O/('external-'+arm)).read_bytes()).hexdigest(),'checks':json.loads(p.stdout)}
cmd=['g++','-std=c++17','-O1','-g','-fsanitize=undefined','-I'+str(O/'csr'),'-I'+str(U/'src/cpp/include'),str(O/'external.cpp'),*map(str,sources),'-o',str(O/'external-sanitizer')]
p=subprocess.run(cmd,capture_output=True,text=True);(O/'external-sanitizer.compile.log').write_text(p.stderr);p.check_returncode();p=subprocess.run([str(O/'external-sanitizer'),'--self-test'],capture_output=True,text=True);(O/'external-sanitizer.log').write_text(p.stdout+p.stderr);p.check_returncode();assert not p.stderr
records['sanitizer']={'command':cmd,'checks':json.loads(p.stdout)}
records['upstream_sha']='0c84ca38de2d384c561690f4782f93e19fc76816';records['source_sha256']=hashlib.sha256((O/'external.cpp').read_bytes()).hexdigest();records['sources']={str(p.relative_to(U)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+list((U/'src/cpp/include/reachability').glob('*.hpp'))}
(O/'external_builds.json').write_text(json.dumps(records,indent=2)+'\n');print('Built and oracle-tested external adapters')

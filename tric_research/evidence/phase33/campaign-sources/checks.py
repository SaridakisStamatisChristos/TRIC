from pathlib import Path
import subprocess,json,hashlib
R=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');O=Path(__file__).resolve().parent
records={}
for arm in ('previous','csr','closure','buffers'):
 d=O/arm;source=d/'native_runtime_check.cpp';source.write_bytes((R/source.name).read_bytes())
 cmd=['g++','-std=c++17','-O2','-fsanitize=undefined',str(source),'-o',str(d/'check')]
 p=subprocess.run(cmd,capture_output=True,text=True);p.check_returncode()
 p=subprocess.run([str(d/'check'),'--self-test'],capture_output=True,text=True);p.check_returncode();assert p.stderr==''
 records[arm]={'command':cmd,'result':json.loads(p.stdout),'binary_sha256':hashlib.sha256((d/'check').read_bytes()).hexdigest()}
 print('Passed',arm,flush=True)
(O/'checks.json').write_text(json.dumps(records,indent=2)+'\n')

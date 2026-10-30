from pathlib import Path
import sys,argparse,json
R=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');O=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from benchmark_native_changes import run,digest
p=json.loads((O/'qualification_v2_protocol.json').read_text());builds=json.loads((O/'v2_builds.json').read_text());resources=json.loads((O/'resources.json').read_text());assert len(resources['records'])==52
assert digest((O/'csr_v2/scc_decomposition.h').read_bytes())==p['candidate_header_sha256']
for name,h in p['fixtures'].items():assert digest((O/'qualification-fixtures'/name).read_bytes())==h
for kind in ('warm','cold'):
 exe=O/'csr_v2'/(kind+'-bench');assert digest(exe.read_bytes())==builds[kind]['sha256']
 baseline=O/'previous/bench' if kind=='warm' else O/'standard-build/previous'
 args=argparse.Namespace(fixtures=str(O/'qualification-fixtures'),output=str(O/('qualification-'+kind)),cpu=p['cpu'],arm=[('previous',str(baseline),'auto'),('csr_v2',str(exe),'auto'),('identical',str(baseline),'auto')],trials=p['trials'],horizons=[1],cap=p['cap'],datasets=None,seeds=None,timeout=300)
 run(args);print('Completed',kind,'qualification',flush=True)

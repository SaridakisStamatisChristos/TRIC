from pathlib import Path
import sys,argparse,json
O=Path(__file__).resolve().parent;R=O.parent/'TRIC/tric_research';sys.path.insert(0,str(R))
from benchmark_native_changes import run,digest
p=json.loads((O/'replication_protocol.json').read_text());builds=json.loads((O/'v2_builds.json').read_text())
for name,h in p['fixtures'].items():assert digest((O/'qualification-fixtures'/name).read_bytes())==h
for kind in ('warm','cold'):
 exe=O/'csr_v2'/(kind+'-bench');assert digest(exe.read_bytes())==builds[kind]['sha256']
 baseline=O/'previous/bench' if kind=='warm' else O/'standard-build/previous'
 run(argparse.Namespace(fixtures=str(O/'qualification-fixtures'),output=str(O/('replication-'+kind)),cpu=p['cpu'],arm=[('previous',str(baseline),'auto'),('csr_v2',str(exe),'auto'),('identical',str(baseline),'auto')],trials=p['trials'],horizons=[1],cap=p['cap'],datasets=None,seeds=None,timeout=300))
 print('Completed',kind,'replication',flush=True)

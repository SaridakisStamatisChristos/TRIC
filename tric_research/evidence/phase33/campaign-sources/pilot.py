from pathlib import Path
import sys,argparse,json
R=Path('/workspace/scratch/750cc954fdb8/TRIC/tric_research');O=Path(__file__).resolve().parent;sys.path.insert(0,str(R))
from benchmark_native_changes import run,digest
p=json.loads((O/'protocol.json').read_text());checks=json.loads((O/'checks.json').read_text())
assert set(checks)=={'previous','csr','closure','buffers'}
for arm,files in p['headers'].items():
 for name,expected in files.items():assert digest((O/arm/name).read_bytes())==expected
assert digest((O/'native_compare_bench.cpp').read_bytes())==p['harness_sha256']
run(argparse.Namespace(fixtures=str(O/'fixtures'),output=str(O/'pilot'),cpu=p['cpu'],
 arm=[(a,str(O/('previous' if a=='identical' else a)/'bench'),'auto') for a in p['arms']],
 trials=p['trials'],horizons=[1],cap=p['cap'],datasets=None,seeds=None,timeout=300))

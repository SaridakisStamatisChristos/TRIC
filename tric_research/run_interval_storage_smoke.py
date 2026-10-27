"""Check the full comparator-enabled binaries; single executions are not timing evidence."""
import argparse
import gzip
import json
import subprocess
from pathlib import Path

from benchmark_native_changes import payload
from verify_interval_storage import ROOT, FIXTURES, sha


def run(build, output):
    build,output=Path(build).resolve(),Path(output).resolve()
    if output.exists():
        raise ValueError('output already exists')
    manifest=json.loads((build/'build_manifest.json').read_text())
    binaries={a['name']:a['executable_sha256'] for a in manifest['commands']}
    for arm,digest in binaries.items():
        assert sha((build/arm).read_bytes())==digest
    records=[]
    for folder in FIXTURES:
        for path in sorted((ROOT/folder).glob('*.json.gz')):
            f=json.loads(gzip.decompress(path.read_bytes()));case=f['cases'][0]
            raw=payload(f,case)
            record=dict(fixture=str(path.relative_to(ROOT)),fixture_sha256=sha(path.read_bytes()),
                        seed=case['seed'],stratum=case['stratum'],input_sha256=sha(raw),rows={})
            for arm in ('previous','candidate'):
                p=subprocess.run([str(build/arm),'auto','2097152','1'],input=raw,
                                 capture_output=True,check=True,timeout=300)
                assert not p.stderr,p.stderr.decode()
                row=json.loads(p.stdout.splitlines()[-1])
                assert row['available'] and row['oracle_verified_pairs']==len(case['queries'])
                assert row['actual_calls']==len(case['queries'])
                record['rows'][arm]=row
            a,b=record['rows']['previous'],record['rows']['candidate']
            for key in ('checksum','uses_direct_closure','uses_forest_index'):
                assert a[key]==b[key]
            assert a['table_bytes']-b['table_bytes']==a['retained_capacity_bytes']-b['retained_capacity_bytes']>=0
            records.append(record)
            print('Full-build smoke passed '+record['fixture'],flush=True)
    for arm,digest in binaries.items():
        assert sha((build/arm).read_bytes())==digest
    output.write_text(json.dumps(dict(binary_hashes=binaries,records=records,
        scope='One original query case per fixture, one execution per arm. No timing qualification or external comparator execution.'),indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run(args.build,args.output)

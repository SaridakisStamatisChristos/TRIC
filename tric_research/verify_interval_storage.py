"""Rebuild independent allocation probes and validate Phase XXXII memory evidence."""
import argparse
import gzip
import functools
import hashlib
import json
import random
import shlex
import shutil
import subprocess
from pathlib import Path

from test_native_runtime import serialize

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence/phase32'
BASELINE = EVIDENCE / 'baseline-sources/tric_research'
FIXTURES = ('evidence/phase25/fixtures', 'evidence/phase30/fresh-fixtures',
            'evidence/phase27/large-fixtures', 'evidence/phase27/fresh-fixtures')
HEADER = 'partitioned_reachability.h'
CHANGE = '''    // Every interval offset/count is now copied into vertex_labels_. Queries
    // use those labels directly; the construction directory has no remaining
    // readers. Release its allocation, not just its size. Keep admission and
    // rollback accounting above unchanged: reclaimed bytes are not re-spent.
    std::vector<IntervalRow>().swap(interval_rows_);
'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_check():
    protocol = json.loads((EVIDENCE/'protocol.json').read_text())
    before = (BASELINE/HEADER).read_text()
    after = (ROOT/HEADER).read_text()
    assert after.count(CHANGE) == 1 and after.replace(CHANGE, '') == before
    assert sha(after.encode()) == protocol['candidate_header_sha256']
    for path in BASELINE.glob('*.h'):
        if path.name != HEADER:
            assert path.read_bytes() == (ROOT/path.name).read_bytes(), path.name
    return protocol


def purpose_cases():
    star = [list(range(1, 1024))] + [[] for _ in range(1023)]
    r = random.Random(20261023)
    fragmented = [sorted(r.sample(range(512, 1024), 32)) for _ in range(512)] + [[] for _ in range(512)]
    mixed = []
    for graph in (star, fragmented, star):
        offset = len(mixed)
        mixed.extend([[v+offset for v in row] for row in graph])
    aliases = [[] for _ in range(2048)]
    for u, row in enumerate(star):
        aliases[2*u] = [2*u+1] + [2*v for v in row]
        aliases[2*u+1] = [2*u]
    # Equal topology under an arbitrary original-vertex permutation.
    perm = list(range(len(aliases))); r.shuffle(perm)
    relabelled = [[] for _ in aliases]
    for u, row in enumerate(aliases):
        relabelled[perm[u]] = [perm[v] for v in row]
    for name, graph, cap, scratch, expected in (
        ('empty', [], 0, 0, 0),
        ('singleton', [[]], 0, 0, 0),
        ('directory_exact_budget', star, 16384, 16, 8192),
        ('directory_one_byte_short', star, 16383, 16, 0),
        ('no_union_scratch', star, 65536, 0, 0),
        ('dense_bits', star, 1048576, 67108864, 0),
        ('compressed_words', fragmented, 98304, 67108864, 0),
        ('failed_interval_rollback', mixed, 65536, 67108864, 16384),
        ('aliases', relabelled, 16384, 16, 8192),
        ('chain', [[u+1] if u<1023 else [] for u in range(1024)], 4096, 0, 0),
        ('search', [[1,2],[3],[3],[]], 0, 0, 0),
    ):
        n = len(graph)
        queries = [(a,b) for a in range(n) for b in range(n)] if n <= 4 else [
            (a,b) for a in range(0,n,17) for b in range(0,n,31)]
        if n:
            queries += [(0,n-1),(n-1,0),(n-1,n-1)]
        yield dict(name=name, graph=graph, queries=queries, cap=cap, scratch=scratch,
                   mode='partitioned', expected_saved=expected)
    two_stars = star + [[v+1024 for v in row] for row in star]
    yield dict(name='no_respended_budget', graph=two_stars,
               queries=[(0,1023),(1024,2047),(0,2047),(2047,1024)],
               cap=16384, scratch=16, mode='partitioned', expected_saved=8192)
    for name, graph, cap, scratch in (
        ('auto_direct', [[1,2],[3],[3],[]], 4096, 67108864),
        ('auto_forest', star, 0, 67108864),
        ('auto_intervals', star, 16384, 16),
    ):
        yield dict(name=name, graph=graph, queries=[(0,len(graph)-1),(1,0),(1,1)],
                   cap=cap, scratch=scratch, mode='auto', expected_saved=8192 if name=='auto_intervals' else 0)


def cases(full):
    for spec in purpose_cases():
        yield spec, serialize(spec['graph'],spec['queries']).encode(), None
    if full:
        for folder in FIXTURES:
            for path in sorted((ROOT/folder).glob('*.json.gz')):
                f = json.loads(gzip.decompress(path.read_bytes()))
                graph = [[] for _ in range(f['graph']['vertices'])]
                for u,v in f['graph']['arcs']:
                    graph[u].append(v)
                # Resource measurement is graph-based. Cover every distinct
                # pair from every case, sorting to reuse BFS by source only.
                queries = sorted({tuple(q) for c in f['cases'] for q in c['queries']})
                spec = dict(name=str(path.relative_to(ROOT)), mode='auto',
                            cap=2097152, scratch=67108864, expected_saved=None)
                yield spec, serialize(graph,queries).encode(), sha(path.read_bytes())


def validate_pair(record):
    a,b = record['previous'],record['candidate']
    fields = ('oracle_checks','checksum','components','indexed','partitions','chains',
              'bits','compressed','intervals','merged','skipped','direct','forest')
    for field in fields:
        assert a[field] == b[field], (record['name'],field)
    assert a['oracle_checks'] == record['queries']
    saved = a['table_bytes'] - b['table_bytes']
    assert isinstance(saved,int) and saved >= 0 and saved % 8 == 0
    assert saved == a['retained_bytes'] - b['retained_bytes']
    assert saved == a['live_heap_bytes'] - b['live_heap_bytes']
    assert a['live_blocks'] - b['live_blocks'] == (1 if saved else 0)
    assert b['construction_peak_heap_bytes'] <= a['construction_peak_heap_bytes']
    if record['expected_saved'] is not None:
        assert saved == record['expected_saved'], record['name']
    for row in (a,b):
        assert all(type(v) is int and v>=0 for v in row.values())
        assert row['retained_bytes'] >= row['live_heap_bytes'] >= row['table_bytes']
        assert row['table_bytes'] <= record['cap']
    if record['mode']=='partitioned' and not a['intervals']:
        assert saved == 0
    if a['direct'] or a['forest']:
        assert saved == 0
    return saved


def build_probes(output):
    source = output/'interval_storage_check.cpp'
    shutil.copyfile(ROOT/source.name,source)
    builds = {}
    for arm,headers in (('previous',BASELINE),('candidate',ROOT)):
        dependency = output/(arm+'.d')
        cmd = ['g++','-std=c++17','-O2','-Wall','-Wextra','-Wpedantic','-fsanitize=undefined',
               '-MMD','-MF',str(dependency),'-I'+str(headers),str(source),'-o',str(output/arm)]
        result = subprocess.run(cmd,capture_output=True,text=True,check=True)
        assert not result.stderr, result.stderr
        paths = shlex.split(dependency.read_text().replace('\\\n','').split(':',1)[1])
        selected = {Path(p).name:Path(p).resolve() for p in paths if Path(p).suffix=='.h'}
        assert len(selected)==5 and all(p.parent==headers for p in selected.values())
        builds[arm] = dict(command=cmd, binary_sha256=sha((output/arm).read_bytes()),
                           sources={name:sha(p.read_bytes()) for name,p in selected.items()})
    return builds


def execute(output, full):
    source_check()
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    assert not any(output.iterdir()), 'output must be empty'
    builds = build_probes(output)
    records = []
    for spec,raw,fixture_hash in cases(full):
        record = {k:v for k,v in spec.items() if k not in ('graph','queries')}
        record.update(input_sha256=sha(raw), fixture_sha256=fixture_hash,
                      queries=int(raw.splitlines()[0].split()[2]))
        for arm in ('previous','candidate'):
            p = subprocess.run([str(output/arm),spec['mode'],str(spec['cap']),str(spec['scratch'])],
                               input=raw,capture_output=True,check=True,timeout=300)
            assert not p.stderr, p.stderr.decode()
            record[arm] = json.loads(p.stdout)
        validate_pair(record)
        records.append(record)
        print('Verified '+spec['name'],flush=True)
    data = dict(schema=1, full=full, protocol_sha256=sha((EVIDENCE/'protocol.json').read_bytes()),
                probe_sha256=sha((ROOT/'interval_storage_check.cpp').read_bytes()),
                compiler=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
                builds=builds, records=records)
    (output/'results.json').write_text(json.dumps(data,indent=2)+'\n')
    return data


@functools.lru_cache(maxsize=1)
def expectations():
    expected = {}
    for spec,raw,fixture_hash in cases(True):
        expected[spec['name']] = spec,sha(raw),fixture_hash,int(raw.splitlines()[0].split()[2])
    return expected


def verify(data):
    source_check()
    assert data['schema']==1 and data['full'] is True
    assert data['protocol_sha256']==sha((EVIDENCE/'protocol.json').read_bytes())
    assert data['probe_sha256']==sha((ROOT/'interval_storage_check.cpp').read_bytes())
    expected = expectations()
    assert len(data['records'])==len(expected)
    seen = set(); savings = {}; checks=0
    for record in data['records']:
        assert record['name'] not in seen;seen.add(record['name'])
        spec,digest,fixture_hash,queries=expected[record['name']]
        for key in ('cap','scratch','mode','expected_saved'):
            assert record[key]==spec[key]
        assert record['input_sha256']==digest and record['fixture_sha256']==fixture_hash
        assert record['queries']==queries
        savings[record['name']]=validate_pair(record)
        checks+=2*queries
    assert seen==set(expected)
    for arm,headers in (('previous',BASELINE),('candidate',ROOT)):
        build=data['builds'][arm]
        assert set(build['sources'])=={'tric_reachability.h','partitioned_reachability.h',
                                      'closure_index.h','scc_decomposition.h','forest_reachability.h'}
        for name,digest in build['sources'].items():
            assert sha((headers/name).read_bytes())==digest
    return dict(status='ACCEPT_MEMORY_RELEASE',cases=len(seen),oracle_checks=checks,
                improved_cases=sum(v>0 for v in savings.values()),saved_bytes=savings,
                latency_claim='NOT_ESTABLISHED',global_sota='NOT_ESTABLISHED')


def verify_full_build(data):
    build=json.loads((EVIDENCE/'build_manifest.json').read_text())
    prior=json.loads((ROOT/'evidence/phase30/build_manifest.json').read_text())
    for key in ('compiler','source_sha256','oreach_sha','bfl_commit','bfl_main_sha256',
                'pruned_labeling_commit','pruned_labeling_sources'):
        assert build[key]==prior[key],key
    hashes={}
    for arm in build['commands']:
        headers=BASELINE if arm['name']=='previous' else ROOT
        hashes[arm['name']]=arm['executable_sha256']
        assert len(arm['selected_runtime_dependencies'])==8
        for name,digest in arm['runtime_source_hashes'].items():
            assert sha((headers/name).read_bytes())==digest
        for name,digest in arm['selected_runtime_dependencies'].items():
            assert sha((headers/Path(name).name).read_bytes())==digest
    assert hashes['previous']==next(a['executable_sha256'] for a in prior['commands'] if a['name']=='candidate')
    smoke=json.loads((EVIDENCE/'full-build-smoke.json').read_text())
    assert smoke['binary_hashes']==hashes
    from benchmark_native_changes import payload
    paths={str(p.relative_to(ROOT)):p for folder in FIXTURES for p in (ROOT/folder).glob('*.json.gz')}
    assert len(smoke['records'])==len(paths)
    observed={};saved={r['name']:validate_pair(r) for r in data['records']}
    checks=0
    for record in smoke['records']:
        name=record['fixture'];assert name not in observed;observed[name]=True
        path=paths[name];f=json.loads(gzip.decompress(path.read_bytes()));case=f['cases'][0]
        assert record['fixture_sha256']==sha(path.read_bytes())
        assert record['input_sha256']==sha(payload(f,case))
        assert (record['seed'],record['stratum'])==(case['seed'],case['stratum'])
        assert set(record['rows'])=={'previous','candidate'}
        a,b=record['rows']['previous'],record['rows']['candidate']
        for key in ('checksum','uses_direct_closure','uses_forest_index'):
            assert a[key]==b[key]
        assert a['table_bytes']-b['table_bytes']==saved[name]
        assert a['retained_capacity_bytes']-b['retained_capacity_bytes']==saved[name]
        for row in (a,b):
            assert row['available'] is True and row['mode']=='auto' and row['repeats']==1
            assert row['queries']==row['actual_calls']==row['oracle_verified_pairs']==len(case['queries'])
            assert row['table_bytes']<=2097152
            checks+=row['oracle_verified_pairs']
    assert set(observed)==set(paths)
    return dict(cases=len(paths),processes=2*len(paths),oracle_checks=checks,
                baseline_binary_reproduced=True,latency_qualification=False)


def verify_seal():
    manifest=json.loads((EVIDENCE/'sealed_manifest.json').read_text())
    for name,digest in manifest['files'].items():
        assert sha((ROOT.parent/name).read_bytes())==digest,name


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',help='Empty output folder for fresh probes')
    parser.add_argument('--quick',action='store_true',help='Purpose-built cases only')
    args=parser.parse_args()
    if args.run:
        execute(args.run,not args.quick)
    else:
        verify_seal()
        data=json.loads((EVIDENCE/'results.json').read_text())
        result=verify(data);result['full_build']=verify_full_build(data)
        assert result==json.loads((EVIDENCE/'metrics.json').read_text())
        print(json.dumps(result,indent=2))

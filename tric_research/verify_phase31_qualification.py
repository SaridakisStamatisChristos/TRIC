"""Validate complete full-build qualification with frozen calibration and null controls."""
import argparse
import base64
import gzip
import json
import math
import statistics

from benchmark_native_changes import payload
from verify_phase31_evidence import EVIDENCE, ROOT, load_archive, sha

COHORTS = [
    ('native','evidence/phase25/fixtures','evidence/phase30/native/qualification-final'),
    ('fresh','evidence/phase30/fresh-fixtures','evidence/phase30/fresh/qualification-final'),
    ('forest','evidence/phase27/large-fixtures','evidence/phase30/forest-warm-replication/qualification-final'),
    ('cold','evidence/phase27/fresh-fixtures','evidence/phase30/forest-replication/qualification-final')]


def verify_qualification(data, original):
    protocol=data['protocol']; build=data['build']
    assert protocol['baseline_commit']==original['baseline_commit']
    assert protocol['arms']==['previous','dispatch','identical'] and protocol['cpu']==1
    assert protocol['gates']=={'duration_warm_ns':50_000_000,'null_ratio_band':[.9,1/.9],
        'median_warm_query_min':1.03,'all_query_min':.9,'median_warm_lifecycle_min':.97}
    expected_source=original['code']['native_compare_bench.cpp'].replace('repeats>1000000)','repeats>1000000000ULL)')
    assert build['source']==expected_source and build['source_sha256']==sha(expected_source.encode())
    assert build['prior_build_manifest_sha256']==sha((ROOT/'evidence/phase30/build_manifest.json').read_bytes())
    prior_build=json.loads((ROOT/'evidence/phase30/build_manifest.json').read_text())
    prior_binary=next(r['executable_sha256'] for r in prior_build['commands'] if r['name']=='candidate')
    assert build['baseline_reproduction']['expected_sha256']==prior_binary
    assert build['baseline_reproduction']['actual_sha256']==prior_binary
    assert {b['name'] for b in build['builds']}=={'previous','dispatch'} and len(build['builds'])==2
    binaries={}
    for record in build['builds']:
        assert len(record['selected_runtime_dependencies'])==8
        for name,digest in record['selected_runtime_dependencies'].items():
            assert sha(original['headers'][record['name']][name].encode())==digest
        assert '-DTRIC_WITH_BFL' in record['command'] and '-DTRIC_WITH_OREACH' in record['command']
        assert '-DTRIC_WITH_PRUNED_LABELING' in record['command']
        assert '-O3' in record['command'] and '-std=c++17' in record['command']
        binaries[record['name']]=record['binary_sha256']
    expected=[]
    for tag,fixtures,calibration in COHORTS:
        for path in sorted((ROOT/calibration).glob('*.json.gz')):
            for cell in json.loads(gzip.decompress(path.read_bytes())):
                if tag=='fresh' and cell['repeats']==1:continue
                per_repeat=statistics.median(r['query_thread_cpu_ns']/cell['repeats'] for r in cell['rows']['candidate'])
                expected.append({'tag':tag,'dataset':cell['dataset'],'seed':cell['seed'],'stratum':cell['stratum'],
                    'input_sha256':cell['input_sha256'],'horizon':1 if tag=='cold' else max(1000,math.ceil(200_000_000/per_repeat)),
                    'fixtures':fixtures,'trials':24 if tag=='cold' else 6,'calibration_file':str(path.relative_to(ROOT)),
                    'calibration_arm':'candidate','calibration_previous_cpu_ns_per_repeat':per_repeat})
    assert protocol['specs']==expected and len(expected)==182
    assert set(data['runs'])=={str(i) for i in range(182)}
    fixtures={}; results=[]; durations=[]; processes=pairs=calls=0
    for i,spec in enumerate(expected):
        key=(spec['fixtures'],spec['dataset'])
        if key not in fixtures:
            fixtures[key]=json.loads(gzip.decompress((ROOT/key[0]/(key[1]+'.json.gz')).read_bytes()))
        fixture=dict(fixtures[key])
        case=next(c for c in fixture['cases'] if (c['seed'],c['stratum'])==(spec['seed'],spec['stratum']))
        fixture['cases']=[case]
        assert sha(payload(fixture,case))==spec['input_sha256']
        run=data['runs'][str(i)]; manifest=run['manifest']
        assert manifest['complete'] is True and manifest['trials']==spec['trials']
        assert manifest['horizons']==[spec['horizon']] and manifest['cap_bytes']==2097152
        assert manifest['environment']['cpu_affinity']==[1]
        assert [a['name'] for a in manifest['arms']]==protocol['arms']
        for arm in manifest['arms']:
            assert arm['executable_sha256']==binaries['dispatch' if arm['name']=='dispatch' else 'previous']
        assert len(manifest['files'])==1 and len(run['raw_gzip_base64'])==1
        entry=manifest['files'][0]
        assert entry['file']==spec['dataset']+'.json.gz' and entry['cells']==1
        # Exact native input is checked against the original fixture above.
        # Temporary gzip container bytes vary with Python/zlib versions.
        assert len(entry['fixture_sha256'])==64
        int(entry['fixture_sha256'],16)
        raw=base64.b64decode(run['raw_gzip_base64'][entry['file']],validate=True)
        assert sha(raw)==entry['sha256']
        cells=json.loads(gzip.decompress(raw));assert len(cells)==1
        cell=cells[0]
        for field in ('dataset','seed','stratum','input_sha256'):assert cell[field]==spec[field]
        assert cell['repeats']==spec['horizon'] and set(cell['rows'])==set(protocol['arms'])
        checksums=set()
        for arm,rows in cell['rows'].items():
            assert [r['trial'] for r in rows]==list(range(spec['trials']))
            for row in rows:
                q=len(case['queries'])
                assert row['available'] and row['queries']==row['oracle_verified_pairs']==q
                assert row['repeats']==spec['horizon'] and row['actual_calls']==q*spec['horizon']
                assert row['mode']=='auto' and row['table_bytes']<=2097152
                for field in ('parse_ns','build_ns','query_ns','query_thread_cpu_ns','lifecycle_ns','timed_peak_rss_kib'):
                    assert math.isfinite(row[field]) and row[field]>0
                assert abs(row['lifecycle_ns']-sum(row[f] for f in ('parse_ns','build_ns','query_ns')))<=2
                checksums.add(row['checksum'])
                if spec['tag']!='cold':durations.append(row['query_thread_cpu_ns'])
                processes+=1;pairs+=q;calls+=row['actual_calls']
        assert len(checksums)==1
        result={k:spec[k] for k in ('tag','dataset','seed','stratum','horizon')}
        for arm in ('dispatch','identical'):
            a=cell['rows']['previous'];b=cell['rows'][arm]
            for x,y in zip(a,b):
                for field in ('table_bytes','retained_capacity_bytes','uses_direct_closure','uses_forest_index'):
                    assert x[field]==y[field]
            result[arm]={field:statistics.median(x[field]/y[field] for x,y in zip(a,b))
                for field in ('query_ns','query_thread_cpu_ns','lifecycle_ns')}
        results.append(result)
    warm=[r for r in results if r['tag']!='cold']
    median=statistics.median(r['dispatch']['query_ns'] for r in warm)
    minimum=min(r['dispatch']['query_ns'] for r in results)
    lifecycle=statistics.median(r['dispatch']['lifecycle_ns'] for r in warm)
    null=[r for r in results if not .9<=r['identical']['query_ns']<=1/.9]
    gates={'duration':min(durations)>=50_000_000,'null_control':not null,'median':median>=1.03,
        'floor':minimum>=.9,'lifecycle':lifecycle>=.97}
    groups={}
    for tag,_,_ in COHORTS:
        group=[r for r in results if r['tag']==tag]
        groups[tag]={'cells':len(group),'median_query':statistics.median(r['dispatch']['query_ns'] for r in group),
            'min_query':min(r['dispatch']['query_ns'] for r in group),'wins':sum(r['dispatch']['query_ns']>1 for r in group)}
    return {'status':'QUALIFIED_INTERNAL_ONLY' if all(gates.values()) else 'PRESERVE_CURRENT',
        'gates':gates,'groups':groups,'median_warm_query':median,'minimum_query':minimum,
        'median_warm_lifecycle':lifecycle,'minimum_warm_query_cpu_ns':min(durations),
        'null_failures':null,'processes':processes,'bfs_pair_executions':pairs,'repeated_query_calls':calls,'cells':results}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write-metrics',action='store_true');args=p.parse_args()
    data=json.loads(gzip.decompress((EVIDENCE/'qualification.json.gz').read_bytes()))
    result=verify_qualification(data,load_archive())
    if args.write_metrics:(EVIDENCE/'qualification_metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    else:assert result==json.loads((EVIDENCE/'qualification_metrics.json').read_text())
    print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2))

"""Verify the frozen longer-duration diagnostic; never promote a candidate here."""
import argparse
import base64
import gzip
import json
import math
import statistics
from pathlib import Path

from benchmark_native_changes import payload
from verify_phase31_evidence import EVIDENCE, ROOT, load_archive, sha


def verify_stability(data, original):
    protocol = data['protocol']
    assert protocol['baseline_commit'] == original['baseline_commit']
    assert protocol['arms'] == ['previous', 'dispatch', 'identical']
    assert protocol['trials'] == 6 and protocol['cpu'] == 1
    assert protocol['candidate_binary'] == original['builds']['dispatch']['binary_sha256']
    assert protocol['target_previous_query_cpu_ns'] == 200_000_000
    assert protocol['gates'] == {'minimum_observed_query_cpu_ns': 50_000_000,
        'null_ratio_band': [.9, 1/.9], 'candidate_median_query_min': 1.03,
        'candidate_min_query': .9, 'candidate_median_lifecycle_min': .97}
    expected = {}
    for tag in ('pilot','pilot-cross','pilot-forest','pilot-cold'):
        run = original['runs'][tag]
        for encoded in run['raw_gzip_base64'].values():
            for cell in json.loads(gzip.decompress(base64.b64decode(encoded))):
                key = (cell['dataset'], cell['seed'], cell['stratum'])
                per_repeat = statistics.median(r['query_thread_cpu_ns']/cell['repeats'] for r in cell['rows']['previous'])
                wanted = max(cell['repeats'], math.ceil(200_000_000/per_repeat))
                expected[key] = (wanted, per_repeat, original['specs'][tag]['fixtures'], cell['input_sha256'])
    assert len(expected) == 46 and len(protocol['specs']) == len(data['runs']) == 46
    assert set(data['runs']) == {str(i) for i in range(46)}
    assert data['bound_rejection']['failure']['stderr'] == 'cap/repeat bounds\n'
    assert data['bound_rejection']['manifest']['files'] == []
    assert not data['bound_rejection']['manifest'].get('complete', False)
    seen = set(); results = []; processes = pairs = calls = 0; durations = []
    fixture_cache = {}
    for i, spec in enumerate(protocol['specs']):
        key = (spec['dataset'], spec['seed'], spec['stratum'])
        assert key in expected and key not in seen; seen.add(key)
        wanted, per_repeat, fixtures, input_hash = expected[key]
        assert spec['requested_horizon'] == wanted and spec['horizon'] == min(wanted, 1_000_000)
        assert spec['calibration_previous_cpu_ns_per_repeat'] == per_repeat
        assert spec['fixtures'] == fixtures and spec['input_sha256'] == input_hash
        assert data['original_protocol']['specs'][i]['horizon'] == wanted
        fixture_key = (fixtures, key[0])
        if fixture_key not in fixture_cache:
            fixture_cache[fixture_key] = json.loads(gzip.decompress((ROOT/fixtures/(key[0]+'.json.gz')).read_bytes()))
        fixture = dict(fixture_cache[fixture_key])
        case = next(c for c in fixture['cases'] if (c['seed'],c['stratum']) == key[1:])
        fixture['cases'] = [case]
        assert sha(payload(fixture,case)) == input_hash
        run = data['runs'][str(i)]; manifest = run['manifest']
        assert manifest['complete'] is True and manifest['trials'] == 6
        assert manifest['horizons'] == [spec['horizon']] and manifest['cap_bytes'] == 2097152
        assert manifest['environment']['cpu_affinity'] == [1]
        assert [a['name'] for a in manifest['arms']] == protocol['arms']
        for arm in manifest['arms']:
            build_name = 'dispatch' if arm['name'] == 'dispatch' else 'previous'
            assert arm['executable_sha256'] == original['builds'][build_name]['binary_sha256']
        assert len(manifest['files']) == 1 and len(run['raw_gzip_base64']) == 1
        entry = manifest['files'][0]
        assert entry['file'] == key[0]+'.json.gz' and entry['cells'] == 1
        # The temporary one-case gzip is not retained. Validate its native
        # input bytes above; do not recompress it across Python/zlib versions
        # and mistake gzip container differences for changed graph inputs.
        assert len(entry['fixture_sha256']) == 64
        int(entry['fixture_sha256'], 16)
        raw = base64.b64decode(run['raw_gzip_base64'][entry['file']],validate=True)
        assert sha(raw) == entry['sha256']
        cells = json.loads(gzip.decompress(raw)); assert len(cells) == 1
        cell = cells[0]
        assert (cell['dataset'],cell['seed'],cell['stratum']) == key
        assert cell['repeats'] == spec['horizon'] and cell['input_sha256'] == input_hash
        assert set(cell['rows']) == set(protocol['arms'])
        checksums = set()
        for arm, rows in cell['rows'].items():
            assert [r['trial'] for r in rows] == list(range(6))
            for row in rows:
                q = len(case['queries'])
                assert row['available'] and row['queries'] == row['oracle_verified_pairs'] == q
                assert row['repeats'] == spec['horizon'] and row['actual_calls'] == q*spec['horizon']
                assert row['mode'] == 'auto' and row['table_bytes'] <= 2097152
                for field in ('parse_ns','build_ns','query_ns','query_thread_cpu_ns','lifecycle_ns','timed_peak_rss_kib'):
                    assert math.isfinite(row[field]) and row[field] > 0
                assert abs(row['lifecycle_ns']-sum(row[f] for f in ('parse_ns','build_ns','query_ns'))) <= 2
                checksums.add(row['checksum']); durations.append(row['query_thread_cpu_ns'])
                processes += 1; pairs += q; calls += row['actual_calls']
        assert len(checksums) == 1
        result = {'dataset':key[0], 'seed':key[1], 'stratum':key[2], 'horizon':spec['horizon']}
        for arm in ('dispatch','identical'):
            a = cell['rows']['previous']; b = cell['rows'][arm]
            for x,y in zip(a,b):
                for field in ('table_bytes','retained_capacity_bytes','uses_direct_closure','uses_forest_index'):
                    assert x[field] == y[field]
            result[arm] = {field:statistics.median(x[field]/y[field] for x,y in zip(a,b))
                for field in ('query_ns','query_thread_cpu_ns','lifecycle_ns')}
        results.append(result)
    assert seen == set(expected)
    candidate_median = statistics.median(r['dispatch']['query_ns'] for r in results)
    candidate_min = min(r['dispatch']['query_ns'] for r in results)
    lifecycle = statistics.median(r['dispatch']['lifecycle_ns'] for r in results)
    null_failures = [r for r in results if not .9 <= r['identical']['query_ns'] <= 1/.9]
    gates = {'duration':min(durations) >= 50_000_000, 'null_control':not null_failures,
        'candidate_median':candidate_median >= 1.03, 'candidate_floor':candidate_min >= .9,
        'lifecycle':lifecycle >= .97}
    return {'status':'DIAGNOSTIC_PASSED_REQUIRES_NEW_QUALIFICATION' if all(gates.values()) else 'NOT_QUALIFIED',
        'gates':gates, 'median_query':candidate_median, 'minimum_query':candidate_min,
        'median_lifecycle':lifecycle, 'minimum_query_cpu_ns':min(durations),
        'null_failures':null_failures,'processes':processes,'bfs_pair_executions':pairs,
        'repeated_query_calls':calls,'cells':results}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-metrics',action='store_true')
    args=parser.parse_args()
    data=json.loads(gzip.decompress((EVIDENCE/'stability.json.gz').read_bytes()))
    result=verify_stability(data,load_archive())
    if args.write_metrics:
        (EVIDENCE/'stability_metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    else:
        assert result == json.loads((EVIDENCE/'stability_metrics.json').read_text())
    print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2))

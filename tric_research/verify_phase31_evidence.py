"""Validate the complete rejected-candidate campaign and its identical-binary control."""
import argparse
import base64
import gzip
import hashlib
import json
import math
import statistics
import subprocess
import tempfile
from pathlib import Path

from benchmark_native_changes import payload

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence/phase31'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_archive():
    return json.loads(gzip.decompress((EVIDENCE / 'experiments.json.gz').read_bytes()))


def verify_seal(source_root=None):
    # A sparse historical snapshot can preserve files that later phases edit.
    # Every chosen byte stream is still checked against the original seal.
    manifest = json.loads((EVIDENCE/'sealed_manifest.json').read_text())
    for name, expected in manifest['files'].items():
        archived = Path(source_root)/name if source_root else None
        path = archived if archived is not None and archived.is_file() else ROOT.parent/name
        assert sha(path.read_bytes()) == expected, name


def verify(archive):
    assert archive['schema'] == 1
    assert archive['baseline_commit'] == 'ac810f576d9dbc6ef2b9579725e6603d3ad4e049'
    assert set(archive['builds']) == {'previous', 'branchless', 'linear4', 'dispatch', 'eytzinger'}
    assert len(archive['specs']) == 12 and set(archive['specs']) == set(archive['runs'])
    prior = json.loads((ROOT / 'evidence/phase30/source_hashes.json').read_text())
    for name, text in archive['headers']['previous'].items():
        assert sha(text.encode()) == prior['sources'][name], name
    for name, text in archive['code'].items():
        assert sha(text.encode()) == prior['sources'][name], name
    for arm, build in archive['builds'].items():
        headers = archive['headers'][arm]
        assert set(headers) == set(build['sources'])
        for name, text in headers.items():
            assert sha(text.encode()) == build['sources'][name], (arm, name)
        assert len(build['selected_runtime_dependencies']) == 5
        for name, expected in build['selected_runtime_dependencies'].items():
            assert sha(headers[name].encode()) == expected, (arm, name)
    assert archive['failed_setup']['manifest']['files'] == []
    assert not archive['failed_setup']['manifest'].get('complete', False)
    check = archive['checks']['residual_check.json']
    assert check['result']['checks'] == 5502440
    assert check['result']['branchless_mutant_disagreements'] > 0
    assert check['result']['linear_mutant_disagreements'] > 0
    assert sha(archive['utilities']['residual_check.cpp'].encode()) == check['source_sha256']
    assert check['stderr'] == ''
    native = archive['checks']['eytzinger-test.json']
    assert native['stderr'] == ''
    assert json.loads(native['stdout'])['interval_checks'] == 589824
    results = {}; total_processes = bfs_pairs = calls = 0
    for tag, spec in archive['specs'].items():
        prefix = tag.split('-')[0]
        suffix = tag[len(prefix):]
        assert prefix in ('pilot', 'layout', 'null') and suffix in ('', '-cross', '-forest', '-cold')
        fixture_sets = {'': ('evidence/phase25/fixtures', [2000], 32),
            '-cross': ('evidence/phase30/fresh-fixtures', [1000], 4),
            '-forest': ('evidence/phase27/large-fixtures', [1000], 8),
            '-cold': ('evidence/phase27/fresh-fixtures', [1], 2)}
        assert (spec['fixtures'], spec['horizons']) == fixture_sets[suffix][:2]
        assert spec['trials'] == (8 if prefix == 'null' else 4)
        assert spec['arms'] == {'pilot': ['previous','branchless','linear4','dispatch'],
            'layout': ['previous','eytzinger'], 'null': ['previous','identical']}[prefix]
        if not suffix:
            assert spec['seeds'] == [20261022,20261025]
            assert set(spec['datasets']) == {'example','grail_citeseer','grail_go','grail_kegg',
                'heldout_agrocyc','heldout_amaze','heldout_human','heldout_ecoo'}
        else:
            assert spec['seeds'] is None
            assert spec['datasets'] == (['phase30_cross_chains'] if suffix == '-cross' else None)
        run = archive['runs'][tag]; manifest = run['manifest']
        assert manifest['complete'] is True
        assert manifest['trials'] == spec['trials'] and manifest['horizons'] == spec['horizons']
        assert manifest['cap_bytes'] == 2097152
        assert manifest['environment']['cpu_affinity'] == [1]
        assert [a['name'] for a in manifest['arms']] == spec['arms']
        assert manifest['trials'] % len(spec['arms']) == 0
        for arm in manifest['arms']:
            key = 'previous' if arm['name'] == 'identical' else arm['name']
            assert arm['executable_sha256'] == archive['builds'][key]['binary_sha256']
        expected = {}; fixtures = {}
        for path in sorted((ROOT / spec['fixtures']).glob('*.json.gz')):
            fixture = json.loads(gzip.decompress(path.read_bytes()))
            if spec['datasets'] and fixture['dataset'] not in spec['datasets']:
                continue
            fixtures[path.name] = sha(path.read_bytes())
            for case in fixture['cases']:
                if spec['seeds'] and case['seed'] not in spec['seeds']:
                    continue
                for horizon in spec['horizons']:
                    key = (fixture['dataset'], case['seed'], case['stratum'], horizon)
                    expected[key] = (sha(payload(fixture, case)), len(case['queries']))
        seen = set(); ratios = {a: [] for a in spec['arms'] if a != 'previous'}
        assert {f['file'] for f in manifest['files']} == set(fixtures) == set(run['raw_gzip_base64'])
        assert len(manifest['files']) == len(fixtures)
        for entry in manifest['files']:
            assert entry['fixture_sha256'] == fixtures[entry['file']]
            raw = base64.b64decode(run['raw_gzip_base64'][entry['file']], validate=True)
            assert sha(raw) == entry['sha256']
            cells = json.loads(gzip.decompress(raw)); assert len(cells) == entry['cells']
            for cell in cells:
                key = tuple(cell[k] for k in ('dataset', 'seed', 'stratum', 'repeats'))
                assert key in expected and key not in seen; seen.add(key)
                digest, pairs = expected[key]
                assert cell['input_sha256'] == digest
                assert set(cell['rows']) == set(spec['arms'])
                checksums = set()
                for arm, rows in cell['rows'].items():
                    assert [r['trial'] for r in rows] == list(range(spec['trials']))
                    for row in rows:
                        assert row['available'] and row['queries'] == pairs
                        assert row['mode'] == 'auto' and row['repeats'] == key[3]
                        assert row['oracle_verified_pairs'] == pairs and row['actual_calls'] == pairs * key[3]
                        assert row['table_bytes'] <= manifest['cap_bytes']
                        for field in ('parse_ns', 'build_ns', 'query_ns', 'query_thread_cpu_ns', 'lifecycle_ns', 'timed_peak_rss_kib'):
                            assert isinstance(row[field], (float, int)) and math.isfinite(row[field]) and row[field] > 0
                        assert abs(row['lifecycle_ns'] - sum(row[k] for k in ('parse_ns', 'build_ns', 'query_ns'))) <= 2
                        checksums.add(row['checksum']); total_processes += 1
                        bfs_pairs += pairs; calls += row['actual_calls']
                assert len(checksums) == 1
                for arm in ratios:
                    before = cell['rows']['previous']; after = cell['rows'][arm]
                    for a, b in zip(before, after):
                        for field in ('table_bytes', 'retained_capacity_bytes', 'uses_direct_closure', 'uses_forest_index'):
                            assert a[field] == b[field], (tag, key, field)
                    ratios[arm].append({'dataset': key[0], 'seed': key[1], 'stratum': key[2], 'horizon': key[3],
                        'query': statistics.median(a['query_ns']/b['query_ns'] for a,b in zip(before,after)),
                        'cpu': statistics.median(a['query_thread_cpu_ns']/b['query_thread_cpu_ns'] for a,b in zip(before,after)),
                        'lifecycle': statistics.median(a['lifecycle_ns']/b['lifecycle_ns'] for a,b in zip(before,after))})
        assert seen == set(expected), tag
        assert len(seen) == fixture_sets[suffix][2], tag
        results[tag] = {arm: {'median_query': statistics.median(c['query'] for c in cells),
            'median_cpu': statistics.median(c['cpu'] for c in cells),
            'median_lifecycle': statistics.median(c['lifecycle'] for c in cells),
            'wins': sum(c['query'] > 1 for c in cells), 'cells': cells} for arm,cells in ratios.items()}
    decisions = {}
    for arm in ('branchless', 'linear4', 'dispatch', 'eytzinger'):
        cells = [c for result in results.values() if arm in result for c in result[arm]['cells']]
        decisions[arm] = {'median_query': statistics.median(c['query'] for c in cells),
            'min_query': min(c['query'] for c in cells),
            'median_lifecycle': statistics.median(c['lifecycle'] for c in cells),
            'qualifies': statistics.median(c['query'] for c in cells) > 1.03 and min(c['query'] for c in cells) >= .90,
            'regressions_below_floor': [c for c in cells if c['query'] < .90]}
        if arm == 'eytzinger':
            decisions[arm]['qualifies'] = (decisions[arm]['median_query'] >= 1.03 and
                decisions[arm]['min_query'] >= .90 and decisions[arm]['median_lifecycle'] >= .97)
    null = [c for result in results.values() if 'identical' in result for c in result['identical']['cells']]
    return {'status': 'PRESERVE_CURRENT' if not any(d['qualifies'] for d in decisions.values()) else 'QUALIFICATION_REQUIRED',
        'timing_processes': total_processes, 'bfs_pair_executions': bfs_pairs, 'repeated_query_calls': calls,
        'decisions': decisions, 'null_outside_band': [c for c in null if not .90 <= c['query'] <= 1/.90],
        'campaigns': results, 'uncertainty': 'Descriptive paired medians; confidence intervals not estimated. One shared host and exposed related inputs.'}


def rebuild_checks(archive):
    receipts = {}
    with tempfile.TemporaryDirectory(prefix='tric-phase31-') as temporary:
        root = Path(temporary)
        for arm, headers in archive['headers'].items():
            folder = root / arm; folder.mkdir()
            for name, text in headers.items():
                (folder / name).write_text(text)
            source = folder / 'native_runtime_check.cpp'
            source.write_text(archive['code'][source.name])
            subprocess.run(['g++', '-std=c++17', '-O2', '-fsanitize=undefined', str(source), '-o', str(folder/'check')], check=True)
            run = subprocess.run([str(folder/'check'), '--self-test'], capture_output=True, text=True, check=True)
            assert run.stderr == ''
            receipts[arm] = json.loads(run.stdout)
        (root/'check_residual.py').write_text(archive['utilities']['check_residual.py'])
        import sys
        subprocess.run([sys.executable, str(root/'check_residual.py')], check=True, capture_output=True)
        receipts['residual'] = json.loads((root/'residual_check.json').read_text())['result']
        assert receipts['residual'] == archive['checks']['residual_check.json']['result']
    return receipts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild-checks', action='store_true')
    parser.add_argument('--write-metrics', action='store_true')
    parser.add_argument('--source-root', help='Sparse repository-shaped historical source snapshot')
    args = parser.parse_args()
    if not args.write_metrics:
        verify_seal(args.source_root)
    archive = load_archive(); metrics = verify(archive)
    if args.write_metrics:
        (EVIDENCE/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
    else:
        assert metrics == json.loads((EVIDENCE/'metrics.json').read_text())
    if args.rebuild_checks:
        print(json.dumps({'rebuilt_checks': rebuild_checks(archive)}, indent=2))
    print(json.dumps({k:v for k,v in metrics.items() if k not in ('campaigns','decisions')}, indent=2))

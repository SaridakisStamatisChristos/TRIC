"""Verify Phase XXX source provenance, complete trials, memory and pilot history."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from benchmark_native_changes import payload
from summarize_native_changes import summarize
from summarize_phase30 import summarize as summarize_phase30


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    source = Path(__file__).resolve().parent
    root = source / 'evidence/phase30'
    frozen = root / 'baseline-sources/tric_research'
    hashes = json.loads((root / 'source_hashes.json').read_text())
    for name, expected in hashes['sources'].items():
        assert sha((source / name).read_bytes()) == expected, name
    for name, expected in hashes['artifacts'].items():
        assert sha((root / name).read_bytes()) == expected, name
    prior_hashes = json.loads((source / 'evidence/phase29/source_hashes.json').read_text())
    for name, expected in prior_hashes['sources'].items():
        assert sha((frozen / name).read_bytes()) == expected, name
    protocol = json.loads((root / 'qualification_protocol.json').read_text())
    assert sha((source / 'partitioned_reachability.h').read_bytes()) == protocol['candidate_header_sha256']
    build = json.loads((root / 'build_manifest.json').read_text())
    prior = json.loads((source / 'evidence/phase29/build_manifest.json').read_text())
    for key in ('compiler', 'source_sha256', 'oreach_sha', 'bfl_commit',
                'bfl_main_sha256', 'pruned_labeling_commit', 'pruned_labeling_sources'):
        assert build[key] == prior[key], key
    assert build['source_sha256'] == sha((source / 'native_compare_bench.cpp').read_bytes())
    assert build['bfl_main_sha256'] == sha((source / 'third_party/bfl/main.cpp').read_bytes())
    for name, expected in build['pruned_labeling_sources'].items():
        assert sha((source / name).read_bytes()) == expected, name
    binaries = {}
    for arm in build['commands']:
        binaries[arm['name']] = arm['executable_sha256']
        headers = frozen if arm['name'] == 'previous' else source
        assert len(arm['selected_runtime_dependencies']) == 8
        for name, expected in arm['runtime_source_hashes'].items():
            assert sha((headers / name).read_bytes()) == expected, name
        for name, expected in arm['selected_runtime_dependencies'].items():
            assert sha((headers / Path(name).name).read_bytes()) == expected, name
    assert binaries['previous'] == next(a for a in prior['commands'] if a['name'] == 'candidate')['executable_sha256']
    assert binaries['previous'] != binaries['candidate']
    # Construction, representations and accounting are unchanged. Both moved
    # bodies must remain exactly the baseline bodies, including branch order.
    before = (frozen / 'partitioned_reachability.h').read_text()
    after = (source / 'partitioned_reachability.h').read_text()
    residual = '      const auto first=intervals_.begin()+from.route+1'
    noninterval = '    if (from.tree_begin==to.tree_begin) return true;'
    accounting = '  std::size_t table_bytes() const'
    assert before[:before.index(residual)] == after[:after.index('      return reaches_residual(from,target);')]
    old_residual = before[before.index(residual):before.index('\n    }', before.index(residual))]
    assert old_residual == after[after.index(residual):after.index('\n  }', after.index(residual))]
    old_other = before[before.index(noninterval):before.index(accounting)]
    assert old_other == after[after.index(noninterval):after.index('public:\n' + accounting)]
    assert before[before.index(accounting):] == after[after.index(accounting):]
    counts = {}
    replication = json.loads((root / 'forest_replication_protocol.json').read_text())
    assert replication['candidate_header_sha256'] == protocol['candidate_header_sha256']
    specs = protocol['runs'] + [dict(replication, tag='forest-replication')]
    warm_replication = json.loads((root / 'forest_warm_replication_protocol.json').read_text())
    assert warm_replication['candidate_header_sha256'] == protocol['candidate_header_sha256']
    specs.append(dict(warm_replication, tag='forest-warm-replication'))
    for spec in specs:
        folder = root / spec['tag']; output = folder / 'qualification-final'
        manifest = json.loads((output / 'manifest.json').read_text())
        assert manifest['complete'] is True
        assert manifest['trials'] == spec['trials'] and manifest['horizons'] == spec['horizons']
        assert manifest['cap_bytes'] == protocol['cap_bytes']
        assert manifest['environment']['cpu_affinity'] == [protocol['cpu']]
        assert [a['name'] for a in manifest['arms']] == spec['arms']
        for arm in manifest['arms']:
            assert arm['executable_sha256'] == binaries['previous' if arm['name'] == 'previous' else 'candidate']
        _, receipt = summarize(folder, source / spec['fixtures'])
        for entry in manifest['files']:
            for cell in json.loads(gzip.decompress((output / entry['file']).read_bytes())):
                for a, b in zip(cell['rows']['previous'], cell['rows']['candidate']):
                    for key in ('table_bytes', 'retained_capacity_bytes', 'uses_direct_closure', 'uses_forest_index'):
                        assert a[key] == b[key], (spec['tag'], cell['dataset'], key)
        counts[spec['tag']] = receipt
    archive = json.loads(gzip.decompress((root / 'experiments.json.gz').read_bytes()))
    assert len(archive['runs']) == 5 and len(archive['builds']) == 16
    pilot_processes = 0
    for run in archive['runs'].values():
        manifest = run['manifest']; selection = run['selection_inputs']
        assert manifest['complete'] is True
        expected = {}
        for name in selection['datasets']:
            fixture = json.loads(gzip.decompress((source / 'evidence/phase25/fixtures' / (name + '.json.gz')).read_bytes()))
            for case in fixture['cases']:
                if case['seed'] in selection['seeds']:
                    for horizon in manifest['horizons']:
                        expected[(name, case['seed'], case['stratum'], horizon)] = sha(payload(fixture, case))
        seen = set()
        for entry in manifest['files']:
            raw = base64.b64decode(run['raw_gzip_base64'][entry['file']], validate=True)
            assert sha(raw) == entry['sha256']
            assert sha((source / 'evidence/phase25/fixtures' / entry['file']).read_bytes()) == entry['fixture_sha256']
            cells = json.loads(gzip.decompress(raw)); assert len(cells) == entry['cells']
            for cell in cells:
                key = tuple(cell[k] for k in ('dataset', 'seed', 'stratum', 'repeats'))
                assert key in expected and key not in seen; seen.add(key)
                assert cell['input_sha256'] == expected[key]
                assert set(cell['rows']) == {a['name'] for a in manifest['arms']}
                checksums = set()
                for rows in cell['rows'].values():
                    assert [r['trial'] for r in rows] == list(range(manifest['trials']))
                    for row in rows:
                        assert row['available'] and row['oracle_verified_pairs'] == row['queries']
                        assert row['actual_calls'] == row['queries'] * cell['repeats']
                        assert row['table_bytes'] <= manifest['cap_bytes']
                        checksums.add(row['checksum']); pilot_processes += 1
                assert len(checksums) == 1
        assert seen == set(expected)
        for arm in manifest['arms']:
            name = arm['name']; record = archive['builds'][name]
            assert arm['executable_sha256'] == record['binary_sha256']
            assert sha(archive['headers'][name].encode()) == record['header_sha256']
            assert len(record['selected_runtime_dependencies']) == 5
            for path, expected_hash in record['selected_runtime_dependencies'].items():
                basename = Path(path).name
                data = (archive['headers'][name].encode() if basename == 'partitioned_reachability.h' else
                        archive['wrappers'][name].encode() if basename == 'tric_reachability.h' else
                        (frozen / basename).read_bytes())
                assert sha(data) == expected_hash, path
    recorded_metrics = json.loads((root / 'result_metrics.json').read_text())
    assert summarize_phase30() == recorded_metrics, 'derived metrics differ from raw records'
    assert all(recorded_metrics['numeric_acceptance'].values()), 'native numeric gate failed'
    return {'baseline_binary_reproduced': True, 'moved_bodies_unchanged': True,
            'memory_and_routes_equal': True, 'qualified_runs': counts,
            'preserved_pilot_processes': pilot_processes}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))

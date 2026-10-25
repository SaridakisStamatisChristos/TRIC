"""Verify current sources, selected compiler dependencies and experiment exclusions."""
import base64
import gzip
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    source = Path(__file__).resolve().parent
    root = source / 'evidence/phase28'
    hashes = json.loads((root / 'source_hashes.json').read_text())
    for path, expected in hashes['sha256'].items():
        assert sha((source.parent / path).read_bytes()) == expected, path
    for path, expected in hashes['artifact_sha256'].items():
        assert sha((root / path).read_bytes()) == expected, path
    build = json.loads((root / 'build_manifest.json').read_text())
    reference = json.loads((root / 'reference26_build_manifest.json').read_text())
    assert build['compiler'] == reference['compiler']
    assert build['source_sha256'] == reference['source_sha256'] == sha((source / 'native_compare_bench.cpp').read_bytes())
    for key in ('bfl_commit', 'bfl_main_sha256', 'oreach_sha', 'pruned_labeling_commit', 'pruned_labeling_sources'):
        assert build[key] == reference[key], key
    binaries = {a['name']: a['executable_sha256'] for a in build['commands']}
    for arm in build['commands']:
        headers = source if arm['name'] == 'candidate' else root / 'baseline-sources/tric_research'
        selected = arm['selected_runtime_dependencies']
        assert len(selected) == 8
        for path, expected in selected.items():
            assert sha((headers / Path(path).name).read_bytes()) == expected, path
        for name, expected in arm['runtime_source_hashes'].items():
            assert sha((headers / name).read_bytes()) == expected, name
    old = next(a for a in reference['commands'] if a['name'] == 'previous')
    new = next(a for a in build['commands'] if a['name'] == 'candidate')
    flags = lambda command: [x for x in command if x.startswith(('-O', '-D', '-std=', '-f')) or x == '-include']
    assert flags(old['command']) == flags(new['command'])
    assert [x for x in old['command'] if x.endswith('.o')] == [x for x in new['command'] if x.endswith('.o')]
    binaries['pr26'] = old['executable_sha256']
    protocol = json.loads((root / 'qualification_protocol.json').read_text())
    assert len(protocol['runs']) == 4
    counts = {}
    for spec in protocol['runs']:
        tag = spec['tag']
        folder = root / tag / 'qualification-final'
        manifest = json.loads((folder / 'manifest.json').read_text())
        assert manifest['complete'] and manifest['trials'] == spec['trials']
        assert manifest['horizons'] == [spec['horizon']] and manifest['cap_bytes'] == 2097152
        assert [a['name'] for a in manifest['arms']] == spec['arms']
        for arm in manifest['arms']:
            assert arm['executable_sha256'] == binaries['pr26' if arm['name'] == 'pr26' else 'previous' if arm['name'] == 'previous' else 'candidate']
        cells = trials = 0
        for entry in manifest['files']:
            data = (folder / entry['file']).read_bytes()
            assert sha(data) == entry['sha256']
            for cell in json.loads(gzip.decompress(data)):
                cells += 1
                for a, b in zip(cell['rows']['previous'], cell['rows']['candidate']):
                    assert a['table_bytes'] == b['table_bytes']
                    assert a['retained_capacity_bytes'] == b['retained_capacity_bytes']
                trials += sum(len(values) for values in cell['rows'].values())
        receipt = json.loads((root / tag / 'verification.json').read_text())
        assert cells == receipt['cells'] and trials == receipt['fresh_process_trials']
        counts[tag] = {'cells': cells, 'processes': trials}
    archive = json.loads(gzip.decompress((root / 'experiments.json.gz').read_bytes()))
    for name, run in archive['runs'].items():
        manifest = run['manifest']
        for entry in manifest['files']:
            data = base64.b64decode(run['raw_gzip_base64'][entry['file']], validate=True)
            assert sha(data) == entry['sha256']
            cells = json.loads(gzip.decompress(data))
            assert len(cells) == entry['cells']
            for cell in cells:
                checksums = set()
                for rows in cell['rows'].values():
                    assert [r['trial'] for r in rows] == list(range(manifest['trials']))
                    for row in rows:
                        assert row['available'] and row['oracle_verified_pairs'] == row['queries']
                        assert row['actual_calls'] == row['queries'] * cell['repeats']
                        checksums.add(row['checksum'])
                assert len(checksums) == 1
        if name == 'small-long-interrupted':
            assert not manifest.get('complete')
        else:
            assert manifest['complete']
        if name in ('interval-pilot', 'inline-pilot'):
            assert len({a['executable_sha256'] for a in manifest['arms']}) == 1
    matched = archive['builds']['matched_builds.json']
    assert len(matched) == 6 and len({a['binary_sha256'] for a in matched}) == 6
    for arm in matched:
        for path, expected in arm['dependencies'].items():
            assert sha(archive['headers'][arm['name']][Path(path).name].encode()) == expected
    receipt = json.loads((root / 'provenance_verification.json').read_text())
    assert sha((root / 'experiments.json.gz').read_bytes()) == receipt['experiments_sha256']
    return {'sources_and_builds': 'passed', 'unchanged_table_and_retained_capacities': 'passed',
            'invalid_and_incomplete_runs_excluded': 'passed', 'accepted_runs': counts}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))

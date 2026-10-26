"""Verify frozen source provenance and the preserved rejected-run archive."""
import base64
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source_root=None):
    live = Path(__file__).resolve().parent
    source = Path(source_root).resolve() / 'tric_research' if source_root else live
    root = live / 'evidence/phase27'
    hashes = json.loads((root / 'source_hashes.json').read_text())
    for path, expected in hashes['sha256'].items():
        assert sha((source.parent / path).read_bytes()) == expected, path
    build = json.loads((root / 'build_manifest.json').read_text())
    candidate = next(a for a in build['commands'] if a['name'] == 'candidate')
    for path, expected in candidate['runtime_source_hashes'].items():
        assert sha((source / path).read_bytes()) == expected, path
    assert sha((source / 'native_compare_bench.cpp').read_bytes()) == build['source_sha256']
    assert sha((live / 'third_party/bfl/main.cpp').read_bytes()) == build['bfl_main_sha256']
    for path, expected in build['pruned_labeling_sources'].items():
        assert sha((live / path).read_bytes()) == expected, path
    upstream = live / 'third_party/pruned_labeling'
    provenance = json.loads((upstream / 'PROVENANCE.json').read_text())
    for path, expected in provenance['files'].items():
        data = (upstream / path).read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == expected
    receipt = json.loads((root / 'provenance_verification.json').read_text())
    for path, expected in receipt['fixture_sha256'].items():
        assert sha((root / path).read_bytes()) == expected, path
    binaries = {a['name']: a['executable_sha256'] for a in build['commands']}
    for tag in ('small', 'large', 'fresh', 'csr'):
        manifest = json.loads((root / tag / 'qualification-final/manifest.json').read_text())
        assert manifest['complete']
        for arm in manifest['arms']:
            assert arm['executable_sha256'] == binaries['previous' if arm['name'] == 'previous' else 'candidate']
    archive = json.loads(gzip.decompress((root / 'ablations.json.gz').read_bytes()))
    assert set(archive['runs']) == {'levels-pilot-matched', 'dispatch-pilot', 'cert-pilot',
                                   'correction-pilot', 'small-qualification',
                                   'large-qualification', 'fresh-qualification'}
    cells = trials = 0
    for name, run in archive['runs'].items():
        manifest = run['manifest']
        assert manifest['complete'], name
        assert set(run['raw_results']) == {f['file'] for f in manifest['files']}
        for entry in manifest['files']:
            results = run['raw_results'][entry['file']]
            assert len(results) == entry['cells']
            data = base64.b64decode(run['raw_gzip_base64'][entry['file']], validate=True)
            assert sha(data) == entry['sha256'], (name, entry['file'])
            assert json.loads(gzip.decompress(data)) == results
            for cell in results:
                cells += 1
                assert set(cell['rows']) == {a['name'] for a in manifest['arms']}
                checksums = set()
                for rows in cell['rows'].values():
                    assert [r['trial'] for r in rows] == list(range(manifest['trials']))
                    for row in rows:
                        assert row['available'] and row['oracle_verified_pairs'] == row['queries']
                        assert row['actual_calls'] == row['queries'] * cell['repeats']
                        checksums.add(row['checksum'])
                        trials += 1
                assert len(checksums) == 1
    return {'source_and_upstream_hashes': 'passed', 'frozen_build_and_fixtures': 'passed',
            'rejected_archive_cells': cells, 'rejected_archive_process_trials': trials}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', help='Frozen repository-shaped source snapshot; defaults to current sources')
    args = parser.parse_args()
    print(json.dumps(verify(args.source_root), indent=2))

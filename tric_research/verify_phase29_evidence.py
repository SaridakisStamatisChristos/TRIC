"""Verify frozen sources, matched builds, all qualified inputs and rejected pilots."""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
from benchmark_native_changes import payload
from summarize_native_changes import summarize


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(source_root=None):
    source=Path(__file__).resolve().parent
    root=source/'evidence/phase29'
    frozen=Path(source_root).resolve()/'tric_research' if source_root is not None else source
    hashes=json.loads((root/'source_hashes.json').read_text())
    for name,expected in hashes['sources'].items():
        assert sha((frozen/name).read_bytes())==expected,name
    for name,expected in hashes['artifacts'].items():
        assert sha((root/name).read_bytes())==expected,name
    protocol=json.loads((root/'qualification_protocol.json').read_text())
    assert sha((frozen/'partitioned_reachability.h').read_bytes())==protocol['candidate_header_sha256']
    build=json.loads((root/'build_manifest.json').read_text())
    previous_build=json.loads((source/'evidence/phase28/build_manifest.json').read_text())
    old=next(a for a in previous_build['commands'] if a['name']=='candidate')
    before=next(a for a in build['commands'] if a['name']=='previous')
    assert before['executable_sha256']==old['executable_sha256'],'PR28 baseline binary reproduction'
    assert build['source_sha256']==sha((source/'native_compare_bench.cpp').read_bytes())
    for key in ('compiler','source_sha256','oreach_sha','bfl_commit','bfl_main_sha256',
                'pruned_labeling_commit','pruned_labeling_sources'):
        assert build[key]==previous_build[key],key
    assert sha((source/'third_party/bfl/main.cpp').read_bytes())==build['bfl_main_sha256']
    for name,expected in build['pruned_labeling_sources'].items():
        assert sha((source/name).read_bytes())==expected,name
    binaries={}
    for arm in build['commands']:
        binaries[arm['name']]=arm['executable_sha256']
        headers=frozen if arm['name']=='candidate' else root/'baseline-sources/tric_research'
        assert len(arm['selected_runtime_dependencies'])==8
        for name,expected in arm['runtime_source_hashes'].items():
            assert sha((headers/name).read_bytes())==expected,name
        for name,expected in arm['selected_runtime_dependencies'].items():
            assert sha((headers/Path(name).name).read_bytes())==expected,name
    assert binaries['previous']!=binaries['candidate']
    control=json.loads((root/'control_build_manifest.json').read_text())
    assert control['source_sha256']==build['source_sha256']
    for key in ('compiler','oreach_sha','bfl_commit','bfl_main_sha256',
                'pruned_labeling_commit','pruned_labeling_sources'):
        assert control[key]==build[key],key
    corrected=next(a for a in control['commands'] if a['name']=='previous')
    assert next(a for a in control['commands'] if a['name']=='candidate')['executable_sha256']==binaries['candidate']
    for name,expected in corrected['runtime_source_hashes'].items():
        path=root/'corrected-control'/name if name=='partitioned_reachability.h' else frozen/name
        assert sha(path.read_bytes())==expected,name
    assert len(corrected['selected_runtime_dependencies'])==8
    for name,expected in corrected['selected_runtime_dependencies'].items():
        basename=Path(name).name
        path=root/'corrected-control'/basename if basename=='partitioned_reachability.h' else frozen/basename
        assert sha(path.read_bytes())==expected,name
    current=(frozen/'partitioned_reachability.h').read_text()
    start=current.index('    // Closure union must see sorted complete rows.')
    end=current.index('    labels_.shrink_to_fit(); bits_.shrink_to_fit();',start)
    assert (root/'corrected-control/partitioned_reachability.h').read_text()==current[:start]+current[end:]
    regression=json.loads((root/'chain_counterexample.json').read_text())
    assert sha((root/'chain_counterexample.txt').read_bytes())==regression['input_sha256']
    assert regression['baseline_binary_sha256']==binaries['previous']
    assert regression['baseline_returncode']!=0
    assert regression['candidate_result']['oracle_verified_pairs']==1
    counts={}
    for spec in protocol['runs']:
        folder=root/spec['tag'];out=folder/'qualification-final'
        manifest=json.loads((out/'manifest.json').read_text())
        assert manifest['complete'] is True
        assert manifest['trials']==spec['trials']
        assert manifest['horizons']==spec['horizons']
        assert manifest['cap_bytes']==protocol['cap_bytes']
        assert manifest['environment']['cpu_affinity']==[protocol['cpu']]
        assert [a['name'] for a in manifest['arms']]==spec['arms']
        for arm in manifest['arms']:
            expected=(corrected['executable_sha256'] if spec['previous_build']=='corrected'
                      else binaries['previous']) if arm['name']=='previous' else binaries['previous' if arm['name']=='pr28' else 'candidate']
            assert arm['executable_sha256']==expected
        # Recompute the complete case set from frozen inputs, not receipt text.
        _,receipt=summarize(folder,source/spec['fixtures'])
        for entry in manifest['files']:
            for cell in json.loads(gzip.decompress((out/entry['file']).read_bytes())):
                for a,b in zip(cell['rows']['previous'],cell['rows']['candidate']):
                    assert a['table_bytes']==b['table_bytes']
                    assert a['retained_capacity_bytes']==b['retained_capacity_bytes']
                    assert a['uses_direct_closure']==b['uses_direct_closure']
                    assert a['uses_forest_index']==b['uses_forest_index']
        counts[spec['tag']]=receipt
    archive=json.loads(gzip.decompress((root/'experiments.json.gz').read_bytes()))
    fixture_paths={p.name:p for p in (source/'evidence/phase25/fixtures').glob('*.json.gz')}
    for run in archive['runs'].values():
        manifest=run['manifest'];assert manifest['complete'] is True
        seen=set()
        for entry in manifest['files']:
            raw=base64.b64decode(run['raw_gzip_base64'][entry['file']],validate=True)
            assert sha(raw)==entry['sha256']
            fixture_bytes=fixture_paths[entry['file']].read_bytes()
            assert sha(fixture_bytes)==entry['fixture_sha256']
            fixture=json.loads(gzip.decompress(fixture_bytes))
            expected={(c['seed'],c['stratum']):sha(payload(fixture,c)) for c in fixture['cases']}
            cells=json.loads(gzip.decompress(raw));assert len(cells)==entry['cells']
            assert {(c['seed'],c['stratum']) for c in cells}==set(expected)
            for cell in cells:
                key=(cell['dataset'],cell['seed'],cell['stratum'])
                assert key not in seen;seen.add(key)
                assert cell['input_sha256']==expected[key[1:]]
                checksums=set()
                assert set(cell['rows'])=={a['name'] for a in manifest['arms']}
                for rows in cell['rows'].values():
                    assert [r['trial'] for r in rows]==list(range(manifest['trials']))
                    for row in rows:
                        assert row['available'] and row['oracle_verified_pairs']==row['queries']
                        assert row['actual_calls']==row['queries']*cell['repeats']
                        assert row['table_bytes']<=manifest['cap_bytes']
                        checksums.add(row['checksum'])
                assert len(checksums)==1
        for arm in manifest['arms']:
            record=archive['builds'][arm['name']]
            assert record['binary_sha256']==arm['executable_sha256']
            assert sha(archive['headers'][arm['name']].encode())==record['header_sha256']
            assert len(record['selected_runtime_dependencies'])==5
            for name,expected in record['selected_runtime_dependencies'].items():
                basename=Path(name).name
                raw=(archive['headers'][arm['name']].encode() if basename=='partitioned_reachability.h'
                     else (root/'baseline-sources/tric_research'/basename).read_bytes())
                assert sha(raw)==expected,name
    superseded=json.loads(gzip.decompress((root/'superseded.json.gz').read_bytes()))
    assert superseded['runs']['fresh']['failure']['stderr']=='independent BFS mismatch\n'
    assert not superseded['runs']['fresh']['manifest'].get('complete')
    for tag in ('native','external'):
        run=superseded['runs'][tag];assert run['manifest']['complete'] is True
        for entry in run['manifest']['files']:
            raw=base64.b64decode(run['raw_gzip_base64'][entry['file']],validate=True)
            assert sha(raw)==entry['sha256']
            assert len(json.loads(gzip.decompress(raw)))==entry['cells']
    return {'sources_builds_and_inputs':'passed','baseline_binary_reproduced':True,
            'chain_counterexample_and_corrected_control':'passed',
            'table_and_retained_capacities_equal':True,'all_rejected_pilots_preserved':True,
            'qualified_runs':counts}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root",help="Repository-shaped frozen source snapshot")
    print(json.dumps(verify(parser.parse_args().source_root),indent=2))

"""Validate frozen construction trials and implementation-specific comparisons."""
import argparse
import functools
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
E = ROOT/'evidence/phase33'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


@functools.lru_cache(maxsize=1)
def fixtures():
    out={}
    for item in read(E/'fixture_manifest.json'):
        if item['source']=='generated':
            raw=(E/'new-fixtures'/item['file']).read_bytes()
        else:
            raw=(ROOT/item['source']).read_bytes()
            assert sha(raw)==item['source_sha256']
            f=json.loads(gzip.decompress(raw));f['cases']=f['cases'][:1]
            raw=gzip.compress(json.dumps(f,separators=(',',':')).encode(),mtime=0)
            # Preserve the Python 3.12/zlib Unix OS byte across Python releases.
            raw=raw[:9]+b'\x03'+raw[10:]
        assert sha(raw)==item['sha256']
        out[item['file']]=(raw,json.loads(gzip.decompress(raw)))
    for p in sorted((E/'new-fixtures').glob('phase33_holdout_*.gz')):
        raw=p.read_bytes();out[p.name]=(raw,json.loads(gzip.decompress(raw)))
    assert len(out)==37
    protocol=read(E/'qualification_v2_protocol.json')
    assert {n:sha(raw) for n,(raw,_) in out.items()}==protocol['fixtures']
    for _,f in out.values():
        assert len(f['cases'])==1
        assert sha(payload(f,f['cases'][0]))==f['cases'][0]['native_input_sha256']
    return out


def positive(value):
    assert type(value) in (int,float) and math.isfinite(value) and value>0


def construction(folder,arms,trials,kind,expected_names):
    manifest=read(E/folder/'manifest.json')
    assert manifest['complete'] is True and manifest['trials']==trials
    assert manifest['cap_bytes']==2097152 and manifest['horizons']==[1]
    assert [a['name'] for a in manifest['arms']]==['previous',*arms]
    assert manifest['arms'][0]['executable_sha256']==manifest['arms'][-1]['executable_sha256']
    for arm in manifest['arms']:
        name='previous' if arm['name']=='identical' else arm['name']
        if name=='csr_v2':expected_hash=read(E/'v2_builds.json')[kind]['sha256']
        elif folder=='pilot' or kind=='warm':expected_hash=read(E/'builds.json')[name]['binary_sha256']
        else:expected_hash=read(E/'standard_builds.json')[name]['sha256']
        assert arm['executable_sha256']==expected_hash
    seen=set();cells={a:[] for a in arms};processes=0
    for entry in manifest['files']:
        name=entry['file'];assert name in expected_names and name not in seen;seen.add(name)
        path=E/folder/name;assert sha(path.read_bytes())==entry['sha256']
        raw,f=fixtures()[name];assert sha(raw)==entry['fixture_sha256']
        values=read(path);assert len(values)==entry['cells']==1
        cell=values[0];case=f['cases'][0]
        assert (cell['dataset'],cell['seed'],cell['stratum'],cell['input_sha256'])==(f['dataset'],case['seed'],case['stratum'],case['native_input_sha256'])
        rows=cell['rows'];assert set(rows)=={'previous',*arms}
        for arm,records in rows.items():
            assert len(records)==trials
            assert [r['trial'] for r in records]==list(range(trials))
            for row in records:
                assert row['available'] is True and row['mode']=='auto'
                assert row['repeats']==1 and row['queries']==row['actual_calls']==row['oracle_verified_pairs']==len(case['queries'])
                positive(row['build_thread_cpu_ns'])
                assert row['table_bytes']<=2097152
                if kind=='warm':
                    assert row['build_thread_cpu_ns']>=200000000
                    assert type(row['build_count']) is int and 2<=row['build_count']<=1000000
                processes+=1
        for arm in arms:
            ratios=[]
            for a,b in zip(rows['previous'],rows[arm]):
                for key in ('table_bytes','retained_capacity_bytes','uses_direct_closure','uses_forest_index','checksum'):
                    assert a[key]==b[key],(folder,name,arm,key)
                na=a['build_count'] if kind=='warm' else 1
                nb=b['build_count'] if kind=='warm' else 1
                ratios.append(a['build_thread_cpu_ns']/na/(b['build_thread_cpu_ns']/nb))
            cells[arm].append({'dataset':f['dataset'],'ratio':statistics.median(ratios),'paired_ratios':ratios})
    assert seen==set(expected_names)
    return cells,processes


def verify_construction():
    p=read(E/'protocol.json');q=read(E/'qualification_v2_protocol.json')
    assert p['gates']=={'median_build_cpu_ratio_min':1.05,'minimum_build_cpu_ratio':.9,'null_control_band':[.9,1/.9],'retained_and_table_equal':True,'BFS_and_sanitizers':True}
    assert q['gates']=={'warm_median':1.10,'warm_floor':.95,'cold_median':1.05,'cold_floor':.90,'null_band':[.9,1/.9],'correctness':True,'same_retained_memory':True,'same_components':True,'allocation_peak_no_increase':True}
    for arm,headers in p['headers'].items():
        for name,digest in headers.items():assert sha((E/'prototypes'/arm/name).read_bytes())==digest
    v2=E/'prototypes/csr_v2/scc_decomposition.h'
    assert sha(v2.read_bytes())==q['candidate_header_sha256']
    for name in p['headers']['previous']:
        if name!='scc_decomposition.h':assert (E/'prototypes/csr_v2'/name).read_bytes()==(E/'prototypes/previous'/name).read_bytes()
    assert v2.read_text().replace('    if(n==0)return;  // No transpose sentinel allocation for an empty graph.\n','')==(E/'prototypes/csr/scc_decomposition.h').read_text()
    pilot,n=construction('pilot',['csr','closure','buffers','identical'],5,'warm',[x['file'] for x in read(E/'fixture_manifest.json')])
    result={'pilot':{},'qualification':{},'processes':n}
    null=all(.9<=c['ratio']<=1/.9 for c in pilot['identical'])
    for arm,cells in pilot.items():
        median=statistics.median(c['ratio'] for c in cells);worst=min(c['ratio'] for c in cells)
        result['pilot'][arm]={'median':median,'worst':worst,'passes':null if arm=='identical' else median>=1.05 and worst>=.9 and null}
        old=read(E/'pilot_metrics.json')['arms'][arm]
        assert median==old['median'] and worst==old['worst']
    for kind in ('warm','cold'):
        cells,n=construction('qualification-'+kind,['csr_v2','identical'],9,kind,q['fixtures']);result['processes']+=n
        median=statistics.median(c['ratio'] for c in cells['csr_v2']);worst=min(c['ratio'] for c in cells['csr_v2'])
        bad=[c for c in cells['identical'] if not .9<=c['ratio']<=1/.9]
        passed=median>=q['gates'][kind+'_median'] and worst>=q['gates'][kind+'_floor'] and not bad
        result['qualification'][kind]={'median':median,'worst':worst,'null_failures':bad,'passes':passed}
        old=read(E/'qualification_metrics.json')[kind]
        assert (median,worst,passed)==(old['median'],old['worst'],old['passes'])
    result['promotable']=all(v['passes'] for v in result['qualification'].values())
    assert result['promotable']==read(E/'qualification_metrics.json')['promotable']
    return result


def verify_builds():
    expected={'exhaustive_checks':18432,'adversarial_checks':1440,'interval_checks':589824,'interval_indexes':9248,'cross_chain_checks':153600,'forest_checks':207360,'packed_checks':1296}
    for arm,build in read(E/'builds.json').items():
        assert len(build['selected'])==8
        for name,digest in build['selected'].items():assert sha((E/'prototypes'/arm/name).read_bytes())==digest
        assert read(E/'checks.json')[arm]['result']==expected
    for arm,build in read(E/'standard_builds.json').items():
        assert len(build['headers'])==8
        for name,digest in build['headers'].items():assert sha((E/'prototypes'/arm/name).read_bytes())==digest
    previous=read(E/'standard_builds.json')['previous']['sha256']
    old=read(ROOT/'evidence/phase32/build_manifest.json')
    assert previous==next(c['executable_sha256'] for c in old['commands'] if c['name']=='candidate')
    builds=read(E/'v2_builds.json')
    assert builds['native_checks']==expected
    assert builds['identity']=={'identical_decompositions':8002,'invalid_edges_rejected':2}
    for kind in ('warm','cold'):
        assert len(builds[kind]['headers'])==8
        for name,digest in builds[kind]['headers'].items():assert sha((E/'prototypes/csr_v2'/name).read_bytes())==digest
    failure=read(E/'empty-resource-counterexample.json')['rows']
    assert failure['previous']['construction_peak_heap_bytes']==0
    assert failure['csr']['construction_peak_heap_bytes']==16
    return {'selected_headers_verified':True,'baseline_binary_reproduced':True,'native_checks_per_variant':expected,'identity':builds['identity']}


def verify_resources():
    from verify_interval_storage import purpose_cases
    from test_native_runtime import serialize
    expected={s['name']:(serialize(s['graph'],s['queries']).encode(),s['mode'],s['cap'],s['scratch']) for s in purpose_cases()}
    for name,(_,f) in fixtures().items():
        graph=[[] for _ in range(f['graph']['vertices'])]
        for u,v in f['graph']['arcs']:graph[u].append(v)
        expected[Path(name).stem]=(serialize(graph,f['cases'][0]['queries']).encode(),'auto',2097152,67108864)
    data=read(E/'resources.json');seen=set();checks=0;savings={}
    for r in data['records']:
        assert r['name'] not in seen;seen.add(r['name'])
        raw,mode,cap,scratch=expected[r['name']]
        assert (r['input_sha256'],r['mode'],r['cap'],r['scratch'])==(sha(raw),mode,cap,scratch)
        assert set(r['arms'])=={'previous','csr_v2','buffers'}
        a=r['arms']['previous'];count=int(raw.splitlines()[0].split()[2])
        for name,b in r['arms'].items():
            assert all(type(v) is int and v>=0 for v in b.values())
            assert b['oracle_checks']==count;checks+=count
            assert b['retained_bytes']>=b['live_heap_bytes']>=b['table_bytes'] and b['table_bytes']<=cap
            assert b['construction_peak_heap_bytes']<=a['construction_peak_heap_bytes']
            for k in a:
                if k!='construction_peak_heap_bytes':assert b[k]==a[k],(r['name'],name,k)
        savings[r['name']]=a['construction_peak_heap_bytes']-r['arms']['csr_v2']['construction_peak_heap_bytes']
    assert seen==set(expected) and len(seen)==52
    return {'cases':52,'oracle_checks':checks,'csr_peak_improved_cases':sum(x>0 for x in savings.values()),'maximum_peak_bytes_saved':max(savings.values())}


def verify_seal():
    manifest=read(E/'sealed_manifest.json')
    for name,digest in manifest['files'].items():assert sha((ROOT.parent/name).read_bytes())==digest,name


def verify_replication():
    p=read(E/'replication_protocol.json');q=read(E/'qualification_v2_protocol.json')
    assert p['trials']==27 and p['gates']==q['gates'] and p['fixtures']==q['fixtures']
    assert p['qualification_metrics_sha256']==sha((E/'qualification_metrics.json').read_bytes())
    combined=read(E/'replication-warm/manifest.json')
    segments=combined['segments'];assert len(segments)==2
    entries=[]
    for segment in segments:
        path=E/segment['directory']/'manifest.json'
        assert sha(path.read_bytes())==segment['manifest_sha256']
        part=read(path);entries.extend(part['files'])
        for entry in part['files']:
            assert sha((path.parent/entry['file']).read_bytes())==entry['sha256']
    assert sorted(entries,key=lambda x:x['file'])==combined['files']
    result={'processes':0}
    for kind in ('warm','cold'):
        original,_=construction('qualification-'+kind,['csr_v2','identical'],9,kind,p['fixtures'])
        repeated,n=construction('replication-'+kind,['csr_v2','identical'],27,kind,p['fixtures'])
        result['processes']+=n
        result[kind]={}
        for group in ('replication','pooled'):
            cells=[]
            for i,cell in enumerate(repeated['csr_v2']):
                values={}
                for arm in ('csr_v2','identical'):
                    a,b=original[arm][i],repeated[arm][i]
                    assert a['dataset']==b['dataset']==cell['dataset']
                    ratios=b['paired_ratios']+(a['paired_ratios'] if group=='pooled' else [])
                    values[arm]=statistics.median(ratios)
                cells.append({'dataset':cell['dataset'],**values})
            median=statistics.median(c['csr_v2'] for c in cells);worst=min(c['csr_v2'] for c in cells)
            bad=[c for c in cells if not .9<=c['identical']<=1/.9]
            passed=median>=p['gates'][kind+'_median'] and worst>=p['gates'][kind+'_floor'] and not bad
            result[kind][group]={'median':median,'worst':worst,'null_failures':bad,'passes':passed}
            old=read(E/'replication_metrics.json')[kind][group]
            assert (median,worst,passed)==(old['median'],old['worst'],old['passes'])
    result['promotable']=all(result[k][g]['passes'] for k in ('warm','cold') for g in ('replication','pooled'))
    assert result['promotable']==read(E/'replication_metrics.json')['promotable']
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--skip-seal',action='store_true');args=p.parse_args()
    if not args.skip_seal:verify_seal()
    print(json.dumps({'builds':verify_builds(),'construction':verify_construction(),'resources':verify_resources(),'replication':verify_replication()},indent=2))

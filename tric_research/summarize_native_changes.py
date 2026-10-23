"""Validate the complete pinned comparison and emit paired-ratio tables."""
import argparse
import csv
import gzip
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from benchmark_native_changes import payload


def digest(data):
    return hashlib.sha256(data).hexdigest()


def summarize(root,fixtures=None):
    root=Path(root)
    fixtures=Path(fixtures) if fixtures is not None else root/'fixtures'
    output=root/'qualification-final'
    manifest=json.loads((output/'manifest.json').read_text())
    assert manifest.get('complete') is True,'unsealed comparison manifest'
    expected={}
    for p in fixtures.glob('*.json.gz'):
        fixture=json.loads(gzip.decompress(p.read_bytes()))
        for case in fixture['cases']:
            raw=payload(fixture,case)
            assert digest(raw)==case['native_input_sha256']
            for repeats in manifest['horizons']:
                key=(fixture['dataset'],case['seed'],case['stratum'],repeats)
                expected[key]=(case['native_input_sha256'],len(case['queries']),fixture['graph']['vertices'],len(fixture['graph']['arcs']))
    seen=set();per_seed=[];processes=oracle_checks=calls=0
    for entry in manifest['files']:
        p=output/entry['file'];raw=p.read_bytes()
        assert digest(raw)==entry['sha256'],p
        assert digest((fixtures/p.name).read_bytes())==entry['fixture_sha256']
        cells=json.loads(gzip.decompress(raw));assert len(cells)==entry['cells']
        for cell in cells:
            key=tuple(cell[k] for k in ('dataset','seed','stratum','repeats'))
            assert key in expected and key not in seen,key
            seen.add(key);input_hash,count,n,m=expected[key]
            assert cell['input_sha256']==input_hash
            rows=cell['rows'];assert set(rows)=={a['name'] for a in manifest['arms']}
            checksums=set()
            for name,values in rows.items():
                assert len(values)==manifest['trials']
                assert {r['trial'] for r in values}==set(range(manifest['trials']))
                for row in values:
                    assert row['available'] and row['vertices']==n and row['edges']==m
                    assert row['queries']==count and row['repeats']==key[3]
                    assert row['oracle_verified_pairs']==count and row['actual_calls']==count*key[3]
                    assert abs(row['lifecycle_ns']-sum(row[k] for k in ('parse_ns','build_ns','query_ns')))<=2
                    if 'table_bytes' in row:assert row['table_bytes']<=manifest['cap_bytes']
                    checksums.add(row['checksum']);processes+=1
                    oracle_checks+=count;calls+=row['actual_calls']
            assert len(checksums)==1
            result=dict(zip(('dataset','seed','stratum','repeats'),key));result['calls_per_trial']=count*key[3]
            cand=rows['candidate'];prev=rows['previous']
            for metric in ('query_ns','query_thread_cpu_ns','build_ns','lifecycle_ns'):
                result['previous_over_candidate_'+metric]=statistics.median(a[metric]/b[metric] for a,b in zip(prev,cand))
                for label,names in [('oreach',('oreach-pdfs','oreach-pbibfs')),('external',('bfl','oreach-pdfs','oreach-pbibfs'))]:
                    result[label+'_over_candidate_'+metric]=statistics.median(min(rows[name][i][metric] for name in names)/r[metric] for i,r in enumerate(cand))
            for label,values in [('previous',prev),('candidate',cand)]:
                for metric in ('query_ns','query_thread_cpu_ns'):
                    result[label+'_'+metric+'_per_call']=statistics.median(r[metric]/r['actual_calls'] for r in values)
                for metric in ('build_ns','lifecycle_ns','timed_peak_rss_kib','table_bytes','retained_capacity_bytes'):
                    result[label+'_'+metric]=statistics.median(r[metric] for r in values)
            per_seed.append(result)
    assert seen==set(expected),(len(seen),len(expected))
    per_seed.sort(key=lambda r:(r['dataset'],r['stratum'],r['repeats'],r['seed']))
    with (root/'per_seed_summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(per_seed[0]),lineterminator='\n');writer.writeheader();writer.writerows(per_seed)
    groups=defaultdict(list)
    for row in per_seed:groups[(row['dataset'],row['stratum'],row['repeats'])].append(row)
    aggregate=[]
    for key,values in sorted(groups.items()):
        row=dict(zip(('dataset','stratum','repeats'),key));row['seeds']=len(values)
        for field in per_seed[0]:
            if field in ('dataset','seed','stratum','repeats'):continue
            numbers=[r[field] for r in values];row[field]=statistics.median(numbers)
            if '_over_candidate_' in field:
                row['min_seed_'+field]=min(numbers);row['max_seed_'+field]=max(numbers)
        aggregate.append(row)
    with (root/'aggregate_summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(aggregate[0]),lineterminator='\n');writer.writeheader();writer.writerows(aggregate)
    result={'datasets':len(manifest['files']),'graph_seed_experiments':sum(len(json.loads(gzip.decompress(p.read_bytes()))['cases'])//4 for p in fixtures.glob('*.gz')),
            'cells':len(seen),'aggregate_cells':len(aggregate),'fresh_process_trials':processes,
            'independent_BFS_pair_checks':oracle_checks,'actual_query_calls':calls,
            'input_digest_checks':'all passed','result_digest_checks':'all passed','case_completeness':'all expected cases present'}
    (root/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    return aggregate,result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root');p.add_argument('--fixtures');args=p.parse_args()
    _,result=summarize(args.root,args.fixtures);print(json.dumps(result,indent=2))

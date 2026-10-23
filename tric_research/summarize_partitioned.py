"""Validate complete graph/seed matrices and retain positive AND negative cells.

Consumes extracted benchmark summaries; rejects mixed source code, partial
oracles, mismatched query hashes, timing failures and duplicate graph/seed cells.
Does not turn absent/failed baselines into speedup observations.
"""
import argparse
import csv
import hashlib
import json
import statistics
from pathlib import Path
from benchmark_partitioned import MODES,STRATA,validate,assert_parity
SEEDS={20261022,20261023,20261024}

def collect(paths,required):
    documents=[json.loads(Path(p).read_text()) for p in paths]
    expected={(d,s) for d in required for s in SEEDS}
    observed={(d['dataset'],d['seed']) for d in documents}
    if len(observed)!=len(documents):raise ValueError('duplicate graph/seed results')
    if observed!=expected:raise ValueError(f'incomplete or unexpected graph/seed matrix: missing {expected-observed}, extra {observed-expected}')
    hashes={json.dumps(d['source_hashes'],sort_keys=True) for d in documents}
    if len(hashes)!=1:raise ValueError('different implementation sources in same matrix')
    rows=[];graph_hashes={}
    for doc in documents:
        dataset=doc['dataset'];cap=doc['cap_bytes']
        graph_hash=doc['preprocessing']['original_graph_sha256']
        if dataset in graph_hashes and graph_hashes[dataset]!=graph_hash:raise ValueError('graph changed between seeds')
        graph_hashes[dataset]=graph_hash
        if set(doc['cells'])!=set(STRATA):raise ValueError('missing query strata')
        for stratum,cell in doc['cells'].items():
            if set(cell['horizons'])!={'1','100'}:raise ValueError('missing actual-call horizon')
            for repeat,h in cell['horizons'].items():
                modes=h['modes'];names=set(modes)
                external={'oreach-pdfs0','oreach-pbibfs0'} if dataset.startswith('generated_') else {'oreach-pdfs','oreach-pbibfs'}
                if names!=set(MODES)|external:raise ValueError('missing exact comparator')
                count=len(modes['auto']['trials'])
                if count!=len(modes):raise ValueError('launch positions are not balanced')
                for i in range(count):
                    trial=[]
                    for mode,data in modes.items():
                        if len(data['trials'])!=count:raise ValueError('missing timing trials')
                        observation=data['trials'][i]
                        validate(observation,mode,cell['pair_count'],int(repeat),cap)
                        trial.append(observation)
                    assert_parity(trial)
                auto=modes['auto']['trials']
                for mode,data in modes.items():
                    trials=data['trials']
                    if not all(r['available'] for r in trials):continue
                    row={'dataset':dataset,'seed':doc['seed'],'stratum':stratum,'repeat':int(repeat),'control':mode,
                         'query_ratio':statistics.median(r['query_ns']/a['query_ns'] for r,a in zip(trials,auto)),
                         'lifecycle_ratio':statistics.median(r['lifecycle_ns']/a['lifecycle_ns'] for r,a in zip(trials,auto)),
                         'auto_ns_per_query':statistics.median(a['query_ns']/a['actual_calls'] for a in auto),
                         'control_ns_per_query':statistics.median(r['query_ns']/r['actual_calls'] for r in trials),
                         'auto_retained_capacity_bytes':auto[0]['retained_capacity_bytes'],
                         'auto_table_bytes':auto[0]['table_bytes'],
                         'auto_uses_direct_closure':auto[0]['uses_direct_closure'],
                         'native_input_sha256':cell['native_input_sha256'],'graph_sha256':graph_hash,
                         'actual_calls':auto[0]['actual_calls'],'oracle_pairs':auto[0]['oracle_verified_pairs']}
                    rows.append(row)
    return {'sources':json.loads(next(iter(hashes))),'graph_hashes':graph_hashes,'comparisons':rows,'experiments':documents}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--datasets',nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();paths=sorted(a.root.rglob('summary.json'));d=collect(paths,a.datasets)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(d,indent=2)+'\n')
    csv_path=a.output.with_suffix('.csv')
    with csv_path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(d['comparisons'][0]));writer.writeheader();writer.writerows(d['comparisons'])
    print(json.dumps({'experiments':len(d['experiments']),'comparisons':len(d['comparisons']),
                      'json_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest()}))
if __name__=='__main__':main()

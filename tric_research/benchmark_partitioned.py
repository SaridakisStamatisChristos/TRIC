"""Phase XXIV graph-only indexes: exact answers, fresh-process lifetime and caps.

No training. Every arm receives identical native graph/query bytes. Each timing
trial is a new process. Replays are actual calls on frozen pairs, not IID draws.
External modes use unmodified O'Reach through its public singleQuery API.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
from pathlib import Path
from benchmark_oreach_ci import read_metis, generate_queries, write_queryfile
from stratified_queries import generate_stratified_queries
from oreach_compatible_input import prepare_comparator, remap_queryfile
from test_partitioned_reachability import serialize
ROOT=Path(__file__).resolve().parent
MODES=('compact','bounded','partitioned')
STRATA=('uniform','positive','negative','balanced')

def validate(row,mode,count,repeats,cap):
    if row['mode']!=mode or row['queries']!=count or row['repeats']!=repeats:
        raise AssertionError('wrong benchmark mode or query shape')
    if not row['available']:
        if mode!='bounded' or row['actual_calls']!=0 or row['oracle_verified_pairs']!=0:
            raise AssertionError('only an unmaterialized bounded closure may be unavailable')
    elif row['actual_calls']!=count*repeats or row['oracle_verified_pairs']!=count:
        raise AssertionError('missing actual calls / independent BFS checks')
    for key in ('parse_ns','build_ns','query_ns','lifecycle_ns','timed_peak_rss_kib'):
        if not isinstance(row[key],(int,float)) or not math.isfinite(row[key]) or row[key]<=0:
            raise AssertionError('invalid measured '+key)
    if row['available'] and 'table_bytes' in row and row['table_bytes']>cap:
        raise AssertionError('table payload cap violated')
    if abs(row['lifecycle_ns']-sum(row[k] for k in ('parse_ns','build_ns','query_ns')))>2:
        raise AssertionError('lifecycle accounting mismatch')

def assert_parity(rows):
    available=[r for r in rows if r['available']]
    if not available or len({r['checksum'] for r in available})!=1:
        raise AssertionError('answer checksum mismatch')

def run(args):
    if args.trials<3 or args.trials%3 or args.count<1 or args.cap_mib<0:
        raise ValueError('use a positive multiple of three position-balanced trials')
    out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    graph=Path(args.graph).resolve();original,_=read_metis(graph)
    adj=original;mapping=None
    preprocessing={'mode':'raw graph','original_graph_sha256':hashlib.sha256(graph.read_bytes()).hexdigest()}
    if args.external and args.dataset.startswith('generated_'):
        _,adj,mapping,preprocessing=prepare_comparator(original,graph,args.dataset,out/'scc-input')
        preprocessing['boundary']='All arms receive SAME SCC quotient; raw-to-SCC time is separately reported, excluded from all native lifecycle timers.'
    exe=Path(args.executable).resolve() if args.executable else out/'partitioned_bench'
    compile_cmd=None
    if not args.executable:
        if args.external:raise ValueError('external benchmark requires compiled adapter executable')
        compile_cmd=[args.compiler,'-std=c++17','-O3','-DNDEBUG','-Wall','-Wextra','-Wpedantic',
                     str(ROOT/'partitioned_bench.cpp'),'-o',str(exe)]
        subprocess.run(compile_cmd,check=True,capture_output=True,text=True)
    modes=MODES
    if args.external:
        suffix='0' if mapping is not None else ''
        modes+=('oreach-pdfs'+suffix,'oreach-pbibfs'+suffix)
    cap=args.cap_mib*1024*1024
    cells={}
    for stratum in args.strata:
        qs=(generate_queries(original,args.count,args.seed) if stratum=='uniform' else
            generate_stratified_queries(original,args.count,args.seed,stratum))
        folder=out/stratum;folder.mkdir(exist_ok=True)
        queryfile=folder/'original.query.m.txt';positive=write_queryfile(queryfile,original,qs)
        if mapping is not None:
            remap_queryfile(queryfile,folder/'serving.query.m.txt',original,adj,mapping)
            qs=[(mapping[s],mapping[t]) for s,t in qs]
        payload=serialize(adj,qs).encode('ascii')
        (folder/'native_input.txt').write_bytes(payload)
        horizons={}
        for repeats in args.horizons:
            observations={m:[] for m in modes}
            # n modes => n launch positions across n trials. For external's
            # five arms use 5 trials (native's three arms use args.trials).
            trials=len(modes) if args.external else args.trials
            for trial in range(trials):
                rows=[]
                for j in range(len(modes)):
                    mode=modes[(trial+j)%len(modes)]
                    cmd=[str(exe),mode,str(cap),str(repeats)]
                    proc=subprocess.run(cmd,input=payload,capture_output=True,timeout=args.timeout)
                    prefix=folder/f'r{repeats}-trial{trial}-{mode}'
                    prefix.with_suffix('.stderr.txt').write_bytes(proc.stderr)
                    if proc.returncode:raise RuntimeError(f'{mode} failed: {proc.returncode}: {proc.stderr[-1500:]!r}')
                    row=json.loads(proc.stdout);validate(row,mode,len(qs),repeats,cap)
                    prefix.with_suffix('.json').write_text(json.dumps(row,indent=2)+'\n')
                    observations[mode].append(row);rows.append(row)
                assert_parity(rows)
            summary={}
            for mode,rows in observations.items():
                summary[mode]={'available':rows[0]['available'],'trials':rows}
                if rows[0]['available']:
                    summary[mode].update({
                      'median_query_ns_per_call':statistics.median(r['query_ns']/r['actual_calls'] for r in rows),
                      'median_build_ns':statistics.median(r['build_ns'] for r in rows),
                      'median_lifecycle_ns':statistics.median(r['lifecycle_ns'] for r in rows),
                      'median_timed_peak_rss_kib':statistics.median(r['timed_peak_rss_kib'] for r in rows)})
            ratios={}
            target=observations['partitioned']
            for mode,rows in observations.items():
                if mode=='partitioned' or not rows[0]['available']:continue
                ratios[mode]={key:statistics.median(r[key]/t[key] for r,t in zip(rows,target))
                              for key in ('query_ns','build_ns','lifecycle_ns')}
            horizons[str(repeats)]={'modes':summary,'paired_control_over_partitioned':ratios}
        cells[stratum]={'positive_pairs':positive,'pair_count':len(qs),
                        'native_input_sha256':hashlib.sha256(payload).hexdigest(),
                        'original_query_sha256':hashlib.sha256(queryfile.read_bytes()).hexdigest(),
                        'horizons':horizons}
        print(json.dumps({'dataset':args.dataset,'seed':args.seed,'stratum':stratum,'complete':True}),flush=True)
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'partitioned_reachability.h',ROOT/'partitioned_bench.cpp',ROOT/'benchmark_partitioned.py']}
    try:revision=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    except subprocess.CalledProcessError:revision=None
    result={'schema':1,'dataset':args.dataset,'seed':args.seed,'cap_bytes':cap,'preprocessing':preprocessing,
      'original_vertices':len(original),'original_edges':sum(map(len,original)),
      'serving_vertices':len(adj),'serving_edges':sum(map(len,adj)),
      'external_adapter':bool(args.external),'environment':{'python':sys.version,'platform':platform.platform(),
      'machine':platform.machine(),'compiler':subprocess.check_output([args.compiler,'--version'],text=True).splitlines()[0]},
      'source_hashes':hashes,'checkout_sha':revision,'compile_command':compile_cmd,'cells':cells,
      'limits':['Table cap excludes total RSS, input and construction scratch. Default dense compression scratch cap is 64 MiB.',
                'Frozen query pairs replayed; not independent new requests. Shared-machine exploratory timings.',
                'OReach adapter uses unchanged pinned library via per-query API, not upstream CSV application.',
                'No matched total-memory, production, global SOTA or algorithmic novelty claim.']}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--dataset',required=True)
    p.add_argument('--output-dir',required=True);p.add_argument('--executable');p.add_argument('--external',action='store_true')
    p.add_argument('--compiler',default='g++');p.add_argument('--seed',type=int,default=20261023)
    p.add_argument('--count',type=int,default=1200);p.add_argument('--trials',type=int,default=3)
    p.add_argument('--horizons',type=int,nargs='+',default=[1,100]);p.add_argument('--cap-mib',type=int,default=2)
    p.add_argument('--strata',nargs='+',choices=STRATA,default=list(STRATA));p.add_argument('--timeout',type=int,default=180)
    run(p.parse_args())
if __name__=='__main__':main()

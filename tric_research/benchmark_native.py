"""Phase IX: reproducible *compiled* TRIC query-plane comparisons.

Includes real C++ query timings for BFS and three indexed variants, all
using the same compiled C++ data structures and exact fallback.
Training remains offline CPython and is accounted for separately.
Only internally generated graph families are used in the default experiment;
O'Reach real datasets are NOT present and no O'Reach SOTA claim is made.
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import random
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path
from tric import graph_family, make_pivot, early_reachable
from ordered_probe import optimize_ordered, greedy_coverage_order, hit_masks_for_pivots, ordered_cost

ROOT = Path(__file__).resolve().parent


def sample_queries(n, count, seed, mode, hot_s, hot_t):
    rng = random.Random(seed)
    return [(
        (rng.choice(hot_s), rng.choice(hot_t))
        if mode == 'hot' and rng.random() < .8 else
        (rng.randrange(n), rng.randrange(n))
    ) for _ in range(count)]


def build_executable(directory, cxx='g++', optimization='-O3'):
    output = Path(directory)/'native_query_bench'
    args = [cxx, '-std=c++17', optimization, '-DNDEBUG', '-Wall', '-Wextra', '-Wpedantic',
            '-o', str(output), str(ROOT/'native_query_bench.cpp')]
    t0 = time.perf_counter()
    subprocess.run(args, check=True, capture_output=True, text=True)
    return output, time.perf_counter()-t0, args


def serialize_native(adj, candidate_vertices, methods, queries, selector_train=None):
    edges=[(u,v) for u,row in enumerate(adj) for v in row]
    chunks=[f'{len(adj)} {len(edges)} {len(candidate_vertices)} {len(queries)}',
            *[f'{u} {v}' for u,v in edges],
            ' '.join(map(str,candidate_vertices)), str(len(methods))]
    for name,order in methods.items():
        if not name.isascii() or not name.isalnum():
            raise ValueError('policy name must be alphanumeric')
        if len(order)!=len(set(order)) or any(not 0<=i<len(candidate_vertices) for i in order):
            raise ValueError('invalid policy')
        chunks.append(' '.join([name,str(len(order))]+[str(i) for i in order]))
    chunks.extend(f'{s} {t}' for s,t in queries)
    # Appended optional train-only query set. All existing callers remain valid.
    if selector_train is not None:
        chunks.append(str(len(selector_train)))
        chunks.extend(f'{s} {t}' for s,t in selector_train)
    return ('\n'.join(chunks)+'\n').encode('ascii')


def call_native(executable, adj, vertices, methods, queries, repetitions):
    p = subprocess.run([str(executable),str(repetitions)],
                       input=serialize_native(adj,vertices,methods,queries),
                       check=True, capture_output=True)
    return json.loads(p.stdout)


def trial(family, mode, trial_index, executable, args):
    seed=args.seed+trial_index*1009+sum(map(ord,family))
    adj,rev=graph_family(family,args.n,seed)
    vertex_ids=sorted(range(args.n), key=lambda v:(-(len(adj[v])+len(rev[v])),v))[:args.candidates]
    pivots=[make_pivot(adj,rev,v) for v in vertex_ids]
    rng=random.Random(seed+11)
    hot_s=[rng.randrange(args.n) for _ in range(10)]
    hot_t=[rng.randrange(args.n) for _ in range(10)]
    train_mode, test_mode = ('hot','uniform') if mode=='hot_to_uniform' else (mode,mode)
    train=sample_queries(args.n,args.train,seed+101,train_mode,hot_s,hot_t)
    test=sample_queries(args.n,args.test,seed+202,test_mode,hot_s,hot_t)
    t0=time.perf_counter()
    hit_train=hit_masks_for_pivots(pivots,train)
    fb_train=[1+early_reachable(adj,*q)[1] for q in train]
    ordered,model_cost,_=optimize_ordered(hit_train,[1.0]*len(train),fb_train,
                                          [1.0]*args.candidates,args.budget)
    greedy=greedy_coverage_order(hit_train,[1.0]*len(train),args.candidates,args.budget)
    training_seconds=time.perf_counter()-t0
    policies={'BFS':[],'NoIndexControl':[], 'Degree':list(range(args.budget)), 'Greedy':greedy, 'Ordered':ordered}
    result=call_native(executable,adj,vertex_ids,policies,test,args.repetitions)
    # Held-out model costs are computed strictly after the policy is fixed.
    model_test_hits=hit_masks_for_pivots(pivots,test)
    model_test_fallbacks=[1+early_reachable(adj,*q)[1] for q in test]
    model_costs={name:ordered_cost(order,model_test_hits,[1.0]*len(test),model_test_fallbacks,[1.0]*args.candidates) for name,order in policies.items()}
    result['heldout_model_work']=model_costs
    metrics={x['name']:x for x in result['policies']}
    bfs_ns=metrics['BFS']['median_ns_per_query']
    control_ratio=metrics['NoIndexControl']['median_ns_per_query']/bfs_ns
    result['identical_empty_policy_ratio']=control_ratio
    result['empty_policy_control_within_15pct']=0.85<=control_ratio<=1.15
    result['index_bits_logical_bytes']=2*len(vertex_ids)*((args.n+63)//64)*8
    gain=bfs_ns-metrics['Ordered']['median_ns_per_query']
    result['amortized_break_even_queries_vs_bfs']=(training_seconds*1e9+result['index_build_ms']*1e6)/gain if gain>0 else None
    for p in result['policies']:
        p['speedup_vs_bfs']=bfs_ns/p['median_ns_per_query']
    result.update({'family':family,'distribution':mode,'seed':seed,
                   'training_seconds_python':training_seconds,
                   'training_samples':len(train), 'heldout_samples':len(test),
                   'model_training_optimum':model_cost,
                   'candidate_vertices':vertex_ids,
                   'selected_sequences':policies,
                   'graph_is_synthetic':True,
                   'index_compiled_in_cpp':True})
    return result


def execute(args):
    if not 0 <= args.budget <= args.candidates <= args.n:
        raise ValueError('invalid pivot budget/candidate size')
    if args.n<1 or args.train<1 or args.test<1 or args.trials<1:
        raise ValueError('invalid sample size')
    with tempfile.TemporaryDirectory(prefix='tric_phase9_') as tmp:
        executable, compile_time, command=build_executable(tmp,args.compiler,args.optimization)
        version=subprocess.run([args.compiler,'--version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
        cases=[]
        for family in args.families:
            for mode in args.modes:
                for trial_i in range(args.trials):
                    cases.append(trial(family,mode,trial_i,executable,args))
        ratios=lambda name:[next(x for x in c['policies'] if x['name']=='Ordered')['median_ns_per_query']/next(x for x in c['policies'] if x['name']==name)['median_ns_per_query'] for c in cases]
        out={'protocol':'Phase IX compiled query-plane pilot, NOT O-Reach comparison',
             'source':'TRIC Phase IX synthetic graph generator',
             'compiler':version,'compile_command':command,'compile_seconds':compile_time,
             'python':platform.python_version(),'platform':platform.platform(),
             'config':vars(args),'cases':cases,
             'summary':{
                 'cases':len(cases),
                 'median_ordered_over_bfs_latency_ratio':statistics.median(ratios('BFS')),
                 'median_ordered_over_greedy_latency_ratio':statistics.median(ratios('Greedy')),
                 'median_ordered_over_degree_latency_ratio':statistics.median(ratios('Degree')),
                 'proxy_ordered_better_than_greedy':sum(c['heldout_model_work']['Ordered'] < c['heldout_model_work']['Greedy'] for c in cases),
                 'walltime_proxy_preference_disagreement_vs_greedy':sum((c['heldout_model_work']['Ordered'] < c['heldout_model_work']['Greedy']) != (next(x for x in c['policies'] if x['name']=='Ordered')['median_ns_per_query'] < next(x for x in c['policies'] if x['name']=='Greedy')['median_ns_per_query']) for c in cases),
                 'ordered_faster_than_bfs':sum(v<1 for v in ratios('BFS')),
                 'ordered_faster_than_greedy':sum(v<1 for v in ratios('Greedy')),
                 'mean_trained_seconds':statistics.mean(c['training_seconds_python'] for c in cases),
                 'mean_index_build_ms':statistics.mean(c['index_build_ms'] for c in cases),
                 'empty_policy_controls_passed':sum(c['empty_policy_control_within_15pct'] for c in cases),
                 'eligible_cases_for_bfs_amortization':sum(c['amortized_break_even_queries_vs_bfs'] is not None for c in cases),
                 'median_finite_break_even_queries':statistics.median(c['amortized_break_even_queries_vs_bfs'] for c in cases if c['amortized_break_even_queries_vs_bfs'] is not None),
                 'median_empty_policy_latency_ratio':statistics.median(c['identical_empty_policy_ratio'] for c in cases)
             }}
        return out


def parser():
    p=argparse.ArgumentParser()
    p.add_argument('--n',type=int,default=360)
    p.add_argument('--train',type=int,default=750)
    p.add_argument('--test',type=int,default=2800)
    p.add_argument('--candidates',type=int,default=11)
    p.add_argument('--budget',type=int,default=5)
    p.add_argument('--repetitions',type=int,default=7)
    p.add_argument('--trials',type=int,default=2)
    p.add_argument('--seed',type=int,default=20261021)
    p.add_argument('--families',nargs='+',default=['dag','chain','blocks','communities'])
    p.add_argument('--modes',nargs='+',default=['uniform','hot','hot_to_uniform'])
    p.add_argument('--compiler',default='g++')
    p.add_argument('--optimization',choices=['-O2','-O3'],default='-O3')
    p.add_argument('--output',default='phase9_native_results.json')
    return p


if __name__=='__main__':
    args=parser().parse_args()
    result=execute(args)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary'],indent=2))

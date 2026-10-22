"""Phase XIX source-hotset falsification. Native C++17; synthetic-only, not SOTA.

No evaluation query influences training source choice. Three workload-shift
classes share a fixed training source distribution and original graph.
All query answers are independently BFS checked by hot_source_bench.cpp.
"""
import argparse
import json
import math
import platform
import random
import subprocess
import tempfile
from pathlib import Path
from tric import graph_family

HERE = Path(__file__).resolve().parent

def samples(n, count, seed, sources=(), hot_fraction=0.8):
    rng = random.Random(seed)
    return [(rng.choice(sources) if sources and rng.random()<hot_fraction
             else rng.randrange(n), rng.randrange(n))
            for _ in range(count)]

def native_input(adj, training, test, rows, cap):
    edges=[(u,v) for u,vs in enumerate(adj) for v in vs]
    lines=[f'{len(adj)} {len(edges)} {len(training)} {len(test)} {rows} {cap}']
    lines.extend(f'{u} {v}' for u,v in edges)
    lines.extend(f'{u} {v}' for u,v in training)
    lines.extend(f'{u} {v}' for u,v in test)
    return ('\\n'.join(lines)+'\\n').encode('ascii')

def execute(n, train_count, test_count, seed, cache_sources, cap=65536):
    adj,_ = graph_family('dag',n,seed)
    shuffled=list(range(n));random.Random(seed+13).shuffle(shuffled)
    hot_sources=shuffled[:cache_sources]
    shifted_sources=shuffled[cache_sources:2*cache_sources]
    training=samples(n,train_count,seed+51,hot_sources)
    outcomes={}
    with tempfile.TemporaryDirectory() as td:
        exe=Path(td)/'hotbench'
        command=['g++','-std=c++17','-O3','-DNDEBUG','-Wall','-Wextra',
                 '-Wpedantic',str(HERE/'hot_source_bench.cpp'),'-o',str(exe)]
        subprocess.run(command,check=True,capture_output=True,text=True)
        for name, sources in [('matched_hot',hot_sources),
                              ('uniform',()),
                              ('shifted_hot',shifted_sources)]:
            test=samples(n,test_count,seed+71,sources)
            proc=subprocess.run([str(exe)],input=native_input(
                adj,training,test,cache_sources,cap),
                check=True,capture_output=True)
            row=json.loads(proc.stdout)
            b=row['baseline_ns_per_query']
            c=row['cached_ns_per_query']
            f=row['build_ns']
            row['strict_projected_break_even_queries']=(math.floor(f/(b-c))+1
                 if b>c else None)
            row['ratio_baseline_over_cached']=b/c
            row['workload']=name
            outcomes[name]=row
    return outcomes

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--n',type=int,default=600)
    ap.add_argument('--training',type=int,default=500)
    ap.add_argument('--heldout',type=int,default=4000)
    ap.add_argument('--sources',type=int,default=8)
    ap.add_argument('--seeds',type=int,default=3)
    ap.add_argument('--output',type=Path,default=HERE/'phase19_hotset_results.json')
    args=ap.parse_args()
    if not(1<=args.sources and 2*args.sources<=args.n
           and args.training>0 and args.heldout>0 and 1<=args.seeds<=10):
        ap.error('invalid workload parameters')
    rows=[{'seed':20261022+i, 'classes':execute(
        args.n,args.training,args.heldout,20261022+i,args.sources)}
          for i in range(args.seeds)]
    result={'scope':'synthetic DAG only, DFS control only, not OReach/TRIC head-to-head',
            'selector':'training-source frequency, no heldout queries',
            'protocol':{'n':args.n,'training':args.training,
                        'heldout':args.heldout,'cache_rows':args.sources,
                        'train_hot_probability':0.8,'test_hot_probability':0.8,
                        'cache_byte_cap':65536,'repetitions':14},
            'system':{'platform':platform.platform(),'python':platform.python_version()},
            'results':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\\n')
    for row in rows:
        for cls,rec in row['classes'].items():
            print(f"seed={row['seed']} class={cls} ratio={rec['ratio_baseline_over_cached']:.3f} "
                  f"hits={rec['hits']}/{rec['heldout']} break_even={rec['strict_projected_break_even_queries']}")
    print(f"written {args.output}")

if __name__=='__main__':
    main()

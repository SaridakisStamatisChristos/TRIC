"""Exploratory Phase VI exact optimizer comparison on deterministic instances.

Run: python benchmark_adaptive.py > phase6_benchmark.json
Internal Python optimizer comparisons only. Report median of repeated calls.
"""
import json,statistics,platform,sys,time,os
from adaptive_exact import optimize_adaptive
from backbone import optimize_intervals
from frontier_dp import optimize_frontier

def suite(r, pattern):
    if pattern=='separated':
        h=4*r
        signatures=[((4*i,4*i),(4*i+2,4*i+2)) for i in range(r)]
    elif pattern=='overlapping':
        h=3*r+1
        signatures=[((i,i),(2*r+i,2*r+i)) for i in range(r)]
    elif pattern=='single':
        h=4*r
        signatures=[((4*i,4*i+1),) for i in range(r)]
    else:raise ValueError(pattern)
    return h,signatures,[1+(i%3) for i in range(r)],r//2

def timed(fn):
    measures=[];res=None
    for _ in range(5):
        start=time.perf_counter();res=fn();measures.append(time.perf_counter()-start)
    return res,statistics.median(measures),measures

def main():
    out=[]
    for pattern,ns in [('separated',[2,4,6,8,10,12,20]),
                       ('overlapping',[3,5,7,9]),('single',[10,50,100])]:
        for r in ns:
            h,ivs,weights,k=suite(r,pattern)
            candidate,adaptive_m,am=timed(lambda:optimize_adaptive(h,ivs,weights,k))
            oldf=None;oldo=None
            # Protect benchmarks from exponential blow-up.
            if r<=12:
                frontier,frontier_m,fm=timed(lambda:optimize_frontier(h,ivs,weights,k))
                assert frontier[1]==candidate[1]
                oldf={'median_seconds':frontier_m,'samples':fm}
            if r<=8:
                orient,orient_m,om=timed(lambda:optimize_intervals(h,ivs,weights,k))
                assert orient[1]==candidate[1]
                oldo={'median_seconds':orient_m,'samples':om}
            out.append({'pattern':pattern,'r':r,'n':h,'budget':k,
                        'component_count':candidate[2]['components'],
                        'max_component_width':max((z['frontier_width'] for z in candidate[2]['component_stats']),default=0),
                        'loss':candidate[1],'adaptive':{'median_seconds':adaptive_m,'samples':am},
                        'frontier':oldf,'orientation':oldo})
    print(json.dumps({'experiment':'Phase VI: decomposed adaptive exact optimizer',
            'date':'2026-10-21','python':sys.version,'platform':platform.platform(),
            'cpu_count':os.cpu_count(),'repetitions':5,
            'qualification':'synthetic paired internal Python comparisons; not external SOTA benchmarking',
            'cases':out},indent=2))
if __name__=='__main__':main()

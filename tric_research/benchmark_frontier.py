"""Deterministic exploratory benchmarks for frontier-width parameterization.

Run from tric_research/: python benchmark_frontier.py > phase5_benchmark.json
DO NOT interpret as O'Reach/SOTA comparative evidence.
"""
import json
import os
import platform
import statistics
import sys
import time
from frontier_dp import optimize_frontier
from backbone import optimize_intervals


def suite(r, pattern):
    if pattern == 'separated':
        h=4*r
        signatures=[((4*i,4*i),(4*i+2,4*i+2)) for i in range(r)]
    elif pattern == 'overlapping':
        h=3*r+1
        signatures=[((i,i),(2*r+i,2*r+i)) for i in range(r)]
    else:
        raise ValueError(pattern)
    return h,signatures,[1]*r,r//2


def time_it(fn,repeat=5):
    samples=[]
    result=None
    for _ in range(repeat):
        st=time.perf_counter()
        result=fn()
        samples.append(time.perf_counter()-st)
    return result,samples


def main():
    cases=[]
    for pattern,counts in (('separated',(2,4,6,8,12,18)),
                           ('overlapping',(4,6,8,10))):
        for r in counts:
            h,ivs,weights,k=suite(r,pattern)
            frontier,f_samples=time_it(lambda:optimize_frontier(h,ivs,weights,k))
            old_samples=None
            if r <= 8:
                old,old_samples=time_it(lambda:optimize_intervals(h,ivs,weights,k))
                assert old[1] == frontier[1], (old,frontier)
            cases.append({'family':pattern,'r':r,'h':h,'k':k,
                          'frontier_width':frontier[2]['frontier_width'],
                          'maximum_states':frontier[2]['max_states'],
                          'uncovered_weight':frontier[1],
                          'frontier_seconds':f_samples,
                          'frontier_median_seconds':statistics.median(f_samples),
                          'orientation_seconds':old_samples,
                          'orientation_median_seconds':statistics.median(old_samples) if old_samples else None})
    print(json.dumps({'experiment':'TRIC Phase V frontier exact DP versus Phase III orientation exact DP',
          'date':'2026-10-21','python':sys.version,'platform':platform.platform(),
          'cpu_count':os.cpu_count(),'repetitions':5,
          'warnings':['synthetic workloads only','local CPython wall-clock timings',
                      'baseline is TRIC Phase III, not O-Reach',
                      'orientation baseline omitted above r=8 to avoid impractical exponential time'],
          'cases':cases},indent=2))

if __name__ == '__main__':main()

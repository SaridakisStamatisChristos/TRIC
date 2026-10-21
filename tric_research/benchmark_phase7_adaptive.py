"""Fair paired comparison of Phase VI and Phase VII adaptive exact modes.

Uses the SAME workload, objective, local decomposition and budget convolution;
only the frontier state representation changes. This is exploratory Python,
not a compiled graph reachability benchmark.
"""
import json
import statistics
import sys
import time
from adaptive_exact import optimize_adaptive


def main():
    rows=[]
    for family,h,signatures in [
        ('long-2interval',80,6),('long-2interval',200,6),
        ('long-2interval',400,6),('more-concurrent',80,9),
        ('single-interval',400,0)]:
        if signatures:
            iv=[((1,i+3),(h-20+i,h-1)) for i in range(signatures)]
            wt=[i+1 for i in range(signatures)]
        else:
            iv=[((0,h-1),)]*40+[((h//4,3*h//4),)]*40
            wt=[1]*len(iv)
        k=5
        results={}
        samples={}
        for method in ('frontier','compact','auto'):
            times=[]
            for _ in range(5):
                t0=time.perf_counter()
                pivots,loss,diag=optimize_adaptive(h,iv,wt,k,engine=method)
                times.append(1000*(time.perf_counter()-t0))
                assert len(pivots)==k
                assert loss==sum(w for reg,w in zip(iv,wt)
                    if not any(a<=p<=b for a,b in reg for p in pivots))
            results[method]={'objective':loss,'median_ms':statistics.median(times),
                             'engine':diag['component_stats'][0]['engine']}
            samples[method]=times
        assert len({v['objective'] for v in results.values()})==1
        print(f'{family},h={h}: legacy={results["frontier"]["median_ms"]:.3f} ms '
              f'compact={results["compact"]["median_ms"]:.3f} ms '
              f'auto={results["auto"]["median_ms"]:.3f} ms',file=sys.stderr,flush=True)
        rows.append({'family':family,'h':h,'k':k,'signatures':signatures,
                     'queries':len(iv),'result':results,'samples_ms':samples})
    print(json.dumps({'python':sys.version,'cases':rows,'status':'local-exploratory',
       'caveat':'No O\u2019Reach comparison; Phase VI frontier is forced to isolate state compression.'},indent=2))

if __name__=='__main__':main()

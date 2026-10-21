"""Exact path optimizer comparisons, same queries, weights and hardware."""
import json,platform,random,statistics,sys,time
from tric import choose_path_optimal
from path_monge import choose_path_monge
from path_sweep import choose_path_sweep

def measure(fn, repeats=5):
    t=[];ans=None
    for _ in range(repeats):
        start=time.perf_counter();ans=fn();t.append(time.perf_counter()-start)
    return statistics.median(t),ans

def main():
    r=[]
    for n in (160,320,640,960):
        rng=random.Random(20261021+n)
        qs=[(rng.randrange(n),rng.randrange(n)) for _ in range(5*n)]
        weights=[rng.randrange(1,10) for _ in qs]
        methods={'quadratic':choose_path_optimal,'monge':choose_path_monge,'sweep':choose_path_sweep}
        med={};sol={}
        for name,f in methods.items():
            med[name],sol[name]=measure(lambda:f(n,qs,8,weights))
        if len(set(tuple(s[0])+ (s[1],) for s in sol.values()))!=1:raise AssertionError((n,sol))
        r.append(dict(n=n,queries=len(qs),k=8,repeats=5,objective=sol['sweep'][1],median_s={name:round(v,6) for name,v in med.items()},speedup_vs_quadratic={name:round(med['quadratic']/v,2) for name,v in med.items()}))
        print(r[-1],flush=True)
    # Sparse workload scaling: fixed m=2000, more vertices than dense cost table can handle.
    extra=[]
    for n in (2000,5000,10000):
        rng=random.Random(2026+n)
        qs=[(rng.randrange(n),rng.randrange(n)) for _ in range(2000)]
        weights=[rng.randrange(1,10) for _ in qs]
        ts,v=measure(lambda:choose_path_sweep(n,qs,8,weights),3)
        extra.append(dict(n=n,q=len(qs),k=8,repeats=3,sweep_median_s=round(ts,6),objective=v[1]))
        print(extra[-1],flush=True)
    with open('optimizer_comparison.json','w') as f:
        json.dump(dict(environment=dict(python=sys.version,platform=platform.platform()),seed=20261021,comparisons=r,sweep_scaling=extra),f,indent=2)
if __name__=='__main__': main()

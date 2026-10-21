"""Reference-vs-Monge path pivot optimization benchmark (excludes graph search)."""
import argparse, json, platform, random, statistics, sys, time
from tric import choose_path_optimal
from path_monge import choose_path_monge

def timed(fn, repeat=3):
    vals=[]; solution=None
    for _ in range(repeat):
        start=time.perf_counter();solution=fn();vals.append(time.perf_counter()-start)
    return statistics.median(vals), solution

def run(sizes=(160,320,640,960), seed=20261021, k=8, repeat=3, multiplier=5):
    rows=[]
    for n in sizes:
        r=random.Random(seed+n)
        queries=[(r.randrange(n),r.randrange(n)) for _ in range(multiplier*n)]
        weights=[r.randint(1,9) for _ in queries]
        t1,a=timed(lambda:choose_path_optimal(n,queries,k,weights),repeat)
        t2,b=timed(lambda:choose_path_monge(n,queries,k,weights),repeat)
        if a!=b: raise AssertionError((n,a,b))
        rows.append(dict(n=n,k=k,train_queries=len(queries),repeats=repeat,reference_median_s=round(t1,6),monge_median_s=round(t2,6),speedup=round(t1/t2,3),objective=b[1]))
    return dict(environment={'python':sys.version,'platform':platform.platform()},seed=seed,rows=rows)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sizes',type=int,nargs='+',default=[160,320,640,960]);p.add_argument('--k',type=int,default=8);p.add_argument('--repeat',type=int,default=3);p.add_argument('--output',default='path_monge_results.json');a=p.parse_args()
    obj=run(tuple(a.sizes),k=a.k,repeat=a.repeat)
    with open(a.output,'w') as f:json.dump(obj,f,indent=2)
    print(json.dumps(obj['rows'],indent=2))

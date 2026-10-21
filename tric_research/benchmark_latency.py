"""Exploratory Python wall-clock benchmark; not a comparison with optimized graph indexes."""
import json,time,statistics,random
from tric import graph_family,make_queries,candidates_for,choose_greedy,selected_certify,early_reachable

def workload(n,count,seed,distribution,hotseed):
    if distribution!='hot':return make_queries(n,count,seed,'uniform')
    r=random.Random(hotseed);sources=[r.randrange(n) for _ in range(10)];targets=[r.randrange(n) for _ in range(10)]
    rr=random.Random(seed);out=[]
    for _ in range(count):
        if rr.random()<.8:out.append((rr.choice(sources),rr.choice(targets)))
        else:out.append((rr.randrange(n),rr.randrange(n)))
    return out

def run(seed=20261021,n=240,count=20000,k=8,c=48,reps=5):
    rows=[]
    for fam in ('dag','chain','blocks','communities'):
        adj,rev=graph_family(fam,n,seed+len(fam))
        for dist in ('uniform','hot'):
            train=workload(n,2000,seed+5,dist,seed+101)
            test=workload(n,count,seed+6,dist,seed+101)
            t=time.perf_counter();candidates=candidates_for(adj,rev,train,c,seed+13)
            selected=choose_greedy(candidates,train,k);preprocessing=time.perf_counter()-t
            timings={'bfs':[],'tric':[]}
            for _ in range(reps):
                t=time.perf_counter();expected=[early_reachable(adj,s,t)[0] for s,t in test]
                timings['bfs'].append(time.perf_counter()-t)
                t=time.perf_counter()
                result=[]
                for s,target in test:
                    a=selected_certify(selected,s,target)
                    result.append(early_reachable(adj,s,target)[0] if a is None else a)
                timings['tric'].append(time.perf_counter()-t)
                assert result==expected
            basetime=statistics.median(timings['bfs']);newtime=statistics.median(timings['tric'])
            # Estimated break-even query count, assuming preprocessing cost and measured per-query savings stay stable.
            saving=(basetime-newtime)/count
            breakeven=(round(preprocessing/saving) if saving>0 else None)
            rows.append(dict(family=fam,distribution=dist,queries=count,repeats=reps,
                         preprocessing_s=round(preprocessing,4),baseline_median_s=round(basetime,4),
                         tric_median_s=round(newtime,4),query_speedup=round(basetime/newtime,3),
                         estimated_breakeven_queries=breakeven))
    return rows

if __name__=='__main__':
    x=run()
    with open('latency_results.json','w') as f:json.dump(x,f,indent=2)
    for r in x:print(r)

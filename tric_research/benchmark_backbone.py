"""Phase III: local exploratory measurements, not a SOTA reachability benchmark."""
import json,platform,random,statistics,time,sys,itertools
from tric import build_graph
from backbone import (backbone_intervals,backbone_intervals_fast,
                      optimize_intervals,greedy_intervals)
from backbone_hardness import make_vertex_cover_instance


def track(f,repeat=3):
    times=[];value=None
    for i in range(repeat):
        start=time.perf_counter();value=f();times.append(time.perf_counter()-start)
    return statistics.median(times),value,times


def case(n,r,k,seed):
    rng=random.Random(seed);h=n
    # distinct, nonadjacent undirected edges -> r two-singleton workloads
    pool=[(u,v) for u in range(n) for v in range(u+2,n)]
    rng.shuffle(pool);cross=pool[:r]
    adj,rev,bb,queries=make_vertex_cover_instance(n,cross)
    # Add 2n single-interval chain queries with varied nonnegative weights.
    for _ in range(2*n):
        a=rng.randrange(n);b=rng.randrange(n)
        queries.append((a,b))
    weights=[rng.randrange(1,7) for _ in queries]
    regions=backbone_intervals_fast(adj,rev,bb,queries)
    r_eff=sum(len(z)==2 for z in regions)
    return adj,rev,bb,queries,weights,regions,r_eff


def run():
    out={'environment':{'python':sys.version,'platform':platform.platform()},
         'selection':[],'extraction':[],'small_oracle':[]}
    for r in (0,2,4,6,8,10):
        n=32;k=4
        case_args=case(n,r,k,20261021)
        adj,rev,bb,qs,ws,regs,r_eff=case_args
        exact_t,(pivots,uncov,r_unique),samples=track(lambda:optimize_intervals(n,regs,ws,k))
        greedy_t,(picked,greedy_uncov),gs=track(lambda:greedy_intervals(n,regs,ws,k))
        assert uncov<=greedy_uncov
        out['selection'].append({'n':n,'k':k,'queries':len(qs),'r_requests':r,
            'r_effective':r_eff,'r_distinct':r_unique,
            'exact_uncovered':uncov,'greedy_uncovered':greedy_uncov,
            'exact_time_s_median':exact_t,'greedy_time_s_median':greedy_t,
            'exact_runs_s':samples,'greedy_runs_s':gs})
    for h in (60,160,320,640):
        rng=random.Random(999+h)
        n=h+max(2,h//6)
        topo=list(range(h))
        for x in range(h,n):topo.insert(rng.randrange(len(topo)+1),x)
        edges=[(i,i+1) for i in range(h-1)]
        # Sparse forward shortcuts with no backward graph arcs.
        for j in range(n*3):
            a,b=sorted(rng.sample(range(n),2))
            edges.append((topo[a],topo[b]))
        adj,rev=build_graph(n,edges)
        queries=[(rng.randrange(n),rng.randrange(n)) for _ in range(500)]
        fast_t,fast,fast_runs=track(lambda:backbone_intervals_fast(adj,rev,list(range(h)),queries))
        ref_t,ref,ref_runs=track(lambda:backbone_intervals(adj,rev,list(range(h)),queries))
        assert fast==ref
        out['extraction'].append({'vertices':n,'backbone':h,'edges':sum(map(len,adj)),
            'queries':len(queries),'fast_s_median':fast_t,'reference_s_median':ref_t,
            'speedup_reference_over_fast':ref_t/fast_t,'fast_runs_s':fast_runs,'reference_runs_s':ref_runs})
    for r in (0,2,4,6):
        n=15;k=3
        adj,rev,bb,qs,ws,regs,reff=case(n,r,k,321+r)
        exact_t,(p,uncov,rr),times=track(lambda:optimize_intervals(n,regs,ws,k))
        sets=[]
        a=time.perf_counter()
        for chosen in itertools.combinations(range(n),k):
            cost=sum(w for reg,w in zip(regs,ws) if not any(i>=lo and i<=hi for lo,hi in reg for i in chosen))
            sets.append(cost)
        brute_t=time.perf_counter()-a
        assert min(sets)==uncov
        out['small_oracle'].append({'n':n,'k':k,'r':rr,'exact_s':exact_t,
                                    'brute_s':brute_t,'objective':uncov})
    return out

if __name__=='__main__':
    data=run()
    with open('phase3_results.json','w') as f:json.dump(data,f,indent=2)
    print(json.dumps({'selection':data['selection'],'extraction':data['extraction'],'small_oracle':data['small_oracle']},indent=2))

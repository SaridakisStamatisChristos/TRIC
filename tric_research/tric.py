"""TRIC: Ternary Rectangular Index of Certificates, research prototype.

Pure Python executable demonstration. Not a production implementation.
"""
from collections import deque
from dataclasses import dataclass
import argparse, json, random, statistics, sys, time, platform


def build_graph(n, edges):
    adj=[[] for _ in range(n)]; rev=[[] for _ in range(n)]
    for u,v in sorted(set(edges)):
        if u==v: continue
        adj[u].append(v);rev[v].append(u)
    return adj,rev


def reach_mask(graph,start):
    visited=1<<start; stack=[start]; traversals=0
    while stack:
        u=stack.pop()
        for v in graph[u]:
            traversals += 1
            if not (visited>>v)&1:
                visited |= 1<<v;stack.append(v)
    return visited,traversals


def early_reachable(graph,s,t):
    if s==t:return True,0
    visited=1<<s;stack=[s];traversals=0
    while stack:
        u=stack.pop()
        for v in graph[u]:
            traversals+=1
            if v==t: return True,traversals
            if not (visited>>v)&1:
                visited |= 1<<v;stack.append(v)
    return False,traversals


@dataclass(frozen=True)
class Pivot:
    vertex:int
    forward:int
    backward:int
    build_edges:int


def make_pivot(adj,rev,v):
    f,e1=reach_mask(adj,v); b,e2=reach_mask(rev,v)
    return Pivot(v,f,b,e1+e2)


def certify(p,s,t,mode='all'):
    f=p.forward;b=p.backward
    fs=bool((f>>s)&1);ft=bool((f>>t)&1)
    bs=bool((b>>s)&1);bt=bool((b>>t)&1)
    if mode in ('all','positive') and bs and ft: return True
    if mode in ('all','negative') and ((fs and not ft) or (bt and not bs)): return False
    return None


def selected_certify(pivots,s,t,mode='all'):
    for p in pivots:
        answer=certify(p,s,t,mode)
        if answer is not None:return answer
    return None


def mask_covered(p,queries,mode='all'):
    ans=0
    for i,(s,t) in enumerate(queries):
        if certify(p,s,t,mode) is not None: ans|=1<<i
    return ans


def choose_greedy(candidates,queries,k,mode='all',weights=None):
    masks=[mask_covered(p,queries,mode) for p in candidates]
    chosen=[];have=0;rem=set(range(len(candidates)))
    def uncovered_value(i):
        new=masks[i] & ~have
        if weights is None:return new.bit_count()
        score=0
        while new:
            bit=new & -new
            score+=weights[bit.bit_length()-1]
            new-=bit
        return score
    for _ in range(min(k,len(candidates))):
        best=max(rem,key=lambda i:(uncovered_value(i),-candidates[i].vertex))
        chosen.append(candidates[best]);have|=masks[best];rem.remove(best)
    return chosen



def choose_path_optimal(n,queries,k,weights=None):
    """Globally optimal k pivots for directed path reachability under a finite query workload.

    Assumes reachability(s,t) iff s<=t. Under arbitrary forward shortcuts
    this remains valid as long as the base Hamiltonian path exists and there
    are no backward edges.
    """
    if k<0 or k>n:raise ValueError('invalid pivot budget')
    if weights is None: weights=[1]*len(queries)
    counts=[[0]*(n+1) for _ in range(n+1)]
    for (s,t),w in zip(queries,weights):
        counts[s+1][t+1]+=w
    prefix=[[0]*(n+1) for _ in range(n+1)]
    for i in range(1,n+1):
        for j in range(1,n+1):
            prefix[i][j]=counts[i][j]+prefix[i-1][j]+prefix[i][j-1]-prefix[i-1][j-1]
    def gap(l,r):
        if l>r:return 0
        a=r+1;b=l
        return prefix[a][a]-prefix[b][a]-prefix[a][b]+prefix[b][b]
    if k==0:return [],gap(0,n-1)
    inf=10**100
    dp=[[inf]*n for _ in range(k+1)]
    parent=[[-1]*n for _ in range(k+1)]
    for j in range(n):dp[1][j]=gap(0,j-1)
    for r in range(2,k+1):
        for j in range(r-1,n):
            dp[r][j],parent[r][j]=min((dp[r-1][i]+gap(i+1,j-1),i) for i in range(r-2,j))
    bestlast=min(range(k-1,n),key=lambda j:(dp[k][j]+gap(j+1,n-1),j))
    min_uncertified=dp[k][bestlast]+gap(bestlast+1,n-1)
    positions=[];last=bestlast
    for r in range(k,0,-1):
        positions.append(last);last=parent[r][last]
    positions.reverse()
    return positions,min_uncertified

def graph_family(kind,n,seed):
    rng=random.Random(seed); edges=[]
    if kind=='dag':
        edges=[(u,v) for u in range(n) for v in range(u+1,n) if rng.random()<0.019]
    elif kind=='chain':
        edges=[(u,u+1) for u in range(n-1)]
        edges += [(u,v) for u in range(n) for v in range(u+2,n) if rng.random()<0.006]
    elif kind=='blocks':
        block=40
        edges=[(u,v) for u in range(n) for v in range(u+1,min(n,((u//block)+1)*block)) if rng.random()<0.065]
    elif kind=='communities':
        block=40
        for u in range(n):
            for v in range(n):
                if u==v:continue
                bu=u//block;bv=v//block
                if bu==bv and rng.random()<0.07:edges.append((u,v))
                elif bv==bu+1 and rng.random()<0.003:edges.append((u,v))
    else:raise ValueError(kind)
    return build_graph(n,edges)


def make_queries(n,num,seed,distribution):
    r=random.Random(seed)
    hot_src=[r.randrange(n) for _ in range(10)]
    hot_tgt=[r.randrange(n) for _ in range(10)]
    out=[]
    for _ in range(num):
        if distribution=='hot' and r.random()<0.8:
            s=r.choice(hot_src);t=r.choice(hot_tgt)
        else:
            s=r.randrange(n);t=r.randrange(n)
        out.append((s,t))
    return out


def candidates_for(adj,rev,train,limit,seed):
    r=random.Random(seed);n=len(adj)
    weighted=sorted(range(n),key=lambda i:-(len(adj[i])+len(rev[i])))
    src_tgt=[q[j] for q in train[:min(180,len(train))] for j in (0,1)]
    pool=list(dict.fromkeys(weighted[:limit//3]+src_tgt+r.sample(range(n),n)))
    return [make_pivot(adj,rev,v) for v in pool[:limit]]


def eval_mode(adj,selected,test,mode='all'):
    hits=0;pos=0;neg=0;mis=0;fallback_edges=0;baseline_edges=0
    for s,t in test:
        known=selected_certify(selected,s,t,mode)
        actual,be=early_reachable(adj,s,t)
        baseline_edges+=be
        if known is not None:
            if known!=actual:mis+=1
            hits+=1; pos+=(known is True);neg+=(known is False)
        else:
            fallback_edges+=be
    return dict(hit_rate=round(hits/len(test),4),positive_hits=pos,negative_hits=neg,
                errors=mis,baseline_edges=baseline_edges,fallback_edges=fallback_edges,
                avoided_edge_scans=round(1-fallback_edges/max(1,baseline_edges),4),
                certificate_checks=len(test)*len(selected))


def exhaustive(n=4):
    all_possible=[(u,v) for u in range(n) for v in range(n) if u!=v]
    cases=0;comparisons=0
    for bits in range(1<<len(all_possible)):
        edges=[e for i,e in enumerate(all_possible) if (bits>>i)&1]
        adj,rev=build_graph(n,edges)
        ps=[make_pivot(adj,rev,p) for p in range(n)]
        for p in ps:
            for s in range(n):
                for t in range(n):
                    a=certify(p,s,t)
                    if a is not None:
                        truth,_=early_reachable(adj,s,t)
                        if a!=truth:
                            raise AssertionError((bits,p.vertex,s,t,a,truth))
                    comparisons+=1
        cases+=1
    return dict(graphs=cases,pivot_query_triples=comparisons,errors=0)


def run(seed=20261021,n=240,train_size=2000,test_size=5000,k=8,C=48):
    results=[]
    for fam in ['dag','chain','blocks','communities']:
        adj,rev=graph_family(fam,n,seed+len(fam))
        m=sum(map(len,adj))
        for dist in ['uniform','hot']:
            train=make_queries(n,train_size,seed+11,dist)
            test=make_queries(n,test_size,seed+999,dist)
            # Fix hot training/test support overlap while keeping independent samples:
            # queries use different RNG draws but a shared list of hot endpoints.
            if dist=='hot':
                hotseed=seed+101
                r=random.Random(hotseed);sources=[r.randrange(n) for _ in range(10)];targets=[r.randrange(n) for _ in range(10)]
                def sample(num,drawseed):
                    rr=random.Random(drawseed);out=[]
                    for _ in range(num):
                        if rr.random()<0.8:out.append((rr.choice(sources),rr.choice(targets)))
                        else:out.append((rr.randrange(n),rr.randrange(n)))
                    return out
                train=sample(train_size,seed+5);test=sample(test_size,seed+6)
            pool=candidates_for(adj,rev,train,C,seed+13)
            rr=random.Random(seed+int(m)+33)
            weights=[early_reachable(adj,s,t)[1] for s,t in train]
            configs={
                'random_all':(rr.sample(pool,k),'all'),
                'degree_all':(sorted(pool,key=lambda p:-(len(adj[p.vertex])+len(rev[p.vertex])))[:k],'all'),
                'greedy_all':(choose_greedy(pool,train,k,'all'),'all'),
                'weighted_greedy':(choose_greedy(pool,train,k,'all',weights),'all'),
                'greedy_positive':(choose_greedy(pool,train,k,'positive'),'positive'),
                'greedy_negative':(choose_greedy(pool,train,k,'negative'),'negative'),
            }
            if fam=='chain':
                verts,_=choose_path_optimal(n,train,k)
                verts_weighted,_=choose_path_optimal(n,train,k,weights)
                configs['path_dp'] = ([make_pivot(adj,rev,v) for v in verts], 'all')
                configs['path_dp_weighted'] = ([make_pivot(adj,rev,v) for v in verts_weighted], 'all')
            for name,(picked,mode) in configs.items():
                ev=eval_mode(adj,picked,test,mode)
                ev.update(family=fam,distribution=dist,n=n,m=m,method=name, pivots=[p.vertex for p in picked],
                          build_edges=sum(p.build_edges for p in picked),candidate_build_edges=sum(p.build_edges for p in pool),training_edge_scans=sum(weights))
                results.append(ev)
    return results


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--n',type=int,default=240);ap.add_argument('--test',type=int,default=5000)
    ap.add_argument('--train',type=int,default=2000);ap.add_argument('--seed',type=int,default=20261021)
    ap.add_argument('--k',type=int,default=8);ap.add_argument('--candidates',type=int,default=48)
    ap.add_argument('--output',default='results.json');args=ap.parse_args()
    assert 0<args.k<=args.candidates<=args.n
    start=time.perf_counter()
    verified=exhaustive(4)
    results=run(args.seed,args.n,args.train,args.test,args.k,args.candidates)
    output={'verification':verified,'config':vars(args),'runtime_info':{'python':sys.version,'platform':platform.platform()},
            'wall_seconds':round(time.perf_counter()-start,3),'results':results}
    with open(args.output,'w') as f:json.dump(output,f,indent=2)
    print(json.dumps({'verification':verified,'elapsed':output['wall_seconds'],'summary':[
        {'family':x['family'],'distribution':x['distribution'],'method':x['method'],
         'hit_rate':x['hit_rate'],'edge_scans_avoided':x['avoided_edge_scans']}
         for x in results]},indent=2))

if __name__=='__main__':main()

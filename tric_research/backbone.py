"""Exact certificate characterization and optimization on a directed backbone.

Given a directed graph containing a specified simple directed path (backbone),
select exactly k backbone pivots maximizing nonnegative-weight query coverage.
The algorithm is fixed-parameter tractable in the number of distinct 2-interval
signatures induced by the query workload. It does not claim to solve unrestricted
reachability indexing or to be globally novel.
"""
from collections import defaultdict
from itertools import product
from tric import make_pivot, certify, reach_mask
from path_sweep import choose_path_sweep


def backbone_intervals(adj, rev, backbone, queries):
    """Return ordered discrete 1- or 2-interval cover sets per query.

    Each [l,r] is inclusive in BACKBONE POSITIONS, not vertex IDs.
    Requires (backbone[i],backbone[i+1]) an edge of G, and distinct vertices.
    """
    n=len(adj);h=len(backbone)
    if len(rev)!=n or any(not(0<=p<n) for p in backbone):
        raise ValueError('invalid graph/backbone')
    if len(set(backbone))!=h:
        raise ValueError('backbone repeated vertices')
    if any(backbone[i+1] not in adj[backbone[i]] for i in range(h-1)):
        raise ValueError('backbone is not a directed path')
    if not h and queries: raise ValueError('empty backbone with queries')
    # L[v]: last backbone pivot reaching v; R[v]: first pivot reachable from v.
    L=[-1]*n;R=[h]*n
    for idx,p in enumerate(backbone):
        fw,_=reach_mask(adj,p)
        bw,_=reach_mask(rev,p)
        for v in range(n):
            if (fw>>v)&1: L[v]=idx
            if (bw>>v)&1 and R[v]==h:R[v]=idx
    answers=[]
    for s,t in queries:
        if not (0<=s<n and 0<=t<n):raise ValueError('bad query')
        raw=[(R[s],L[t]), (L[t]+1,L[s]), (R[t],R[s]-1)]
        # Every raw interval is either a positive or a negative certificate.
        valid=sorted((max(0,a),min(h-1,b)) for a,b in raw if max(0,a)<=min(h-1,b))
        merged=[]
        for a,b in valid:
            if merged and a<=merged[-1][1]+1:
                merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else: merged.append((a,b))
        if len(merged)>2:
            raise AssertionError(('unexpected >2 intervals',s,t,merged))
        answers.append(tuple(merged))
    return answers


def backbone_intervals_fast(adj, rev, backbone, queries):
    """Exact intervals in O(V+E+|Q|) time on a DAG with a directed backbone.

    Compute last backbone ancestor L and first backbone descendant R using
    max-propagation on a topological order and min-propagation in reverse.
    For reference checking use backbone_intervals (BFS from each pivot).
    """
    from collections import deque
    n=len(adj);h=len(backbone)
    if len(rev)!=n or len(set(backbone))!=h or any(not(0<=p<n) for p in backbone):
        raise ValueError('bad backbone')
    if any(backbone[i+1] not in adj[backbone[i]] for i in range(h-1)):
        raise ValueError('backbone is not a directed path')
    if not h and queries:raise ValueError('empty backbone with queries')
    indeg=[0]*n
    for v in range(n):
        for t in adj[v]:indeg[t]+=1
    ready=deque(i for i,d in enumerate(indeg) if d==0)
    order=[]
    while ready:
        v=ready.popleft();order.append(v)
        for t in adj[v]:
            indeg[t]-=1
            if indeg[t]==0:ready.append(t)
    if len(order)!=n:raise ValueError('fast method requires DAG')
    L=[-1]*n;R=[h]*n
    for i,v in enumerate(backbone):L[v]=i;R[v]=i
    for v in order:
        for t in adj[v]:
            if L[v]>L[t]:L[t]=L[v]
    for v in reversed(order):
        for t in adj[v]:
            if R[t]<R[v]:R[v]=R[t]
    out=[]
    for s,t in queries:
        if not (0<=s<n and 0<=t<n):raise ValueError('bad query')
        candidates=[(R[s],L[t]),(L[t]+1,L[s]),(R[t],R[s]-1)]
        valid=sorted((max(0,a),min(h-1,b)) for a,b in candidates if max(0,a)<=min(h-1,b))
        merged=[]
        for a,b in valid:
            if merged and a<=merged[-1][1]+1:
                merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:merged.append((a,b))
        if len(merged)>2:raise AssertionError('certificate interval violation')
        out.append(tuple(merged))
    return out


def optimize_intervals(n, intervals, weights, k):
    """Exact solution by orienting only disconnected certificate intervals.

    For each query covered by two separate intervals A|B, assign that query to
    exactly one of A,B. The best orientation and k-pivot set attains the exact
    union-coverage optimum. Identical signatures are aggregated before branching.

    Complexity O(2^r * k*(n+q)*log(n)) (r unique two-piece signatures), in
    addition to a linear-in-q aggregation per branch. Appropriate only for small r.
    """
    if n<0 or not(0<=k<=n) or len(intervals)!=len(weights):
        raise ValueError('invalid optimizer input')
    if any(w<0 for w in weights):raise ValueError('negative workload weight')
    groups=defaultdict(int)
    zero=0
    for ivs,w in zip(intervals,weights):
        for a,b in ivs:
            if not(0<=a<=b<n):raise ValueError('invalid interval')
        if len(ivs)>2:raise ValueError('need at most two intervals')
        if w==0:continue
        if not ivs:
            zero+=w
        else:groups[tuple(ivs)]+=w
    simple=[(sig[0],w) for sig,w in groups.items() if len(sig)==1]
    double=[(sig,w) for sig,w in groups.items() if len(sig)==2]
    # k=0: everything uncovered; no need to orient.
    if k==0:return [],sum(weights),len(double)
    best_value=float('inf');best_pivots=None
    for bits in product((0,1),repeat=len(double)):
        converted=list(simple)
        converted.extend((signature[bit],w) for (signature,w),bit in zip(double,bits))
        queries=[iv for iv,w in converted]
        ws=[w for iv,w in converted]
        pivots,uncov=choose_path_sweep(n,queries,k,ws)
        objective=zero+uncov
        if objective<best_value or (objective==best_value and (best_pivots is None or pivots<best_pivots)):
            best_value=objective;best_pivots=pivots
    return best_pivots,best_value,len(double)


def optimize_backbone(adj,rev,backbone,queries,weights,k):
    intervals=backbone_intervals_fast(adj,rev,backbone,queries)
    positions,uncov,r=optimize_intervals(len(backbone),intervals,weights,k)
    return [backbone[i] for i in positions],uncov,r


def greedy_intervals(n,intervals,weights,k):
    """Fair max-weight marginal-coverage baseline, operating on cached intervals."""
    if n<0 or not (0<=k<=n) or len(intervals)!=len(weights):
        raise ValueError('invalid greedy inputs')
    remaining=set(range(n));chosen=[]
    covered=[False]*len(intervals)
    for _ in range(k):
        p=max(sorted(remaining),key=lambda i:sum(w for ivs,w,c in zip(intervals,weights,covered)
                                            if not c and any(a<=i<=b for a,b in ivs)))
        chosen.append(p);remaining.remove(p)
        for j,ivs in enumerate(intervals):
            if any(a<=p<=b for a,b in ivs):covered[j]=True
    return chosen,sum(w for w,c in zip(weights,covered) if not c)


def greedy_backbone(adj,rev,backbone,queries,weights,k):
    intervals=backbone_intervals_fast(adj,rev,backbone,queries)
    positions,uncovered=greedy_intervals(len(backbone),intervals,weights,k)
    return [backbone[p] for p in positions],uncovered


def verify_intervals(adj,rev,backbone,queries):
    ivs=backbone_intervals(adj,rev,backbone,queries)
    for q,regions in zip(queries,ivs):
        for i,p in enumerate(backbone):
            membership=any(a<=i<=b for a,b in regions)
            truth=certify(make_pivot(adj,rev,p),*q) is not None
            if membership!=truth:raise AssertionError((q,i,regions,truth))
    return len(queries)*len(backbone)

"""Fresh synthetic distribution checks; deterministic, graph-only, BFS sampled.

Not real-world datasets or independent hardware replication. Generate only after
candidate selection; do not tune against these qualification inputs.
"""
import argparse
import gzip
import hashlib
import json
import random
from collections import OrderedDict
from pathlib import Path
from benchmark_native_changes import payload


def prepare(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for shape in ('fragmented','shared_hubs','scc_aliases','cross_chains'):
        seed=30001+('fragmented','shared_hubs','scc_aliases','cross_chains').index(shape)
        rng=random.Random(seed);n=6000;g=[[] for _ in range(n)]
        if shape in ('fragmented','scc_aliases'):
            g[0]=list(range(1,n))
            for u in range(1,1500):g[u]=sorted(rng.sample(range(1500,n),rng.randrange(2,13)))
        elif shape=='shared_hubs':
            for u in range(2000):g[u]=sorted(rng.sample(range(2000,4000),4))
            for u in range(2000,4000):g[u]=sorted(rng.sample(range(4000,6000),12))
        else:
            for u in range(n):
                if u%750<749:g[u].append(u+1)
                if u<5250 and u%29==0:g[u].append(u+750)
        if shape=='scc_aliases':
            expanded=[[] for _ in range(2*n)]
            for u,row in enumerate(g):
                expanded[2*u]=[2*u+1]+[2*v for v in row]
                expanded[2*u+1]=[2*u]
            g=expanded;n=len(g)
        perm=list(range(n));rng.shuffle(perm)
        adj=[[] for _ in range(n)]
        for u,row in enumerate(g):adj[perm[u]]=[perm[v] for v in row]
        arcs=[[u,v] for u,row in enumerate(adj) for v in row]
        cache=OrderedDict()
        def reachable(s):
            if s in cache:cache.move_to_end(s);return cache[s]
            seen=bytearray(n);seen[s]=1;work=[s]
            for u in work:
                for v in adj[u]:
                    if not seen[v]:seen[v]=1;work.append(v)
            cache[s]=(seen,work)
            if len(cache)>32:cache.popitem(last=False)
            return seen,work
        positive_sources=[u for u,row in enumerate(adj) if any(v!=u for v in row)]
        cases=[];count=2048
        for stratum in ('uniform','positive','negative','balanced'):
            q=[]
            for i in range(count):
                if stratum=='uniform':s,t=rng.randrange(n),rng.randrange(n)
                elif stratum=='positive' or (stratum=='balanced' and i%2==0):
                    s=rng.choice(positive_sources);_,work=reachable(s);t=rng.choice(work[1:])
                else:
                    while True:
                        s=rng.randrange(n);seen,work=reachable(s)
                        if len(work)<n:break
                    t=rng.randrange(n)
                    while seen[t]:t=rng.randrange(n)
                q.append([s,t])
            rng.shuffle(q);cases.append({'seed':seed,'stratum':stratum,'queries':q})
        fixture={'dataset':'phase30_'+shape,'graph':{'vertices':n,'arcs':arcs},'cases':cases,
                 'sampling':'Fixed synthetic graph seed; random relabeling; uniform endpoints or BFS-conditioned source then target; 2048 pairs per stratum. Frozen after candidate selection.'}
        for case in cases:case['native_input_sha256']=hashlib.sha256(payload(fixture,case)).hexdigest()
        dest=output/(fixture['dataset']+'.json.gz')
        if dest.exists():raise ValueError('refuse overwrite')
        dest.write_bytes(gzip.compress(json.dumps(fixture,separators=(',',':')).encode(),mtime=0))
        print(f'{shape}: {n} vertices, {len(arcs)} arcs',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);prepare(p.parse_args().output)

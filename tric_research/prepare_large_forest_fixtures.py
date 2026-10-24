"""Freeze author-published large graphs and independent source-weighted BFS pairs."""
import argparse
import gzip
import hashlib
import json
import random
from collections import OrderedDict
from pathlib import Path
from benchmark_native_changes import payload

SOURCES={
    'citeseer.scc.gra.gz':('large_citeseer', '4565ba10ff71a99c217ce986f387428b73e46dd5'),
    'uniprotenc_22m.scc.gra.gz':('large_uniprot_22m','d6effc0bf7fde29dafcef069a8ebb4156e2f58e2'),
}

def prepare(source,output,count=64,seed=20261028,uniform_only=False):
    source=Path(source);dataset,expected=SOURCES[source.name]
    raw=source.read_bytes()
    blob=hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()
    if blob!=expected:raise ValueError('author archive Git blob mismatch')
    with gzip.open(source,'rt') as stream:
        if next(stream).strip()!='graph_for_greach':raise ValueError('graph format')
        n=int(next(stream));adj=[[] for _ in range(n)];arcs=[];rows=0
        for line in stream:
            key,values=line.split(':');u=int(key)
            if u!=rows:raise ValueError('noncanonical vertex row order')
            rows+=1
            for item in values.strip().removesuffix('#').split():
                v=int(item)
                if not 0<=v<n:raise ValueError('invalid endpoint')
                adj[u].append(v);arcs.append([u,v])
        if rows!=n:raise ValueError('missing graph rows')
    positive_sources=[u for u,row in enumerate(adj) if any(v!=u for v in row)]
    cache=OrderedDict()
    def reachable(s):
        if s in cache:cache.move_to_end(s);return cache[s]
        flags=bytearray(n);flags[s]=1;work=[s]
        for u in work:
            for v in adj[u]:
                if not flags[v]:flags[v]=1;work.append(v)
        cache[s]=(flags,work)
        if len(cache)>32:cache.popitem(last=False)
        return flags,work
    cases=[]
    for stratum in (('uniform',) if uniform_only else ('uniform','positive','negative','balanced')):
        rng=random.Random(seed+('uniform','positive','negative','balanced').index(stratum))
        if stratum=='uniform':queries=[[rng.randrange(n),rng.randrange(n)] for _ in range(count)]
        else:
            wanted=[True]*count if stratum=='positive' else [False]*count
            if stratum=='balanced':wanted=[True]*(count//2)+[False]*(count-count//2);rng.shuffle(wanted)
            queries=[]
            for truth in wanted:
                if truth:
                    s=rng.choice(positive_sources);flags,work=reachable(s)
                    t=work[rng.randrange(1,len(work))]
                else:
                    while True:
                        s=rng.randrange(n);flags,work=reachable(s)
                        if len(work)<n:break
                    if len(work)>n//2:
                        t=rng.choice([v for v in range(n) if not flags[v]])
                    else:
                        t=rng.randrange(n)
                        while flags[t]:t=rng.randrange(n)
                queries.append([s,t])
        cases.append({'seed':seed,'stratum':stratum,'queries':queries})
    fixture={'dataset':dataset,'graph':{'vertices':n,'arcs':arcs},'cases':cases,
             'source':{'repository':'https://github.com/zakimjz/grail',
                       'commit':'c13a7364fbc185841fc6277cd295acf33a7188f0',
                       'path':'Downloads/'+source.name,'git_blob':blob,
                       'compressed_sha256':hashlib.sha256(raw).hexdigest(),
                       'semantics':'Authors supplied SCC-condensed graph; original vertex aliases already removed. Raw vertex IDs, arc order and duplicate arcs preserved.'},
             'sampling':'uniform: independent vertex endpoints; other strata: source uniform conditioned on eligible non-self target, then target uniform within that source BFS class. Positive sources selected by non-self outgoing arcs. Negative targets use rejection sampling. No index consulted.'}
    for case in cases:case['native_input_sha256']=hashlib.sha256(payload(fixture,case)).hexdigest()
    output=Path(output);output.mkdir(parents=True,exist_ok=True);dest=output/(dataset+'.json.gz')
    if dest.exists():raise ValueError('refuse overwrite of frozen fixture')
    dest.write_bytes(gzip.compress(json.dumps(fixture,separators=(',',':')).encode(),mtime=0))
    print(json.dumps({'fixture':str(dest),'vertices':n,'arcs':len(arcs),'queries_per_stratum':count,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('sources',nargs='+');p.add_argument('--output',required=True);p.add_argument('--count',type=int,default=64);p.add_argument('--seed',type=int,default=20261028);p.add_argument('--uniform-only',action='store_true');args=p.parse_args()
    if args.count<1:raise ValueError('positive query count required')
    for path in args.sources:prepare(path,args.output,args.count,args.seed,args.uniform_only)

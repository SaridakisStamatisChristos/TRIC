"""Canonical SCC condensation for DAG-only reachability competitor input.

Source graph and queries remain frozen; every original source/target pair is
mapped to SCC IDs. Reachability is exactly preserved, including s==t and
different vertices of the same SCC. This adapter is distinct from the
unchanged original O-Reach comparator and its conversion overhead is recorded.
"""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from benchmark_oreach_ci import read_metis
from tric import early_reachable

def condensation(adj):
    n=len(adj)
    if not n or any(v<0 or v>=n for row in adj for v in row):
        raise ValueError("invalid graph")
    reverse=[[] for _ in range(n)]
    for u,vs in enumerate(adj):
        for v in vs:reverse[v].append(u)
    seen=bytearray(n)
    finish=[]
    for root in range(n):
        if seen[root]: continue
        seen[root]=1
        stack=[(root,0)]
        while stack:
            u,i=stack[-1]
            if i<len(adj[u]):
                v=adj[u][i]
                stack[-1]=(u,i+1)
                if not seen[v]:
                    seen[v]=1
                    stack.append((v,0))
            else:
                finish.append(u)
                stack.pop()
    component=[-1]*n
    sizes=[]
    for root in reversed(finish):
        if component[root]!=-1:continue
        cid=len(sizes)
        todo=[root]
        component[root]=cid
        count=0
        while todo:
            u=todo.pop()
            count+=1
            for v in reverse[u]:
                if component[v]==-1:
                    component[v]=cid
                    todo.append(v)
        sizes.append(count)
    out=[set() for _ in sizes]
    for u,vs in enumerate(adj):
        cu=component[u]
        for v in vs:
            cv=component[v]
            if cu!=cv:out[cu].add(cv)
    dag=[sorted(row) for row in out]
    indeg=[0]*len(dag)
    for row in dag:
        for v in row:indeg[v]+=1
    queue=[u for u in range(len(dag)) if indeg[u]==0]
    i=0
    while i<len(queue):
        u=queue[i];i+=1
        for v in dag[u]:
            indeg[v]-=1
            if indeg[v]==0:queue.append(v)
    if len(queue)!=len(dag):
        raise AssertionError("SCC condensation contains a cycle")
    return dag,component,sizes

def metis_dump(path,adj):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="ascii",newline="\n") as fp:
        fp.write(f"{len(adj)} {sum(len(row) for row in adj)}\n")
        for row in adj:
            fp.write(" ".join(str(x+1) for x in row)+"\n")
    roundtrip,_=read_metis(path)
    if adj!=roundtrip:
        raise AssertionError("condensed directed METIS roundtrip differs")
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare(source_graph,output_dir):
    start=time.perf_counter_ns()
    source_graph=Path(source_graph)
    original,_=read_metis(source_graph)
    dag,component,sizes=condensation(original)
    path=Path(output_dir)
    path.mkdir(parents=True,exist_ok=True)
    graph=path/"condensed.metis"
    condensed_sha=metis_dump(graph,dag)
    elapsed=time.perf_counter_ns()-start
    record={
        "source_graph_sha256":hashlib.sha256(source_graph.read_bytes()).hexdigest(),
        "condensed_graph_sha256":condensed_sha,
        "source_nodes":len(original),
        "source_edges":sum(map(len,original)),
        "scc_nodes":len(dag),
        "scc_edges":sum(map(len,dag)),
        "nontrivial_scc_count":sum(x>1 for x in sizes),
        "largest_scc":max(sizes),
        "converted_before_queries":True,
        "conversion_total_ns_including_graph_read_write":elapsed,
        "competitor_semantics":"Patched O-Reach on SCC-condensed DAG, not original unmodified O-Reach"
    }
    (path/"component_ids.json").write_text(json.dumps(component)+"\n")
    (path/"provenance.json").write_text(json.dumps(record,indent=2)+"\n")
    return graph,component,record

def remap_queries(original_queryfile,output,dag,component,require_oracle=True):
    source=Path(original_queryfile).read_bytes()
    digest=hashlib.sha256(source).hexdigest()
    pairs=[]
    with Path(output).open("w",encoding="ascii",newline="\n") as fp:
        for line in source.splitlines():
            bits=line.split()
            if len(bits)!=3:raise ValueError("bad original query file")
            s,t,ans=map(int,bits)
            if s<0 or s>=len(component) or t<0 or t>=len(component) or ans not in (0,1):
                raise ValueError("invalid original query")
            cs,ct=component[s],component[t]
            if require_oracle and bool(early_reachable(dag,cs,ct)[0]) != bool(ans):
                raise AssertionError("SCC query remapping changed independent BFS truth")
            fp.write(f"{cs} {ct} {ans}\n")
            pairs.append((cs,ct,ans))
    if not pairs: raise ValueError("empty query set")
    return {
        "original_query_sha256":digest,
        "condensed_query_sha256":hashlib.sha256(Path(output).read_bytes()).hexdigest(),
        "verified_original_ground_truth_matches_condensed_dag":require_oracle,
        "query_count":len(pairs),"positive_count":sum(ans for _,_,ans in pairs)
    }

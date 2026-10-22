"""Exact reachability-equivalent input for pinned original O-Reach.

Original O-Reach expects DAGs; its default support sampler is invalid when
there are too few candidates in disjoint small components. For generated
families only, run original unmodified pinned binary with --support 0 and
SCC-condense cycles. Equivalent query mapping must be checked against BFS.
"""
from __future__ import annotations
import hashlib
import json
import time
from collections import deque
from pathlib import Path
from benchmark_oreach_ci import read_metis
from tric import early_reachable

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def scc_quotient(adj):
    n=len(adj)
    if n<1:raise ValueError("empty graph")
    reverse=[[] for _ in range(n)]
    for row in adj:
        for v in row:
            if v<0 or v>=n:raise ValueError("invalid directed arc")
    for u,row in enumerate(adj):
        for v in row:reverse[v].append(u)
    visited=bytearray(n)
    order=[]
    for source in range(n):
        if visited[source]:continue
        visited[source]=1
        stack=[(source,0)]
        while stack:
            node,j=stack[-1]
            if j<len(adj[node]):
                vertex=adj[node][j]
                stack[-1]=(node,j+1)
                if not visited[vertex]:
                    visited[vertex]=1
                    stack.append((vertex,0))
            else:
                order.append(node);stack.pop()
    comp=[-1]*n
    sizes=[]
    for source in reversed(order):
        if comp[source]!=-1:continue
        identifier=len(sizes)
        sizes.append(0);stack=[source];comp[source]=identifier
        while stack:
            node=stack.pop();sizes[identifier]+=1
            for v in reverse[node]:
                if comp[v]==-1:
                    comp[v]=identifier;stack.append(v)
    quotient=[set() for _ in sizes]
    for u,row in enumerate(adj):
        for v in row:
            if comp[u]!=comp[v]:quotient[comp[u]].add(comp[v])
    graph=[sorted(row) for row in quotient]
    indeg=[0]*len(graph)
    for row in graph:
        for v in row:indeg[v]+=1
    pending=deque(u for u,d in enumerate(indeg) if d==0)
    seen=0
    while pending:
        u=pending.popleft();seen+=1
        for v in graph[u]:
            indeg[v]-=1
            if indeg[v]==0:pending.append(v)
    if seen!=len(graph):raise AssertionError("SCC quotient is cyclic")
    if len(sizes)!=len(graph) or sum(sizes)!=n:
        raise AssertionError("component assignment incomplete")
    return graph,comp,sizes

def write_graph(path,adj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="ascii",newline="\n") as f:
        f.write(f"{len(adj)} {sum(map(len,adj))}\n")
        for row in adj:f.write(" ".join(str(v+1) for v in row)+"\n")
    parsed,_=read_metis(path)
    if parsed!=adj:raise AssertionError("O-Reach METIS graph roundtrip mismatch")

def prepare_comparator(adj,original_graph,dataset,dest):
    if dataset not in ("generated_dag","generated_blocks","generated_communities"):
        raise ValueError("compatible comparator only for explicitly generated graph families")
    t0=time.perf_counter_ns()
    dag,mapping,sizes=scc_quotient(adj)
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
    graph=dest/"semantically_equivalent_scc_dag.metis"
    write_graph(graph,dag)
    assignment=dest/"vertex_to_scc.json"
    assignment.write_text(json.dumps(mapping,separators=(",",":"))+"\n")
    preprocess_ns=time.perf_counter_ns()-t0
    meta={
        "mode":"original_pinned_binary_support0_scc_quotient",
        "upstream_support_parameter":0,
        "original_graph_sha256":digest(original_graph),
        "comparator_graph_sha256":digest(graph),
        "mapping_sha256":digest(assignment),
        "original_nodes":len(adj),
        "comparator_scc_nodes":len(dag),
        "comparator_arcs":sum(map(len,dag)),
        "nontrivial_scc":sum(s>1 for s in sizes),
        "largest_scc":max(sizes),
        "scc_preprocess_ns_excluded_from_upstream_process":preprocess_ns,
        "preprocess_memory_peak":"not isolated",
        "claim_boundary":"Original pinned binary with support=0 and quotient DAG, unlike default authentic O-Reach; equivalent queries independently checked; preprocessing outside upstream process wall"
    }
    (dest/"comparator_provenance.json").write_text(json.dumps(meta,indent=2)+"\n")
    return graph,dag,mapping,meta

def remap_queryfile(source_file,dest_file,original_adj,quotient,mapping):
    source_file=Path(source_file);dest_file=Path(dest_file)
    if dest_file.resolve()==source_file.resolve():
        raise ValueError("must preserve original query file")
    lines=source_file.read_text().splitlines()
    n=len(original_adj)
    if not lines:raise ValueError("no query records")
    positives=0;translated=[]
    for line in lines:
        fields=line.split()
        if len(fields)!=3:raise ValueError("unexpected original query row format")
        s,t,known=map(int,fields)
        if not 0<=s<n or not 0<=t<n or known not in (0,1):
            raise ValueError("invalid query source, target or truth")
        exact=int(bool(early_reachable(original_adj,s,t)[0]))
        transformed=int(bool(early_reachable(quotient,mapping[s],mapping[t])[0]))
        if exact!=known or transformed!=exact:
            raise AssertionError(f"SCC reachability truth changed for ({s},{t})")
        positives+=exact
        translated.append(f"{mapping[s]} {mapping[t]} {exact}\n")
    dest_file.parent.mkdir(parents=True,exist_ok=True)
    dest_file.write_text("".join(translated),encoding="ascii")
    return {"original_query_sha256":digest(source_file),
            "translated_query_sha256":digest(dest_file),
            "original_query_count":len(lines),
            "comparator_query_count":len(translated),
            "equivalence_verified_pairs":len(translated),
            "positive_count":positives}

"""Phase XXIII: input-parity, exact native/legacy pivot training.

The objective and optimal DP remain completely unchanged. Only the
expensive Python per-pivot bitset construction and Python DFS traversal
counts are transferred to equivalent C++17 loops. No heldout data.
"""
from __future__ import annotations
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
from benchmark_hot_source_external import ROOT
from ordered_probe import optimize_ordered,greedy_coverage_order,hit_masks_for_pivots
from tric import make_pivot,early_reachable

def compile_native(directory,compiler="g++",optimization="-O3"):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    exe=out/"phase23_train"
    cmd=[compiler,"-std=c++17",optimization,"-DNDEBUG",
         "-Wall","-Wextra","-Wpedantic",
         str(ROOT/"native_training_phase23.cpp"),"-o",str(exe)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    return exe

def serialize_training(adj,candidates,train):
    n=len(adj); c=len(candidates)
    if n<1 or not 0<=c<=19 or not train or len(train)>100000:
        raise ValueError("bad graph/training shape")
    if any(x<0 or x>=n for x in candidates) or len(set(candidates))!=c:
        raise ValueError("invalid candidate vertices")
    edges=[]
    for u,row in enumerate(adj):
        for v in row:
            if v<0 or v>=n:raise ValueError("invalid graph edge")
            edges.append(f"{u} {v}")
    if any(not (0<=s<n and 0<=t<n) for s,t in train):
        raise ValueError("invalid training-only pair")
    return ("\n".join([f"{n} {len(edges)} {c} {len(train)}",
            *edges, " ".join(map(str,candidates)),
            *(f"{a} {b}" for a,b in train)])+"\n").encode("ascii")

def choose(hit_masks,fallback_costs,c,budget):
    if not 0<=budget<=c:
        raise ValueError("invalid exact DP budget")
    order,cost,info=optimize_ordered(
        hit_masks,[1.0]*len(hit_masks),fallback_costs,
        [1.0]*c,budget)
    greedy=greedy_coverage_order(hit_masks,[1.0]*len(hit_masks),c,budget)
    return order,greedy,cost,info

def native_fit(adj,candidates,train,budget,exe,timeout=300):
    start=time.perf_counter_ns()
    raw=serialize_training(adj,candidates,train)
    serialization_end=time.perf_counter_ns()
    proc=subprocess.run([str(exe)],input=raw,capture_output=True,timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f"native trainer exited {proc.returncode}: {proc.stderr[-1600:]!r}")
    values=json.loads(proc.stdout)
    n=len(adj);c=len(candidates)
    if values["n"]!=n or values["candidates"]!=c or values["train"]!=len(train):
        raise AssertionError("trainer changed input graph, candidate set or training count")
    masks=values["hit_masks"];costs=values["fallback_costs"]
    if len(masks)!=len(train) or len(costs)!=len(train):
        raise AssertionError("missing training-only observations")
    if any(not isinstance(m,int) or m<0 or m>=1<<c for m in masks):
        raise AssertionError("malformed pivot hit bitset")
    if any(not isinstance(x,int) or x<1 for x in costs):
        raise AssertionError("malformed exact fallback edge count")
    order,greedy,cost,info=choose(masks,costs,c,budget)
    finish=time.perf_counter_ns()
    return {"ordered":order,"greedy":greedy,"objective":cost,
            "hit_masks":masks,"fallback_costs":costs,
            "fit_ns":finish-start,
            "serialize_ns":serialization_end-start,
            "input_sha256":hashlib.sha256(raw).hexdigest(),
            "native_metrics":{k:v for k,v in values.items()
                              if k not in ("hit_masks","fallback_costs")},
            "optimizer":info}

def legacy_fit(adj,rev,candidates,train,budget):
    start=time.perf_counter_ns()
    pivots=[make_pivot(adj,rev,v) for v in candidates]
    masks=hit_masks_for_pivots(pivots,train)
    fallback=[1+early_reachable(adj,*q)[1] for q in train]
    order,greedy,cost,info=choose(masks,fallback,len(candidates),budget)
    end=time.perf_counter_ns()
    return {"ordered":order,"greedy":greedy,"objective":cost,
            "hit_masks":masks,"fallback_costs":fallback,
            "fit_ns":end-start,"optimizer":info}

def assert_parity(native,legacy):
    for key in ("ordered","greedy","objective","hit_masks","fallback_costs"):
        if native[key]!=legacy[key]:
            a,b=native[key],legacy[key]
            diff=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),None) if isinstance(a,list) else None
            raise AssertionError(f"native/legacy {key} differ: first index {diff}")
    return True

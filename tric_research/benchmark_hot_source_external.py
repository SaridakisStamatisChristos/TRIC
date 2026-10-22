"""Phase XX: same-file native hot-source/TRIC/O'Reach benchmark.

Experimental research harness; NOT a matched-index-memory or SOTA proof.
All three systems receive the identical heldout file for each class.
The chosen hot sources, cache rows and pivot order depend on graph topology
and separately sampled train-only pairs, never on heldout labels.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

from benchmark_oreach_ci import read_metis, write_queryfile, parse_oreach_csv
from benchmark_native import build_executable, serialize_native
from benchmark_hot_source_cache import native_input
from ordered_probe import greedy_coverage_order, hit_masks_for_pivots, optimize_ordered
from tric import make_pivot, early_reachable

ROOT=Path(__file__).resolve().parent
CLASSES=("matched_hot", "uniform", "shifted_hot")
OREACH_SHA="78b3e326bbb021b7ee225ab605a4cdd074fa1d93"

def sample_pairs(n, count, seed, hot=(), probability=0.8):
    if not (n>0 and count>0 and 0<=probability<=1):
        raise ValueError("bad workload shape")
    if any(s<0 or s>=n for s in hot):
        raise ValueError("hot source outside graph")
    rng=random.Random(seed)
    return [(rng.choice(hot) if hot and rng.random()<probability
             else rng.randrange(n), rng.randrange(n)) for _ in range(count)]

def workload_sets(adj, seed, train_count, test_count, hot_count):
    n=len(adj)
    if not (n>=2*hot_count and hot_count>0 and train_count>0 and test_count>0):
        raise ValueError("invalid hot-source workload configuration")
    # Choose a fixed deterministic high-outdegree rank as realistic potential
    # hot sources; withheld/disjoint sources remain strictly independent.
    ranked=sorted(range(n),key=lambda v:(-len(adj[v]),v))
    rng=random.Random(seed+17)
    # Shuffle within degree-independent random layout instead of tuning after
    # seeing any heldout queries or graph reachability answers.
    rng.shuffle(ranked)
    train_hot=tuple(ranked[:hot_count])
    shifted=tuple(ranked[hot_count:2*hot_count])
    train=sample_pairs(n,train_count,seed+101,train_hot)
    heldout={
      "matched_hot":sample_pairs(n,test_count,seed+201,train_hot),
      "uniform":sample_pairs(n,test_count,seed+202),
      "shifted_hot":sample_pairs(n,test_count,seed+203,shifted)
    }
    return train, heldout, train_hot, shifted

def fingerprint_pairs(qs):
    return hashlib.sha256(json.dumps(qs,separators=(",",":")).encode("ascii")).hexdigest()

def check_times(method, value):
    if not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
        raise ValueError(f"bad positive timing: {method}")
    return value

def compile_cache_binary(out, compiler, optimization):
    exe=out/"phase20_cache_bench"
    cmd=[compiler,"-std=c++17",optimization,"-DNDEBUG","-Wall",
         "-Wextra","-Wpedantic",str(ROOT/"hot_source_bench.cpp"),
         "-o",str(exe)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    return exe,cmd

def run(args):
    if not (args.hot_sources>=1 and args.train>=1 and args.test>=1
            and args.tric_repetitions>=15 and args.oreach_repetitions>=1
            and 0<=args.closure_cap_mib<=1024 and args.hot_cache_cap_mib>=1
            and 0<args.pivot_budget<=args.candidates<=19):
        raise ValueError("invalid benchmark parameters")
    out=Path(args.output_dir).resolve()
    out.mkdir(parents=True,exist_ok=True)
    graph=Path(args.graph).resolve()
    adj,rev=read_metis(graph)
    n=len(adj)
    train,heldout,hot,shifted=workload_sets(
        adj,args.seed,args.train,args.test,args.hot_sources)
    if args.candidates>n:
        raise ValueError("too few vertices for pivot candidates")
    train_hash=fingerprint_pairs(train)
    candidates=sorted(range(n),key=lambda v:(-len(adj[v])-len(rev[v]),v))[:args.candidates]
    t0=time.perf_counter_ns()
    pivots=[make_pivot(adj,rev,v) for v in candidates]
    hits=hit_masks_for_pivots(pivots,train)
    fallback_work=[1+early_reachable(adj,*q)[1] for q in train]
    ordered,_,_=optimize_ordered(hits,[1.0]*len(train),fallback_work,
                                 [1.0]*len(candidates),args.pivot_budget)
    greedy=greedy_coverage_order(hits,[1.0]*len(train),
                                 len(candidates),args.pivot_budget)
    pivot_fit_ns=time.perf_counter_ns()-t0
    policies={"BFS":[],"Control":[],"Greedy":greedy,"Ordered":ordered}
    native_exe,compile_seconds,build_cmd=build_executable(out,args.compiler,args.optimization)
    cache_exe,cache_compile_cmd=compile_cache_binary(
        out,args.compiler,args.optimization)
    # Phase XXI: the new arm composes the existing exact cache with
    # the same TRIC compact, ordered pivot and bidirectional algorithms.
    indexed_exe=out/"phase21_cache_indexed_bench"
    indexed_compile_cmd=[
        args.compiler,"-std=c++17",args.optimization,"-DNDEBUG",
        "-Wall","-Wextra","-Wpedantic",
        str(ROOT/"cache_indexed_bench.cpp"),"-o",str(indexed_exe)]
    subprocess.run(indexed_compile_cmd,check=True,capture_output=True,text=True)
    by_class={}
    for cls in CLASSES:
        queries=heldout[cls]
        directory=out/cls
        directory.mkdir(exist_ok=True)
        # 'mixed' is upstream O'Reach's filename-derived label, NOT a claim
        # of 50:50 true/false outcomes; actual truth count is measured.
        queryfile=directory/"heldout.query.m.txt"
        positives=write_queryfile(queryfile,adj,queries)
        input_data=native_input(adj,train,queries,
                                args.hot_sources,args.hot_cache_cap_mib*1024*1024)
        cache_proc=subprocess.run([str(cache_exe)],input=input_data,
                                  capture_output=True,check=True,timeout=args.timeout)
        cached=json.loads(cache_proc.stdout)
        if (cached["training"]!=len(train) or cached["heldout"]!=len(queries)
            or cached["retained_bytes"]>cached["cap_bytes"]):
            raise AssertionError("cache budget/inputs mismatch")
        native_bytes=serialize_native(adj,candidates,policies,queries,train)
        # Immutable native input shared by Phase XXI and lifetime replay.
        (directory/"native_input.txt").write_bytes(native_bytes)
        native_proc=subprocess.run([str(native_exe),str(args.tric_repetitions),
                                    str(args.closure_cap_mib)],
                                   input=native_bytes,capture_output=True,
                                   check=True,timeout=args.timeout)
        native=json.loads(native_proc.stdout)
        hybrid_proc=subprocess.run([
            str(indexed_exe),"16",str(args.hot_sources),
            str(args.hot_cache_cap_mib*1024*1024)],
            input=native_bytes,capture_output=True,check=True,timeout=args.timeout)
        indexed=json.loads(hybrid_proc.stdout)
        if indexed["queries"]!=len(queries) or indexed["training"]!=len(train):
            raise AssertionError("Phase XXI cache+index input mismatch")
        if indexed["cache_hits"]!=cached["hits"]:
            raise AssertionError("Phase XXI cache hit accounting changed")
        if indexed["oracle_positive_count"]!=positives:
            raise AssertionError("Phase XXI standalone BFS truth count mismatch")
        if indexed["cache_retained_bytes"]>indexed["cache_cap_bytes"]:
            raise AssertionError("Phase XXI cache exceeds memory cap")
        if len({v["checksum"] for v in indexed["modes"].values()})!=1:
            raise AssertionError("Phase XXI ablation has mismatched answer checksums")
        for key,value in indexed["modes"].items():
            if len(value["samples_ns_per_query"])!=16:
                raise AssertionError(f"Phase XXI unbalanced rotation {key}")
        reference=next(p["checksum"] for p in native["policies"] if p["name"]=="BFS")
        keys=["compact_pivots_bidir","compact_pivots_topo","compact_pivots_selector"]
        for key in keys:
            if native[key]["checksum"]!=reference:
                raise AssertionError(f"TRIC {key} checksum differs from BFS")
        if native["queries"]!=len(queries):
            raise AssertionError("TRIC did not execute our test pairs")
        rss_values=[]
        oreach_raw=[]
        if not Path(args.oreach_binary).is_file():
            raise FileNotFoundError("pinned O'Reach binary missing")
        for rep in range(args.oreach_repetitions):
            csv_path=directory/f"oreach_{rep}.csv"
            rss_path=directory/f"oreach_{rep}.rss_kib.txt"
            cmd=["/usr/bin/time","-f","%M","-o",str(rss_path),
                 str(Path(args.oreach_binary).resolve()),
                 str(graph),"--seed",str(args.seed),"--queries",str(queryfile),
                 "--pbibfs","--pdfs","--output",str(csv_path)]
            proc=subprocess.run(cmd,capture_output=True,text=True,
                                timeout=args.timeout)
            (directory/f"oreach_{rep}.stderr.txt").write_text(proc.stderr)
            (directory/f"oreach_{rep}.stdout.txt").write_text(proc.stdout)
            if proc.returncode:
                raise RuntimeError(f"pinned O'Reach failed {cls}/{rep}: {proc.returncode}")
            rows=parse_oreach_csv(csv_path,len(queries),"mixed")
            oreach_raw+=rows
            rss_values.append(int(rss_path.read_text().strip()))
        times={}
        for method in ("oreach-pdfs","oreach-pbibfs"):
            values=[r["query_us"]*1000 for r in oreach_raw if r["algorithm"]==method]
            if len(values)!=args.oreach_repetitions:
                raise ValueError("O'Reach incomplete method repetitions")
            times[method]={"median_ns_per_query":check_times(
                method,statistics.median(values)),"samples_ns_per_query":values}
        for key in keys:
            times[key]={"median_ns_per_query":check_times(
                key,native[key]["median_ns_per_query"]),
                "samples_ns_per_query":native[key]["samples_ns_per_query"]}
        # The within-executable pairs below share the exact same TRIC
        # preprocessing, candidate pivots and graph buffers.
        for key,value in indexed["modes"].items():
            times[key]={"median_ns_per_query":check_times(
                key,value["median_ns_per_query"]),
                "samples_ns_per_query":value["samples_ns_per_query"]}
        times["hot_source_cache"]={"median_ns_per_query":check_times(
                "hot_source_cache",cached["cached_ns_per_query"]),
                "samples_ns_per_query":cached["cache_samples"]}
        times["plain_dfs"]={"median_ns_per_query":check_times(
                "plain_dfs",cached["baseline_ns_per_query"]),
                "samples_ns_per_query":cached["baseline_samples"]}
        (directory/"tric_native.json").write_text(json.dumps(native,indent=2)+"\n")
        (directory/"hot_source_native.json").write_text(json.dumps(cached,indent=2)+"\n")
        (directory/"cache_indexed_native.json").write_text(json.dumps(indexed,indent=2)+"\n")
        # Store only immutable arguments, raw per-query input SHA256 and
        # class-specific controls; never blend separate graph families.
        result={"class":cls, "seed":args.seed, "graph":graph.name,
                "train_sha256":train_hash, "heldout_sha256":fingerprint_pairs(queries),
                "query_file_sha256":hashlib.sha256(queryfile.read_bytes()).hexdigest(),
                "source_hot_train":hot, "source_hot_shifted":shifted,
                "training_count":len(train),"heldout_count":len(queries),
                "positive_count":positives,
                "cache_hits":cached["hits"],"cache_rows":cached["cache_rows"],
                "cache_retained_bytes":cached["retained_bytes"],
                "cache_build_ns":cached["build_ns"],
                "cache_indexed_build_ns":indexed["cache_build_ns"],
                "cache_indexed_retained_bytes":indexed["cache_retained_bytes"],
                "cache_indexed_pivot_build_ns":indexed["pivot_build_ns"],
                "cache_indexed_compact_build_ns":indexed["compact_build_ns"],
                "pivot_fit_ns":pivot_fit_ns,
                "tric_pivot_build_ms":native["index_build_ms"],
                "tric_compact_build_ms":native["compact"]["build_ms"],
                "tric_index_labels_bytes":native["compact"]["labels_bytes"],
                "tric_bidir_extra_bytes":native["compact_bidir"]["extra_storage_bytes"],
                "oreach_median_init_ms":statistics.median(
                    [r["init_ms"] for r in oreach_raw if r["algorithm"]=="oreach-pdfs"]),
                "oreach_process_maxrss_kib":rss_values,
                "times":times,"oreach_raw_csv_rows":oreach_raw,
                "claim_limit":"Identical heldout queries but different index budgets and separate timed process runs; source skew is synthetic on authentic graph topology; per-query O'Reach output not independently exported"}
        by_class[cls]=result
        index_base=times["pivot_index"]["median_ns_per_query"]
        index_fast=times["cache_pivot_index"]["median_ns_per_query"]
        cache_extra_build=indexed["cache_build_ns"]
        result["incremental_cache_model"]={
            "extra_cache_build_ns":cache_extra_build,
            "query_ns_saved":index_base-index_fast,
            "strict_break_even_queries":(
                math.floor(cache_extra_build/(index_base-index_fast))+1
                if index_base>index_fast else None),
            "description":"Algebraic, not a real long-horizon replay; holds only if fixed query medians remain representative"}
        (directory/"comparison.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({"class":cls,"seed":args.seed,"graph":graph.name,
            "positive":positives,"cache_hits":cached["hits"],
            "cache_ns":times["hot_source_cache"]["median_ns_per_query"],
            "tric_bidir_ns":times["compact_pivots_bidir"]["median_ns_per_query"],
            "oreach_pdfs_ns":times["oreach-pdfs"]["median_ns_per_query"],
            "cache_indexed_ns":times["cache_pivot_index"]["median_ns_per_query"],
            "index_control_ns":times["pivot_index"]["median_ns_per_query"]}))
    result={"phase":"XX","state":"EXECUTED PILOT, not global SOTA",
        "graph_sha256":hashlib.sha256(graph.read_bytes()).hexdigest(),
        "oreach_commit":args.oreach_git_sha,
        "graph_vertices":len(adj),"graph_edges":sum(map(len,adj)),
        "seed":args.seed,"training_sha256":train_hash,
        "train_hot_sources":hot,"shift_hot_sources":shifted,
        "train":args.train,"test_per_class":args.test,
        "hot_probability":0.8,"hot_cache_cap_mib":args.hot_cache_cap_mib,
        "pivot_budget":args.pivot_budget,
        "matched_resource_budgets":False,
        "native_compile_seconds":compile_seconds,
        "native_compile_cmd":build_cmd,"cache_compile_cmd":cache_compile_cmd,
        "cache_indexed_compile_cmd":indexed_compile_cmd,
        "environment":{"python":sys.version,"platform":platform.platform()},
        "classes":by_class}
    (out/"phase20_summary.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def parser():
    p=argparse.ArgumentParser()
    p.add_argument("--graph",required=True)
    p.add_argument("--oreach-binary",required=True)
    p.add_argument("--oreach-git-sha",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--seed",type=int,default=20261022)
    p.add_argument("--train",type=int,default=500)
    p.add_argument("--test",type=int,default=2400)
    p.add_argument("--hot-sources",type=int,default=8)
    p.add_argument("--hot-cache-cap-mib",type=int,default=2)
    p.add_argument("--candidates",type=int,default=11)
    p.add_argument("--pivot-budget",type=int,default=5)
    p.add_argument("--tric-repetitions",type=int,default=15)
    p.add_argument("--oreach-repetitions",type=int,default=5)
    p.add_argument("--closure-cap-mib",type=int,default=64)
    p.add_argument("--optimization",default="-O3")
    p.add_argument("--compiler",default="g++")
    p.add_argument("--timeout",type=int,default=300)
    return p

if __name__=="__main__":
    run(parser().parse_args())

"""Phase XXIII: independently reproduce Phase XXII training on identical inputs.

Report inclusive Python training vs native input serialization + subprocess +
DP time, assert exact bitmask/edge-count/order parity, and verify that the
unchanged native C++ query engine produces identical oracle-approved results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys
from pathlib import Path

from benchmark_hot_source_external import CLASSES,workload_sets
from benchmark_native import serialize_native
from benchmark_oreach_ci import read_metis
from phase23_training import compile_native,native_fit,legacy_fit,assert_parity
from phase23_admission import compare as compare_admission
from tric import early_reachable

ROOT=Path(__file__).resolve().parent

def run(args):
    graph=Path(args.graph).resolve()
    adj,rev=read_metis(graph)
    if args.candidates>len(adj) or args.budget>args.candidates or args.train<1:
        raise ValueError("training parameters out of range")
    train,heldout,hot,shifted=workload_sets(
        adj,args.seed,args.train,args.test,args.hot_sources)
    vertices=sorted(range(len(adj)),key=lambda u:(
        -len(adj[u])-len(rev[u]),u))[:args.candidates]
    out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    native_exe=compile_native(out,args.compiler,args.optimization)
    cpp_exe=out/"phase23_native_query"
    subprocess.run([args.compiler,"-std=c++17",args.optimization,"-DNDEBUG",
                   "-Wall","-Wextra","-Wpedantic",
                   str(ROOT/"cache_indexed_bench.cpp"),"-o",str(cpp_exe)],
                   capture_output=True,check=True,text=True)
    # Alternate ordering to reduce cold-cache / CPU-clock bias.
    trials=[]
    for rep in range(args.training_reps):
        if rep%2==0:
            fast=native_fit(adj,vertices,train,args.budget,native_exe,args.timeout)
            slow=legacy_fit(adj,rev,vertices,train,args.budget)
        else:
            slow=legacy_fit(adj,rev,vertices,train,args.budget)
            fast=native_fit(adj,vertices,train,args.budget,native_exe,args.timeout)
        assert_parity(fast,slow)
        trials.append({
           "legacy_fit_ns":slow["fit_ns"],
           "native_fit_ns":fast["fit_ns"],
           "native_internal_ns":fast["native_metrics"]["total_native_ns"],
           "native_serialization_ns":fast["serialize_ns"],
           "objective_equal":True,
           "exact_same_order":True})
    cold_runner=out/"phase23_lifetime"
    subprocess.run([args.compiler,"-std=c++17",args.optimization,"-DNDEBUG",
                   "-Wall","-Wextra","-Wpedantic",
                   str(ROOT/"lifetime_replay.cpp"),"-o",str(cold_runner)],
                   capture_output=True,check=True,text=True)
    query_comparisons={}
    policy_admission={}
    policies={"BFS":[],"Control":[],"Greedy":fast["greedy"],"Ordered":fast["ordered"]}
    for cls in CLASSES:
        qs=heldout[cls]
        raw=serialize_native(adj,vertices,policies,qs,train)
        proc=subprocess.run([str(cpp_exe),"16",str(args.hot_sources),
                             str(args.hot_cache_cap_mib*1024*1024)],
                            input=raw,capture_output=True,timeout=args.timeout)
        if proc.returncode:
            raise RuntimeError(f"indexed TRIC runner failed {cls}: {proc.stderr[-1500:]!r}")
        result=json.loads(proc.stdout)
        modes=result["modes"]
        if len({data["checksum"] for data in modes.values()})!=1:
            raise AssertionError("native index/cache disagreement")
        if result["queries"]!=len(qs) or result["training"]!=len(train):
            raise AssertionError("train/test data was changed")
        policy_admission[cls]=compare_admission(
            cold_runner,raw,args.hot_sources,
            args.hot_cache_cap_mib*1024*1024,
            out/cls/"admission",args.timeout,replications=2)
        query_comparisons[cls]={
          "training_hash":hashlib.sha256(str(train).encode()).hexdigest(),
          "heldout_hash":hashlib.sha256(str(qs).encode()).hexdigest(),
          "all_native_modes_agree":True,
          "oracle_positive_count":result["oracle_positive_count"],
          "sampled_query_count":len(qs),
          "latencies_ns":{key:val["median_ns_per_query"]
                          for key,val in modes.items()},
          "cache_hits":result["cache_hits"],
        }
    train_old=statistics.median(x["legacy_fit_ns"] for x in trials)
    train_new=statistics.median(x["native_fit_ns"] for x in trials)
    if train_old<=0 or train_new<=0:
        raise AssertionError("invalid trainer timing")
    report={
      "phase":"XXIII",
      "goal":"Same exact objective, pivot order and fallback work; train-only speedup",
      "dataset":args.dataset,
      "seed":args.seed,
      "graph_sha256":hashlib.sha256(graph.read_bytes()).hexdigest(),
      "graph_vertices":len(adj),
      "graph_edges":sum(map(len,adj)),
      "training_sha256":hashlib.sha256(str(train).encode()).hexdigest(),
      "training_pairs":len(train),
      "heldout_per_class":args.test,
      "pivots":vertices,
      "ordered_policy":fast["ordered"],
      "greedy_policy":fast["greedy"],
      "training_bitsets_identical":True,
      "training_fallback_scan_counts_identical":True,
      "exact_objective_identical":True,
      "native_fit_includes_serialization_subprocess_dp":True,
      "trainer_compilation_excluded_both_arms":True,
      "candidate_preselection_excluded_both_arms":True,
      "training_repetitions":len(trials),
      "samples":trials,
      "median_legacy_fit_ns":train_old,
      "median_native_fit_ns":train_new,
      "training_speedup":train_old/train_new,
      "query_tests":query_comparisons,
      "three_arm_lifecycle_admission":policy_admission,
      "admission_design":"After first 256 LIVE sources only; trained high-frequency source candidate list, 60%-support threshold, 50000 known future call horizon; same graph/index/pivot policy, cache lazily constructed only when admitted",
      "admission_target_query_labels_used":False,
      "environment":{"python":sys.version,"platform":platform.platform(),
                     "compiler":args.compiler,"optimization":args.optimization},
      "claim_limit":"Same exact trained pivot order and native serving behavior on these inputs; does not claim improvement to original O-Reach, cold whole-application deployment or general SOTA"}
    (out/"phase23_summary.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({
        "dataset":args.dataset,"seed":args.seed,
        "training_speedup":report["training_speedup"],
        "legacy_train_ms":train_old/1e6,
        "native_train_ms":train_new/1e6,
        "exact_same_order":True,
        "classes_checked":list(query_comparisons),
        "matched_hot_120k_admitted":policy_admission["matched_hot"]["50"]["adaptive_cache_pivot_index"]["admitted"],
        "uniform_120k_admitted":policy_admission["uniform"]["50"]["adaptive_cache_pivot_index"]["admitted"],
        "shifted_120k_admitted":policy_admission["shifted_hot"]["50"]["adaptive_cache_pivot_index"]["admitted"],
        "lifecycle_adaptive_matched_speedup":policy_admission["matched_hot"]["50"]["adaptive_cache_pivot_index"]["speedup_over_index"]}),flush=True)
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--graph",required=True)
    p.add_argument("--output-dir",required=True)
    p.add_argument("--dataset",required=True)
    p.add_argument("--seed",type=int,default=20261022)
    p.add_argument("--train",type=int,default=500)
    p.add_argument("--test",type=int,default=2400)
    p.add_argument("--candidates",type=int,default=11)
    p.add_argument("--budget",type=int,default=5)
    p.add_argument("--hot-sources",type=int,default=8)
    p.add_argument("--hot-cache-cap-mib",type=int,default=2)
    p.add_argument("--training-reps",type=int,default=3)
    p.add_argument("--compiler",default="g++")
    p.add_argument("--optimization",default="-O3")
    p.add_argument("--timeout",type=int,default=300)
    run(p.parse_args())

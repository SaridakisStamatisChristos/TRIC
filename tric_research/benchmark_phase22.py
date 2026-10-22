"""Phase XXII: exact three-seed published graph replication plus cold-start replay.

Run original Phase XXI same-file/O'Reach benchmark FIRST, then run fresh native
processes containing *only* the selected index policy. Each process measures
graph input parsing, pivot building, compact index, optional source cache and
actual replayed heldout calls. Independent full heldout truth check is AFTER
native timed sections. External /usr/bin/time maxRSS includes verification.

Replays repeat the same frozen heldout set; they are not new IID samples.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import subprocess
import time
from pathlib import Path

import benchmark_hot_source_external as previous

MODES=("pivot_index","cache_pivot_index")

def run_fresh(exe, payload, mode, factor, sources, cap, dest, timeout=300):
    if mode not in MODES or factor<1:
        raise ValueError("invalid lifetime configuration")
    dest=Path(dest)
    dest.mkdir(parents=True,exist_ok=True)
    time_report=dest/"maxrss_kib.txt"
    command=["/usr/bin/time","-f","%M","-o",str(time_report),
             str(exe),mode,str(factor),str(sources),str(cap)]
    start=time.perf_counter_ns()
    proc=subprocess.run(command,input=payload,capture_output=True,timeout=timeout)
    process_wall_ns=time.perf_counter_ns()-start
    (dest/"stderr.txt").write_bytes(proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"fresh-process {mode} factor={factor}: exit={proc.returncode}: {proc.stderr[-1500:]!r}")
    data=json.loads(proc.stdout)
    if data["mode"]!=mode or data["factor"]!=factor:
        raise AssertionError("mode or requested calls changed")
    if data["actual_query_calls"]!=data["unique_queries"]*factor:
        raise AssertionError("not all actual replay calls completed")
    if data["independently_verified_queries"]!=data["unique_queries"]:
        raise AssertionError("independent validation incomplete")
    if data["retained_cache_bytes"]>cap:
        raise AssertionError("retained cache cap exceeded")
    if mode=="pivot_index" and (data["cache_rows"]!=0 or data["cache_hits"]!=0):
        raise AssertionError("control accidentally allocated cache")
    if not (0<data["full_native_build_plus_queries_ns"]<
            process_wall_ns*2 and
            data["actual_query_loop_ns"]>=0):
        raise AssertionError("invalid wall/CPU timer boundary")
    data["fresh_process_elapsed_ns_including_validation"]=process_wall_ns
    data["process_maxrss_kib_including_validation"]=int(time_report.read_text().strip())
    data["input_sha256"]=hashlib.sha256(payload).hexdigest()
    (dest/"result.json").write_text(json.dumps(data,indent=2)+"\n")
    return data

def checked_median(values):
    if not values or any(not isinstance(v,(int,float)) or
                         not math.isfinite(v) or v<0 for v in values):
        raise ValueError("invalid timing replication")
    return statistics.median(values)

def replay_pair(exe,payload,factor,sources,cap,out,replications=2,timeout=300):
    if not 1<=replications<=8:
        raise ValueError("replications out of bound")
    out=Path(out)
    arms={mode:[] for mode in MODES}
    for rep in range(replications):
        # Position balancing eliminates a systematic always-second cache
        # advantage in the available same-runner experiment.
        sequence=MODES if rep%2==0 else tuple(reversed(MODES))
        for mode in sequence:
            row=run_fresh(exe,payload,mode,factor,sources,cap,
                          out/f"rep{rep}_{mode}",timeout)
            arms[mode].append(row)
    for rep in range(replications):
        if arms["pivot_index"][rep]["checksum"]!=arms["cache_pivot_index"][rep]["checksum"]:
            raise AssertionError("cache/index lifetime answers differ")
        if arms["pivot_index"][rep]["input_sha256"]!=arms["cache_pivot_index"][rep]["input_sha256"]:
            raise AssertionError("cache/index native inputs differ")
    summary={}
    for mode,rows in arms.items():
        summary[mode]={
            "median_build_plus_query_ns":checked_median(
                [x["full_native_build_plus_queries_ns"] for x in rows]),
            "median_graph_parse_ns":checked_median([x["parse_input_ns"] for x in rows]),
            "median_index_pivot_build_ns":checked_median(
                [x["build_pivots_ns"]+x["build_compact_ns"] for x in rows]),
            "median_cache_build_ns":checked_median([x["build_cache_ns"] for x in rows]),
            "median_query_loop_ns":checked_median(
                [x["actual_query_loop_ns"] for x in rows]),
            "median_maxrss_kib":checked_median(
                [x["process_maxrss_kib_including_validation"] for x in rows]),
            "max_maxrss_kib":max(
                x["process_maxrss_kib_including_validation"] for x in rows),
            "cache_rows":rows[0]["cache_rows"],
            "cache_retained_bytes":rows[0]["retained_cache_bytes"],
            "actual_query_calls":rows[0]["actual_query_calls"],
            "replications":replications,
            "samples_build_plus_query_ns":[
                x["full_native_build_plus_queries_ns"] for x in rows],
            "samples_maxrss_kib":[
                x["process_maxrss_kib_including_validation"] for x in rows],
            "checksum_verified":True,
        }
    base=summary["pivot_index"]["median_build_plus_query_ns"]
    accelerated=summary["cache_pivot_index"]["median_build_plus_query_ns"]
    summary["paired_cost_ratio_baseline_over_cache"]=base/accelerated
    summary["cache_wins_full_native_lifecycle"]=accelerated<base
    return summary

def run(args):
    if not args.replay_factors or min(args.replay_factors)<1 or max(args.replay_factors)>1000:
        raise ValueError("invalid replay factors")
    if args.lifetime_repetitions<1 or args.lifetime_repetitions>8:
        raise ValueError("invalid lifetime repetition count")
    base=previous.run(args)
    out=Path(args.output_dir).resolve()
    lifetime_exe=out/"phase22_lifetime"
    command=[args.compiler,"-std=c++17",args.optimization,"-DNDEBUG",
             "-Wall","-Wextra","-Wpedantic",
             str(previous.ROOT/"lifetime_replay.cpp"),"-o",str(lifetime_exe)]
    subprocess.run(command,check=True,capture_output=True,text=True)
    results={}
    for cls in previous.CLASSES:
        p=(out/cls/"native_input.txt").read_bytes()
        comparison=base["classes"][cls]
        if comparison["train_sha256"]!=base["training_sha256"]:
            raise AssertionError("stale input, changed training set")
        factor_results={}
        for factor in args.replay_factors:
            factor_results[str(factor)]=replay_pair(
                lifetime_exe,p,factor,args.hot_sources,
                args.hot_cache_cap_mib*1024*1024,
                out/cls/f"lifetime_factor_{factor}",
                args.lifetime_repetitions,args.timeout)
            cell=factor_results[str(factor)]
            print(json.dumps({"dataset":args.dataset,"seed":args.seed,
              "class":cls,"factor":factor,
              "actual_calls":cell["pivot_index"]["actual_query_calls"],
              "full_build_query_speedup":cell["paired_cost_ratio_baseline_over_cache"],
              "indexed_rss_kib":cell["pivot_index"]["median_maxrss_kib"],
              "cached_rss_kib":cell["cache_pivot_index"]["median_maxrss_kib"]}),
              flush=True)
        results[cls]=factor_results
    report={
       "phase":"XXII",
       "dataset":args.dataset,
       "seed":args.seed,
       "graph_sha256":base["graph_sha256"],
       "graph_vertices":base["graph_vertices"],
       "graph_edges":base["graph_edges"],
       "upstream_oreach_git_sha":base["oreach_commit"],
       "training_sha256":base["training_sha256"],
       "three_classes":list(previous.CLASSES),
       "factors":args.replay_factors,
       "lifetime_repetitions":args.lifetime_repetitions,
       "query_set_size_per_class":args.test,
       "replayed_query_sets_not_independent":True,
       "python_pivot_fit_ns":base["classes"]["matched_hot"]["pivot_fit_ns"],
       "hosted_runner_noise_warning":True,
       "comparative_scope":"Full native input parse+index build+actual repeated query calls; Python fit separately; OReach upstream init/query and RSS separately; not unified whole-product time or matched RSS",
       "compiler_command":command,
       "classes":results,
       "underlying_phase21_summary":str(out/"phase20_summary.json")
    }
    (out/"phase22_lifetime_summary.json").write_text(json.dumps(report,indent=2)+"\n")
    return report

def main():
    parser=previous.parser()
    parser.add_argument("--dataset",default="unspecified")
    parser.add_argument("--replay-factors",type=int,nargs="+",default=[1,50])
    parser.add_argument("--lifetime-repetitions",type=int,default=2)
    args=parser.parse_args()
    run(args)

if __name__=="__main__":
    main()

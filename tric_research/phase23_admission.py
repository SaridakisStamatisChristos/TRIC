"""Phase XXIII causal lifetime comparison of eager, never, and adaptive cache.

No target labels/answers/future query observations used for admission.
The adaptive arm learns from first 256 live source IDs; admission is
enabled only if future known request horizon >=50000 and >=60% of the
prefix references selected train-only cacheable source IDs. This regime
is a bounded prototype, not a production streaming traffic guarantee.
"""
from __future__ import annotations
import hashlib
import json
import statistics
import subprocess
from pathlib import Path

MODES=("pivot_index","cache_pivot_index","adaptive_cache_pivot_index")

def run_one(exe,payload,mode,factor,max_sources,cap_bytes,out,timeout=300):
    if mode not in MODES or not 1<=factor<=1000:
        raise ValueError("invalid admission test shape")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rss=out/"maxrss_kib.txt"
    cmd=["/usr/bin/time","-f","%M","-o",str(rss),str(exe),mode,
         str(factor),str(max_sources),str(cap_bytes)]
    proc=subprocess.run(cmd,input=payload,capture_output=True,timeout=timeout)
    (out/"stderr.txt").write_bytes(proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"{mode} failed: {proc.returncode} {proc.stderr[-1200:]!r}")
    row=json.loads(proc.stdout)
    if row["mode"]!=mode or row["factor"]!=factor:
        raise AssertionError("runner returned a different mode/horizon")
    if row["actual_query_calls"]!=row["unique_queries"]*factor or (
        row["independently_verified_queries"]!=row["unique_queries"]):
        raise AssertionError("not all calls and independent oracles executed")
    if row["retained_cache_bytes"]>cap_bytes:
        raise AssertionError("retained cap exceeded")
    if mode=="pivot_index" and row["cache_rows"]!=0:
        raise AssertionError("control unexpectedly allocated rows")
    if mode=="adaptive_cache_pivot_index":
        if row["admission_prefix_queries"]!=min(row["actual_query_calls"],256):
            raise AssertionError("adaptive runner sampled outside bounded prefix")
        if row["adaptive_admitted"] and (
            row["actual_query_calls"]<50000 or row["cache_rows"]<1 or
            row["admission_potential_hits"]*100 <
            row["admission_prefix_queries"]*60):
            raise AssertionError("admission violated conservative gate")
        if not row["adaptive_admitted"] and row["cache_rows"]!=0:
            raise AssertionError("cache allocated despite refusal")
    row["maxrss_kib"]=int(rss.read_text().strip())
    row["input_sha256"]=hashlib.sha256(payload).hexdigest()
    if row["maxrss_kib"]<=0 or row["full_native_build_plus_queries_ns"]<=0:
        raise AssertionError("invalid fresh-process timing or RSS")
    (out/"result.json").write_text(json.dumps(row,indent=2)+"\n")
    return row

def compare(exe,payload,max_sources,cap_bytes,out,timeout=300,replications=2):
    if not 1<=replications<=8:
        raise ValueError("invalid repetitions")
    out=Path(out)
    results={}
    for factor in (1,50):
        observations={m:[] for m in MODES}
        for rep in range(replications):
            # Clock position balanced among three methods across runs.
            order=MODES if rep%2==0 else tuple(reversed(MODES))
            for mode in order:
                row=run_one(exe,payload,mode,factor,max_sources,cap_bytes,
                            out/f"factor_{factor}"/f"rep{rep}_{mode}",timeout)
                observations[mode].append(row)
        for rep in range(replications):
            hashes={observations[m][rep]["checksum"] for m in MODES}
            if len(hashes)!=1:
                raise AssertionError("adaptive/eager/index disagree on exact answers")
            data_sha={observations[m][rep]["input_sha256"] for m in MODES}
            if len(data_sha)!=1:
                raise AssertionError("paired modes received different native input")
        cell={}
        for mode,rows in observations.items():
            cell[mode]={
                "median_full_native_ns":statistics.median(
                    r["full_native_build_plus_queries_ns"] for r in rows),
                "median_maxrss_kib":statistics.median(r["maxrss_kib"] for r in rows),
                "peak_maxrss_kib":max(r["maxrss_kib"] for r in rows),
                "cache_rows":rows[0]["cache_rows"],
                "retained_cache_bytes":rows[0]["retained_cache_bytes"],
                "cache_hits":rows[0]["cache_hits"],
                "actual_calls":rows[0]["actual_query_calls"],
                "admitted":rows[0]["adaptive_admitted"],
                "admission_prefix_queries":rows[0]["admission_prefix_queries"],
                "admission_potential_hits":rows[0]["admission_potential_hits"],
                "samples_ns":[r["full_native_build_plus_queries_ns"] for r in rows],
                "all_answers_independently_verified":True,
            }
            if any(r["adaptive_admitted"]!=rows[0]["adaptive_admitted"] for r in rows):
                raise AssertionError("admission decision inconsistent with fixed query prefix")
        denominator=cell["pivot_index"]["median_full_native_ns"]
        for mode in MODES[1:]:
            cell[mode]["speedup_over_index"]=denominator/cell[mode]["median_full_native_ns"]
        results[str(factor)]=cell
    return results

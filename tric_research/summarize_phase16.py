"""Phase XVI falsification matrix: two-sided interval filtering vs all prior controls."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def summarize(paths):
    groups=defaultdict(list)
    graph_sha=None
    seen_files=set()
    for path in paths:
        d=json.loads(Path(path).read_text(encoding="utf-8"))
        if graph_sha is None:
            graph_sha=d["graph_sha256"]
        elif d["graph_sha256"]!=graph_sha:
            raise ValueError("different graph identities; do not pool")
        stratum=d.get("query_stratum")
        if stratum not in ("uniform","positive","negative","balanced"):
            raise ValueError("invalid or absent query stratum")
        qkey=(stratum,d["query_file_sha256"])
        if qkey in seen_files:
            raise ValueError("duplicate query file")
        seen_files.add(qkey)
        methods=d["tric"]
        reference=next(p["checksum"] for p in methods["policies"] if p["name"]=="BFS")
        controls=[methods[key] for key in
                  ("compact_pivots_topo","compact_pivots_bidir","compact_pivots_bidir_intervals")]
        for x in controls:
            if x["checksum"]!=reference:
                raise ValueError("wrong answer checksum")
        for key in ("pivot_probes","pivot_rescues","fallback_queries"):
            if len({x[key] for x in controls})!=1:
                raise ValueError("different certificate or pivot work")
        raw=methods["compact_bidir_intervals"]
        if raw["checksum"]!=reference:
            raise ValueError("nonhybrid two-sided filter incorrect")
        if raw["fallback_queries"]!=methods["compact_bidir"]["fallback_queries"]:
            raise ValueError("different nonhybrid fallback counts")
        n=d["test_count"]
        true=d["heldout_positive_count"]
        expected={"positive":n,"negative":0,"balanced":n//2}
        if stratum in expected and true!=expected[stratum]:
            raise ValueError("incorrect target class")
        vals=[x["median_ns_per_query"] for x in controls]
        if min(vals)<=0:
            raise ValueError("nonpositive native timing")
        groups[stratum].append({
            "input_sha256":d["query_file_sha256"],
            "true_answers":true,
            "num_queries":n,
            "topological_hybrid_ns":vals[0],
            "baseline_bidir_hybrid_ns":vals[1],
            "interval_pruned_hybrid_ns":vals[2],
            "old_bidir_over_interval_ratio":vals[1]/vals[2],
            "topo_over_interval_ratio":vals[0]/vals[2],
            "oreach_pdfs_ns":d["oreach"]["oreach-pdfs"]["median_ns_per_query"],
            "old_bidir_scanned_arcs":methods["compact_bidir"]["fallback_edges"],
            "interval_scanned_arcs":raw["fallback_edges"],
            "interval_pruned_neighbors":raw["interval_rejections"],
            "pivot_fallback_queries":controls[0]["fallback_queries"],
            "extra_interval_index_bytes":0,
        })
    if set(groups)!=set(("uniform","positive","negative","balanced")):
        raise ValueError("missing one or more strata")
    if any(len(rows)!=3 for rows in groups.values()):
        raise ValueError("need three seeded query sets per stratum")
    result={"graph_sha256":graph_sha,
            "scope":"three seeded heldout source-stratified workloads on one fixed graph, unmodified pinned O'Reach reference",
            "query_protocol":"uniform source-target pairs or oracle-defined source-uniform nonself reachable class",
            "limits":"No novelty, no general SOTA; O'Reach index construction/memory unmatched; hosted-runner noise and source selection bias",
            "strata":{}}
    for stratum,rows in sorted(groups.items()):
        result["strata"][stratum]={
            "seeds":len(rows),
            "median_paired_bidir_over_intervals":
                statistics.median(r["old_bidir_over_interval_ratio"] for r in rows),
            "median_paired_topo_over_intervals":
                statistics.median(r["topo_over_interval_ratio"] for r in rows),
            "interval_faster_than_old_bidir":
                sum(r["interval_pruned_hybrid_ns"] < r["baseline_bidir_hybrid_ns"] for r in rows),
            "median_old_bidir_ns":statistics.median(r["baseline_bidir_hybrid_ns"] for r in rows),
            "median_intervals_ns":statistics.median(r["interval_pruned_hybrid_ns"] for r in rows),
            "median_topo_ns":statistics.median(r["topological_hybrid_ns"] for r in rows),
            "median_oreach_ns":statistics.median(r["oreach_pdfs_ns"] for r in rows),
            "rows":rows}
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("files",nargs="+",type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    report=summarize(args.files)
    args.out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({name:{
       "median_paired_bidir_over_intervals":x["median_paired_bidir_over_intervals"],
       "median_interval_ns":x["median_intervals_ns"],
       "interval_wins":x["interval_faster_than_old_bidir"]}
       for name,x in report["strata"].items()},indent=2))

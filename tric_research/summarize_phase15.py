"""Phase XV: exact per-stratum paired query latency; never pool graph identities.

Three deterministic held-out seeds per graph and query outcome class.
Numbers are observations on noisy shared CI runners, not confidence intervals.
"""
import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path


def summarize(paths):
    groups = defaultdict(list)
    graph_sha = None
    seen_inputs = set()
    for filename in paths:
        d = json.loads(Path(filename).read_text(encoding="utf-8"))
        sha = d["graph_sha256"]
        if graph_sha is None:
            graph_sha = sha
        if sha != graph_sha:
            raise ValueError("cannot aggregate different graph SHA256 values")
        stratum = d.get("query_stratum")
        if stratum not in ("uniform", "positive", "negative", "balanced"):
            raise ValueError(f"unknown/missing Phase XV query stratum: {stratum}")
        query_sha = d["query_file_sha256"]
        if (stratum, query_sha) in seen_inputs:
            raise ValueError("duplicate held-out query file")
        seen_inputs.add((stratum, query_sha))
        count = d["test_count"]
        positive = d["heldout_positive_count"]
        expected = {"positive": count, "negative": 0, "balanced": count//2}
        if stratum in expected and positive != expected[stratum]:
            raise AssertionError("incorrect oracle-generated query class")
        if count < 1:
            raise ValueError("empty query set")
        methods = d["tric"]
        truth = next(p["checksum"] for p in methods["policies"] if p["name"] == "BFS")
        topo = methods["compact_pivots_topo"]
        bidir = methods["compact_pivots_bidir"]
        for method in (topo, bidir):
            if method["checksum"] != truth:
                raise AssertionError("query answer checksum mismatch")
        for k in ("pivot_rescues", "pivot_probes", "fallback_queries"):
            if topo[k] != bidir[k]:
                raise AssertionError("pivot work differs between methods")
        a = topo["median_ns_per_query"]
        b = bidir["median_ns_per_query"]
        o = d["oreach"]["oreach-pdfs"]["median_ns_per_query"]
        if min(a, b, o) <= 0:
            raise ValueError("invalid nonpositive latency")
        groups[stratum].append({
            "file": str(filename),
            "query_sha256": query_sha,
            "queries": count,
            "positive_count": positive,
            "positive_fraction": positive / count,
            "topological_hybrid_ns": a,
            "bidirectional_hybrid_ns": b,
            "oreach_pdfs_ns": o,
            "topo_over_bidir": a / b,
            "bidir_over_oreach": b / o,
            "pivot_rescues": bidir["pivot_rescues"],
            "fallback_queries": bidir["fallback_queries"],
            "direct_topo_fallback_edges": methods["compact_topo"]["fallback_edges"],
            "direct_bidir_fallback_edges": methods["compact_bidir"]["fallback_edges"],
            "bidir_extra_bytes": methods["compact_bidir"]["extra_storage_bytes"]
        })
    if set(groups) != {"uniform", "positive", "negative", "balanced"}:
        raise ValueError("all four query strata required")
    if any(len(rows) != 3 for rows in groups.values()):
        raise ValueError("three deterministic seeds required for each stratum")
    output = {}
    for name, rows in sorted(groups.items()):
        output[name] = {
            "seeds": len(rows),
            "median_paired_topo_over_bidir": statistics.median(
                row["topo_over_bidir"] for row in rows),
            "median_paired_bidir_over_oreach": statistics.median(
                row["bidir_over_oreach"] for row in rows),
            "bidir_faster_than_topo_seeds": sum(
                row["bidirectional_hybrid_ns"] < row["topological_hybrid_ns"]
                for row in rows),
            "median_topo_ns": statistics.median(
                row["topological_hybrid_ns"] for row in rows),
            "median_bidir_ns": statistics.median(
                row["bidirectional_hybrid_ns"] for row in rows),
            "median_oreach_pdfs_ns": statistics.median(
                row["oreach_pdfs_ns"] for row in rows),
            "rows": rows
        }
    return {
        "scope": "Single graph, deterministic seed splits, same oracle answers across methods; not independent graph replication",
        "graph_sha256": graph_sha,
        "query_generation": "uniform endpoints or source-uniform eligible non-self target; balanced half positive; all oracle checked",
        "strata": output,
        "limitations": [
            "Positive/negative cases are source-uniform, not uniform over all labeled pairs",
            "Three splits of one graph are not three independent graph instances",
            "Hosted-runner timing is noisy; index memory and build costs not matched to O'Reach",
            "No new algorithmic novelty claim"]
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("results", nargs="+", type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    summary = summarize(a.results)
    a.out.write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({name:{
        "median_paired_topo_over_bidir": data["median_paired_topo_over_bidir"],
        "median_paired_bidir_over_oreach": data["median_paired_bidir_over_oreach"],
        "bidir_faster_seeds": data["bidir_faster_than_topo_seeds"]
    } for name,data in summary["strata"].items()}, indent=2))


if __name__ == "__main__":
    main()

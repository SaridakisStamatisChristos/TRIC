"""Summarize multiple held-out seeds from one graph without SOTA extrapolation."""
import argparse
import json
import statistics
from pathlib import Path


def aggregate(paths):
    rows = []
    graph_hash = None
    for p in paths:
        result = json.loads(Path(p).read_text(encoding="utf-8"))
        h = result["graph_sha256"]
        if graph_hash is None:
            graph_hash = h
        if h != graph_hash:
            raise ValueError("Multi-seed summary requires the same graph")
        policies = {item["name"]: item for item in result["tric"]["policies"]}
        baseline = policies["Ordered"]["median_ns_per_query"]
        hybrid = result["tric"]["compact_pivots"]["median_ns_per_query"]
        plain = result["tric"]["compact_plain"]["median_ns_per_query"]
        guided = result["tric"]["compact"]["median_ns_per_query"]
        if baseline <= 0 or hybrid <= 0:
            raise ValueError("nonpositive measurement")
        if policies["BFS"]["checksum"] != result["tric"]["compact_pivots"]["checksum"]:
            raise AssertionError("Hybrid mismatch on " + str(p))
        rows.append({
            "result_file": str(p),
            "test_count": result["test_count"],
            "ordered_ns": baseline,
            "hybrid_ns": hybrid,
            "compact_plain_ns": plain,
            "compact_guided_ns": guided,
            "speedup_ordered_over_hybrid": baseline / hybrid,
            "pivot_rescues": result["tric"]["compact_pivots"]["pivot_rescues"],
            "fallback_queries": result["tric"]["compact_pivots"]["fallback_queries"],
            "oreach_pdfs_ns": result["oreach"]["oreach-pdfs"]["median_ns_per_query"],
            "oreach_pbibfs_ns": result["oreach"]["oreach-pbibfs"]["median_ns_per_query"]
        })
    return {
        "scope": "One published example graph, multiple deterministic held-out seeds; not a matched-memory SOTA claim",
        "graph_sha256": graph_hash,
        "seeds": len(rows),
        "hybrid_faster_than_ordered_count": sum(x["hybrid_ns"] < x["ordered_ns"] for x in rows),
        "median_paired_speedup_ordered_over_hybrid":
            statistics.median(x["speedup_ordered_over_hybrid"] for x in rows),
        "rows": rows
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = aggregate(args.results)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"seeds": result["seeds"],
                      "hybrid_faster_count": result["hybrid_faster_than_ordered_count"],
                      "median_speedup": result["median_paired_speedup_ordered_over_hybrid"]},
                     indent=2))


if __name__ == "__main__":
    main()

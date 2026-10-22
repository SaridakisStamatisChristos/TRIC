"""Phase XIV paired fallback comparison; do not conflate seeds with graph replications."""
import argparse
import json
import statistics
from pathlib import Path


def aggregate(paths):
    rows = []
    graph_sha = None
    for path in paths:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        if graph_sha is None:
            graph_sha = d["graph_sha256"]
        if d["graph_sha256"] != graph_sha:
            raise ValueError("different graphs must not be pooled")
        trie = d["tric"]
        topo = trie["compact_pivots_topo"]
        bidir = trie["compact_pivots_bidir"]
        bfs = next(p for p in trie["policies"] if p["name"] == "BFS")
        for key in ("pivot_probes", "pivot_rescues", "fallback_queries"):
            if topo[key] != bidir[key]:
                raise AssertionError("different pivot work: "+key)
        if topo["checksum"] != bidir["checksum"] or bidir["checksum"] != bfs["checksum"]:
            raise AssertionError("exact reachability mismatch")
        top_ns = topo["median_ns_per_query"]
        bi_ns = bidir["median_ns_per_query"]
        oreach_ns = d["oreach"]["oreach-pdfs"]["median_ns_per_query"]
        if min(top_ns, bi_ns, oreach_ns) <= 0:
            raise ValueError("nonpositive latency")
        rows.append({
            "result_file": str(path),
            "n": d["n"],
            "m": d["edges"],
            "queries": d["test_count"],
            "positive_fraction": d["heldout_positive_count"]/d["test_count"],
            "topo_hybrid_ns": top_ns,
            "bidirectional_hybrid_ns": bi_ns,
            "oreach_pdfs_ns": oreach_ns,
            "paired_topo_over_bidir": top_ns/bi_ns,
            "paired_bidir_over_oreach": bi_ns/oreach_ns,
            "bidir_additional_bytes": trie["compact_bidir"]["extra_storage_bytes"],
            "topo_fallback_edges": trie["compact_topo"]["fallback_edges"],
            "bidirectional_fallback_edges": trie["compact_bidir"]["fallback_edges"],
            "hybrid_fallback_queries": bidir["fallback_queries"]
        })
    if not rows:
        raise ValueError("no results")
    return {
        "scope": "Same graph with separate seeded splits; not independent graph replication",
        "graph_sha256": graph_sha,
        "seeds": len(rows),
        "median_paired_topo_over_bidir":
            statistics.median(row["paired_topo_over_bidir"] for row in rows),
        "bidirectional_faster_seeds":
            sum(row["bidirectional_hybrid_ns"] < row["topo_hybrid_ns"] for row in rows),
        "rows": rows,
        "claim_boundary": "Static exact SCC reachability, known bidirectional BFS; unmatched O'Reach resource budget; hosted CI timing; no SOTA/novelty claim"
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("results", nargs="+", type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    result = aggregate(a.results)
    a.out.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"seeds": result["seeds"],
                      "median_paired_topo_over_bidir": result["median_paired_topo_over_bidir"],
                      "bidirectional_faster_seeds": result["bidirectional_faster_seeds"]}, indent=2))

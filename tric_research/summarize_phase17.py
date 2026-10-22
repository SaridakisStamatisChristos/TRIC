"""Phase XVII paired off-policy, heldout fallback-dispatch qualification."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import statistics


def aggregate(paths):
    groups=defaultdict(list)
    graph_sha=None
    seen=set()
    for path in paths:
        d=json.loads(Path(path).read_text(encoding="utf8"))
        if graph_sha is None: graph_sha=d["graph_sha256"]
        if graph_sha!=d["graph_sha256"]:
            raise ValueError("different graph hashes")
        typ=d["query_stratum"]
        if typ not in ("uniform","positive","negative","balanced"):
            raise ValueError("invalid query stratum")
        key=(typ,d["query_file_sha256"])
        if key in seen: raise ValueError("duplicate query file")
        seen.add(key)
        native=d["tric"]
        strategies={k:native["compact_pivots_"+k] for k in
                    ("selector","topo","bidir","bidir_intervals")}
        checksum=next(row["checksum"] for row in native["policies"]
                      if row["name"]=="BFS")
        for k,row in strategies.items():
            if row["checksum"]!=checksum:
                raise AssertionError(k+" mismatched independent BFS oracle")
        for counter in ("pivot_probes","pivot_rescues","fallback_queries"):
            if len({x[counter] for x in strategies.values()})!=1:
                raise AssertionError("unequal pivot work")
        selected=strategies["selector"]
        if selected["training_queries"] != 500:
            raise AssertionError("selector training-set size changed")
        if selected["topological_fallbacks"]+selected["bidirectional_fallbacks"] != selected["fallback_queries"]:
            raise AssertionError("selector fallback accounting changed")
        if selected["policy_id"] not in range(9):
            raise AssertionError("unrecognized selector")
        q=d["test_count"]
        positives=d["heldout_positive_count"]
        if typ=="positive" and positives!=q or typ=="negative" and positives or typ=="balanced" and positives!=q//2:
            raise AssertionError("wrong query stratum truth fraction")
        ns={k:v["median_ns_per_query"] for k,v in strategies.items()}
        if min(ns.values())<=0:
            raise AssertionError("nonpositive measurement")
        groups[typ].append({
            "input_sha256":d["query_file_sha256"],
            "train_count":selected["training_queries"],
            "selector_policy_id":selected["policy_id"],
            "training_ns":selected["training_ns"],
            "selected_topological_fallbacks":selected["topological_fallbacks"],
            "selected_bidirectional_fallbacks":selected["bidirectional_fallbacks"],
            "queries":q,
            "positive_fraction":positives/q,
            "ns_per_query":ns,
            "bidir_over_selector":ns["bidir"]/ns["selector"],
            "topo_over_selector":ns["topo"]/ns["selector"],
            "oreach_pdfs_ns":d["oreach"]["oreach-pdfs"]["median_ns_per_query"],
            "selector_over_oreach":ns["selector"]/d["oreach"]["oreach-pdfs"]["median_ns_per_query"]
        })
    if set(groups)!=set(("uniform","positive","negative","balanced")):
        raise ValueError("missing a query class")
    if any(len(v)!=3 for v in groups.values()):
        raise ValueError("missing seeded comparisons")
    return {
        "scope":"two original published source graph instances, uniform-only selector training, four heldout classes and three seeds",
        "graph_sha256":graph_sha,
        "evaluation_boundary":"never selected using heldout labels, scores or timings; selector cost included; O'Reach memory/preprocessing unmatched",
        "strata":{typ:{
            "median_paired_bidir_over_selector":statistics.median(v["bidir_over_selector"] for v in vals),
            "median_paired_topo_over_selector":statistics.median(v["topo_over_selector"] for v in vals),
            "selector_wins_vs_bidir":sum(v["bidir_over_selector"]>1 for v in vals),
            "selector_wins_vs_topo":sum(v["topo_over_selector"]>1 for v in vals),
            "median_selector_ns":statistics.median(v["ns_per_query"]["selector"] for v in vals),
            "median_bidir_ns":statistics.median(v["ns_per_query"]["bidir"] for v in vals),
            "median_topo_ns":statistics.median(v["ns_per_query"]["topo"] for v in vals),
            "training_policy_ids":[v["selector_policy_id"] for v in vals],
            "rows":vals
        } for typ,vals in sorted(groups.items())}
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("results",nargs="+",type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    result=aggregate(args.results)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:{
        "bidir_over_selector":v["median_paired_bidir_over_selector"],
        "topo_over_selector":v["median_paired_topo_over_selector"],
        "selector_wins_bidir":v["selector_wins_vs_bidir"],
        "trained_policies":v["training_policy_ids"]
    } for k,v in result["strata"].items()},indent=2))

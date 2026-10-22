"""Phase XVIII: auditable incremental training amortization, not invented runtimes.

Use only same-graph/seed/stratum empirical benchmark records. Q horizons
extrapolate measured per-query medians and assume steady-state query mix;
they are *projections*, never executed Q-length latency benchmarks.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics

HORIZONS=(1200,10000,100000,1000000,10000000)
ARMS=("bidir","topo")


def amortize_training(fit_ns, baseline_ns, selected_ns):
    if fit_ns<0 or min(baseline_ns, selected_ns)<=0:
        raise ValueError("bad training/latency values")
    delta=baseline_ns-selected_ns
    return None if delta<=0 else math.ceil(fit_ns/delta)


def summarize(paths):
    groups=defaultdict(list)
    seen=set()
    sha=None
    train_selection=defaultdict(dict)
    origin=None
    for path in paths:
        d=json.loads(Path(path).read_text(encoding="utf8"))
        graph=d["graph_sha256"]
        if d["graph_origin"] not in ("published","synthetic"):
            raise ValueError("unrecognized or missing graph provenance")
        if origin is None:
            origin=d["graph_origin"]
        elif origin!=d["graph_origin"]:
            raise ValueError("mixed provenance for a supposedly identical graph")
        if sha is None:
            sha=graph
        if sha!=graph:
            raise ValueError("do not mix graph identities")
        typ=d["query_stratum"]
        if typ not in ("uniform","positive","negative","balanced"):
            raise ValueError("invalid stratum")
        query_hash=d["query_file_sha256"]
        if query_hash in seen:raise ValueError("repeated heldout query file")
        seen.add(query_hash)
        tric=d["tric"]
        selector=tric["compact_pivots_selector"]
        reference=next(v["checksum"] for v in tric["policies"] if v["name"]=="BFS")
        if selector["checksum"]!=reference:
            raise AssertionError("selector incorrect")
        if selector["training_queries"]!=d["training_count"]:
            raise AssertionError("missing or inconsistent training evidence")
        if not 0<=selector["policy_id"]<=8:
            raise ValueError("invalid policy")
        if selector["topological_fallbacks"]+selector["bidirectional_fallbacks"]!=selector["fallback_queries"]:
            raise AssertionError("fallback accounting mismatch")
        for k in ("pivot_probes","pivot_rescues","fallback_queries"):
            if selector[k]!=tric["compact_pivots_bidir"][k]:
                raise AssertionError("selector and control changed pivot work")
        positives=d["heldout_positive_count"]
        count=d["test_count"]
        if count<=0 or not 0<=positives<=count:
            raise AssertionError("physically impossible query true-count")
        if typ!="uniform" and positives != {
            "positive":count,
            "negative":0,
            "balanced":count//2
        }[typ]:
            raise AssertionError("stratum mislabel")
        selected_ns=selector["median_ns_per_query"]
        fit_ns=selector["training_ns"]
        row={
            "seed":d["seed"],
            "graph_origin":d["graph_origin"],
            "graph_sha256":graph,
            "query_sha256":query_hash,
            "test_count":d["test_count"],
            "positive_count":d["heldout_positive_count"],
            "policy_id":selector["policy_id"],
            "incremental_training_ns":fit_ns,
            "selector_query_ns":selected_ns,
            "shared_construction_components_ns":{
                "python_pivot_and_policy_training":d["offline_training_seconds_including_pivot_build"]*1e9,
                "native_pivot_build":tric["index_build_ms"]*1e6,
                "native_compact_build":tric["compact"]["build_ms"]*1e6},
            "baselines":{}
        }
        for arm in ARMS:
            base=tric["compact_pivots_"+arm]
            if base["checksum"]!=reference:
                raise AssertionError("control incorrect")
            baseline_ns=base["median_ns_per_query"]
            if baseline_ns<=0 or selected_ns<=0 or fit_ns<=0:
                raise ValueError("bad measurements")
            delta=baseline_ns-selected_ns
            row["baselines"][arm]={
                "query_ns":baseline_ns,
                "saved_ns_per_query":delta,
                "break_even_queries":amortize_training(fit_ns,baseline_ns,selected_ns),
                "horizons":{str(q):{
                    "selector_incremental_ns":fit_ns+q*selected_ns,
                    "baseline_incremental_ns":q*baseline_ns,
                    "net_saving_ns":q*delta-fit_ns,
                    "selector_wins":q*delta>fit_ns
                } for q in HORIZONS}
            }
        groups[typ].append(row)
        train_selection[d["seed"]][typ]=selector["policy_id"]
    if set(groups)!={"uniform","positive","negative","balanced"} or any(len(v)!=3 for v in groups.values()):
        raise ValueError("expect four query strata and three seeds each")
    if len(train_selection)!=3 or any(len(v)!=4 for v in train_selection.values()):
        raise ValueError("incomplete seed policy stability data")
    by_class={}
    for typ,rows in sorted(groups.items()):
        by_class[typ]={
            "seeds":len(rows),
            "median_policy_fit_ns":statistics.median(r["incremental_training_ns"] for r in rows),
            "selected_policies":[r["policy_id"] for r in rows],
            "wins_at_horizon":{arm:{str(q):sum(r["baselines"][arm]["horizons"][str(q)]["selector_wins"] for r in rows)
                                       for q in HORIZONS} for arm in ARMS},
            "median_paired_saved_ns":{arm:statistics.median(r["baselines"][arm]["saved_ns_per_query"] for r in rows) for arm in ARMS},
            "break_even_queries":{
                arm:[r["baselines"][arm]["break_even_queries"] for r in rows] for arm in ARMS},
            "rows":rows
        }
    return{
        "graph_sha256":sha,
        "scope":"incremental fit-cost amortization for Phase XVII selector versus same-graph bidir/topo controls",
        "source_category":origin,
        "horizon_type":"EXTRAPOLATED per-query medians, not executed at 10k/100k/1m/10m query lengths",
        "shared_cost_caveat":"Python training and native pivot construction overlap in this research harness; provided separately, NOT added as deployable system end-to-end wall time",
        "fitting_cost_caveat":"C++ reported fit_ns excludes training-oracle validation, Python common training and compiler; therefore a LOWER BOUND on total selector-specific cost",
        "stability_same_uniform_train_by_seed":{str(k):{
            "policy_by_heldout_stratum":v,
            "unique_policy_count":len(set(v.values()))
        } for k,v in sorted(train_selection.items())},
        "classes":by_class,
        "claim_boundary":"No general SOTA/novelty. Query-time medians from noisy hosted runners and two real plus synthetic graph structures; do not interpret extrapolated horizons as measurements."
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("results",nargs="+",type=Path)
    p.add_argument("--out",required=True,type=Path)
    x=p.parse_args()
    r=summarize(x.results)
    x.out.write_text(json.dumps(r,indent=2)+"\n",encoding="utf8")
    print(json.dumps({c:{
        "median_fit_ms":s["median_policy_fit_ns"]/1e6,
        "break_even_vs_bidir":s["break_even_queries"]["bidir"],
        "wins_vs_bidir_at_1200":s["wins_at_horizon"]["bidir"]["1200"],
        "wins_vs_bidir_at_1000000":s["wins_at_horizon"]["bidir"]["1000000"]
    } for c,s in r["classes"].items()},indent=2))

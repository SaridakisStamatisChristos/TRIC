"""Phase XVIII: auditable incremental offline-fit amortization model.

NO claim of measured end-to-end lifetime latency. A projection based on
pair-specific native query medians and measured *incremental* C++ selector
fitting cost. Shared pivot/SCC construction cancels between TRIC variants,
but it does not cancel against O'Reach (which is NOT modeled here).
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics

QUERY_COUNTS = (1200, 10000, 100000, 1000000, 10000000)
STRATA = ("uniform", "positive", "negative", "balanced")
BASELINES = {"bidir": "compact_pivots_bidir", "topo": "compact_pivots_topo"}


def strict_break_even(fit_ns, baseline_ns, selector_ns):
    """Smallest integer Q with Q*selector_ns + fit_ns < Q*baseline_ns."""
    if fit_ns < 0 or not math.isfinite(fit_ns):
        raise ValueError("invalid selector training cost")
    if min(baseline_ns, selector_ns) <= 0 or not (
            math.isfinite(baseline_ns) and math.isfinite(selector_ns)):
        raise ValueError("invalid per-query latency")
    saving = baseline_ns - selector_ns
    if saving <= 0:
        return None
    # Strictly positive savings, not a tie; these are timing estimates.
    return math.floor(fit_ns / saving) + 1


def amortize(paths):
    rows = defaultdict(dict)
    graph_sha = None
    training_by_seed = {}
    for path in paths:
        d = json.loads(Path(path).read_text(encoding="utf8"))
        if graph_sha is None:
            graph_sha = d["graph_sha256"]
        if d["graph_sha256"] != graph_sha:
            raise ValueError("different graph SHA256 values must not be pooled")
        cls = d.get("query_stratum")
        seed = d.get("seed")
        if cls not in STRATA or seed not in (20261022, 20261023, 20261024):
            raise ValueError("invalid stratum or seed provenance")
        if seed in rows[cls]:
            raise ValueError("duplicate graph/seed/stratum result")
        n = d["test_count"]
        truths = d["heldout_positive_count"]
        if n <= 0 or ((cls == "positive" and truths != n)
                      or (cls == "negative" and truths != 0)
                      or (cls == "balanced" and truths != n//2)):
            raise AssertionError("heldout class mismatch")
        fingerprint = d.get("selector_training_queries_sha256")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise ValueError("missing/invalid training input fingerprint")
        if d["selector_training_count"] != 500:
            raise ValueError("unexpected number of train-only queries")
        if seed in training_by_seed and training_by_seed[seed] != fingerprint:
            raise AssertionError("same-seed uniform training data changed between strata")
        training_by_seed[seed] = fingerprint

        tric = d["tric"]
        ref = next(x["checksum"] for x in tric["policies"] if x["name"] == "BFS")
        selector = tric["compact_pivots_selector"]
        fit_ns = selector["training_ns"]
        if selector["training_queries"] != d["selector_training_count"]:
            raise AssertionError("selector fitted on different input count")
        if not isinstance(fit_ns, (int, float)) or not math.isfinite(fit_ns) or fit_ns < 0:
            raise ValueError("nonfinite or negative fit cost")
        if selector["policy_id"] not in range(9):
            raise ValueError("invalid selected policy")
        if selector["topological_fallbacks"] + selector["bidirectional_fallbacks"] != selector["fallback_queries"]:
            raise AssertionError("invalid selector dispatch counter")

        controls = {k: tric[v] for k, v in BASELINES.items()}
        if any(x["checksum"] != ref for x in (selector, *controls.values())):
            raise AssertionError("incorrect reachability checksum")
        for stat in ("pivot_probes", "pivot_rescues", "fallback_queries"):
            if len({x[stat] for x in (selector, *controls.values())}) != 1:
                raise AssertionError("unequal pivot probe and fallback work")
        sel_ns = selector["median_ns_per_query"]
        if not math.isfinite(sel_ns) or sel_ns <= 0:
            raise ValueError("invalid selector query latency")

        comparisons = {}
        for name,control in controls.items():
            base_ns = control["median_ns_per_query"]
            threshold = strict_break_even(fit_ns, base_ns, sel_ns)
            saving = base_ns - sel_ns
            comparisons[name] = {
                "baseline_ns_per_query": base_ns,
                "selector_ns_per_query": sel_ns,
                "query_saving_ns": saving,
                "strict_break_even_queries": threshold,
                "scenario_net_savings_ns": {
                    str(q): q * saving - fit_ns for q in QUERY_COUNTS
                }
            }
        rows[cls][seed] = {
            "seed":seed,
            "source_file":str(path),
            "heldout_count":n,
            "heldout_positive_count":truths,
            "heldout_query_sha256":d["query_file_sha256"],
            "train_input_sha256":fingerprint,
            "selector_policy_id":selector["policy_id"],
            "incremental_offline_fit_ns":fit_ns,
            "comparisons":comparisons
        }

    if set(rows) != set(STRATA) or any(set(v)!={20261022,20261023,20261024} for v in rows.values()):
        raise ValueError("must have exactly three distinct seeds for all four query classes")

    strata = {}
    for cls in STRATA:
        observations = [rows[cls][seed] for seed in sorted(rows[cls])]
        baseline_summary = {}
        for name in BASELINES:
            values = [r["comparisons"][name] for r in observations]
            break_evens = [x["strict_break_even_queries"] for x in values]
            baseline_summary[name] = {
                "strict_query_latency_wins":sum(x["query_saving_ns"] > 0 for x in values),
                "no_finite_break_even_seeds":sum(x is None for x in break_evens),
                "per_seed_strict_break_even_queries":break_evens,
                "modelled_net_wins_by_query_count":{
                    str(q):sum(x["scenario_net_savings_ns"][str(q)] > 0 for x in values)
                    for q in QUERY_COUNTS
                },
                "median_query_saving_ns":statistics.median(
                    x["query_saving_ns"] for x in values)
            }
        strata[cls] = {"seeds":observations,"baselines":baseline_summary}

    policy_variation = {
        str(seed):sorted(set(rows[cls][seed]["selector_policy_id"] for cls in STRATA))
        for seed in (20261022,20261023,20261024)
    }
    return {
        "graph_sha256":graph_sha,
        "method":"analytical extrapolation from paired per-seed native query medians + measured additional offline selector fit cost",
        "NOT_MEASURED":"No end-to-end runtime at projected volumes has been executed; future workloads may differ; O'Reach index costs not comparable",
        "cost_accounting":"Shared TRIC pivot training, SCC builds, and index storage CANCEL when comparing selector against topo/bidir on the same graph. They are not omitted from any cross-system claim because none is made.",
        "query_counts":list(QUERY_COUNTS),
        "uniform_train_same_across_all_heldout_classes":True,
        "train_fingerprints_by_seed":{str(seed):fp for seed,fp in sorted(training_by_seed.items())},
        "selected_policies_by_seed_across_identical_uniform_training":policy_variation,
        "strata":strata
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("results",type=Path,nargs="+")
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    result=amortize(args.results)
    args.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps({cls:{
        name:{
            "strict_latency_wins":data["strict_query_latency_wins"],
            "non_break_even_seeds":data["no_finite_break_even_seeds"],
            "Q_1200_net_wins":data["modelled_net_wins_by_query_count"]["1200"],
            "Q_1000000_net_wins":data["modelled_net_wins_by_query_count"]["1000000"]
        } for name,data in group["baselines"].items()
    } for cls,group in result["strata"].items()},indent=2))


if __name__=="__main__":
    main()

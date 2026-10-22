"""Independent Phase XXII evidence gate, separate from the benchmark producer.

A passing synthetic CI job proves TRIC's exactness and measured lifetimes,
not that the original O'Reach executable supported the generated topology.
Never reinterpret missing external timing as a zero-cost/winning baseline.
"""
import argparse
import json
import math
from pathlib import Path

CLASSES=("matched_hot","uniform","shifted_hot")
HORIZONS=("1","50")
MODES=("pivot_index","cache_pivot_index")
UNAVAILABLE=("unavailable_upstream_segfault",
             "unavailable_after_upstream_segfault")

def verify(summary_path,dataset,seed,require_external_complete=False):
    path=Path(summary_path)
    obj=json.loads(path.read_text())
    if obj.get("dataset")!=dataset or obj.get("seed")!=seed:
        raise AssertionError("provenance identity mismatch")
    if set(obj.get("classes",{}))!=set(CLASSES):
        raise AssertionError("missing exact classes")
    is_generated=dataset.startswith("generated_")
    if not is_generated and dataset not in {"example","kron_logn12"}:
        raise AssertionError("unknown published dataset")
    if require_external_complete and obj.get("upstream_comparisons_complete") is not True:
        raise AssertionError("all external comparators must be measured in the repaired matrix")
    comparator_meta=obj.get("oreach_comparator_input",{})
    if is_generated and require_external_complete:
        if comparator_meta.get("mode")!="original_pinned_binary_support0_scc_quotient":
            raise AssertionError("generated graph missing explicit nondefault comparator provenance")
        if comparator_meta.get("upstream_support_parameter")!=0:
            raise AssertionError("synthetic original O-Reach should avoid invalid support sampling")
        if comparator_meta.get("original_graph_sha256")!=obj.get("graph_sha256"):
            raise AssertionError("comparator source graph SHA disagrees with TRIC graph")
        if comparator_meta.get("comparator_scc_nodes",0)<1:
            raise AssertionError("missing quotient graph shape")
        input_dir=path.parent/"oreach_compatible_graph"
        for key,fn in (("comparator_graph_sha256","semantically_equivalent_scc_dag.metis"),
                       ("mapping_sha256","vertex_to_scc.json")):
            if not (input_dir/fn).is_file():
                raise AssertionError("missing exact comparator replay input")
            from oreach_compatible_input import digest
            if digest(input_dir/fn)!=comparator_meta[key]:
                raise AssertionError("comparator graph/mapping provenance hash mismatch")
    external=obj.get("upstream_comparator_per_class",{})
    if set(external)!=set(CLASSES):
        raise AssertionError("no explicit external-comparator evidence")
    unavailable=[]
    for cls in CLASSES:
        status=external[cls]
        state=status.get("status")
        if state=="measured":
            if status.get("valid_comparisons",0)<1:
                raise AssertionError("measured competitor requires actual valid runs")
        elif state in UNAVAILABLE:
            if not is_generated or status.get("valid_comparisons")!=0:
                raise AssertionError("upstream failure masked on authentic graph or invented timings")
            if state=="unavailable_upstream_segfault":
                if status.get("returncode") not in (139,-11) or status.get("signal")!=11:
                    raise AssertionError("non-SIGSEGV failure silently skipped")
            else:
                trigger=status.get("trigger",{})
                if trigger.get("status")!="unavailable_upstream_segfault" or trigger.get("signal")!=11:
                    raise AssertionError("previously failed external comparator lacks cause")
            unavailable.append(cls)
        else:
            raise AssertionError(f"invalid original-comparator status: {state}")
        comp=json.loads((path.parent/cls/"comparison.json").read_text())
        if is_generated and require_external_complete:
            equivalence=comp.get("oreach_query_equivalence",{})
            if equivalence.get("equivalence_verified_pairs")!=obj["query_set_size_per_class"]:
                raise AssertionError("missing independent original vs mapped query equivalence proof")
            if equivalence.get("positive_count")!=comp.get("positive_count"):
                raise AssertionError("original and quotient query truth differ")
            for key,fn in (("original_query_sha256","heldout.query.m.txt"),
                           ("translated_query_sha256","oreach_equivalent.query.m.txt")):
                from oreach_compatible_input import digest
                if digest(path.parent/cls/fn)!=equivalence[key]:
                    raise AssertionError("exact original/normalized query artifact changed")

        if comp["oreach_status"]["status"]!=state:
            raise AssertionError("class report and full report contradict")
        for method in ("oreach-pdfs","oreach-pbibfs"):
            if state=="measured":
                m=comp["times"].get(method,{})
                if not math.isfinite(m.get("median_ns_per_query",float("nan"))) or m["median_ns_per_query"]<=0:
                    raise AssertionError("measured external timings missing")
            elif method in comp["times"]:
                raise AssertionError("unavailable original competitor has invented query latency")
        cells=obj["classes"][cls]
        if set(cells)!=set(HORIZONS):
            raise AssertionError("missing actual lifetime horizon")
        for factor in HORIZONS:
            entry=cells[factor]
            expected=obj["query_set_size_per_class"]*int(factor)
            for mode in MODES:
                d=entry[mode]
                if (d["actual_query_calls"]!=expected or
                    d["checksum_verified"] is not True or
                    d["median_build_plus_query_ns"]<=0 or
                    d["median_maxrss_kib"]<=0 or
                    len(d.get("samples_build_plus_query_ns",[]))!=obj["lifetime_repetitions"]):
                    raise AssertionError("invalid TRIC replay, oracle or memory evidence")
            ext=entry["original_oreach_pdfs_fresh_process"]
            if state=="measured":
                if ext.get("actual_calls")!=expected or ext.get("full_external_process_wall_ns",0)<=0:
                    raise AssertionError("missing real original-comparator lifetime sample")
            elif (ext.get("status")!="unavailable_upstream_segfault" or
                  ext.get("valid_comparisons")!=0 or ext.get("actual_calls")!=0):
                raise AssertionError("invented upstream process evidence")
    if bool(unavailable)==bool(obj.get("upstream_comparisons_complete")):
        raise AssertionError("external completeness flag contradicts per-class evidence")
    print(json.dumps({
        "phase":"XXII",
        "dataset":dataset,
        "seed":seed,
        "tric_lifecycle_status":"fully_executed_and_checked",
        "original_oreach_external_status":(
            "incomplete_upstream_segfault" if unavailable else "all_measured"),
        "unavailable_comparator_classes":unavailable,
        "evaluated_graph_is_generated":is_generated,
        "valid_native_workloads":len(CLASSES)*len(HORIZONS),
    }),flush=True)
    if unavailable:
        print("::warning::Original pinned O-Reach SIGSEGV on generated graph; original external comparator UNAVAILABLE, NOT PASSED. TRIC native exactness and lifecycle measurements remain complete.",flush=True)
    return unavailable

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--summary",type=Path,required=True)
    ap.add_argument("--dataset",required=True)
    ap.add_argument("--seed",type=int,required=True)
    ap.add_argument("--require-external-complete",action="store_true",
                    help="Require valid measured original O-Reach result for every class")
    args=ap.parse_args()
    verify(args.summary,args.dataset,args.seed,args.require_external_complete)

# TRIC — Reachability Certificates and Exact Pivot Optimization

**Research prototype | 21 October 2026**

TRIC studies exact directed-graph reachability certificates, workload-aware pivot selection, efficient exact optimization on directed paths, and complexity boundaries for DAGs with a directed backbone.

> **Research integrity:** The original three supportive-vertex reachability rules overlap O'Reach (2022) and must not be presented as novel. The original Python timings and subsequent native comparisons have bounded experimental scope and do not establish generalized SOTA. The novelty and publication status of the later exact-optimization results remain unresolved.

## Research phases

- **Phase I:** Original experimental certificate engine, correctness tests, weighted-query optimization, benchmark evidence.
- **Phase II:** Exact directed-path optimization using Monge DP and a sweep-line segment tree, including memory/time comparisons.
- **Phase III:** DAG-backbone certificate geometry, a constructive Vertex Cover reduction for budgeted pivot selection, linear graph-time signature extraction, and an exact fixed-parameter method.

## Project contents

The complete research artifacts originate from `TRIC_Phase_III_Research_2026-10-21.zip` and include implementation files, tests, benchmark scripts, JSON measurements, and research reports. The original source, reports, tests, and benchmark data are available in [`tric_research/`](tric_research/).

## Reproduce (Python 3.10+)

```bash
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone
python benchmark_optimizers.py
python benchmark_backbone.py
```

## Notes

This is an **active research project**, not a vetted production graph library or submission-ready publication. All theoretical and empirical claims must be independently checked against the cited literature and archived runs.

Created collaboratively in the ChatGPT TRIC research initiative.

## Archived phase snapshots

The three original deliverable archives are preserved verbatim in [`archives/`](archives/): the Phase I prototype, Phase II research package, and Phase III research package. Browse [`tric_research/`](tric_research/) for the directly accessible source, tests, research notes, and benchmark evidence.


## Native graph-only exact reachability

A dependency-free C++17 API now complements the Python pivot-optimization research.
`TricReachability` uses direct SCC bitset closure when it fits the table allowance;
otherwise it uses compact forest labels when applicable, or partitioned
chain/bitset labels, exact interval unions, lossless sparse-row compression,
and exact search on table refusal. It needs no query training. Interval labels
cache their widest complete range without adding memory.
The common query path keeps residual lookup and fallback work in separate
helpers, allowing supported compilers to inline the quick certificate checks.
The interval construction directory is released after its offsets and counts
have been copied into vertex labels, saving eight retained bytes per interval
SCC on the tested toolchain without changing admission or query code.

See [native runtime usage and limitations](NATIVE_RUNTIME.md). The table allowance
is not a total-memory cap. The existing research algorithms and archives remain
available. [Latest comparative evidence, regressions and remaining gaps](tric_research/PHASE_XXX_RESEARCH_REPORT.md)
are recorded in Phase XXX; no universal SOTA or novel algorithm claim is made.
Phase XXXI rejected four query optimizations. [Phase XXXII](tric_research/PHASE_XXXII_RESEARCH_REPORT.md)
validates the directory release with independent allocation tracking; it makes
no new latency or external-comparator claim. See [current status](RESEARCH_STATUS.md).

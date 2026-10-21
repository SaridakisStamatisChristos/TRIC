# TRIC — Reachability Certificates and Exact Pivot Optimization

**Research prototype | 21 October 2026**

TRIC studies exact directed-graph reachability certificates, workload-aware pivot selection, efficient exact optimization on directed paths, and complexity boundaries for DAGs with a directed backbone.

> **Research integrity:** The original three supportive-vertex reachability rules overlap O'Reach (2022) and must not be presented as novel. The reported timing results use local Python prototypes and do not establish superiority over existing graph reachability indexes. The novelty and publication status of the later exact-optimization results remain unresolved.

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

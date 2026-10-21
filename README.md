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


## Phase IV — Exact certificates on cyclic graphs

Phase IV extends the known-backbone optimization to **arbitrary directed graphs** by condensing strongly connected components (SCCs), dropping redundant same-SCC backbone pivots, and reusing Phase III's exact interval selector.

- [Phase IV research report](tric_research/PHASE_IV_RESEARCH_REPORT.md) — proof arguments, complexity, literature boundaries, and limitations
- [Phase IV usage and reproduction](tric_research/PHASE_IV_README.md)
- [SCC backbone implementation](tric_research/backbone_scc.py)
- [SCC correctness tests](tric_research/test_backbone_scc.py) and [benchmark evidence](tric_research/phase4_benchmark.json)

Run: `cd tric_research && python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc`.

**Scientific caveat:** SCC condensation and O'Reach's supportive-vertex certificates are existing methods. This specialized exact extension is experimentally checked on small instances, but no distinct SOTA or publication-level novelty claim has been established.

## Phase V — Exact optimization by frontier width

Phase V adds a frontier-state exact weighted selector for one- and two-interval certificate signatures. Its worst-case exponent depends on the maximum number of simultaneously live two-interval query statuses (`w`) rather than the total number of two-interval signatures (`r`). It complements the Phase III orientation-enumeration algorithm; performance can still be exponential when `w` is large.

- [Phase V research report](tric_research/PHASE_V_RESEARCH_REPORT.md)
- [Implementation](tric_research/frontier_dp.py)
- [Tests](tric_research/test_frontier_dp.py) · [Local benchmark](tric_research/phase5_benchmark.json)

Run `cd tric_research && python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp`.

**Scientific caveat:** Frontier-based dynamic programming and partial multi-interval stabbing have existing literature; no publication-level novelty claim has been established. Local Python improvements against the earlier TRIC selector are not comparisons against O'Reach.


## Phase VI — Exact adaptive budget-profile decomposition

Phase VI groups weighted certificate queries by disjoint support hulls, computes each group's exact pivot-budget profile, and allocates the total pivot budget by min-plus convolution. It combines the existing path-sweep, orientation and frontier engines. Cyclic graphs are supported through Phase IV SCC compression.

- [Phase VI research report](tric_research/PHASE_VI_RESEARCH_REPORT.md) — exactness argument, costs, limitations and prior-art boundaries
- [Adaptive optimizer](tric_research/adaptive_exact.py) · [Tests](tric_research/test_adaptive_exact.py) · [Exploratory benchmark](tric_research/phase6_benchmark.json)

Run all phase tests with `cd tric_research && python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact`.

**Scientific limitation:** The decomposition and dynamic-programming operations use established techniques. No new reachability certificate, global novelty, or O'Reach superiority is claimed from this internal Python prototype.

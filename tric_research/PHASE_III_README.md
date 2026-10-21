# Phase III: exact DAG-backbone pivot selection

This continues the original TRIC research package without overwriting Phase I and II artifacts. It investigates a restricted but rigorously defined problem: selecting a fixed number of **backbone-only** O'Reach-supportive pivots for a weighted query workload on a DAG containing a known directed path.

**Main deliverables**

- O(|V|+|E|+|Q|) certificate interval extraction via topological propagation (`backbone_intervals_fast`).
- Constructive NP-completeness reduction from Vertex Cover (`make_vertex_cover_instance`).
- Exact parameterized optimizer with runtime exponential only in distinct two-piece query signatures (`optimize_backbone`).
- Differential, exhaustive, and adversarial tests; benchmark scripts and raw results.

**Status:** tested research prototype; literature novelty not established; no comparison claiming superiority to O'Reach.

**Commands**

```
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone
python benchmark_backbone.py
```

Read `PHASE_III_RESEARCH_REPORT.md` for the theorem statements, proofs, computational limits and prior art.

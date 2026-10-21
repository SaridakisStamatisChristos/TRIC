# Phase VIII — Exact cost-aware ordered pivot selection

Phase VIII adds a **separate** work-model optimization. Earlier phases maximize certificate *coverage*; Phase VIII exactly minimizes total modeled probe plus fallback cost over any ordered subset of <= k candidate pivots.

```bash
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact test_frontier_compact test_ordered_probe
python benchmark_ordered_probe.py
```

- `ordered_probe.py`: exact subset DP with subset-zeta preprocessing; per-query certifier masks, independent direct objective checker and a coverage-greedy comparator.
- `test_ordered_probe.py`: exhaustive permutation oracle, random floating-weight oracle, graph-certificate checks, no-index cases, malformed input checks.
- `benchmark_ordered_probe.py`, `phase8_benchmark.json`: held-out synthetic graph workloads with measured preprocessing, selection, query work proxy and actual CPython test inference timing.
- `PHASE_VIII_RESEARCH_REPORT.md`: precise objective, proof, benchmark protocol, prior-art map, reviewer objections and publication gates.

**Limits:** Runtime is exponential in number of candidate pivots, not graph vertices. A trained ordered cost proxy is not measured end-to-end latency. The algorithm is a known-family exact engineering approach, **not an established new algorithm**. No actual O'Reach runtime baseline is present.

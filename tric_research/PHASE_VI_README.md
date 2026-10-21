# Phase VI — Exact Adaptive Component Decomposition

Phase VI adds `adaptive_exact.py`: an exact solver for selecting weighted reachability-certificate pivots on a designated directed backbone. It uses disjoint support-hull components, computes per-component pivot-budget profiles with the Phase II, III, and V engines, and distributes the budget through min-plus convolution. It also supports cyclic graphs via Phase IV SCC condensation.

## Usage

```python
from adaptive_exact import optimize_adaptive, optimize_scc_adaptive

queries=[((1,1),(3,3)), ((8,8),(10,10)), ((17,18),)]
weights=[4,7,2]
pivots, uncovered, stats=optimize_adaptive(21,queries,weights,2)
assert len(set(pivots))==2

# For cyclic graph inputs:
# pivots, uncovered, stats = optimize_scc_adaptive(adj, backbone, vertex_pairs, weights, k)
```

Run `python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact` from `tric_research/` to validate all phases. To regenerate exploratory synthetic timings, run `python benchmark_adaptive.py > phase6_benchmark.json`.

See [Phase VI report](PHASE_VI_RESEARCH_REPORT.md) for exact proof, limitations, and novelty caveats. **Do not claim global novelty, superior indexing performance, or publication readiness from the local results.**

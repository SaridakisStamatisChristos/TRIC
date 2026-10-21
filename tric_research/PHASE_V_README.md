# Phase V: Exact Pivot Selection Parameterized by Frontier Width

This phase introduces [`frontier_dp.py`](frontier_dp.py), an exact dynamic-programming alternative to Phase III's global orientation enumeration for weighted one- or two-interval query signatures.

**Why:** Existing Phase III is exponential in the total `r` of separated signatures. Phase V is exponential in the maximum number `w` of simultaneously pending separated signatures. On geographically separated or low-overlap workloads, `w` can be much smaller than `r`.

## Usage

```python
from frontier_dp import optimize_frontier, optimize_scc_frontier

intervals = [((0, 0), (2, 2)), ((4, 4), (6, 6))]
pivots, uncovered, diagnostics = optimize_frontier(8, intervals, [3, 5], 1)
# For original cyclic directed graphs:
# pivots, uncovered, diagnostics = optimize_scc_frontier(adj, backbone, queries, weights, k)
```

## Run tests and exploratory measurements

```bash
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp
python benchmark_frontier.py > phase5_benchmark.json
```

See [`PHASE_V_RESEARCH_REPORT.md`](PHASE_V_RESEARCH_REPORT.md) for proof, complexity, limitations, and prior-art boundaries. No publication-grade novelty claim has been established.

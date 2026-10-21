# TRIC Phase VII — Active-Start Equivalence Compression

## Use

From `tric_research/`:

```python
from frontier_compact import optimize_compact, optimize_compact_profile
from adaptive_exact import optimize_adaptive

intervals = [((1, 6), (75, 79)), ((1, 7), (76, 79)), ((1, 8), (77, 79))]
weights = [3, 4, 5]
pivots, missed_weight, diagnostics = optimize_adaptive(80, intervals, weights, 5, engine='auto')
profile, stats = optimize_compact_profile(80, intervals, weights, 5)
```

`optimize_compact` returns selected positions, exact missed weight, and diagnostics for one exact budget. `optimize_compact_profile` returns costs and valid witnesses for every exact budget `0..max_k`.

Phase VI's `optimize_adaptive(..., engine='compact')` and `optimize_scc_adaptive(..., engine='compact')` route this engine through region budgets and SCC condensation. `engine='auto'` uses a conservative threshold on interval-start diversity; alternatives remain available.

## Verify

```sh
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact test_frontier_compact
python benchmark_phase7_adaptive.py > phase7_adaptive_results.json
```

**Scientific caveat:** Correctness is tested, but frontier-state compression is not claimed to be globally novel. Times are local exploratory microbenchmarks and do not compare with O'Reach or real graph workloads. Full proof argument and limitations: [`PHASE_VII_RESEARCH_REPORT.md`](PHASE_VII_RESEARCH_REPORT.md).

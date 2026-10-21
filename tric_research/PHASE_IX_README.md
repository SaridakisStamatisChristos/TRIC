# Phase IX — Native Query-Latency Validation

Phase IX evaluates Phase VIII's selected certificate-probe orders with **a separate C++17 query implementation**. It is experimental validation, *not* an external O'Reach comparison.

Run from `tric_research`:

```bash
python -m unittest discover -p 'test_*.py' -q
python benchmark_native.py --test 24000 --repetitions 15 --output phase9_native_results_controlled.json
```

Artifacts:

- `native_query_bench.cpp`: zero-dependency C++17 executor with BFS oracle, checksum, per-policy time/coverage statistics and randomized rotated executions
- `benchmark_native.py`: deterministic graph/query generation, existing Phase VIII policy selection, graph transfer, offline-training accounting, held-out modeled-work audit, compiler metadata
- `test_native_benchmark.py`: native differential tests on DAGs, cyclic graphs, and empty/reflexive graphs
- `phase9_native_results_controlled.json`: native O3 raw measurements, 24 cases, 15 repetitions each
- `phase9_native_results_O2.json`: native O2 comparison pilot, 12 cases
- `PHASE_IX_RESEARCH_REPORT.md`: complete claims, prior-art limits, negative results, reproducibility and missing scientific gates

The core scientific conclusion is narrow: cost-aware pivot ordering reduces actual compiled query latency **in some** synthetic regimes, but **not universally**, and setup/training may dominate realistic query counts. A null-policy control verifies that time measurement effects can mimic speedup when both algorithms perform exactly the same work.

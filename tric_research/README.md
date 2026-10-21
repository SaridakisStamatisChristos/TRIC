# TRIC reachability research (Phase I + Phase II)

**Research status: exact experimental prototype, not a novel/SOTA-certified algorithm.**

**Important prior art:** O'Reach (2022) already contains the same three supportive-vertex positive/negative reachability conditions as the original TRIC certificates. Do not claim those three rules as a new invention. See [PHASE_II_RESEARCH_REPORT.md](PHASE_II_RESEARCH_REPORT.md) for the explicit overlap, improved exact optimizers, correctness analyses, benchmark evidence, and remaining publication blockers.

- `RESEARCH_NOTE.md`: Phase I graph reachability and prototype dossier.
- `tric.py`: original certificate engine and quadratic path optimizer.
- `path_monge.py`: O(n²+|Q|+kn log n) exact path optimization using Monge DP.
- `path_sweep.py`: O(k(n+|Q|) log n) exact path optimization using range-add/min event sweeping.
- `optimizer_comparison.json`, `pivot_quality.json`: local Phase II measurements.

All commands below use standard Python 3.10+:

```bash
python -m unittest -q test_tric test_path_monge test_path_sweep
python benchmark_optimizers.py
python benchmark_pivot_quality.py
```

Static graph assumptions; no incremental certificate maintenance. Published algorithms are not included and no head-to-head state-of-the-art comparison has been executed.

## Phase III — DAG backbone (21 October 2026)

See [PHASE_III_README.md](PHASE_III_README.md) and [PHASE_III_RESEARCH_REPORT.md](PHASE_III_RESEARCH_REPORT.md). New result: linear-time backbone certificate extraction; constructive Vertex Cover hardness proof for exhaustive certification; FPT exact optimizer parameterized by distinct separated query intervals / number of off-backbone vertices. **Novelty and paper readiness remain unverified.**

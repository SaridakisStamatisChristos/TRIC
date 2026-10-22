# TRIC Phase XXIII — Exact Native Training + Streaming Cache Admission

Date: 2026-10-22. Status: research candidate, opt-in only. Parent: Phase XXII draft PR #21 (`a09f92ef929150d380c8d29ac86d4ce84418dabc`).

## Problem statement and frozen baseline

Phase XXII established narrow gains of an exact train-only hot-source cache over indexed TRIC for repeated hot sources, but that gain shrinks when expensive Python pivot training is included. On uniform or shifted-source traffic, eager cache construction and lookup may cause regressions. No unrestricted SOTA claim or default promotion is warranted.

The two changes in Phase XXIII are **separable**:

1. **Mechanically equivalent training implementation**: C++17 extracts the same forward/backward pivot reachability hit masks and exactly the same Python `early_reachable` DFS edge counts using the same candidate vertices and train-only query pairs. The original `optimize_ordered` subset DP and `greedy_coverage_order` functions still select the pivot order. The C++ binary never receives heldout pairs or truth labels. It reports raw arrays for independent parity checks against the unchanged Python reference.
2. **Opt-in online cache admission**: Additional fresh-process lifetime arm `adaptive_cache_pivot_index`, leaving Phase XXII `pivot_index` and `cache_pivot_index` as untouched control semantics. It builds pivots and compact index first but **does not build a source cache** until first observing 256 *live source IDs*, and only if future supplied workload horizon is at least 50,000 total calls **and** at least 60% of observed sources belong to the training-only, frequency-eligible capped cache candidate set. If not admitted, the arm stays indexed and allocates no source-cache rows. Actual late cache construction is included within the timed query loop, not excluded from the full build-plus-query time.

## Exactness invariants

- Graph, candidates, training pairs and budget are identical for Python and C++; C++ mask and fallback arrays, greedy/ordered order and objective must match **exactly**. Independent Python reference remains unmodified.
- Cache admissions observe only source IDs from the **first 256 actual queries**. They never inspect target IDs, answer labels, future query frequencies, oracle output, heldout graph reachability, or baseline timing. Replayed heldout queries count as real calls, **not independent new queries**.
- Cache uses the original `HotSourceCache` exact bitmap builder with the original retained byte cap and frequency threshold of three. On misses, answer from existing compact-index certificate/pivot and exact bidirectional traversal, regardless of cache state.
- Independent DFS verification for all distinct heldout test queries occurs outside the native timed query section. All mode checksums, exact input hashes and process metadata must agree.
- A cache-admission refusal is not a claim of high performance; per-run end-to-end cost and peak RSS are required, with both short 2,400-query and longer 120,000-call horizons.
- Eager cache construction cost is **before** the timed query loop; deferred cache construction happens **inside** the timed loop and is fully included in total end-to-end time.

## Experimental design

Five graph families from Phase XXII: authentic arXiv and Kronecker, explicitly generated fixed-seed DAG, blocks and communities. Three train/query seeds, 500 train-only pairs, 2,400 heldout pairs in matched-hot, uniform and shifted-hot classes. Each graph/seed runs three alternating paired training measurements, with native input serialization, subprocess and subset DP included. Compilation is excluded equally from both training timing arms and is reported as a separate deployment cost. Identical C++ indexed query execution verifies policies.

Lifecycle: index-only, eager cache and admitted cache, fresh processes with position-balanced repetitions, at 1× and 50× test-set replays. MaxRSS and retained bytes are distinct. Training is measured separately and must be added when assessing total solution cost; independent O'Reach comparisons remain Phase XXII.

## Prespecified qualification criteria

**Mechanically equivalent native training**: all graph/seed runs and tests must pass with *zero* mask, fallback cost, ordered/greedy objective, oracle checksum or protocol discrepancies. Claim training acceleration only if end-to-end measured native fitting including serialization/process and DP is faster in at least 12/15 graph/seed cells with three paired repetitions. Retain slowdowns and outliers.

**Online admission**: correctness must pass unconditionally, no cache rows for short horizon, and no unanticipated cache admission on uniform or shifted class under 15 seeds. Matched-hot should normally admit, but threshold outcomes must be reported even when the predictive policy fails. Gate remains only a research candidate: known fixed query horizon is an API contract assumption not guaranteed in production.

**Global TRIC default promotion: NO-GO** independently of these pilot outcomes. An adaptive policy introduces new deployment assumptions (unknown horizon, midstream distribution change, online synchronization, concurrency, memory accounting). No unconditional speedup, automatic adoption, altered baseline PRs or novelty claim.

## Artifact provenance

`native_training_phase23.cpp`, `phase23_training.py`, `benchmark_phase23.py`, `phase23_admission.py`, `test_phase23_training.py`, `test_phase23_admission.py`, `.github/workflows/research-phase23.yml`, plus an experimental optional mode in `lifetime_replay.cpp`. GitHub artifacts include `phase23_summary.json` with each trial, process median/peak RSS and admission decisions, as well as graph hashes and environment.

At initial proposal time **the full matrix is not yet observed**. Do not fill performance values with forecasts, relabeled Phase XXII samples, or guesses. Record final exact SHA, workflow results and remaining failures after CI actually finishes.

## Main limitations

Training two physically separate graph-loading paths is still required when the native trainer and query runner run in distinct processes. A production integrated runner could reuse the resident compact index and pivot bitsets, but doing so would change the architecture and warrants its own measurement. The 60%/256/50,000 thresholds are transparent *hypotheses*, not calibrated statistically or claimed optimal. Fixed source-prefix admission could be wrong after abrupt distribution drift; this remains explicit research scope.

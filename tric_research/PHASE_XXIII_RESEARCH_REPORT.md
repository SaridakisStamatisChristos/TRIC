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


## Observed Phase XXIII qualification — CI run 39847666038

Evidence: [pinned 17-job Phase XXIII CI](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39847666038), plus [2/2 full tests](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39847666028) and [15/15 Phase XXII regression tests](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39847666022), all on **0c79a6c84d5e8e8d69fc3ee3d065d599eb657a83**.

All 15 dataset/seed artifacts were downloaded and inspected from the named GitHub workflow. They contain independent Python/C++ parity, per-run training timings, and the actual three-arm native lifecycle comparisons, not estimates.

### Native train-only optimizer: same result, lower cost in 12/15 cells

The median of 15 *within-dataset/seed* median legacy/native training ratios is **7.39×**. Exactly **12/15** cells improve; this *meets but does not exceed* the preregistered minimum of 12/15 cells. The three regressions are all synthetic block instances, with native at **0.87×, 0.93×, 0.93×** of the Python trainer. This requires maintaining the legacy fallback for small/sparse disconnected training regimes.

| Dataset | Native training speedup, three seeds |
| --- | --- |
| arXiv | 12.52×, 6.24×, 7.70× |
| Kronecker | 15.98×, 8.83×, 10.92× |
| Generated DAG | 10.91×, 9.80×, 7.27× |
| Generated blocks | **0.87×, 0.93×, 0.93×** (regression) |
| Generated communities | 7.39×, 7.15×, 5.58× |

These are *training pipeline timings*, including native serialization/subprocess/DP, excluding compilation and candidate preselection from both alternatives. Candidate order, per-query hit masks, fallback edge counts, greedy/ordered policy and model objective were checked for **exact parity**. Full original O-Reach external comparisons remain part of Phase XXII, not Phase XXIII.

### Online cache admission: all 45 source-shape/horizon-50 decisions as intended

At the **120,000 actual-call** horizon, the source-only gate admitted the cache in **15/15 matched-hot** cases and refused it in **15/15 uniform** plus **15/15 shifted-hot** cases. Cache rows remain unallocated after refusal. All three modes had the same per-run heldout answers against the independent reachability oracle. At the short 2,400-call horizon, the gate refuses admission by design.

Across all 15 graph-seed cases, the medians of adaptive/cache-free full native build-plus-query ratios were **1.223× matched-hot**, **0.988× uniform**, and **0.992× shifted-hot**. The negative-class medians represent **small remaining overhead** from admission instrumentation; neither class produced a slowdown worse than 5% on these 30 measured cells. For matched-hot, adaptive beat cache-free indexed TRIC in **15/15** cells, but the sizes and improvement are graph-specific.

| Dataset | Adaptive matched-hot full native speedup, three seeds |
| --- | --- |
| arXiv | 1.469×, 1.417×, 1.483× |
| Kronecker | 1.083×, 1.069×, 1.125× |
| Generated DAG | 1.537×, 1.483×, 1.387× |
| Generated blocks | 1.127×, 1.242×, 1.120× |
| Generated communities | 1.201×, 1.223×, 1.065× |

### Disposition: conditional research uplift, still no general promotion

1. **Native train-only acceleration: conditional GO as an opt-in research path**, with exact parity verified and all sparse-block slowdowns preserved. To choose automatically in production, first measure a training-graph feature gate or rework the trainer to reduce fixed subprocess overhead for short tasks; do not use heldout timing to choose.
2. **Admission logic: conditional GO as an experimental policy**, not a universal default. First 256 *live* source IDs and a **known 50,000+ call horizon** are assumed; real streams may have unknown lifetimes or sudden phase shifts. Replaying a frozen 2,400-pair test set 50 times is **not 120,000 IID queries**.
3. **Default TRIC/SOTA promotion: NO-GO.** Unchanged main/default algorithm, original Phase XXII and source code are preserved. The gates above are research evidence only, not matched-memory broad superiority or a field-deployed predictor.

Raw artifact URL: https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39847666038.

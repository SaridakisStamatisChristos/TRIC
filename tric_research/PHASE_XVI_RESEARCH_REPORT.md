# Phase XVI — Two-sided interval pruning: a falsification experiment

## Predeclared hypothesis and evidence contract
The Phase XV stratum-controlled experiments found two competing facts:

1. Bidirectional SCC-DAG BFS is markedly faster than the previous
   topological-only fallback on true pairs and dense Kronecker searches.
2. On arXiv negative-only pairs it was **slower** in all tested seeds;
   O'Reach pDFS remained competitive or faster in most regimes.

Test whether adding the existing *necessary* four-dimensional interval
filters on **both search directions** improves or worsens the fallback.
The user-visible goal is lower **query latency** without changing exact
reachability, preprocessor labels, pivot training, or the held-out pairs.

## Exact mechanism and correctness

`CompactReachability::reaches_bidirectional(s,t,stats,true)` reuses
the existing SCC condensation graph, topological ranks, and fixed-four-
dimensional min/max descendant-permutation bounding labels. Before adding
a newly encountered forward neighbor `v`, require `necessary(v,t)`.
Before adding a newly encountered reverse neighbor `v`, require
`necessary(s,v)`. Both are evaluated only after the original topo bounds.

These are **necessary, never sufficient**, filters:

- If a path from `v` to `t` existed, the descendant rank of `t`
  must be within the per-dimension descendant bounds of `v`.
- If a path from `s` to `v` existed, the descendant rank of `v`
  must fall within the bounds of `s`.

Pruned vertices therefore cannot participate in a source-to-target path.
Every unpruned forward/reverse visited vertex is genuinely reachable from
the corresponding endpoint, so intersections remain positive witnesses.
Exhausting either queue proves negative reachability. The SCC map
preserves reachability within and between components.

**Scope:** C++17 static graph with O(C+M) worst-case query time
(C SCCs, M condensation arcs), O(C) reusable bidirectional buffer space,
and **zero new interval-index labels** relative to Phase XIV.
Each interval candidate check incurs O(d) comparisons, d=4. We expect
less scanning on some graphs, but **do not assume reduced CPU time**.

**Prior art / novelty gate (NO-GO).** This is not a novel primitive.
O'Reach uses pruning observations inside pruned bidirectional BFS:
Hanauer et al., *O'Reach: Even Faster Reachability in Large Graphs*,
[SEA 2021](https://doi.org/10.4230/LIPIcs.SEA.2021.13), Section 4.
Yildirim et al., *GRAIL: A scalable index for reachability queries in
very large graphs*, [VLDB Journal 2012](https://www.cs.rpi.edu/~zaki/PaperDir/VLDBJ12.pdf)
evaluates recursive DFS, bidirectional search, labels, and filters.
The experiment isolates the value of TRIC's already-existing interval
labels inside its Phase XIV bidirectional fallback; it does not claim
invention of bidirectional pruning.

## Strict ablations

Native benchmark exposes:

- `compact_bidir` (Phase XIV control, no pivot);
- `compact_bidir_intervals` (new interval filter, no pivot);
- `compact_pivots_topo` (Phase XIII pivot + topological DFS);
- `compact_pivots_bidir` (Phase XIV pivot + bidirectional BFS);
- `compact_pivots_bidir_intervals` (same exact pivot order, new fallback);
- unchanged original pivot/plain/closure candidates.

Each hybrid uses the **same precomputed certificate** and trained pivot
order. Compare queries only within each pinned graph/heldout seed/query
class. Four hybrid configurations rotate across **12 native measurement
repetitions**: each occupies every execution position three times.
Even-number repetition medians are calculated as the middle-two average.
O'Reach still runs unchanged, pinned, 5 repetitions per query set.

Four classes: `uniform`, `positive`, `negative`, `balanced`;
three seeds, 1200 queries each, on each of two pre-existing graph instances.
The generation retains Phase XV's documented source-uniform conditional
class distributions, *not* the published O'Reach input query collections.
Every native method's checksum must match independently calculated graph
traversal; every hybrid has identical probe/rescue/fallback counts.

Track direct (no-pivot) SCC neighbor arcs scanned and the count of neighbor
rejections by interval labels. **Do not assert** the pruned method examines
fewer total arcs: different forward/backward queue decisions can alter search
order and termination, so fewer admitted vertices need not produce fewer
scanned arcs in a different execution path.

## Scientific acceptance/falsification gates

1. All C++17 regression tests, three-node exhaustive graph enumerations,
   randomized cycles, dense DAGs, disconnected and cyclic graphs pass.
2. Python 3.10/3.13 research CI passes; paired O'Reach CI passes for both
   graph datasets; correctly labeled query types and query hashes survive.
3. A mechanism success is a measured **decrease in latency** on at least
   one declared class without unacceptable regression elsewhere.
   Fewer arcs alone is not a win.
4. Document every class where interval pruning is slower. Do not condition
   runtime algorithm selection on the oracle's true/false label: it is
   unknown before answering the query.
5. No SOTA/general superiority/paper novelty claim without more graph
   families, memory-matched O'Reach and independent per-query baseline
   correctness traces, amortized indexing and dedicated-machine results.

## Reproduction
```bash
cd tric_research
python -m unittest -q test_compact_reachability test_stratified_queries test_oreach_ci
```

Run the pre-existing `.github/workflows/research-oreach.yml` for native
O'Reach comparison and inspect each workflow artifact's
`phase16_summary.json`, `comparison.json`, query files and SHA hashes.

**Evidence state:** exactness and benchmark execution verified by CI.
The proposed **unconditional performance optimization was refuted** on most
of the benchmarked classes. The interval-pruned method remains a research
ablation, not a recommended replacement.

## Executed pilot — CI run 39750761518 (source SHA `6030ca3927cd8c5d053368ec084192086e53ebe4`)

The unit suite ran on Python 3.10 and 3.13, including all prior
reachability regressions and new adversarial tests:
[unit CI run 39750761486](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39750761486),
both successful.

The paired pinned O'Reach benchmark completed on both published-graph jobs:
[paired native CI run 39750761518](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39750761518).
All 24 three-seed/stratum graph/split experiments completed with no checksum
or probe-accounting errors. This is the **first run** of the modified code.

The following times are median per-seed native nanoseconds/query, and
ratio is the *median of the three paired unpruned/pruned* ratios.
Ratio <1 means **interval pruning is slower**.

| Graph | Stratum | Old bidir hybrid ns/q | Pruned hybrid ns/q | Median old/pruned | Pruned wins |
|---|---|---:|---:|---:|---:|
| arXiv | uniform | 415.70 | 426.15 | **0.9755** | **0/3** |
| arXiv | positive | 577.69 | 710.08 | **0.8197** | **0/3** |
| arXiv | negative | 359.36 | 361.42 | **0.9552** | **0/3** |
| arXiv | balanced | 554.68 | 626.62 | **0.8852** | **0/3** |
| Kronecker | uniform | 71.29 | 85.40 | **0.8349** | **0/3** |
| Kronecker | positive | 218.04 | 288.11 | **0.7568** | **0/3** |
| Kronecker | negative | 21.73 | 18.17 | 1.1961 | 3/3 |
| Kronecker | balanced | 138.33 | 182.38 | **0.7632** | **0/3** |

All values compare the same graph, seed, class and CPU job; the query
pairs, pivot order, certificate behavior, and oracle checksum match exactly.

### Important mechanism counterevidence

Interval pruning **does** cut candidates, but CPU overhead dominates.
For example, arXiv uniform queries rejected a median 5,605 neighbors,
reducing median directly scanned arcs from 128,391 to 116,734, while
hybrid timing still became slower (415.70 → 426.15 ns/query).
For arXiv positive-only, median interval rejections were 16,180; timing
regressed from 577.69 to 710.08 ns/query. Kronecker positive-only
saw median 2,526 interval rejections with 218.04 → 288.11 ns/query.

The **sole measured positive** is Kronecker negative-only, with the new
method at 18.17 vs 21.73 ns/query. However, both variants scanned a
median of **4,380 arcs** across this class and the interval filter
rejected only a median of **four neighbors**. Therefore, the apparent
~20% speed gain is **not convincingly attributable to useful pruning**;
microbenchmark noise, instruction layout, cache, or compiler effects are
credible alternatives. Reproduce on dedicated hardware before promoting.

### Evidence disposition

- **Correctness/CI evidence:** PASS within disclosed test scope.
- **Universal replacement of Phase XIV bidirectional fallback:** REJECTED.
- **Potential negative-only, resource-aware dispatch optimization:** UNRESOLVED;
  method selection cannot use oracle truth labels or other information
  unavailable before the query.
- **Original algorithmic invention / general SOTA claim:** NO-GO.
- **Publication-grade evidence:** NO-GO (two small graphs, nonuniform
  class sampling, unmatched index/RSS costs and non-dedicated CI timing).

Raw artifacts:
[arXiv experiment](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39750761518/artifacts/12413199329)
and [Kronecker experiment](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39750761518/artifacts/12413826178)
preserve `phase16_summary.json`, hashes, per-seed `comparison.json`,
query files and O'Reach CSV.

**Recommended next falsification:** rather than adding still more
per-edge interval checks, evaluate a *query-visible, outcome-blind*
fallback selection policy with its cost included in timing, plus more
independent graphs and index size/RSS matching.

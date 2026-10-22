# TRIC Phase XXI — Composed Cache + Exact Indexed Reachability

**Date:** 2026-10-22. **Status:** Experimental draft; no default changes.
Stacked on Phase XX PR #19; older negative results preserved.

## Why this phase exists

Phase XX compared an exact train-only hot-source bitmap cache with a plain
DFS fallback against indexed TRIC and unchanged upstream O'Reach on two
authentic published graph sources. BOTH Phase XX source jobs passed:
https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39787587262

The hot-source cache lost by >10x query time even on matched source reuse:
arXiv cache 1979.99 ns/q versus TRIC pivot+bidir 162.19 ns/q and
O'Reach pDFS 137.07 ns/q; Kronecker cache 6460.34 ns/q versus TRIC
94.58 ns/q and O'Reach 61.12 ns/q. Despite ~80% hits,
uncached queries invoked slow plain DFS. This is not evidence that
materialized hot sources cannot help as a *fast path*.

## New falsifiable mechanism

Compose the established, exact hot-source bitmap cache with the
**existing exact compact SCC/interval labels, ordered pivot certificates
and bidirectional graph fallback**.

For source/target pair (s,t):

1. If s is in the train-only selected hot-source table, answer directly
   from its exact reachable-target bitmap in O(1).
2. Otherwise use the **unchanged exact indexed pipeline**. Either check
   the compact SCC certificate, then existing ordered supportive pivots,
   then bidirectional fallback; or use exact bidirectional alone.
3. No answer-label-driven routing and no approximation.

This is an established cache-then-index algorithm portfolio, not a new
graph theoretical primitive. Correctness follows from soundness of
either the exact cache answer or the unchanged exact fallback, and is
independently exercised under finite exhaustive tests.

## Native four-arm ablation: same binary / data / preprocessing

- index_only: exact compact bidirectional reachability.
- cache_index: bitset hot hit, else exact compact bidirectional.
- pivot_index: compact certificate, ordered pivot certificates and exact
  bidirectional fallback.
- cache_pivot_index: cache first, then EXACT same pivot_index pipeline
  when a hot-source row is unavailable.

The four arms use the same C++17 compiled executable, graph, training
pairs, heldout queries, compact index, pivot vectors and cache memory.
16 repetitions with equal, rotated position exposure, and an
independent graph BFS reference checked against every method on every
permutation. Cache construction and retained vectors are reported
separately as an increment relative to a shared index.

The first test covers all 512 directed graphs with three vertices
(including loops/cycles), additionally a 65-vertex boundary graph.
This is finite bounded evidence; the exactness argument does not
rely on those tests alone.

## External experimental protocol

The Phase XX GitHub workflow is retained and extended at this new
branch; it reruns same-file comparisons against original pinned
O'Reach pDFS and pBiBFS on:

- upstream arXiv METIS sample and published Kronecker logn12;
- matched 80% source-hot heldout, uniform, disjoint shifted-source-hot;
- exactly 500 training pairs and 2,400 heldout pairs per class/graph;
- 15 original TRIC repetitions, 14 cache-vs-DFS repetitions, 16
  four-arm cache-indexed repetitions, 5 unchanged O'Reach runs.

Outputs preserve full native per-method samples, SHA of real graph and
every query file, true-positive count, reported O'Reach init/memory
data, cache and index memory/build costs, and compiler provenance.

## Incremental economic comparison

Let B be the median query ns for pivot_index, S be the median query ns
for cache_pivot_index, and F be the additional measured cache build ns
within the same shared index. The **modeled** strict break-even is:

- No finite threshold if B <= S.
- Otherwise Q_min = floor(F/(B-S)) + 1.

These are algebraic projections from one batch's query medians, NOT
actual prolonged Q-query runs, and exclude unchanged graph/prep costs.
Extra retained bitmap bytes are a separate constraint even if the
incremental time breaks even. On queries from unseen sources the
additional cache probe may induce a regression.

## Research and code audit

Status at proposal: SPECIFIED / new combined mechanism not yet
benchmark-verified. This phase will be promoted only on real CI evidence.

1. Correctness gate: identical independent BFS checksums and all
   four native modes; independent test on all three-vertex digraphs.
2. Resource gate: never exceed byte cap; measure extra cache memory
   and construction overhead; do not pretend O'Reach's RSS and TRIC
   label/vector bytes are equivalent.
3. Falsification gate: explicitly preserve losing uniform/shifted
   cases, where near-zero cache hits can increase overhead.
4. External gate: report original O'Reach separately; query-only
   figures are not matched-budget end-to-end SOTA.
5. Novelty gate: source subset closure, SCC condensation, interval
   pruning, bidirectional search and algorithm portfolios are
   prior art; the challenge is reproducible empirical suitability,
   not a priority claim.
6. Publication gate: neither a narrow result on two graphs nor the
   mathematical composition makes a new theorem or publication-grade
   general performance claim.

Reference anchors:

- Hanauer et al., O'Reach: Even Faster Reachability in Large Graphs,
  SEA 2021, https://doi.org/10.4230/LIPIcs.SEA.2021.13
- Zhang, Bonifati, Ozsu, Indexing Techniques for Graph Reachability
  Queries, ACM Computing Surveys 58(6), December 2025,
  https://doi.org/10.1145/3776737
- Zhang, Gan, Yang, MLRQ: an efficient labeling scheme for reachability
  queries on reduced DAGs, November 2025,
  https://doi.org/10.1007/s44443-025-00310-0

**Current deployment decision:** NO-GO for default code or generalized
superiority until the exact Phase XXI CI and an independent, budget-matched
multi-graph validation complete.

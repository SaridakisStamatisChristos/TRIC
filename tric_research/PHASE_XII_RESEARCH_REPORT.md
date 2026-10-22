# Phase XII — Compact Exact SCC Reachability: Pruning and Positive Forest Certificates

## Purpose and non-novelty
Phase XI demonstrated that a full SCC transitive closure is extremely fast for
a 6,000-vertex example but requires quadratic matrix storage. Phase XII
implements a lower-memory comparison class without claiming invention.
Randomized interval pruning, directed DFS-tree witnesses, and pruning-guided
graph traversal are established research themes; see GRAIL (Yildirim et al.,
VLDB Journal 2012, https://www.vldb.org/vldb_journal/index.php/component/article_manager/article/1208),
PReaCH (Merz & Sanders, https://arxiv.org/abs/1404.4465),
and O'Reach (Hanauer et al.,
https://doi.org/10.4230/LIPIcs.SEA.2021.13).

## Inputs and exact semantics
A fixed directed graph G, arbitrary reachability queries (s,t), including
cycles, isolated vertices, and self-reachability. For every query, the index
must return exactly the same Boolean result as ordinary graph reachability.
An independently executed graph traversal checks all test answers.

## Procedure
1. Use an iterative strongly connected component decomposition and form the
   condensation DAG.
2. Build four deterministic-seed randomized permutations of the DAG vertices.
   In reverse topological order propagate each vertex's minimum and maximum
   descendant permutation labels across all outgoing arcs.
3. Build a directed DFS spanning forest. If source and target are in the same
   SCC, or target is a descendant of source in this directed forest, return
   reachable (positive certificates).
4. If the target's permutation rank lies outside ANY source descendant range,
   return unreachable (negative certificates).
5. Otherwise run exact DFS on the condensation DAG, pruning any newly
   considered vertex whose interval range excludes the target.

Positive and negative checks are sound for all directed graphs. The final DFS
ensures no false positives. The index is for static graphs only.

## Complexity
Let n=|V|, m=|E|, C=number of SCCs, M=number of arcs in the condensation DAG
(counting duplicate arcs), and d=4 dimensions. Build is
O(n+m+d(C+M)) time and O(n+m+dC+M) space. The reported labels_bytes covers
permutation bounds, DFS forest times, seen markers and source-to-SCC mapping,
but does NOT include adjacency capacity, original graph memory, allocator
overhead or process RSS. Worst-case fallback searches are O(C+M) per query,
so constant-time queries are NOT guaranteed.

## Experiment constraints
The GitHub CI job provides:
- a pinned public O'Reach build and held-out, seeded queries on exactly
  the same directed METIS graph;
- 7 repetitions of native TRIC query loops, 5 repetitions of O'Reach;
- independent oracle checking for all TRIC policies and compact index;
- compact build milliseconds, labels bytes, query latency, certified positive
  and negative counts, fallback count and scan edges;
- closure build milliseconds, matrix bytes, single-pass timing and separate
  128-pass hot-cache timing (the latter MUST NOT be compared to O'Reach);
- raw output artifact with checksums and full query file.

O'Reach's own compiled query loop, label data structures and memory capacity
differ from TRIC. This is a diagnostic comparison, NOT a matched-index-memory
or state-of-the-art superiority benchmark; O'Reach per-query outputs are
not yet independently exported and checked in this harness. GitHub-hosted
timings also have scheduler noise.

## Reproduce
```sh
cd tric_research
python -m unittest -q test_compact_reachability
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone \
  test_backbone_scc test_frontier_dp test_adaptive_exact test_frontier_compact \
  test_ordered_probe test_native_benchmark test_oreach_ci \
  test_closure_index test_compact_reachability
```

The GitHub workflow `.github/workflows/research-oreach.yml` builds O'Reach
from pinned upstream commit 78b3e326bbb021b7ee225ab605a4cdd074fa1d93
and runs exactly the same workload for TRIC and O'Reach.

## Acceptance gates
- All tests and CI matrix jobs pass.
- Zero wrong reachability answers.
- Pilot comparison reports actual memory/build/query costs separately.
- No claim of novelty for known SCC/interval algorithms.
- Larger graphs and a matched-memory baseline remain necessary for a paper.

Status is preliminary until attached GitHub CI evidence for the exact PR commit
has been inspected.
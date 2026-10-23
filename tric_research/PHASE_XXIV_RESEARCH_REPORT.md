# Phase XXIV — graph-only partitioned exact reachability

## Problem contract

Static directed graphs, integer vertices `[0,n)`, reflexive reachability. Answer
all queries exactly, including cycles, isolates and parallel edges. No query
training, hot-source prior, target labels, future request horizon or pivot policy
is required by this index. Optimize query latency / preprocessing / retained
space together; reject a universal performance claim if a credible baseline wins.

This is an additive C++17 index, not a replacement for the exact pivot-optimization
research. Earlier experimental implementations and their negative results remain.

## Implementation

`tric_reachability.h` provides `TricReachability`, a graph-only automatic entry
point. It first tries the existing `BoundedClosure`. If its global SCC bit matrix
fits, query it directly. Otherwise destroy the refused probe and build the new
partitioned index. Both SCC probes count in measured construction time. This
routing depends only on graph structure and the declared table allowance, never
on query outcomes. Direct full closure trades greater retained space for its
constant-time query path; use `PartitionedReachability` explicitly when preferring
its space savings. The automatic mode and both constituent controls are measured
separately. The existing direct closure API now validates input/query endpoints
and exposes retained capacity; its underlying closure algorithm is unchanged.


`partitioned_reachability.h` computes iterative Kosaraju SCCs, deduplicates and
sorts the quotient arcs, and partitions the DAG by weak connectivity. Within each
partition, a greedy directed path cover yields chain labels. The smaller of the
chain-label and full-bitset payloads is selected without inspecting queries.
Singleton partitions require no closure table. Cross-partition queries are false;
same-SCC queries are true, with reflexive semantics.

A label in column c is the earliest topological position on path c reachable from
a vertex. Successor row union is componentwise minimum. Reachability to a target
on c is equivalent to this minimum being no greater than the target's position.
Bit rows instead record every descendant. Both propagate in reverse topological
order. Since successor arcs are processed in increasing topological order, a row
merge can be skipped when that successor is already reachable; all its descendants
were inherited through an already processed successor. This is ordinary transitive
edge elimination, not a new reachability theorem.

If the chosen table does not fit, bitsets may be built under a **separate 64 MiB
dense construction-scratch cap** and compressed row by row. Each row chooses a
dense suffix or a sorted list of nonzero `(word ID, word)` entries. The compressed
payload includes row descriptors, IDs and words. Sparse membership uses binary
search. If no exact representation fits, preserve exact topologically bounded DFS
on that partition. Refusing a table changes performance, never answer semantics.

Query metadata is coalesced into 32-byte aligned per-vertex labels. Two
longest-path level bounds on the quotient give additional necessary conditions:
a distinct reachable target must have strictly greater forward level and strictly
smaller backward level. These reject many sparse negative pairs before a sparse
word lookup. The level filters are established DAG techniques (also used by
O'Reach), not novel certificates. Their additional retained metadata is counted.

The constructor accepts a table-payload cap and an optional dense-compression
scratch cap. Neither is a total-RSS cap. Graph copies, SCC / DAG scratch, fixed
metadata, vector capacity and allocator overhead are additional. `table_bytes()`
reports payload; `retained_bytes()` includes actual retained vector capacities and
the object, excluding allocator metadata, input graph and construction peak. Native
peak RSS is sampled after timed queries and before oracle allocation. An instance
reuses fallback scratch and must not be shared concurrently across query threads.

## Correctness and resource argument

1. Iterative Kosaraju's reverse-finish traversal on reverse arcs yields exact SCCs
   in topological order. The constructor checks that every quotient arc increases
   its SCC ID. Reachability is preserved under SCC contraction.
2. A directed path cannot cross weak components. Within one SCC all pairs are
   reachable; between distinct components a path strictly increases SCC ID.
3. The greedy cover extends a path only over an actual incoming arc from its
   current tail. Its columns are therefore totally ordered by real directed paths.
4. Reverse-topological induction: a row consists precisely of its own vertex and
   the union of every successor's exact reachable set. For chain rows the union is
   a minimum, since each reachable path suffix is contiguous. For bitsets it is OR.
5. If a successor b is already represented as reachable, a previously merged
   successor has a path to b; its exact row already contains every descendant of b.
   Skipping b's row introduces no omission. Sparse/dense compression is lossless.
6. For an edge a->b, longest-from-source level strictly increases and
   longest-to-sink level strictly decreases. These inequalities are transitive,
   so rejecting a pair that violates either condition cannot remove a real path.
7. Refused partitions use exhaustive DFS restricted to SCC IDs no greater than
   the target, which cannot remove a successful path.

These give a human-checkable argument, not formal verification. For a quotient
with C vertices and A distinct arcs, sorting costs sum d log d; SCC construction
is O(n+m). Path cover and weak partitioning are linear apart from disjoint-set
inverse-Ackermann cost. Per partition i, s_i vertices and k_i paths require
O(s_i*k_i) 32-bit chain labels or O(s_i*ceil(s_i/64)) 64-bit words. Reverse-DAG
propagation costs O((s_i+A_i)*k_i) or O((s_i+A_i)*ceil(s_i/64)) before skipped merges.
Compression scans the temporary table. Indexed chain/dense queries take O(1),
sparse rows O(log ceil(s_i/64)); a refused partition may require O(s_i+A_i) search.
No exponential optimization/training step is included or needed.

## Prior art / novelty boundary

These are established techniques combined for this repository. No novel primitive,
new complexity result, or globally fastest index is claimed.

- Hanauer, Schulz, Trummer, *O'Reach: Even Faster Reachability in Large Graphs*,
  SEA 2021, https://doi.org/10.4230/LIPIcs.SEA.2021.13 ; code pinned to
  `78b3e326bbb021b7ee225ab605a4cdd074fa1d93`.
- Kritikakis and Tollis, *Fast Reachability Using DAG Decomposition*, SEA 2023,
  https://doi.org/10.4230/LIPIcs.SEA.2023.2 (chain / path closure and reduction).
- Kritikakis and Tollis, *Parameterized Linear Time Transitive Closure*,
  https://arxiv.org/abs/2404.17954 .
- Bulteau et al., *Incremental Reachability Index*, SEA 2025,
  https://doi.org/10.4230/LIPIcs.SEA.2025.9 (chain indexes and space tradeoffs;
  this implementation does not implement their incremental anchor algorithm).
- Zhang, Bonifati, Özsu, *Indexing Techniques for Graph Reachability Queries*,
  https://doi.org/10.1145/3776737 (2025 survey).

## Measurement contract

`benchmark_partitioned.py` uses equal input bytes, independent fresh processes,
position-balanced rotations, two actual-call horizons and per-answer independent
BFS checks after timing. Controls include automatic routing, the existing `CompactReachability` with
bidirectional search and `BoundedClosure`, including explicit unavailable cases
when its global table exceeds its cap. An unavailable control is never a win.
Queries cover uniform, positive, negative and balanced classes. Conditional
samplers remain source-weighted (see `stratified_queries.py`), not uniform over
all pairs with that truth value. No truth information enters index construction.

Native lifecycle covers reading graph AND frozen query file, index construction,
then actual calls. Source download, query generation, compilation, process startup,
independent verification, destruction and application integration are excluded.
Frozen pairs replayed 100 times are 120,000 calls, not 120,000 IID requests.
Short-horizon build regressions and full-bitset wins must be retained.

For external comparison, `build_oreach_adapter.py` compiles the unchanged original
library at its pinned SHA and links `oreach_adapter.h` against its PUBLIC per-query
API. This enables identical input, query loop, lifecycle clock, checksums and
independent verification of **every external answer**. The adapter is not the
original application's CSV timing loop. The missing standard cstdint include is
supplied as a compile flag, not a source edit. Raw authentic graph inputs use
upstream support=3; explicitly generated families use support=0 and a lossless SCC
quotient because the original topological index requires a DAG and its default
support sampler cannot handle tiny components. **Every arm receives that same
quotient**, and raw/quotient pairs are independently checked for exact equivalence.
Preprocessing time is separately recorded, excluded equally from native timers.
No upstream crash tolerance or missing-comparator exception is enabled.

The table-payload allowance is the same for TRIC table controls. O'Reach has its
own index design and is not total-memory-matched. Report retained capacity and RSS;
do not equate a 2 MiB table allowance with equal overall memory. Small graph/shared
host results cannot establish broad-world SOTA.

## Original real-graph recovery

The GRAIL author's repository preserves `sigmod08.tar.gz` and `sigmod09.tar.gz` at
commit `c13a7364fbc185841fc6277cd295acf33a7188f0`. `grail_datasets.py` downloads from
that immutable source and requires exact original Git blob identity and byte
length before reading one named archive member. It writes no archive paths to the
filesystem and retains every vertex and outgoing arc, including duplicates and
order, in a lossless directed-METIS conversion. Archive/member/output SHA256s and
source provenance are saved. These are the authentic benchmark graphs, not the
Phase XXII generated replacements and not new copies of arXiv.

| Author archive graph | Vertices | Arcs |
|---|---:|---:|
| go_sub_6793 | 6,793 | 13,361 |
| pubmed_sub_9000-1 | 9,000 | 40,028 |
| citeseer_sub_10720 | 10,720 | 44,258 |
| yago_sub_6642 | 6,642 | 42,392 |
| kegg_dag_uniq | 3,617 | 4,395 |

`research-real-graphs.yml` runs the same per-answer comparator, four query strata,
three seeds and both horizons, with **raw original graphs and default support=3**.
It does not use the generated-family compatibility exception. Together with arXiv
this supplies six real graphs plus the separately identified published Kronecker
and three generated stress families. Success and numerical outcomes are recorded
only after each run finishes.

## Executed evidence and decision — 23 October 2026

Measured source: `b5e1a1c3aa4a32cbf4bafedb3a68680722195e00`.
The standalone runtime in [PR #24](https://github.com/SaridakisStamatisChristos/TRIC/pull/24)
has byte-identical runtime headers at `267085808ad53065825c9b1f464a3f15824a450e`.

- [Full research tests](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39899645960)
  passed **126 selected test methods** on Python 3.10 and 3.13. Local full
  discovery additionally passes **129 methods**; the three older lifecycle tests
  were absent from the hand-maintained CI list. This final evidence update replaces
  that list with discovery so future modules cannot be silently omitted. The focused main integration additionally passes its 25 original/new
  tests and normal address/undefined-behavior sanitizers on both Python versions
  in [native CI](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39899819705).
- [All five recovered original real graphs x three seeds](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39899645952)
  passed **17/17 jobs**, including independent exact per-answer OReach validation.
- All arXiv and published Kronecker graph/seed jobs passed in
  [the original/stress matrix](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39899645925).
  This completes **21/21 primary graph/seed experiments**, with four query strata,
  two call horizons and six position-balanced fresh-process trials per method.
  No incorrect answer or unavailable external comparator occurred in this primary
  matrix. BoundedClosure refusals remain explicitly unavailable, not wins.
- The original/stress matrix completed **17/17 jobs**, including all **nine of
  nine** generated graph/seed experiments. The final campaign therefore has
  **30/30 completed CI graph/seed experiments across 10 graphs**: six real graphs,
  published Kronecker, and three explicitly generated stress families. Every
  external answer was checked against an independent oracle. All 30 preserved
  experiment records are CI-origin and share the measured implementation hashes.
  The earlier local timing/layout ablation is separately labeled exploratory.

### Primary uniform workload — all seven graphs

120,000 actual calls = 1,200 frozen pairs replayed 100 times. Each reported speedup
is the median of the three per-seed paired ratios against the **faster of OReach
pDFS and pBiBFS** for that metric and cell. Above 1 favors automatic TRIC; below 1
is a real regression. Query and lifecycle may select different faster fallbacks.

| Graph | Query speedup | Three-seed query range | Native lifecycle speedup |
|---|---:|---:|---:|
| arXiv (real) | 18.341x | 12.085–21.732x | 2.868x |
| Kronecker (published synthetic) | 13.383x | 11.055–22.507x | 2.849x |
| GO (real) | 0.619x | 0.617–0.742x | 0.800x |
| PubMed (real) | 1.532x | 1.314–1.545x | 0.883x |
| CiteSeer (real) | 1.538x | 1.137–1.585x | 0.879x |
| YAGO (real) | 0.597x | 0.566–0.601x | 0.876x |
| KEGG (real) | 0.886x | 0.864–0.927x | 2.242x |

This is substantial improvement on arXiv and Kronecker but **not a global win**.
GO and YAGO lose in all four warm query strata. PubMed/CiteSeer have faster query
paths but generally slower complete native lifecycles at this horizon. PubMed
positive-only is a useful conditional gain (4.208x query, 1.176x lifecycle), not a
universal claim. KEGG generally has much faster construction/lifecycle while
negative and uniform query-only latency still loses. Existing direct global
closure remains a credible competing control wherever its memory fits; automatic
TRIC reuses that exact algorithm and does not establish a new faster primitive.

All **56** primary graph/stratum/horizon median cells, seed ranges and memory
figures appear in [primary_summary.csv](evidence/phase24/primary_summary.csv).
Per-graph CSVs include every available control/seed; compressed JSONs preserve raw
numeric trials, source identities, checksums, independent oracle counts and
execution origins. The downloaded ZIP digests were verified against GitHub's
artifact receipts. The evidence remains in the repository after CI artifacts
expire. See [the evidence index](evidence/phase24/README.md).

**Verdict:** exact native runtime integration is ready for review through PR #24.
This is an established-technique portfolio with measured regime-specific gains.
**Global SOTA promotion remains NO-GO.** Remaining failures include GO/YAGO query
regressions and preprocessing costs on several sparse real graphs. Other modern
indexes (e.g. additional 2-hop/BFL-family implementations), large-graph scaling,
dedicated hardware replication and matched total-memory frontiers are not yet
measured. No claim of paper novelty or production readiness follows.

## Reproduce

```bash
cd tric_research
python -m unittest -q test_partitioned_reachability test_partitioned_benchmark
python benchmark_partitioned.py --graph /absolute/path/graph.metis \
  --dataset example --output-dir /tmp/tric-phase24 --cap-mib 2 \
  --seed 20261023 --count 1200 --horizons 1 100
```

External adapter needs Boost headers and CMake. See `research-phase24.yml` for the
pinned build and five-family / three-seed matrix. Preserve all negative cases and
raw samples before any default-promotion decision. **No global SOTA promotion.**

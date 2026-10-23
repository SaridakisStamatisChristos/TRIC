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
6. Refused partitions use exhaustive DFS restricted to SCC IDs no greater than
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

## Executed evidence

Pending final campaign results. Local development exactness tests and pilot timings
are preliminary. CI links, exact source SHA, machine-readable trials and negative
cells will be recorded after execution; queued workflows are not passed workflows.

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

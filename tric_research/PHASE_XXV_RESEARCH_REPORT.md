# Phase XXV: shared SCCs and bounded interval closure

## Problem and implementation

Static directed graphs, contiguous integer vertex IDs, reflexive exact
reachability, owned snapshots, invalid endpoint exceptions, and one index per
query thread. Default budgets remain 2 MiB of table payload and 64 MiB for the
dense matrix or two interval-union buffers. Neither budget means total RSS.

`TricReachability` decomposes SCCs once. When full closure does not fit, the same
result is consumed by `PartitionedReachability`. Partition-local chains and
bitsets retain precedence when they fit. Otherwise, a bounded union-of-intervals
index is attempted before the existing compressed-word construction and exact
search fallback. A failed interval attempt rolls back all of its table entries.

Each 32-byte vertex label carries a descendant signature and DFS subtree
interval. Signatures are sound negative filters; subtree containment is a sound
positive certificate. Two saturating 16-bit longest-path levels protect the
search route. Its SCC ID shares storage with the mutually exclusive chain ID.
No additional per-vertex label bytes or query training were introduced.

## Correctness argument and limits

1. SCC contraction preserves reachability. Kosaraju IDs increase along every
   condensation arc; all preprocessing DFS passes are iterative.
2. A DFS tree edge is a real DAG edge. Every vertex in a node's half-open
   DFS-preorder subtree interval is therefore reachable from that node.
3. For every SCC a, its 64-bit signature contains its own hashed bit and the OR
   of all successor signatures. If a reaches b, every bit in b is present in a.
   Collisions can only weaken this negative filter, never establish an answer.
4. Reverse topological processing makes each child interval row complete before
   its parent. Initialize the parent with its singleton preorder position and
   union each child's complete, sorted, disjoint intervals. The result is
   exactly the parent's reflexive reachable set. Adjacent intervals can merge
   because their integer preorder positions contain no gap.
5. If a successor's preorder position is already covered by a previously merged
   child closure, that successor's entire closure is inherited. Skipping that
   transitive arc is sound. Starting with a whole DFS subtree would NOT justify
   this optimization: it may omit cross-edge descendants of subtree members.
6. Budget refusal never installs a partial row set. Existing word compression
   or exact DAG search answers the partition instead.
7. Longest-path levels strictly increase forward and decrease backward along
   nontrivial reachable pairs. A saturated value of 65535 is not used to reject
   an equal saturated value; deeper paths retain exact answers.

For s SCCs and R stored ranges, the interval payload is 8*s + 8*R bytes on the
recorded toolchain. Query membership is O(log r) for r ranges in the source row,
after constant-time certificates. Construction can examine many ranges per arc;
this is not a linear-time construction guarantee. Fallback search remains
O(s + m) in the worst case. Table/vector capacities, graph storage and other
constructor allocations remain separately accounted for.

These are established SCC, tree-cover, closure, Bloom-style filtering and
transitive-arc-skipping techniques. This work does not establish novelty or
universal SOTA. The argument above is human-checkable, not proof-assistant
verification.

## Verification

The local original/new suite passes 31 test methods. Each native self-test
checks both automatic and partitioned indexes against independent BFS on:

- 18,432 exhaustive three-vertex query/cap cases, including self loops;
- 1,440 larger adversarial cases;
- 589,824 cases across all 4,096 members of a 12-variable-arc DAG family lifted
  to 160 vertices to force interval routing; 9,248 interval partitions are built.

Additional tests cover fragmented interval refusal into word compression,
rollback between partitions, random relabeling and cycles, parallel arcs,
100,000-vertex interval indexing beyond the dense scratch limit, saturated
levels on 140,000-vertex paths, 16-byte union scratch, zero scratch, invalid
endpoints, the independent original BFL adapter, and benchmark input integrity.

Address and undefined-behavior checks pass locally. Local LeakSanitizer cannot
inspect threads under this environment's tracing setup, so only the local run
uses `ASAN_OPTIONS=detect_leaks=0`. The existing GitHub workflow retains its full
sanitizer command and runs Python 3.10 and 3.13; its final status is recorded
separately after publication.

## Comparison protocol

Baseline runtime: PR #24 commit `267085808ad53065825c9b1f464a3f15824a450e`.
Original O'Reach: `78b3e326bbb021b7ee225ab605a4cdd074fa1d93`, public per-query API,
both pDFS and pBiBFS fallbacks. Original BFL:
`0c837927a3f2fa3fc633abeedd56cea6e75d3a9a`, unchanged source, MIT license,
default K=5 and D=1600. The benchmark adapter includes SCC/adjacency construction
in BFL build time and calls the original `bs::reach` on indexed nodes; it does
not use the upstream file-driven query loop or pre-copy query endpoint nodes.

All arms parse identical graph/query bytes, execute actual calls, and BFS-check
every input query after timing. Every trial is a fresh process. All arms use one
benchmark source, GCC -O3, and the same pinned external code. Five launch orders
balance every arm over every launch position. Horizons are 1 and 100 replays of
1,200 frozen pairs, not independent new requests. Uniform and source-weighted
positive, negative and balanced strata are disclosed independently.

The original ten graphs retain three seeds from Phase XXIV. Nine additional
GRAIL-author graphs are held out from candidate tuning and use seed 20261025.
Their original archive members, hashes and all input bytes are preserved.
Generated stress graphs use the same previously recorded SCC quotient for every
arm, with O'Reach support=0; other graphs retain upstream support=3.

Wall-clock parse/build/query lifetimes are primary. Thread CPU time is also
recorded to distinguish scheduling noise. The Linux current-executable VmHWM is
read before oracle verification. `getrusage` peaks are retained separately:
they can include the larger Python launcher's pre-exec RSS and are unsuitable
as the native peak measure here. Process startup, verification and teardown are
excluded from lifecycle time. Total retained/peak memory is measured, not
budget-matched across different systems. CPU affinity does not make this shared
machine dedicated hardware.

## Results

Qualification is in progress. Final summaries and raw trials will replace this
paragraph before the PR is marked ready. No result from the superseded
exploratory candidates is promoted as final evidence.

## Reproduction

The optional comparator does not add a production runtime dependency. Build
previous/current executables from one benchmark source:

```bash
python tric_research/build_native_comparison.py \
  --before-headers /path/to/checkout-at-2670858/tric_research \
  --output /tmp/tric-comparison
```

This includes the original vendored BFL comparator. To also include O'Reach,
pass `--oreach-source` pointing at the pinned unchanged checkout and
`--oreach-build` at its release CMake build. Optional `--extra-include` accepts
an extracted Boost include directory. The recorded build manifest preserves
all actual flags, object files, source hashes and executable hashes.

```bash
python tric_research/benchmark_native_changes.py \
  --fixtures tric_research/evidence/phase25/fixtures \
  --output /tmp/tric-results \
  --arm previous /tmp/tric-comparison/previous auto \
  --arm candidate /tmp/tric-comparison/candidate auto \
  --arm bfl /tmp/tric-comparison/candidate bfl \
  --arm oreach-pdfs /tmp/tric-comparison/candidate oreach-pdfs \
  --arm oreach-pbibfs /tmp/tric-comparison/candidate oreach-pbibfs \
  --trials 5 --horizons 1 100
```

Omit the two O'Reach arms when it is not built; use `--trials 3` to balance the
remaining three arms. The runner checks fixture hashes, actual call counts,
independent verification counts, cap compliance and cross-arm checksums.

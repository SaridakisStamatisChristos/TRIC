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

Qualification is complete: **39 graph/seed experiments on 19 graphs**, 312
stratum/horizon cells, 7,800 fresh processes, 9,360,000 post-timing independent
BFS pair checks and 472,680,000 actual query calls. Every expected input/result
hash and case count passes the final validator. The fixed runtime is commit
`a94c1828abe2212e0239cdc93f09ff9d440d6c4f`; subsequent changes add tests,
artifact durability, summaries and evidence, without changing runtime headers.

Across the 76 warm graph/stratum aggregates (100 replays), paired median build
speed improved in 76/76, query speed in 71/76, and parse/build/query lifecycle
in 71/76 against the previous TRIC. The median cell ratios are 1.78× for build,
1.21× for queries and 1.29× for lifecycle. These are equal-cell medians, not an
aggregate throughput guarantee or statistically established universal dominance.

The following uniform 120,000-call cells show the median of paired trial ratios,
then the median across seeds. Nine held-out graphs have one seed rather than
three. Ratios above one favor this candidate. The fastest external comparator
is selected separately for each metric and paired trial from original BFL and
both original O'Reach variants.

| Graph | Query speed vs previous | Build speed vs previous | Lifecycle vs previous | Query vs fastest external |
|---|---:|---:|---:|---:|
| arXiv | 0.91× | 1.27× | 1.07× | 9.90× |
| CiteSeer | 1.29× | 2.07× | 1.39× | 0.85× |
| GO | 1.29× | 1.90× | 1.38× | 0.90× |
| KEGG | 1.03× | 1.18× | 1.01× | 0.87× |
| PubMed | 1.37× | 1.67× | 1.29× | 1.00× |
| YAGO | 1.39× | 1.74× | 1.19× | 0.93× |
| agrocyc | 1.17× | 5.35× | 2.55× | 0.58× |
| amaze | 1.01× | 1.13× | 1.06× | 0.88× |
| anthra | 1.10× | 5.46× | 2.55× | 0.60× |
| ecoo | 1.12× | 5.19× | 2.47× | 0.57× |
| human | 1.55× | 1.09× | 1.06× | 0.60× |
| mtbrv | 1.09× | 3.78× | 1.98× | 0.52× |
| nasa | 1.47× | 2.47× | 1.61× | 1.03× |
| vchocyc | 1.22× | 3.91× | 2.00× | 0.58× |
| xmark | 1.26× | 2.71× | 1.56× | 1.39× |
| Kronecker | 1.02× | 1.29× | 1.04× | 10.27× |

GO queries improve 1.29× and builds 1.90× against previous TRIC; CiteSeer improves
1.29× and 2.07×. YAGO improves 1.39× and 1.74×. Held-out anthra/agrocyc builds
improve about 5.46×/5.35×, with approximately 2.55× faster lifecycles. Measured
CiteSeer native VmHWM falls from 20,960 to 5,756 KiB; retained index capacity
falls from 2,068,328 to 1,139,992 bytes. These capacities exclude caller input
and allocator metadata as documented.

**Remaining losses matter.** Uniform arXiv queries are approximately 10.5%
slower than previous TRIC, despite faster construction and lower peak memory.
The candidate wins only 34/76 warm query cells and 45/76 lifecycle cells against
the fastest measured external baseline. O'Reach retains large negative-heavy
query advantages on several additional sparse biology graphs; BFL also wins
important construction and query regimes. This is an improved engineering
tradeoff, not global SOTA. Current PLL/MLRQ-O implementations, matched total
memory, authentic graphs above 100,000 vertices and independent dedicated-hardware
replications remain unqualified. See the current MLRQ paper at
https://doi.org/10.1007/s44443-025-00310-0 for why O'Reach alone is insufficient.

One generated-communities result failed final SHA256/case-count verification.
The entire graph was repeated with the same executable hashes; only the
complete verified replacement is promoted. Both manifests and the rejection
reason are recorded. The runner now uses exclusive output initialization,
atomic replacement, fsync and final read-back verification. Superseded
exploratory outputs are not part of this qualification.

A subsequent same-byte-budget signature/metadata split was rejected: small
negative-query gains were offset by positive-query regressions. Its raw pilot
and prototype header are retained in `ablation_layout.json.gz`; it is not the
shipped runtime and is not included in the qualification counts above.

Runtime CI passed on Python 3.10 and 3.13, including full address/undefined/leak
sanitizer commands, at [run 39905073000](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39905073000).
Additional integrity and deep-diamond saturation checks are included in the
final PR head and rechecked by the final CI run. All results remain bounded
empirical evidence, with the analytical invariant argument given above.

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

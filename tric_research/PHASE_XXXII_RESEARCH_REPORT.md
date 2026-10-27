# Phase XXXII: release the interval construction directory

27 October 2026. Baseline: PR #31, `09003cb9d7b915516767894f4881542bb8ff4c44`.

## Outcome and scope

Promote a bounded retained-memory improvement: release `interval_rows_` after
materializing all vertex labels. The only runtime change is a five-line insertion
containing one empty-vector swap and its comment. Query bodies, admission rules,
rollback, representation choice and the table allowance are unchanged. No
algorithmic novelty, latency improvement or global SOTA is claimed.

On the tested C++ toolchain, this saves eight bytes per interval SCC. Independent
allocation tracking confirms improvement in 21 of 42 cases: five purpose-built
cases and 16 preserved graph fixtures. Direct closure, forest, chain, dense-bitset,
compressed-word and pure-search cases retain their previous storage. The two
large forests save zero bytes and serve as negative controls.

| Case | Before retained bytes | After retained bytes | Released bytes |
|---|---:|---:|---:|
| 1,024-SCC interval star | 49,536 | 41,344 | 8,192 |
| `heldout_human` | 1,869,816 | 1,559,328 | 310,488 |

The star's table payload falls from 16,384 to 8,192 bytes; `heldout_human` falls
from 627,472 to 316,984 table bytes. These are table and object/vector allocation
measurements, not RSS. The 100,000-vertex star regression verifies 800,000 final
table bytes, down from 1,600,000, and a retained-size bound. There is no claimed
construction-peak reduction.

## Correctness argument

The directory stores `(offset,count)` pairs used by closure construction,
widest-interval rotation and label materialization. All those reads precede the
swap. Every vertex in an interval SCC receives the row count in `auxiliary`,
offset in `route`, and cached endpoints in its label. SCC aliases receive the
same copied values. Queries read vertex labels and the retained `intervals_`
vector, never the directory. Later fallback CSR construction also has no directory
reads. These vectors have separate allocations, so releasing the directory
invalidates no query-accessible storage. Moving and destroying an empty directory
preserve ownership of the other vectors.

Admission and rollback finish before the swap. The unchanged `remaining` budget
charges directory bytes throughout construction; later partitions cannot spend
the reclaimed bytes. A two-star fixture with capacity for only one verifies this
boundary. Failed interval construction between two successful partitions checks
rollback. One-byte-short admission, zero/minimal scratch, relabeled SCC aliases,
empty graphs and other representation routes are also tested. This is a
human-checkable conditional argument, not proof-assistant certification.

## Independent memory evidence

`interval_storage_check.cpp` overrides ordinary and over-aligned C++ allocation
and deallocation, tracking requested live bytes and allocation counts. Input
storage exists before measurement. After construction, observed heap bytes plus
the index object's size must equal `retained_bytes()`. A move must preserve both
allocation and retained-size measurements. After queries and destruction, live
bytes and block count must return to their initial values.

Every paired record requires table savings to equal reported retained savings
and independently observed heap savings. Nonzero savings must remove exactly one
allocation. Routing, exposed construction counters, answers and oracle coverage
must match, and instrumented peak payload must not grow. This rejects clearing
the vector without deallocation or merely changing accounting.

Probes use GCC 13.3 and UBSan with separately staged headers; dependency files
verify all five selected runtime headers. The campaign covers 15 purpose-built
cases and all 27 preserved fixture files: 19 original graphs, four synthetic
families, and two large forests with warm and single-pass query fixtures. Every
distinct pair from every case is checked; duplicates are removed and pairs sorted
by source for BFS reuse. This is coverage verification, not a timing experiment
or new independent data.

Allocation probes performed **450,648** BFS pair checks across both versions.
Eleven adversarial evidence tests reject omitted/duplicate cases, stale
allocations, false accounting, changed indexing, altered answers, missing oracle
checks, peak growth, changed sources and altered inputs.

## Full build and validation

Both versions also use the original BFL/PLL/PPL/O'Reach-enabled configuration with
pinned upstream sources and objects. The baseline reproduces Phase XXX's binary:
`12cbc59121898bdfb985f8ec88df304d2d2a3a88cc7a92cb7328bd542a5580e7`.
The candidate SHA-256 is
`4c74844f13e660d2ce17dc2359a8e5487b56cb9aef2cb867010cf0e25b4a52fe`.

Separate smoke checks execute the first original query case from each of the 27
fixture files on both binaries: 54 processes and 78,624 independent BFS checks.
Memory differences agree with the allocation probe; routing and answers match.
Single executions do not qualify latency. External comparators were linked but
not executed; no historical win count transfers to this change.

All 35 native/Python tests passed locally. The initial ASan/UBSan invocation hit a
LeakSanitizer `/proc`/ptrace environment failure, preserved in the evidence. Local
address/undefined-behavior checks are also run with leak scanning disabled; hosted
CI retains the normal ASan/UBSan configuration. Independent allocation probes
separately check index destruction for leaked bytes and blocks.

CI validates Phase XXX/XXXI using their original source snapshots, checks this
campaign and rebuilds the 15 allocation cases under UBSan on Python 3.10/3.13.
Artifact seals preserve failures and successes.

## Remaining obligations

This eliminates dead construction metadata. It does not resolve query regressions,
establish a latency/memory Pareto frontier, demonstrate RSS savings or fill the
external-comparator gaps from Phase XXXI. Future speed claims still require frozen
gates, feasible durations, identical-binary controls, broader topology coverage
and matched resource accounting.

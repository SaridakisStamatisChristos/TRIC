# Phase XXXIII — construction qualification and broader comparisons

Baseline: PR #32, `02a91849193e12266785ecfd1d49cd8d87b458f2`.
Campaign began 28 October 2026 and resumed 30 October after an interrupted session.
**Decision: retain the PR #32 runtime. No construction candidate qualified.**
This phase adds reproducible experiments, independent checks and six comparator
adapters; it does not change the production reachability algorithm.

## Construction experiments

Three distinct candidates were frozen before the pilot: stable CSR storage for
the SCC transpose, topological suffix/coverage pruning in direct closure, and
partition-sized interval merge buffers. All used the full existing BFL, PLL,
PPL and O'Reach compiler configuration. No query implementation changed.

The 31-graph pilot used five cyclic trials across four implementations and an
identical-binary control. Each process repeatedly reconstructed an already parsed
graph for at least 200 ms of thread CPU, then independently BFS-checked queries.
The reported ratio is baseline CPU per construction divided by candidate CPU per
construction. Each graph has equal weight. This is not a cold-start or query
latency measurement.

| Candidate | Pilot median ratio | Worst graph | Decision |
|---|---:|---:|---|
| Stable CSR transpose | 1.243× | 1.067× | Proceed to qualification |
| Closure suffix/coverage pruning | 1.011× | 0.898× | Reject |
| Smaller interval buffers | 1.015× | 0.897× | Reject |

The pilot required median ≥1.05, every graph ≥0.90, and every identical control
inside [0.90, 1/0.90]. The closure and buffer candidates failed these fixed gates.
They were not subsequently tuned or promoted.

## Resource counterexample and correctness

The first CSR prototype allocated two temporary eight-byte offset buffers on an
empty graph, increasing peak allocation from zero to 16 bytes. This violated the
no-peak-growth requirement. CSR v2 adds an empty-graph return before allocation;
its source and qualification protocol were frozen before qualification timing.
The original candidate and counterexample remain archived.

CSR v2 matched the exact baseline SCC component IDs on 8,002 graphs, including
8,000 seeded multigraphs and two directed 200,000-vertex paths. Invalid endpoints
were rejected. The native exhaustive/adversarial suite passed under UBSan.
The [proof sketch](evidence/phase33/SCC_CORRECTNESS.md) explains why stable CSR
preserves predecessor order, stack transitions, SCC IDs and downstream behavior.
It is not a machine-checked proof or a new SCC algorithm.

Independent allocation tracking covered 52 cases and 228,033 BFS checks across
three implementations. Retained bytes, live blocks, admission and route counters
were identical. CSR v2 reduced observed peak construction allocation on four
cases, with a maximum reduction of 10,232,864 bytes. These observations do not
establish a universal allocation bound or supersede the failed speed gates.

## Qualification and fixed replication

Qualification added six frozen graph shapes, for 37 graphs total, and used nine
cyclic trials per graph. Warm construction required median ≥1.10 and every graph
≥0.95. Fresh-process single construction required median ≥1.05 and every graph
≥0.90. Both required every identical-binary control within [0.90, 1/0.90].

| Campaign | Warm median / worst | Single-build median / worst | Decision |
|---|---:|---:|---|
| Original qualification, 9 trials | 1.258× / 1.025× | 1.158× / 0.934× | Fail: three control cases |
| Fixed replication, 27 trials | 1.251× / 1.062× | 1.182× / 0.898× | Fail: single-build floor and one control |
| All 36 trials pooled | 1.242× / 1.066× | 1.174× / 0.921× | Pass pooled gates only |

After the original control failures, one additional replication was preregistered:
27 trials, identical source/binaries/fixtures/thresholds, and a requirement that
**both replication and pooled data pass**. No repeat-until-pass rule was allowed.
The warm replication passed. Single construction was about 11.3% slower on
`phase33_dense_order`; its 0.898235 ratio missed the 0.90 floor. The identical
control on `phase33_holdout_sparse_random` was 1.118436, above 1/0.90. Therefore
CSR v2 remains rejected despite favorable medians and pooled results.

The session interruption occurred after 25 completed warm replication graphs.
Their bytes and original incomplete manifest were preserved. Only the remaining
12 graphs were resumed on 30 October, followed by the single-build campaign.
Segment manifests and environment receipts make this boundary explicit. This is
not an independent-host replication claim. The complete construction archive
contains **8,767 fresh timing processes** in complete cells, including unfavorable
results. Counts exclude any uncheckpointed partial cell at interruption; such a
cell is rerun in full. No completed cell was rerun or replaced.

## Expanded external comparison

The unchanged PR #32 runtime completed 4,840 timed processes across 76 cases (19 graphs × four query strata). All methods passed the 29-graph preflight. The campaign independently checked 6,041,774 query pairs across preflight and timing.
There were 4 attempted-process failures and 24 explicitly unattempted TF-Label builds and 0 control-failed cases.

Ratio below is comparator CPU per call divided by TRIC CPU per call; values above 1 favor TRIC. Only cells passing the fixed control and completeness checks qualify. These medians are descriptive measurements, not confidence intervals.

| Pinned implementation | Qualified cells | Median ratio | TRIC faster / comparator faster |
|---|---:|---:|---:|
| feline | 76/76 | 6.727× | 76 / 0 |
| grail | 76/76 | 4.606× | 76 / 0 |
| preach | 76/76 | 3.780× | 76 / 0 |
| ferrari | 76/76 | 2.147× | 76 / 0 |
| tflabel | 72/76 | 3.794× | 72 / 0 |
| tol | 76/76 | 2.622× | 76 / 0 |

Four of eight TF-Label builds on kron_logn12 uniform exceeded 120 seconds. A documented budget-stopping deviation then omitted 24 further TF-Label builds on the same graph across its other three strata. Those cells are unqualified, never wins. All other arms retain eight trials. The original frozen protocol remains archived. The session stopped after 72 complete timing cases. Their original manifest and bytes were preserved; only the final four cases were resumed. The verifier checks this continuation against the preserved prefix.


The new adapters use the C++ implementations in
[PyReachability at the pinned commit](https://github.com/reneveloso/PyReachability/tree/0c84ca38de2d384c561690f4782f93e19fc76816).
These are implementation-specific comparisons. Most are independent
implementations of published algorithms, not the original authors' optimized
reference executables. Upstream's fidelity assessment is preserved but is not
an independently completed paper-to-code audit. The existing author-code
BFL/O'Reach/PLL/PPL evidence remains separate and unchanged.

Each adapter maps original vertices through SCC condensation before indexing.
Defaults are fixed: FELINE one-direction, GRAIL five dimensions/seed 1,
FERRARI k=5/c=4/seeds=32, and upstream defaults for the other methods. Every
process receives identical graph/query bytes, performs one complete untimed query
warmup, and times repeated queries for at least 100 ms of thread CPU. Eight
cyclic trials balance all eight arms, including the identical TRIC control.
BFS verification follows timing. The comparison measures warm repeated-query
throughput, not novel requests or single-query cold latency. Clock checks occur
once per replay; checksum arithmetic remains in the timed loop. Per-call costs
therefore include harness overhead. This shared C++ harness differs from the
older comparator harness, so their absolute timings are not interchangeable.

The process budget is 120 seconds and 4 GiB address space. Failures are preserved
and never counted as victories. TRIC's 2 MiB table allowance is not a total-memory
cap. Comparator payload estimates and process VmHWM are not interchangeable and
are not equalized memory budgets. Consequently, these measurements cannot support
unqualified global SOTA claims, even on cells where TRIC is faster.

## Execution failures and reproducibility

The archive retains a pilot launch failure before checks were ready, the empty
resource counterexample, and a compiler failure caused by a probe executable
named `memory` shadowing the standard `<memory>` header in an include directory.
The latter was fixed by renaming the executable; qualification used successfully
rebuilt, hash-checked binaries. The resumed publication verifier also corrected
fixture path handling and resource-input serialization without changing raw
experimental outputs or acceptance thresholds.

See [reproduction and archive layout](evidence/phase33/README.md). CI rechecks
frozen inputs, all trials, source/binary provenance, acceptance decisions and
historical seals. Corruption tests exercise incomplete or altered evidence.
Fresh UBSan builds check all five archived variants and the external adapters.

## Remaining work

The measured dense-graph single-build regression needs a different construction
strategy and new held-out qualification, rather than threshold relaxation.
Broader comparisons still need independent-host reproduction, comparable total
memory budgets, original-author implementations where available, and additional
recent methods and large real-world graph families. No generalized SOTA or
algorithmic novelty has been established by this phase.

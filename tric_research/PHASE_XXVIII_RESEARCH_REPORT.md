# Phase XXVIII: cache the first exact closure interval

Baseline: PR #27 / 49eafb9b8cc06ff15b9f71058e2eb8770fc50961.
Runtime: 3505d6390e24f30515d78f90c0fed43e7a6e4bb8, stacked PR #28.
The final evidence commit does not change runtime headers.

## Objective and execution

Reduce general-query overhead while retaining exact reflexive reachability,
invalid-endpoint behavior, owned snapshots, C++17 portability, graph-only route
selection, 2 MiB default table payload and 64 MiB requested index scratch.
Neither budget is a total-RSS limit. Global SOTA is an evaluation objective,
not a promised outcome or an acceptance criterion that can be asserted from
one favorable slice.

Elite AGI supplied the factual engineering lens; Knowledge Nexus separates
observed path counts, measured effects and causal hypotheses; Trillion
Developer++ applies the baseline/hypothesis/controlled-change/verification
loop. OmO runtime_info reports installed=false, so OmO Controller used its
native recursive fallback. No real OmO task or parallel worker execution is
claimed. The adversarial pass is a separate reasoning/verification pass in
this controller, with executable BFS and sanitizer evidence where available.
No framework definitions or persistent user memories were changed.

## Reconstruction and rejected experiments

A separate instrumented partitioned runtime counted decisions for 76 frozen
1,200-pair cases. On historically held-out sparse biological graphs, hundreds
of balanced queries reach interval search; fallback DFS is not invoked for
those queries. This is a count of paths through the partitioned backend, not a
cycle profile, and direct-closure automatic routes are outside that diagnostic.
The source generator and complete counts are preserved.

Initial interval/inline pilots accidentally compiled the comparison cpp inside
the live source directory. Quoted includes selected baseline headers before
prototype include directories. All six binaries had the same SHA256. These
runs are INVALID for candidate comparisons; no rejection or uplift claim uses
their timings. Raw bytes, failed build provenance and the correction are kept.
The repaired pilot copies cpp outside the headers, emits compiler dependency
files, verifies the selected runtime paths and obtains six distinct binaries.
The final build helper now enforces dependency-path verification too.

The corrected six-arm pilot compares the baseline, branchless binary search,
linear scans for at most four/eight ranges, inline first interval, and inline
first interval plus branchless search. There are 76 cells, six balanced fresh
process trials per cell and 3,000 actual replays per frozen pair. Stand-alone
branchless and small scans fail to establish broad benefit. Plain inline-first
has a 1.035x median thread-CPU ratio on 52 general-route cells and 1.307x on
historically held-out positive strata; the combined branchless variant is
mixed. These are exploratory selection results, not final qualification.

The final runtime uses portable arithmetic -group_id-1 instead of the pilot's
bitwise complement, removes the now-unreachable interval-mode dispatch block,
and adds invariant comments. Final qualification rebuilds and measures this
exact frozen runtime, rather than treating prototype timings as accepted data.

## Mechanism and correctness argument

Complete interval closure rows already encode exact reachable SCC preorder
coordinates. The old label retains row offset/count, a Bloom signature and
several generic partition/DFS fields. For interval-mode partitions, cache the
first complete interval's begin/end in the existing local/tree_end fields and
encode group as -group_id-1. Keep tree_begin as the queried SCC's original
preorder; keep the same combined ancestor/descendant Bloom signature. Labels
remain exactly 32 bytes, and every original closure row/table stays unchanged.

Queries preserve endpoint checks and the necessary-condition signature reject.
For an interval source, an unsigned range test on the cached first interval is
an exact positive certificate. A miss with one interval is an exact negative.
Otherwise search the remaining sorted, disjoint intervals with upper_bound.
All noninterval source labels keep the existing equality, partition,
topological, DFS, chain/bit/word and fallback behavior.

Why the tag cannot cause a cross-mode error: every vertex of one weak partition
has the same selected representation. If a noninterval source sees a negative
target group, it belongs to a different weak partition and the existing group
check rejects it. Interval queries use globally unique SCC preorder positions;
complete closure ranges cannot contain a foreign unreachable SCC, including
SCCs in another DFS tree or weak component. SCC aliases share coordinates and
closure rows. Thus the cached membership and residual search preserve exactly
the previous row's set; a Bloom collision can only defer rejection.

For a cached half-open range [lo,hi), 0 <= lo < hi <= SCC_count <= INT_MAX.
uint32(target)-uint32(lo) < uint32(hi-lo) holds exactly inside the range.
Underflow wraps to a value larger than any legal width. hi-lo cannot overflow
the signed int fields. There are at most INT_MAX weak partitions, so
-group_id-1 is representable for every constructed tag. No pointer dereference
occurs for the empty residual case. Every accepted interval row contains at
least its own SCC, so caching its first element is valid.

This is an established inline-certificate/cache technique, not a new asymptotic
reachability algorithm or a formal machine proof. Worst-case interval queries
remain O(log k) for k ranges; cached hits use O(1). Construction adds O(1) reads
per original vertex, without a new vector or extra retained table payload.

## Verification and provenance

All 34 existing test methods pass, including relabelled SCC aliases, mixed
partitions, invalid endpoints, rollback, saturation, scratch limits and original
PLL/PPL APIs. Native checks retain 18,432 exhaustive cases, 1,440 adversarial
cases, 589,824 lifted interval cases, 207,360 forest-family cases and 1,296
packed-coordinate boundaries against independent BFS/scalar references.
Local ASAN/UBSAN passes; only local LeakSanitizer is disabled because of the
traced host environment. CI retains full leak checking.

The comparison source and external revisions are unchanged from Phase XXVII.
The new build reproduces PR #27 binary SHA256
8ad6d8cad9567b8eebb1efe0af34d02b4a3e248f6a75402591b3ba2f4b942180.
Candidate SHA256 is
d70aaf578be23ec978f2088e8ce90164fb50e8e5e1de7c6449e4984a505a1858.
Dependency-file records prove which eight runtime headers each binary compiled.
The additional PR #26 binary comes from the preserved matched Phase XXVII
build, with the identical comparison-source hash, external pins and effective
optimization flags; its build manifest is included separately.

Historical Phase XXVII validation now accepts an explicit repository-shaped
frozen source root. All previously recorded source hashes are checked against
that snapshot; current unchanged external source bytes remain independently
pinned. This preserves old evidence without requiring future runtime code to
match a superseded implementation. Current runtime/build hashes are checked
separately by Phase XXVIII's validator.

## Measurement protocol

The first seven-arm long-replay attempt was interrupted because search-heavy
external arms made replay 1,000 costly. This decision used execution cost,
not candidate uplift. That incomplete run is preserved and excluded.
Four complete, separate comparisons replace it; ratios never mix their horizons:

| Comparison | Arms | Trials | Pairs per cell | Replays |
|---|---:|---:|---:|---:|
| Native precision | PR #26, PR #27, candidate | 6 | 1,200 | 3,000 |
| External comparison | PR #27, candidate, BFL, OReach PDFs/PBiBFS, PLL, PPL | 7 | 1,200 | 100 |
| Forest warm guard | PR #27, candidate | 4 | 64 | 1,000 |
| Forest single-pass guard | PR #27, candidate | 4 | 4,096 | 1 |

The first two reuse all 19 original graphs, 39 graph-seed pairs and four query
strata (156 seed-level cells; 76 graph/stratum aggregates). All are exposed to
this continuing campaign, including files historically named heldout. The
forest guards reuse the same two exposed author-provided condensations from
Phase XXVII, not new independent general graphs. Their actual vertex counts
are 693,947 and 1,595,444; UniProt's filename does not make this a 22-million-
vertex experiment. Frozen pair replays are cache-hot reuse, not new requests.
The 4,096-pair guard executes distinct pairs once but does not flush CPU caches.

CPU 1 is pinned; all measured processes are sequential, with cyclic launch
orders balancing every arm over positions. No local compilation, generation
or test workload runs concurrently. Wall query/build/lifecycle measurements are
primary; thread CPU is retained as a secondary check. Lifecycle includes
parse+build+query and excludes process startup, BFS oracle and teardown.
VmHWM is sampled before oracle verification. Each arm independently checks all
pairs with BFS after timing. Memory reports distinguish requested table payload,
actual retained capacities and total executable peak; upstream indexSize() is
not total retained memory. Full PLL/PPL, BFL and OReach provenance and limits
remain as documented in Phase XXVII.

This is shared-host evidence. Launch balancing does not remove scheduler,
frequency, cache or compiler-layout effects. Ratios use matched trial indices,
then medians over trials, seeds and graph/stratum aggregates as explicitly
labelled. Observed trial ranges are not confidence intervals. Related seeds,
strata, historical phases and the same two forest graphs are not independent
performance replications.

## Results

### native

156 seed-level cells; 76 graph/stratum aggregates; 2,808 fresh processes; 10,108,800,000 actual query calls; 3,369,600 BFS pair executions. Every input/result digest, case and budget check passes. Repeated execution of a pair is not a unique independent input.

| Metric | PR #27 / candidate median | Wins / aggregates | Fastest external / candidate median | Wins / aggregates |
|---|---:|---:|---:|---:|
| query_ns | 1.018x | 53/76 | not measured | — |
| query_thread_cpu_ns | 1.019x | 54/76 | not measured | — |
| build_ns | 1.010x | 45/76 | not measured | — |
| lifecycle_ns | 1.020x | 55/76 | not measured | — |

Greater than one favors the candidate. These are medians of per-trial paired ratios, then per-seed medians and unweighted graph/stratum aggregates. External minima use all five external arms separately for each trial and metric.

### small

156 seed-level cells; 76 graph/stratum aggregates; 7,644 fresh processes; 917,280,000 actual query calls; 9,172,800 BFS pair executions. Every input/result digest, case and budget check passes. Repeated execution of a pair is not a unique independent input.

| Metric | PR #27 / candidate median | Wins / aggregates | Fastest external / candidate median | Wins / aggregates |
|---|---:|---:|---:|---:|
| query_ns | 1.009x | 50/76 | 1.007x | 39/76 |
| query_thread_cpu_ns | 1.009x | 51/76 | 1.006x | 39/76 |
| build_ns | 1.005x | 40/76 | 0.946x | 24/76 |
| lifecycle_ns | 1.008x | 46/76 | 1.022x | 47/76 |

Greater than one favors the candidate. These are medians of per-trial paired ratios, then per-seed medians and unweighted graph/stratum aggregates. External minima use all five external arms separately for each trial and metric.

### forest-warm

8 seed-level cells; 8 graph/stratum aggregates; 64 fresh processes; 4,096,000 actual query calls; 4,096 BFS pair executions. Every input/result digest, case and budget check passes. Repeated execution of a pair is not a unique independent input.

| Metric | PR #27 / candidate median | Wins / aggregates | Fastest external / candidate median | Wins / aggregates |
|---|---:|---:|---:|---:|
| query_ns | 1.002x | 4/8 | not measured | — |
| query_thread_cpu_ns | 1.001x | 5/8 | not measured | — |
| build_ns | 0.999x | 4/8 | not measured | — |
| lifecycle_ns | 0.994x | 2/8 | not measured | — |

Greater than one favors the candidate. These are medians of per-trial paired ratios, then per-seed medians and unweighted graph/stratum aggregates. External minima use all five external arms separately for each trial and metric.

| Dataset | Stratum | Query ratio vs #27 | Observed paired query range | Lifecycle ratio vs #27 |
|---|---|---:|---:|---:|
| large_citeseer | uniform | 1.016x | 1.001–1.309x | 0.989x |
| large_citeseer | positive | 0.998x | 0.353–1.430x | 0.981x |
| large_citeseer | negative | 0.990x | 0.821–1.002x | 1.020x |
| large_citeseer | balanced | 0.832x | 0.655–1.013x | 1.000x |
| large_uniprot_22m | uniform | 1.022x | 0.873–1.737x | 1.021x |
| large_uniprot_22m | positive | 1.006x | 0.134–1.874x | 0.976x |
| large_uniprot_22m | negative | 1.283x | 0.689–1.427x | 0.998x |
| large_uniprot_22m | balanced | 0.999x | 0.911–1.770x | 0.953x |

Ranges are observed variability, not confidence intervals. Short forest timings are especially sensitive to scheduling and code layout. No external competitor is rerun in these guards.

### forest-fresh

2 seed-level cells; 2 graph/stratum aggregates; 16 fresh processes; 65,536 actual query calls; 65,536 BFS pair executions. Every input/result digest, case and budget check passes. Repeated execution of a pair is not a unique independent input.

| Metric | PR #27 / candidate median | Wins / aggregates | Fastest external / candidate median | Wins / aggregates |
|---|---:|---:|---:|---:|
| query_ns | 0.976x | 0/2 | not measured | — |
| query_thread_cpu_ns | 0.973x | 0/2 | not measured | — |
| build_ns | 1.000x | 1/2 | not measured | — |
| lifecycle_ns | 0.973x | 1/2 | not measured | — |

Greater than one favors the candidate. These are medians of per-trial paired ratios, then per-seed medians and unweighted graph/stratum aggregates. External minima use all five external arms separately for each trial and metric.

| Dataset | Stratum | Query ratio vs #27 | Observed paired query range | Lifecycle ratio vs #27 |
|---|---|---:|---:|---:|
| large_citeseer | uniform | 0.991x | 0.649–1.310x | 1.026x |
| large_uniprot_22m | uniform | 0.962x | 0.943–1.429x | 0.919x |

Ranges are observed variability, not confidence intervals. Short forest timings are especially sensitive to scheduling and code layout. No external competitor is rerun in these guards.

### Native route and PR #26 comparison

The following are medians over seed-level cells at the same 3,000-replay horizon, rather than graph/stratum aggregates. PR #26 is measured directly in this run; no historical ratios are multiplied.

| Route | Query wall vs #27 | Query CPU vs #27 | Query wall vs #26 | Query CPU vs #26 |
|---|---:|---:|---:|---:|
| all | 1.018x (102/156) | 1.019x (102/156) | 1.030x (124/156) | 1.030x (125/156) |
| general | 1.048x (71/92) | 1.046x (71/92) | 1.077x (78/92) | 1.071x (79/92) |
| direct | 0.999x (31/64) | 0.998x (31/64) | 1.023x (46/64) | 1.023x (46/64) |

### Previously losing sparse biological subset

These six named graphs were selected from the prior campaign's remaining external losses, not newly held-out data: agrocyc, anthra, ecoo, human, mtbrv and vchocyc.

| Stratum | Native query wall vs #27 | Native query CPU vs #27 |
|---|---:|---:|
| positive | 1.478x (6/6) | 1.480x (6/6) |
| negative | 1.028x (5/6) | 1.027x (6/6) |
| balanced | 1.276x (6/6) | 1.275x (6/6) |
| uniform | 0.995x (2/6) | 0.995x (2/6) |

### Complete graph/stratum query results

All 76 aggregates appear below, including every regression. Native columns use horizon 3,000; the external column is a separate matched seven-arm experiment at horizon 100. Those ratios must not be pooled as one measurement. Full build/lifecycle/RSS values and seed ranges are in each run's CSVs.

| Dataset | Stratum | Native query vs #27 | Native query vs #26 | Native lifecycle vs #27 | External query ratio (h100) |
|---|---|---:|---:|---:|---:|
| example | balanced | 1.053x | 1.055x | 1.035x | 1.564x |
| example | negative | 0.946x | 0.924x | 0.974x | 1.852x |
| example | positive | 1.068x | 1.083x | 1.043x | 1.386x |
| example | uniform | 0.938x | 0.986x | 0.996x | 1.572x |
| generated_blocks | balanced | 1.010x | 0.999x | 1.004x | 1.288x |
| generated_blocks | negative | 1.014x | 1.031x | 1.020x | 0.822x |
| generated_blocks | positive | 1.033x | 1.029x | 1.024x | 1.823x |
| generated_blocks | uniform | 1.012x | 1.036x | 1.020x | 0.832x |
| generated_communities | balanced | 1.025x | 1.047x | 1.020x | 1.943x |
| generated_communities | negative | 0.934x | 1.024x | 0.948x | 1.050x |
| generated_communities | positive | 0.999x | 1.029x | 1.012x | 2.119x |
| generated_communities | uniform | 0.979x | 1.047x | 0.976x | 1.721x |
| generated_dag | balanced | 0.990x | 1.029x | 0.983x | 3.530x |
| generated_dag | negative | 0.987x | 1.025x | 0.987x | 3.035x |
| generated_dag | positive | 1.009x | 1.016x | 1.016x | 3.928x |
| generated_dag | uniform | 1.007x | 1.011x | 1.022x | 2.710x |
| grail_citeseer | balanced | 1.104x | 1.135x | 1.041x | 1.641x |
| grail_citeseer | negative | 1.012x | 1.017x | 1.015x | 1.025x |
| grail_citeseer | positive | 1.139x | 1.165x | 1.085x | 1.430x |
| grail_citeseer | uniform | 1.022x | 1.015x | 0.998x | 1.111x |
| grail_go | balanced | 1.098x | 1.131x | 1.070x | 1.675x |
| grail_go | negative | 1.007x | 1.037x | 1.015x | 1.006x |
| grail_go | positive | 1.160x | 1.205x | 1.123x | 1.883x |
| grail_go | uniform | 0.998x | 1.017x | 1.020x | 0.999x |
| grail_kegg | balanced | 0.990x | 1.002x | 0.992x | 1.052x |
| grail_kegg | negative | 0.993x | 1.004x | 0.996x | 0.760x |
| grail_kegg | positive | 1.012x | 1.037x | 1.028x | 0.833x |
| grail_kegg | uniform | 1.000x | 0.995x | 0.996x | 0.679x |
| grail_pubmed | balanced | 1.090x | 1.139x | 1.024x | 1.636x |
| grail_pubmed | negative | 1.017x | 1.008x | 1.020x | 1.093x |
| grail_pubmed | positive | 1.162x | 1.153x | 1.087x | 1.543x |
| grail_pubmed | uniform | 0.975x | 1.012x | 0.988x | 1.113x |
| grail_yago | balanced | 1.229x | 1.247x | 1.118x | 1.332x |
| grail_yago | negative | 1.009x | 1.017x | 1.016x | 0.963x |
| grail_yago | positive | 1.378x | 1.388x | 1.227x | 1.210x |
| grail_yago | uniform | 1.027x | 0.961x | 1.028x | 0.968x |
| heldout_agrocyc | balanced | 1.044x | 1.096x | 1.032x | 0.416x |
| heldout_agrocyc | negative | 0.999x | 1.042x | 1.012x | 0.521x |
| heldout_agrocyc | positive | 1.103x | 1.111x | 1.077x | 0.393x |
| heldout_agrocyc | uniform | 1.018x | 1.009x | 1.015x | 0.517x |
| heldout_amaze | balanced | 0.980x | 1.035x | 0.996x | 0.840x |
| heldout_amaze | negative | 0.973x | 0.995x | 0.981x | 0.774x |
| heldout_amaze | positive | 1.079x | 1.051x | 1.085x | 0.858x |
| heldout_amaze | uniform | 1.003x | 1.021x | 1.007x | 0.663x |
| heldout_anthra | balanced | 1.283x | 1.319x | 1.148x | 0.536x |
| heldout_anthra | negative | 1.019x | 1.027x | 0.992x | 0.559x |
| heldout_anthra | positive | 1.497x | 1.529x | 1.305x | 0.551x |
| heldout_anthra | uniform | 0.964x | 0.976x | 0.990x | 0.449x |
| heldout_ecoo | balanced | 1.046x | 1.078x | 1.030x | 0.440x |
| heldout_ecoo | negative | 1.040x | 1.018x | 0.998x | 0.575x |
| heldout_ecoo | positive | 1.098x | 1.129x | 1.092x | 0.397x |
| heldout_ecoo | uniform | 0.991x | 0.976x | 1.032x | 0.563x |
| heldout_human | balanced | 1.388x | 1.397x | 1.145x | 0.599x |
| heldout_human | negative | 1.037x | 1.033x | 0.995x | 0.550x |
| heldout_human | positive | 1.546x | 1.582x | 1.184x | 0.525x |
| heldout_human | uniform | 0.999x | 1.006x | 1.004x | 0.580x |
| heldout_mtbrv | balanced | 1.293x | 1.372x | 1.193x | 0.588x |
| heldout_mtbrv | negative | 1.071x | 1.092x | 1.026x | 0.542x |
| heldout_mtbrv | positive | 1.477x | 1.517x | 1.376x | 0.625x |
| heldout_mtbrv | uniform | 1.023x | 0.974x | 0.998x | 0.572x |
| heldout_nasa | balanced | 1.099x | 1.108x | 1.083x | 1.099x |
| heldout_nasa | negative | 0.980x | 1.044x | 0.950x | 1.086x |
| heldout_nasa | positive | 1.107x | 1.175x | 1.090x | 1.008x |
| heldout_nasa | uniform | 0.990x | 1.026x | 0.990x | 1.038x |
| heldout_vchocyc | balanced | 1.269x | 1.402x | 1.188x | 0.558x |
| heldout_vchocyc | negative | 1.007x | 1.133x | 0.993x | 0.503x |
| heldout_vchocyc | positive | 1.480x | 1.540x | 1.336x | 0.571x |
| heldout_vchocyc | uniform | 0.974x | 1.002x | 1.017x | 0.570x |
| heldout_xmark | balanced | 1.141x | 1.189x | 1.103x | 1.451x |
| heldout_xmark | negative | 1.071x | 1.076x | 1.048x | 0.871x |
| heldout_xmark | positive | 1.279x | 1.198x | 1.166x | 1.496x |
| heldout_xmark | uniform | 1.042x | 1.016x | 1.030x | 1.325x |
| kron_logn12 | balanced | 0.988x | 1.026x | 1.019x | 1.881x |
| kron_logn12 | negative | 0.998x | 0.985x | 1.028x | 1.340x |
| kron_logn12 | positive | 1.017x | 1.012x | 1.055x | 2.365x |
| kron_logn12 | uniform | 0.978x | 0.996x | 1.020x | 1.685x |

All accepted paired trials have exactly equal candidate/PR #27 table payload and retained capacities. VmHWM may still vary by process and is not a memory matching assertion.


## Claim boundary and next decision

Accept the first-range cache as a bounded general-query improvement, with
per-cell and forest-single-pass regressions preserved. Native wall-query
median is 1.048x over PR #27 (71/92 general seed cells win) and 1.077x over
PR #26 (78/92 win). This directly measured aggregate recovers parity in that
run; it does not establish that every earlier regression is gone. Direct
closure is essentially flat at 0.999x over PR #27. The six targeted biological
positive strata improve 1.478x (6/6), and balanced strata 1.276x (6/6).
Their uniform stratum is 0.995x, illustrating the limited query-mix scope.

The separate seven-arm short-replay comparison wins 39/76 query aggregates
against the fastest of five external arms, with median 1.007x. The worst
remaining cell is agrocyc positive, 0.393x (about 2.54 times slower). Build
median versus the external minimum is 0.946x, while lifecycle is 1.022x.
External and native horizons differ and cannot be pooled. Historical win
counts or worst-case ratios from another phase are not directly paired
measurements of gap reduction.

Forest warm query median is 1.003x (4/8 wins), lifecycle 0.994x. The separate
two-cell single-pass guard has query 0.976x and lifecycle 0.972x; both query
cells lose. The forest code/retained layout is unchanged, but compiler context
and shared-host variability do not permit claiming zero performance effect.
Those small measured losses remain part of the accepted tradeoff, rather than
being erased because the hot algorithm was unchanged. Every accepted trial
has equal table payload and retained capacities to PR #27.

Global SOTA remains unverified. The next high-value work is exact membership
for fragmented positive closure rows on sparse graphs, where PLL/PPL still
lead, followed by independent general graphs and dedicated-hardware replication.
Total-memory Pareto matching and an original or validated MLRQ/MLRQ-O comparison
remain absent. None of the path counts, related historical phases, multiple
seeds or this controller's adversarial reasoning is an independent performance
replication. No algorithmic novelty or machine-checked proof is asserted.

## Reproduction

Build with build_native_comparison.py using the frozen baseline headers and
pinned OReach objects/source/Boost includes from Phase XXVII. The copied cpp,
compiler commands, selected dependencies and source/binary hashes are recorded.
qualification_protocol.json records exact arm sets, pair sources, trials and
horizons. benchmark_native_changes.py refuses nonempty output directories,
verifies each input digest, checks answers/caps/call counts, atomically publishes
completed graph results and seals only complete runs.

Run summarize_native_changes.py separately on each accepted evidence root with
its recorded fixture directory, then verify_phase28_evidence.py. The archive
contains corrected and explicitly invalidated pilot bytes, prototype headers,
commands and the interrupted run. No incomplete/invalid run contributes to final
summary tables. Final-head CI is linked in PR #28.

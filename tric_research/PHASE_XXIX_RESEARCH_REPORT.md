# Phase XXIX: repair chain inheritance and cache the widest interval

Baseline: PR #28 / `4baa1a8b9a19d86bff33e304849e76ed77a7d511`.
Runtime commit: `e5a63e8f429b089439d294362f2629145f349d85`.

## Correctness failure discovered during qualification

The initial fresh cross-linked-chain fixture failed the independent BFS oracle
for both PR #28 and the cache-only candidate. The failure is preserved, together
with both superseded complete native/external runs, in `superseded.json.gz`.
None of those preliminary timings contributes to the final tables below. The
initial protocol and its explicit amendment are both retained.

A smaller counterexample has 160 vertices and 161 arcs: two 80-vertex chains,
with cross edges 0->80, 29->109 and 58->138. At a 1,280-byte table allowance,
`TricReachability.reaches(1,109)` incorrectly returns false in PR #28 despite
path 1->2->...->29->109. `chain_counterexample.txt/json` records the input,
baseline binary failure, exact witness and final candidate's successful BFS
receipt. The optimization did not introduce this bug.

The chain builder initialized its own-chain threshold with the source position.
That proves membership of later vertices on the same path, but not inheritance
of their off-chain descendants. Using that threshold to skip child-row merges
could omit reachable destinations. The fix maintains a separate scalar for
same-chain coverage inherited from complete child rows. Every non-self-chain
threshold already comes from such a row. By reverse-topological induction, a
child row contains its full reachable set; once an inherited row reaches a
later chain vertex, transitivity guarantees that vertex's descendants are also
present. Only this complete inherited coverage now licenses skipping a merge.
The marker is constructor-local, adds no table or retained storage, and preserves
the O(edges * chains) worst-case chain-build bound.

The native sanitizer suite now adds **153,600 all-pairs checks** across original
and permuted versions of that graph and three caps, using both automatic and
partitioned indexes. All 35 Python test methods and ASAN/UBSAN pass after repair.
The full final qualification was restarted on the repaired source; fresh graphs
run first. The accepted runtime includes both the correctness fix and widest
cache. Prior cache-only speed claims are superseded.

Native and fresh runs use a **corrected control**: precisely the final header
with the widest-range finalization removed. Native also measures original
PR #28 as a third arm, at the same horizon, for a direct comparison. External
and forest runs use original PR #28 as their previous arm, solely on inputs
where every process independently passes BFS. This does not validate PR #28 on
arbitrary graphs. The corrected-control source and both build manifests are
preserved and checked; its candidate binary is identical to the final build.

## Change and correctness

The previous interval backend cached its first sorted closure range. This change
selects the widest exact range, places it at row position zero with stable
rotation, and uses the existing cache fields. All closure unions finish before
any rotation. The query implementation, Bloom-first prefix, offsets/counts,
32-byte vertex labels, table budget and requested scratch budget are unchanged.

Before finalization a row is an ordered disjoint sequence of half-open ranges.
Moving one element to the front permutes the same exact set and leaves the
remaining sequence sorted. Cached membership plus binary search over that suffix
therefore answers precisely the original membership predicate. Each row occupies
its own storage segment; SCC aliases reference the same finalized row. Reflexive
membership still succeeds even if the cached range does not contain the source:
the source remains in the residual set. Global preorder coordinates preserve
cross-partition rejection. No further merge consumes the permuted rows.

Strict maximum selection keeps the earliest range on equal widths. The chosen
range maximizes SCC-coordinate coverage among the row's individual intervals;
it need not maximize original-vertex-weighted or application-query hit rate.
Selection uses no query samples. Finalization adds O(R) work for R stored ranges,
constant auxiliary working storage and no allocation or added table payload.
Worst-case query complexity remains O(log k) for k ranges. This is a cache-policy
engineering change using established techniques, not an asymptotic novelty claim.

## Exploration and selection

Three complete, position-balanced pilot runs are preserved in
`evidence/phase29/experiments.json.gz`, including source headers, build digests,
compiler dependency paths, original generation scripts and raw results.

1. Six previously losing biological graphs, four arms and four trials at 1,000
   replays: compare PR #28, widest cache, last cache and early-return binary
   search. Last-cache positive median regressed to 0.805x; early-return did not
   establish consistent gains. Widest helped Agrocyc/Ecoo especially.
2. All 19 existing graphs / 156 seed-stratum cells, four arms, four trials at
   1,000 replays: compare PR #28, widest, widest-before-Bloom and widest-without-
   Bloom. General-route medians were 1.025x, 0.964x and 0.877x respectively.
   Moving/removing Bloom also regressed all six biological uniform cells.
3. Ten general-route graphs, four arms, four trials at 1,000 replays: compare
   PR #28, widest and two degree-ordered DFS variants combined with widest.
   Degree order improved median query ratios to about 1.054x but construction
   ratios were 0.868x/0.888x and lifecycle 0.982x/0.984x. It also changed table
   payload. Plain widest retained the better construction/lifecycle tradeoff.

Plain widest was selected and frozen before fresh-fixture generation and final
qualification. Pilots are selection evidence, not independent confirmations.
No failed/incomplete pilot was discarded; the later aborted qualification is preserved separately. All historical graphs, including
`heldout_*` filenames, are exposed campaign inputs.

## Correctness and build verification

All 35 test methods pass. The new test checks every one of 512 squared endpoint
pairs on an irregular range/gap graph with random relabeling and SCC aliases.
The native checker independently BFS-verifies 18,432 exhaustive, 1,440 larger
adversarial, 589,824 lifted interval-family and 207,360 forest-family cases, plus
1,296 scalar/packed-coordinate comparisons. Local ASAN/UBSAN passes with only
LeakSanitizer disabled for the traced host; CI retains leak detection.

The matched build reproduces PR #28's binary exactly:
`d70aaf578be23ec978f2088e8ce90164fb50e8e5e1de7c6449e4984a505a1858`.
Candidate digest:
`e6550a96854bc092866a4987fc10051d6095959c91e193feb2ad82ebea9491e5`.
Both use g++ 13.3.0, identical comparator source, flags and pinned upstream
objects. Compiler dependency files identify all eight runtime header paths.
Original BFL, both OReach modes, PLL and PPL are unchanged. All accepted paired
trials must have exactly equal table payload, retained capacities and routing.

Phase XXVIII source hashes are checked against a frozen repository-shaped
snapshot, including the original verifier itself. Current sources/builds and
new artifacts are independently checked by `verify_phase29_evidence.py`.
Historical result bytes and hashes are not rewritten to match the new runtime.

## Measurement scope

Every timing process runs sequentially on CPU 1, with cyclic launch orders that
balance all arms over positions. Qualification includes all 19 existing graphs,
39 graph-seed pairs and four strata. Separate fresh synthetic checks use four
new fixed-seed families: fragmented sink blocks, shared hubs, SCC aliases and
cross-linked chains (6,000–12,000 original vertices). Those inputs were frozen
after initial cache selection. They exposed the chain bug and were used for
correctness repair, with no performance retuning. They are distribution
checks, not independent real-world or hardware replication. Forest guards reuse
the prior author-supplied 693,947- and 1,595,444-vertex condensations.

Wall query/build/lifecycle time is primary; thread CPU is secondary. Lifecycle
includes parse + build + query, excluding startup, BFS oracle and teardown.
Each arm BFS-checks every input pair after timing. Native and external replay
horizons are separate experiments and must not be pooled. Repeated frozen pairs
are cache-hot reuse, not distinct requests. Single-pass inputs do not flush
processor caches. The 2 MiB cap is table payload; the 64 MiB scratch allowance
is requested index scratch, neither is total RSS. External total-memory Pareto
matching remains absent. Shared-host scheduling, frequency and compiler layout
can affect unchanged routes. Trial ranges are observed variation, not confidence
intervals; related seeds, strata and historical phases are dependent evidence.

## Qualified results

Ratios greater than one favor the candidate. Aggregate cells first take medians
of paired trial ratios, then medians across seeds for each graph/stratum/horizon.
External minima take the fastest of all five external arms separately per trial
and metric. Build/lifecycle minima may therefore come from different algorithms.

| Run | Replays | Query vs run control | Query wins | Build vs run control | Lifecycle vs run control |
|---|---:|---:|---:|---:|---:|
| native | 3000 | 1.011x | 50/76 | 0.988x | 1.006x |
| external | 100 | 1.004x | 45/76 | 1.004x | 0.998x |
| fresh | 1 | 1.005x | 8/16 | 0.978x | 0.987x |
| fresh | 1000 | 1.035x | 12/16 | 0.983x | 1.000x |
| forest-warm | 1000 | 1.002x | 5/8 | 0.994x | 1.022x |
| forest-fresh | 1 | 0.971x | 1/2 | 0.975x | 1.000x |

Native route breakdown compares the corrected control with the candidate and
uses seed-level cells, rather than graph aggregates:

| Route | Query ratio | Winning seed cells |
|---|---:|---:|
| general | 1.031x | 68/92 |
| direct | 0.999x | 31/64 |

The seven-arm external run has query median **1.009x** against the fastest external, winning **39/76** aggregate cells. The worst current cell is **heldout_ecoo / negative**, **0.528x**, or about **1.89 times slower**. This is a fresh same-run comparison, not a product of historical speedup ratios.

Five sealed comparisons contain **10,788 fresh timing processes**, **12,743,104 post-timing BFS pair executions**, and **11,095,843,072 actual query calls**. These counts do not denote independent inputs or statistical replications.


Direct same-run comparison against original PR #28 (native horizon 3,000):

| Route | PR #28 / final candidate | Winning seed cells |
|---|---:|---:|
| general | 1.028x | 66/92 |
| direct | 1.003x | 34/64 |

### Every historical graph/stratum aggregate

Native columns use 3,000 replays; the external column comes from the separate 100-replay run. All regressions are included.

| Dataset | Stratum | Query vs corrected control | Build vs corrected control | Lifecycle vs corrected control | Fastest external / candidate |
|---|---|---:|---:|---:|---:|
| example | balanced | 1.194x | 1.035x | 1.086x | 1.822x |
| example | negative | 1.015x | 0.924x | 0.985x | 1.850x |
| example | positive | 1.383x | 0.937x | 1.120x | 1.832x |
| example | uniform | 1.017x | 0.967x | 1.014x | 1.624x |
| generated_blocks | balanced | 1.016x | 0.991x | 1.003x | 1.293x |
| generated_blocks | negative | 1.004x | 1.014x | 1.017x | 0.796x |
| generated_blocks | positive | 0.956x | 1.042x | 0.980x | 1.743x |
| generated_blocks | uniform | 1.034x | 0.992x | 1.026x | 0.830x |
| generated_communities | balanced | 0.972x | 0.995x | 0.976x | 1.935x |
| generated_communities | negative | 0.991x | 1.004x | 1.025x | 1.016x |
| generated_communities | positive | 0.991x | 0.989x | 0.986x | 2.021x |
| generated_communities | uniform | 1.020x | 1.005x | 1.026x | 1.750x |
| generated_dag | balanced | 0.999x | 0.990x | 0.985x | 3.435x |
| generated_dag | negative | 1.004x | 0.993x | 0.984x | 3.243x |
| generated_dag | positive | 0.995x | 0.953x | 0.988x | 3.856x |
| generated_dag | uniform | 1.038x | 1.010x | 0.993x | 2.700x |
| grail_citeseer | balanced | 1.105x | 0.982x | 1.076x | 1.892x |
| grail_citeseer | negative | 1.018x | 0.987x | 0.996x | 1.081x |
| grail_citeseer | positive | 1.235x | 0.976x | 1.074x | 1.744x |
| grail_citeseer | uniform | 0.987x | 1.023x | 0.999x | 1.079x |
| grail_go | balanced | 1.064x | 0.966x | 1.045x | 1.575x |
| grail_go | negative | 1.001x | 1.003x | 0.960x | 1.124x |
| grail_go | positive | 1.075x | 0.936x | 1.041x | 2.165x |
| grail_go | uniform | 0.972x | 1.009x | 0.990x | 1.003x |
| grail_kegg | balanced | 0.983x | 0.929x | 0.987x | 0.940x |
| grail_kegg | negative | 0.992x | 0.982x | 0.988x | 0.765x |
| grail_kegg | positive | 1.004x | 1.012x | 1.009x | 0.971x |
| grail_kegg | uniform | 0.991x | 1.053x | 1.003x | 0.720x |
| grail_pubmed | balanced | 1.112x | 0.995x | 1.060x | 1.848x |
| grail_pubmed | negative | 1.015x | 0.964x | 0.979x | 1.129x |
| grail_pubmed | positive | 1.167x | 0.950x | 1.082x | 1.716x |
| grail_pubmed | uniform | 0.980x | 0.985x | 0.982x | 1.310x |
| grail_yago | balanced | 1.076x | 0.877x | 1.019x | 1.544x |
| grail_yago | negative | 1.028x | 1.005x | 1.019x | 0.860x |
| grail_yago | positive | 1.080x | 0.975x | 1.048x | 1.293x |
| grail_yago | uniform | 0.991x | 0.936x | 0.971x | 0.901x |
| heldout_agrocyc | balanced | 1.232x | 1.031x | 1.140x | 0.633x |
| heldout_agrocyc | negative | 0.980x | 1.013x | 0.979x | 0.575x |
| heldout_agrocyc | positive | 1.399x | 0.970x | 1.226x | 0.572x |
| heldout_agrocyc | uniform | 1.000x | 0.908x | 0.986x | 0.532x |
| heldout_amaze | balanced | 1.008x | 0.915x | 1.011x | 0.834x |
| heldout_amaze | negative | 0.994x | 1.070x | 1.006x | 0.775x |
| heldout_amaze | positive | 1.022x | 0.999x | 1.017x | 0.888x |
| heldout_amaze | uniform | 1.015x | 0.945x | 1.013x | 0.613x |
| heldout_anthra | balanced | 1.046x | 0.983x | 1.031x | 0.547x |
| heldout_anthra | negative | 0.999x | 1.042x | 1.015x | 0.567x |
| heldout_anthra | positive | 1.039x | 0.966x | 1.023x | 0.588x |
| heldout_anthra | uniform | 1.015x | 1.060x | 1.006x | 0.562x |
| heldout_ecoo | balanced | 1.253x | 1.044x | 1.162x | 0.585x |
| heldout_ecoo | negative | 0.990x | 0.960x | 0.982x | 0.528x |
| heldout_ecoo | positive | 1.402x | 0.984x | 1.248x | 0.591x |
| heldout_ecoo | uniform | 0.927x | 0.964x | 0.981x | 0.561x |
| heldout_human | balanced | 0.999x | 0.972x | 0.998x | 0.568x |
| heldout_human | negative | 1.011x | 0.977x | 1.006x | 0.560x |
| heldout_human | positive | 1.012x | 1.032x | 1.016x | 0.594x |
| heldout_human | uniform | 1.010x | 0.974x | 1.006x | 0.564x |
| heldout_mtbrv | balanced | 1.008x | 0.966x | 1.004x | 0.601x |
| heldout_mtbrv | negative | 1.031x | 1.005x | 0.989x | 0.576x |
| heldout_mtbrv | positive | 0.989x | 1.080x | 1.027x | 0.625x |
| heldout_mtbrv | uniform | 1.001x | 0.985x | 0.997x | 0.564x |
| heldout_nasa | balanced | 1.038x | 1.067x | 1.020x | 1.201x |
| heldout_nasa | negative | 1.004x | 0.996x | 1.002x | 1.039x |
| heldout_nasa | positive | 1.093x | 0.982x | 1.071x | 1.159x |
| heldout_nasa | uniform | 0.986x | 0.970x | 0.972x | 1.092x |
| heldout_vchocyc | balanced | 1.063x | 1.027x | 1.052x | 0.584x |
| heldout_vchocyc | negative | 0.988x | 0.986x | 0.992x | 0.557x |
| heldout_vchocyc | positive | 1.035x | 0.999x | 1.014x | 0.589x |
| heldout_vchocyc | uniform | 0.996x | 0.997x | 0.999x | 0.558x |
| heldout_xmark | balanced | 1.004x | 0.962x | 0.987x | 1.544x |
| heldout_xmark | negative | 0.986x | 1.067x | 1.011x | 0.975x |
| heldout_xmark | positive | 1.037x | 0.956x | 1.038x | 1.567x |
| heldout_xmark | uniform | 1.050x | 1.025x | 1.062x | 1.301x |
| kron_logn12 | balanced | 0.999x | 0.984x | 1.003x | 1.901x |
| kron_logn12 | negative | 1.013x | 1.022x | 0.983x | 1.346x |
| kron_logn12 | positive | 0.964x | 0.976x | 1.015x | 2.241x |
| kron_logn12 | uniform | 1.005x | 1.016x | 1.006x | 1.727x |

### fresh: every guard cell

| Dataset | Stratum | Replays | Query ratio | Paired trial range | Lifecycle ratio |
|---|---|---:|---:|---:|---:|
| fresh_cross_chains | balanced | 1 | 0.824x | 0.738–2.747x | 0.988x |
| fresh_cross_chains | balanced | 1000 | 1.037x | 0.994–1.194x | 1.034x |
| fresh_cross_chains | negative | 1 | 1.021x | 0.936–1.168x | 0.824x |
| fresh_cross_chains | negative | 1000 | 0.989x | 0.930–1.026x | 0.972x |
| fresh_cross_chains | positive | 1 | 1.071x | 0.935–1.327x | 0.899x |
| fresh_cross_chains | positive | 1000 | 0.896x | 0.824–0.927x | 0.918x |
| fresh_cross_chains | uniform | 1 | 0.999x | 0.947–1.370x | 1.087x |
| fresh_cross_chains | uniform | 1000 | 0.995x | 0.848–1.222x | 0.988x |
| fresh_fragmented | balanced | 1 | 0.963x | 0.204–10.652x | 1.011x |
| fresh_fragmented | balanced | 1000 | 1.111x | 0.969–1.284x | 1.102x |
| fresh_fragmented | negative | 1 | 1.010x | 0.906–1.157x | 1.044x |
| fresh_fragmented | negative | 1000 | 1.005x | 0.926–1.122x | 0.997x |
| fresh_fragmented | positive | 1 | 1.040x | 0.685–1.205x | 0.909x |
| fresh_fragmented | positive | 1000 | 1.051x | 0.945–1.208x | 0.988x |
| fresh_fragmented | uniform | 1 | 0.954x | 0.817–1.056x | 0.937x |
| fresh_fragmented | uniform | 1000 | 1.025x | 0.988–1.155x | 1.034x |
| fresh_scc_aliases | balanced | 1 | 1.140x | 0.914–1.505x | 1.123x |
| fresh_scc_aliases | balanced | 1000 | 1.033x | 0.929–1.144x | 1.025x |
| fresh_scc_aliases | negative | 1 | 0.805x | 0.521–1.599x | 0.972x |
| fresh_scc_aliases | negative | 1000 | 1.384x | 0.813–2.579x | 1.171x |
| fresh_scc_aliases | positive | 1 | 0.880x | 0.186–0.936x | 0.948x |
| fresh_scc_aliases | positive | 1000 | 1.040x | 0.644–1.345x | 0.922x |
| fresh_scc_aliases | uniform | 1 | 1.923x | 0.738–2.198x | 1.024x |
| fresh_scc_aliases | uniform | 1000 | 1.451x | 1.011–2.053x | 1.063x |
| fresh_shared_hubs | balanced | 1 | 1.027x | 0.948–1.114x | 0.995x |
| fresh_shared_hubs | balanced | 1000 | 1.048x | 1.027–1.113x | 1.001x |
| fresh_shared_hubs | negative | 1 | 1.000x | 0.940–1.110x | 1.029x |
| fresh_shared_hubs | negative | 1000 | 0.995x | 0.953–0.997x | 0.989x |
| fresh_shared_hubs | positive | 1 | 1.055x | 0.817–1.302x | 0.985x |
| fresh_shared_hubs | positive | 1000 | 1.075x | 0.981–1.302x | 1.044x |
| fresh_shared_hubs | uniform | 1 | 0.928x | 0.867–1.097x | 0.986x |
| fresh_shared_hubs | uniform | 1000 | 1.032x | 1.001–1.112x | 1.000x |

### forest-warm: every guard cell

| Dataset | Stratum | Replays | Query ratio | Paired trial range | Lifecycle ratio |
|---|---|---:|---:|---:|---:|
| large_citeseer | balanced | 1000 | 0.827x | 0.524–0.969x | 1.035x |
| large_citeseer | negative | 1000 | 1.055x | 0.994–1.181x | 1.030x |
| large_citeseer | positive | 1000 | 1.004x | 0.894–1.164x | 0.943x |
| large_citeseer | uniform | 1000 | 0.864x | 0.746–1.492x | 1.018x |
| large_uniprot_22m | balanced | 1000 | 1.008x | 0.999–2.912x | 1.052x |
| large_uniprot_22m | negative | 1000 | 1.009x | 0.999–1.011x | 1.026x |
| large_uniprot_22m | positive | 1000 | 1.001x | 0.980–1.392x | 0.967x |
| large_uniprot_22m | uniform | 1000 | 0.995x | 0.860–1.420x | 0.972x |

### forest-fresh: every guard cell

| Dataset | Stratum | Replays | Query ratio | Paired trial range | Lifecycle ratio |
|---|---|---:|---:|---:|---:|
| large_citeseer | uniform | 1 | 0.933x | 0.798–0.958x | 1.002x |
| large_uniprot_22m | uniform | 1 | 1.010x | 0.904–2.501x | 0.998x |

## Claim boundary and continuation

This is a bounded local performance improvement. Per-cell regressions and all
guard results above remain part of the tradeoff. Neither an unchanged code path
nor equal retained capacity proves absence of timing regression. Single-pass
sub-millisecond measurements have large trial variation and do not establish
steady-state latency. Fresh synthetic families are useful scope checks but do
not resolve the remaining real-world external losses.

Global SOTA is still unverified. The next work should address residual sparse-
graph costs on the current worst cells, with a new structural hypothesis rather
than replaying the rejected cache, Bloom-order or degree-order variants. Preserve
the exact baseline and distinguish query, build, lifecycle and total-memory
objectives. Required broader qualification still includes original or validated
MLRQ/MLRQ-O execution, total-memory Pareto matching, unexposed general real graphs
and dedicated-hardware replication. Do not merge the stack solely from favorable
aggregate ratios or claim that every previous regression was eliminated.

Knowledge Nexus's claim ledger is in `evidence/phase29/campaign.json`: exactness
has a set-preservation argument plus executable checks; measured performance is
local evidence; universal superiority is unresolved. OmO runtime_info reported
installed=false, so its native recursive fallback ran. No real OmO execution,
extra worker, machine-checked proof or independent performance auditor is claimed.

Primary context: [O'Reach, JEA 2022](https://doi.org/10.1145/3556540),
[original PLL/PPL implementation](https://github.com/y3eadgbe/PrunedLabeling),
and [MLRQ/MLRQ-O, 2025](https://doi.org/10.1007/s44443-025-00310-0).
The MLRQ paper combines topological, partial two-hop and spanning-tree labels;
its reported comparisons are not measurements of this TRIC revision. A current
search located the paper but did not locate an original runnable MLRQ release.

## Reproduction

Build `build_native_comparison.py` with the frozen headers in
`evidence/phase29/baseline-sources/tric_research`, the pinned OReach checkout/build
and required Boost include directory. Exact commands and dependencies are in
`evidence/phase29/build_manifest.json`. Follow `qualification_protocol.json` with
`benchmark_native_changes.py`; it refuses nonempty output directories and seals
only complete runs. Reconstruct fresh fixtures with `prepare_phase29_fixtures.py`
in an empty output directory. Run `verify_phase29_evidence.py` from
`tric_research`; it checks source/build provenance, regenerates all paired tables,
requires the entire frozen case set and checks equal memory/routing per trial.
Run the historical Phase XXVIII validator with
`--source-root evidence/phase29/baseline-sources`.

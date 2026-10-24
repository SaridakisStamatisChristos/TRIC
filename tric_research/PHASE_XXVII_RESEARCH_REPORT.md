# Phase XXVII: exact forest dominance and scale qualification

This phase improves the large forest-shaped inputs: versus PR #26, warm-query
median speedup is 1.539x, construction 3.243x and lifecycle 1.546x, while retained
index capacity falls by 88–90%. On the broader 76-cell suite, query/lifecycle
medians are essentially flat (1.012x/1.004x); the general route regresses to
0.947x across 92 seed-level cells. Accept this as a structural time/space
improvement with explicit tradeoffs, not general SOTA.

## Contract and implementation

Static directed graphs with contiguous int IDs; reflexive exact reachability,
owned snapshots, invalid endpoint exceptions, C++17 standard library only in
the runtime, and one index per query thread. Default budgets remain 2 MiB table
payload and 64 MiB index-construction scratch, neither being a total-RSS cap.
Baseline is PR #26 at 68f32a47802b2133fa5a107a6d2f7ae3f50b2664.
Runtime candidate is 9b51f3a1d54d1bce8b6dcd13adfc556404c7f50b.

Automatic routing still decomposes SCCs exactly once and prefers full closure
when it fits. Otherwise it probes the condensation for either at most one
DISTINCT successor per SCC, or at most one DISTINCT predecessor per SCC.
Parallel arcs and SCC-internal arcs do not count as additional neighbors.
These two cases are forests oriented toward sinks or away from sources.
Only the graph and explicit budgets select a route; query pairs are not used.

The new forest backend retains one 64-bit label per original vertex. Its four
temporary component arrays require 20 bytes per SCC and are refused before
allocation if that payload exceeds the existing scratch cap. Shared SCC state,
input graph, retained labels, allocator overhead and enclosing-object bytes
remain separate, as in previous phases. Failure preserves the general exact
partition/chain/bitset/interval/word/DFS route.

Automatic dispatch owns the chosen backend inside std::variant, avoiding a
separate index-object heap allocation. Copying remains disabled and moving
remains supported. The general partitioned backend keeps its existing 32-byte
labels and query certificates, but stores search adjacency in CSR: one size_t
offset per SCC plus sentinel and one int per retained arc. Reverse adjacency is
freed before allocating CSR. Zero-budget search and index-refusal semantics
remain exact. Constant object-size changes are included in retained_bytes().

## Correctness and resource argument

SCC contraction preserves reachability. In an acyclic condensation with one
predecessor per vertex, every weak component is a rooted tree with outward
arcs; with one successor per vertex, reversing the arcs gives that structure.
The probe checks distinct neighbors exactly and never assumes the original
vertex labels are topologically ordered.

A threaded iterative DFS assigns a preorder begin and half-open subtree end
to each SCC. Parent, first-child and sibling links avoid recursion and a
depth-sized DFS stack. Different roots occupy disjoint preorder intervals.
For an outward forest with S components, encode x=begin and y=S-end.
Then u reaches v iff x(u)<=x(v) AND y(u)<=y(v). For inward forests, encode
x=S-begin and y=end, reversing the ancestor relation with the same dominance
test. Distinct roots cannot dominate one another. Original vertices in one
SCC receive identical coordinates, preserving all reflexive/cyclic aliases.

Both coordinates fit 31 bits because SCC count fits a nonnegative 32-bit int.
Pack x into the low 32-bit lane and y into the high lane. Set the two high lane
marker bits in the target before subtracting the source. For each lane, biased
target minus source lies between 1 and 2^32-1; therefore the lower lane never
borrows from the upper lane. Its marker survives iff target>=source in that
lane. Testing both markers yields the exact two-coordinate dominance answer.
This is unsigned arithmetic, without signed overflow, SIMD ISA dependencies,
probabilistic answers or a query-result cache.

Forest construction is O(V+E) including SCC processing; its backend uses 8*V
retained label bytes plus a constant-sized enclosing object, and 20*S temporary
payload bytes plus existing shared SCC/input state. Queries use O(1) work and
storage. General DFS retains its previous O(S+M) worst-case bound. CSR stores
8*(S+1)+4*M bytes on the measured 64-bit build, replacing vector headers and
per-row capacities. These are established SCC, forest interval/dominance,
broadword comparison and CSR techniques; no algorithmic novelty is claimed.
The reasoning is human-checkable, not proof-assistant verification.

## Candidate selection and negative results

Preserved exploratory pilots tested full level filters, level-plus-signature
filters, endpoint-check changes, inline automatic dispatch, combined DFS/SCC
certificates and a 16-byte fast-label split. None produced a sufficiently
reliable general-query win to replace the verified signature path. Inline
storage is used as an ownership mechanism for the new backend; pilot timing
noise and mixed nonforest outcomes do not support a broad speedup claim.
The original general signatures and their query order are preserved.
The first complete variant-dispatch qualification exposed a direct-closure
regression (median 0.873x across 64 seed-level direct-closure cells). A matched
76-cell follow-up compared the original variant order, direct-first variant
order and a heap-backed legacy dispatcher. Direct-first recovered the direct
route (1.198x median thread-CPU speedup versus PR #26 in 21/24 pilot cells),
while its general-route pilot was mixed (0.970x median). That ordering was
frozen and the complete comparisons repeated. Initial qualification timings
are preserved as rejected prototype evidence, not mixed into final results.
An interrupted initial level pilot used unmatched build configurations and is
excluded. Only complete matched pilots are preserved for exploratory analysis.

The two new large inputs were selected from the GRAIL authors' archive by size.
Inspection found both have maximum out-degree one after their supplied SCC
reduction. That structure motivated this backend; these are EXPOSED design
inputs, not held-out general-graph evidence. The mechanism is structural and
contains no dataset names, known query answers or source-specific thresholds.

## Verification

The original/new local suite has 34 test methods. Both general and automatic
indexes retain the 18,432 exhaustive three-vertex cases, 1,440 adversarial cases
and 589,824 lifted interval-family checks against BFS. New native tests cover
all 720 increasing-parent forests of six SCCs in both orientations, with SCC
aliases and duplicate external arcs: 207,360 all-pair checks. Another 1,296
coordinate cases exercise all combinations of 0, 1, 65535, 65536, INT_MAX-1 and
INT_MAX against independent scalar comparisons. Python adds randomly relabelled
SCC aliases, multiple roots, nonforest refusal, scratch budgets at/below the
20*S boundary, and the original PLL/PPL query APIs against BFS.

Local address/undefined checks pass. Local LeakSanitizer cannot inspect this
traced environment's threads, so only that local command disables leaks. CI
retains full leak detection. Frozen-runtime CI passes on Python 3.10 and 3.13:
https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39985367589.
Final evidence-head CI is linked separately in PR #27.

## Baselines and prior art

Original OReach and BFL revisions/configuration remain pinned as in Phase XXV.
This phase adds the original Yosuke Yano implementation of PLL and PPL,
commit 65b4cadc8d70cd267cff80c4522b381e4a0b9e30, MIT licensed. All five preserved
upstream files match their Git blob hashes; no source is patched. The adapter
passes zero-based adjacency to the original constructor and source+1,target+1
to its public query method, which subtracts one. The sample executable is
preserved as provenance and is not run. The original cpp is included in the
benchmark translation unit to permit optimizer inlining just as for TRIC.
Both systems receive the same compiler flags and identical input bytes.

upstream_reported_label_bytes is the authors' indexSize(), not total retained
memory; notably PPL charges six bytes per pair while allocator/vector capacities,
C++ pair padding and retained graphs are excluded. Native pre-oracle VmHWM
captures the executable's total peak separately. No total-memory matching is
claimed. These baseline-only sources do not become runtime dependencies.

Primary references: [Yano et al., CIKM 2013](https://doi.org/10.1145/2505515.2505724);
[Hanauer et al., JEA 2022](https://doi.org/10.1145/3556540);
[Zhang et al., MLRQ 2025](https://doi.org/10.1007/s44443-025-00310-0);
[the reachability-index survey](https://doi.org/10.1145/3776737). MLRQ uses topological, partial two-hop and tree labels;
its paper's data availability statement links datasets, not executable code.
The searched original MLRQ/MLRQ-O implementation remains unavailable here, so
its performance is UNVERIFIED. Literature timings are not inserted into the
head-to-head table. Forest dominance is established prior art, not a newly
proved general reachability algorithm.

## Measurement protocol and datasets

The frozen binaries use one comparison source, GCC -O3 -DNDEBUG, the same
external code, native inputs and table cap. Every arm executes actual calls
and checks each input pair independently with BFS after the timed region.
Every trial is a fresh process; seven cyclic orders balance each arm over
all launch positions. Wall-clock parse/build/query lifecycle is primary;
thread CPU time is recorded separately. VmHWM is sampled before oracle
verification. Compilation, startup, oracle verification and teardown are
excluded from lifecycle timing. Benchmarks run sequentially on pinned CPU 1
without concurrent local generation, testing or compilation. This shared host
is not dedicated hardware, and position balancing does not eliminate clock,
cache or scheduler uncertainty.

The original 19 graphs/39 graph-seed pairs reuse Phase XXV's exact 1,200-pair
fixtures. The small/medium qualification uses horizon 100 (120,000 calls).
The new large qualification uses four strata of 64 frozen pairs, horizon 1,000
(64,000 calls), seed 20261028. These are cache-hot replays, not independent new
requests. The separate fresh-query check is described with its own horizon.
Results across different input sizes/horizons are reported separately.
Uniform pairs draw endpoints independently. Positive/negative/balanced strata
are source-uniform conditioned on eligible non-self targets, then target-uniform
within that source's BFS class; they are not uniform over all eligible pairs.

The large CiteSeer file has 693,947 vertices and 312,282 arcs. UniProt 22m's
provided condensation has 1,595,444 vertices and 1,595,442 arcs; this is NOT a
22-million-vertex experiment. Both are original GRAIL-author archive members,
commit c13a7364fbc185841fc6277cd295acf33a7188f0, with pinned compressed Git blobs
and SHA256 values in the fixtures. Original vertex IDs, arc order and duplicates
are preserved. Their already-contracted original aliases are unavailable here.

## Results

### Small qualification

19 graphs; 156 seed-level cells; 76 graph/stratum aggregates; 7,644 fresh-process trials; 917,280,000 actual query calls and 9,172,800 independent BFS pair executions. All digest, completeness, answer and cap checks pass. A BFS pair repeated across arms/trials is counted as an execution, not a new unique input.

| Metric | vs PR #26 median (wins/cells) | vs fastest external median (wins/cells) |
|---|---:|---:|
| query_ns | 1.012x (40/76) | 1.061x (42/76) |
| query_thread_cpu_ns | 1.013x (40/76) | 1.060x (42/76) |
| build_ns | 0.992x (34/76) | 0.926x (25/76) |
| lifecycle_ns | 1.004x (41/76) | 1.008x (40/76) |

Ratios greater than one favor the candidate. For each seed/cell, ratios pair matching launch-trial indices, then take a median. Graph/stratum aggregates take the median over seeds; the table above takes the unweighted median across those aggregates. The fastest external ratio uses the minimum of all five external arms separately for each trial and metric. A win at one metric does not establish a lifecycle win.

Route-specific seed-level paired query ratios (wall / thread CPU):

- direct: 1.183x, 54/64 wins / 1.184x, 54/64 wins
- general: 0.947x, 35/92 wins / 0.946x, 35/92 wins

All small/medium aggregates follow, including every regression. Different graphs contribute equally per stratum here, regardless of vertex count.

| Dataset | Stratum | Query vs #26 | Query vs external | Build vs #26 | Lifecycle vs #26 |
|---|---|---:|---:|---:|---:|
| example | balanced | 0.868x | 1.491x | 1.049x | 1.007x |
| example | negative | 0.821x | 2.075x | 1.011x | 1.029x |
| example | positive | 0.914x | 1.075x | 0.947x | 1.043x |
| example | uniform | 0.968x | 1.452x | 0.990x | 1.036x |
| generated_blocks | balanced | 1.086x | 1.966x | 0.993x | 0.975x |
| generated_blocks | negative | 1.262x | 1.318x | 0.878x | 1.046x |
| generated_blocks | positive | 1.195x | 2.758x | 1.172x | 1.102x |
| generated_blocks | uniform | 1.146x | 1.400x | 0.975x | 1.070x |
| generated_communities | balanced | 1.463x | 2.493x | 0.998x | 1.044x |
| generated_communities | negative | 1.462x | 1.571x | 1.039x | 1.058x |
| generated_communities | positive | 1.499x | 2.820x | 0.985x | 1.146x |
| generated_communities | uniform | 1.530x | 2.217x | 1.012x | 1.115x |
| generated_dag | balanced | 1.178x | 5.308x | 0.983x | 0.941x |
| generated_dag | negative | 1.114x | 4.302x | 0.872x | 0.939x |
| generated_dag | positive | 1.349x | 5.727x | 0.832x | 0.939x |
| generated_dag | uniform | 1.022x | 3.651x | 1.190x | 1.025x |
| grail_citeseer | balanced | 0.927x | 1.448x | 0.958x | 0.902x |
| grail_citeseer | negative | 0.945x | 0.997x | 1.080x | 1.019x |
| grail_citeseer | positive | 0.966x | 1.484x | 1.057x | 1.075x |
| grail_citeseer | uniform | 0.859x | 0.961x | 1.099x | 0.989x |
| grail_go | balanced | 1.154x | 1.459x | 1.009x | 1.076x |
| grail_go | negative | 0.977x | 1.033x | 0.843x | 0.926x |
| grail_go | positive | 0.919x | 1.504x | 0.989x | 0.993x |
| grail_go | uniform | 1.011x | 1.035x | 1.111x | 1.085x |
| grail_kegg | balanced | 1.145x | 1.262x | 1.034x | 1.009x |
| grail_kegg | negative | 1.304x | 1.114x | 0.979x | 1.049x |
| grail_kegg | positive | 0.890x | 1.464x | 0.970x | 0.963x |
| grail_kegg | uniform | 1.027x | 0.993x | 0.944x | 1.107x |
| grail_pubmed | balanced | 0.766x | 1.257x | 0.848x | 0.931x |
| grail_pubmed | negative | 0.941x | 1.104x | 1.108x | 1.054x |
| grail_pubmed | positive | 0.888x | 1.288x | 0.900x | 0.906x |
| grail_pubmed | uniform | 1.268x | 1.389x | 1.120x | 0.989x |
| grail_yago | balanced | 0.863x | 1.178x | 0.913x | 0.924x |
| grail_yago | negative | 1.379x | 0.997x | 1.200x | 1.052x |
| grail_yago | positive | 0.846x | 0.706x | 0.815x | 0.950x |
| grail_yago | uniform | 0.986x | 0.934x | 1.002x | 0.991x |
| heldout_agrocyc | balanced | 0.909x | 0.392x | 1.250x | 1.117x |
| heldout_agrocyc | negative | 0.776x | 0.587x | 1.036x | 0.985x |
| heldout_agrocyc | positive | 0.869x | 0.353x | 1.253x | 1.003x |
| heldout_agrocyc | uniform | 0.818x | 0.628x | 0.987x | 0.979x |
| heldout_amaze | balanced | 1.517x | 1.151x | 0.910x | 1.034x |
| heldout_amaze | negative | 1.155x | 1.312x | 0.852x | 0.997x |
| heldout_amaze | positive | 1.497x | 1.636x | 1.153x | 1.012x |
| heldout_amaze | uniform | 0.890x | 1.047x | 0.980x | 0.888x |
| heldout_anthra | balanced | 1.140x | 0.395x | 1.047x | 1.002x |
| heldout_anthra | negative | 0.836x | 0.593x | 0.978x | 0.983x |
| heldout_anthra | positive | 0.901x | 0.406x | 1.116x | 1.050x |
| heldout_anthra | uniform | 1.038x | 0.723x | 1.042x | 0.920x |
| heldout_ecoo | balanced | 0.910x | 0.390x | 1.074x | 1.101x |
| heldout_ecoo | negative | 1.213x | 0.663x | 0.918x | 0.908x |
| heldout_ecoo | positive | 0.932x | 0.379x | 1.001x | 0.963x |
| heldout_ecoo | uniform | 0.967x | 0.726x | 0.942x | 1.012x |
| heldout_human | balanced | 1.060x | 0.460x | 0.901x | 1.069x |
| heldout_human | negative | 1.206x | 0.690x | 0.930x | 1.002x |
| heldout_human | positive | 0.800x | 0.340x | 0.759x | 0.935x |
| heldout_human | uniform | 0.980x | 0.750x | 1.085x | 1.071x |
| heldout_mtbrv | balanced | 0.891x | 0.328x | 0.932x | 0.891x |
| heldout_mtbrv | negative | 1.219x | 0.701x | 1.218x | 1.120x |
| heldout_mtbrv | positive | 1.126x | 0.357x | 0.864x | 0.907x |
| heldout_mtbrv | uniform | 0.938x | 0.649x | 0.938x | 1.073x |
| heldout_nasa | balanced | 0.901x | 0.973x | 0.942x | 0.963x |
| heldout_nasa | negative | 0.825x | 0.832x | 0.949x | 0.920x |
| heldout_nasa | positive | 0.992x | 1.008x | 0.906x | 0.941x |
| heldout_nasa | uniform | 1.040x | 1.101x | 1.133x | 1.130x |
| heldout_vchocyc | balanced | 1.145x | 0.454x | 0.889x | 0.953x |
| heldout_vchocyc | negative | 1.037x | 0.699x | 1.058x | 1.007x |
| heldout_vchocyc | positive | 1.014x | 0.314x | 0.934x | 0.965x |
| heldout_vchocyc | uniform | 1.014x | 0.788x | 0.997x | 1.087x |
| heldout_xmark | balanced | 0.927x | 1.263x | 0.894x | 1.041x |
| heldout_xmark | negative | 0.783x | 0.994x | 0.995x | 0.876x |
| heldout_xmark | positive | 1.026x | 0.980x | 1.085x | 0.990x |
| heldout_xmark | uniform | 1.109x | 1.469x | 1.053x | 1.082x |
| kron_logn12 | balanced | 1.244x | 2.347x | 0.910x | 0.957x |
| kron_logn12 | negative | 1.474x | 1.897x | 1.118x | 1.006x |
| kron_logn12 | positive | 1.007x | 2.595x | 1.079x | 0.975x |
| kron_logn12 | uniform | 1.089x | 1.836x | 1.018x | 1.023x |

### Large qualification

2 graphs; 8 seed-level cells; 8 graph/stratum aggregates; 392 fresh-process trials; 25,088,000 actual query calls and 25,088 independent BFS pair executions. All digest, completeness, answer and cap checks pass. A BFS pair repeated across arms/trials is counted as an execution, not a new unique input.

| Metric | vs PR #26 median (wins/cells) | vs fastest external median (wins/cells) |
|---|---:|---:|
| query_ns | 1.539x (8/8) | 0.737x (2/8) |
| query_thread_cpu_ns | 1.542x (8/8) | 0.730x (2/8) |
| build_ns | 3.243x (8/8) | 3.291x (8/8) |
| lifecycle_ns | 1.546x (8/8) | 1.570x (8/8) |

Ratios greater than one favor the candidate. For each seed/cell, ratios pair matching launch-trial indices, then take a median. Graph/stratum aggregates take the median over seeds; the table above takes the unweighted median across those aggregates. The fastest external ratio uses the minimum of all five external arms separately for each trial and metric. A win at one metric does not establish a lifecycle win.

| Dataset | Stratum | Query ns/call | Query vs #26 | Query vs external | Paired query ratio range vs #26 |
|---|---|---:|---:|---:|---:|
| large_citeseer | uniform | 3.410 | 1.148x | 0.628x | 0.275–2.391x |
| large_citeseer | positive | 3.078 | 6.582x | 1.408x | 4.542–13.714x |
| large_citeseer | negative | 3.096 | 1.453x | 0.618x | 1.091–1.916x |
| large_citeseer | balanced | 3.095 | 2.777x | 1.123x | 1.048–5.739x |
| large_uniprot_22m | uniform | 3.109 | 1.253x | 0.590x | 0.349–14.203x |
| large_uniprot_22m | positive | 3.092 | 3.296x | 0.994x | 1.111–8.948x |
| large_uniprot_22m | negative | 3.041 | 1.442x | 0.675x | 0.382–7.634x |
| large_uniprot_22m | balanced | 4.261 | 1.624x | 0.799x | 0.793–3.747x |

These min–max ranges are observed trial variability, not confidence intervals. Query phases are very short, so nanosecond figures and ratios are sensitive to scheduling/cache/compiler layout.

| Dataset | Previous retained bytes | Candidate retained bytes | Previous peak KiB | Candidate peak KiB | Candidate table bytes |
|---|---:|---:|---:|---:|---:|
| large_citeseer | 56,853,616 | 5,551,944 | 174,174 | 53,408 | 0 |
| large_uniprot_22m | 108,490,584 | 12,763,920 | 395,078 | 147,752 | 0 |

### Fresh qualification

2 graphs; 2 seed-level cells; 2 graph/stratum aggregates; 98 fresh-process trials; 401,408 actual query calls and 401,408 independent BFS pair executions. All digest, completeness, answer and cap checks pass. A BFS pair repeated across arms/trials is counted as an execution, not a new unique input.

| Metric | vs PR #26 median (wins/cells) | vs fastest external median (wins/cells) |
|---|---:|---:|
| query_ns | 2.770x (2/2) | 1.254x (2/2) |
| query_thread_cpu_ns | 2.819x (2/2) | 1.253x (2/2) |
| build_ns | 3.143x (2/2) | 3.308x (2/2) |
| lifecycle_ns | 1.520x (2/2) | 1.600x (2/2) |

Ratios greater than one favor the candidate. For each seed/cell, ratios pair matching launch-trial indices, then take a median. Graph/stratum aggregates take the median over seeds; the table above takes the unweighted median across those aggregates. The fastest external ratio uses the minimum of all five external arms separately for each trial and metric. A win at one metric does not establish a lifecycle win.

| Dataset | Stratum | Query ns/call | Query vs #26 | Query vs external | Paired query ratio range vs #26 |
|---|---|---:|---:|---:|---:|
| large_citeseer | uniform | 14.405 | 3.204x | 1.371x | 1.047–4.323x |
| large_uniprot_22m | uniform | 23.655 | 2.336x | 1.137x | 0.377–3.352x |

These min–max ranges are observed trial variability, not confidence intervals. Query phases are very short, so nanosecond figures and ratios are sensitive to scheduling/cache/compiler layout.

| Dataset | Previous retained bytes | Candidate retained bytes | Previous peak KiB | Candidate peak KiB | Candidate table bytes |
|---|---:|---:|---:|---:|---:|
| large_citeseer | 56,853,616 | 5,551,944 | 174,204 | 53,536 | 0 |
| large_uniprot_22m | 108,490,584 | 12,763,920 | 395,108 | 147,784 | 0 |

Fresh fixtures contain 4,096 distinct uniform pairs per graph, each executed once per timed trial. They use a different seed from the 64-pair warm replay. Construction precedes queries and caches are not flushed; this is a single-pass check, not an uncached-hardware claim.

### CSR qualification

1 graphs; 1 seed-level cells; 1 graph/stratum aggregates; 8 fresh-process trials; 512 actual query calls and 512 independent BFS pair executions. All digest, completeness, answer and cap checks pass. A BFS pair repeated across arms/trials is counted as an execution, not a new unique input.

| Metric | vs PR #26 median (wins/cells) | vs fastest external median (wins/cells) |
|---|---:|---:|
| query_ns | 1.132x (1/1) | not measured |
| query_thread_cpu_ns | 1.091x (1/1) | not measured |
| build_ns | 0.978x (0/1) | not measured |
| lifecycle_ns | 1.060x (1/1) | not measured |

Ratios greater than one favor the candidate. For each seed/cell, ratios pair matching launch-trial indices, then take a median. Graph/stratum aggregates take the median over seeds; the table above takes the unweighted median across those aggregates. The fastest external ratio uses the minimum of all five external arms separately for each trial and metric. A win at one metric does not establish a lifecycle win.

| Dataset | Stratum | Query ns/call | Query vs #26 | Query vs external | Paired query ratio range vs #26 |
|---|---|---:|---:|---:|---:|
| generated_csr_nonforest | mixed | 155.000 | 1.132x | not measured | 0.941–1.171x |

These min–max ranges are observed trial variability, not confidence intervals. Query phases are very short, so nanosecond figures and ratios are sensitive to scheduling/cache/compiler layout.

| Dataset | Previous retained bytes | Candidate retained bytes | Previous peak KiB | Candidate peak KiB | Candidate table bytes |
|---|---:|---:|---:|---:|---:|
| generated_csr_nonforest | 4,342,648 | 3,280,496 | 18,586 | 18,332 | 0 |

This controlled 60,002-vertex/100,000-arc nonforest rejects both indexed routes at cap zero. All candidate rows use the general route, keep zero table bytes and match BFS. It isolates CSR retained-memory behavior; four trials/two arms do not establish external or general SOTA superiority.


## Remaining gap and claim boundary

No global SOTA claim is justified. TRIC wins 42/76 small/medium aggregate query
cells against the fastest of five external arms, but the worst remaining cell
is 0.314x (about 3.18 times slower). Warm large-forest queries win only 2/8 cells
against that external minimum, despite construction and lifecycle wins in all
8/8. Fresh single-pass queries win 2/2 on those same two exposed forest inputs;
this does not convert them into held-out general graphs. The broad general
route's 0.947x median versus PR #26 is a measured regression, not noise we can
claim to have eliminated. Direct closure improves to 1.183x across its 64
seed-level cells. Overall lifecycle remains essentially flat on the old suite.

The next engineering target is general-route query overhead and sparse
biological graphs, where original PLL/PPL strengthen the external baseline.
Use branch/certificate profiling and mechanism-isolating experiments before
changing the general layout again; retain the forest representation's memory
savings. Dedicated, longer query windows are needed to resolve the large
observed trial ranges and dispatch/code-layout sensitivity. A SOTA comparison
also needs independent general graphs, total-memory Pareto matching, and the
original MLRQ/MLRQ-O implementation or an explicitly validated reproduction.
Neither the unavailable comparator nor a dedicated independent performance
replication has been supplied here. CI/oracle checks establish bounded
correctness evidence, not independent performance replication or formal proof.

## Reproduction

Use build_native_comparison.py with a clean PR #26 header directory and the
same pinned OReach source/objects/Boost includes documented in Phase XXV. Its
manifest records every header, upstream source, compiler flag and binary hash.
Run benchmark_native_changes.py with seven arms: previous auto, candidate auto,
bfl, oreach-pdfs, oreach-pbibfs, pll and ppl. Use a new empty output directory,
trials 7, CPU 1, horizon 100 for original fixtures and 1,000 for large fixtures.
prepare_large_forest_fixtures.py reproduces the large frozen inputs from the
pinned author archives. No TRIC labels are consulted by query generation.

The evidence roots hold raw sealed comparisons, paired per-seed/aggregate CSVs,
complete digest/case receipts, source/build provenance and rejected prototypes.
The summarizer includes all five external variants when present, while retaining
compatibility with the earlier three-external-arm evidence.

Example evidence verification (from tric_research):

```bash
python summarize_native_changes.py evidence/phase27/small --fixtures evidence/phase25/fixtures
python summarize_native_changes.py evidence/phase27/large --fixtures evidence/phase27/large-fixtures
python summarize_native_changes.py evidence/phase27/fresh --fixtures evidence/phase27/fresh-fixtures
python summarize_native_changes.py evidence/phase27/csr --fixtures evidence/phase27/csr-fixtures
python verify_phase27_evidence.py
```

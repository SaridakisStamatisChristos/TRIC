# Phase XXX: isolate the common exact query path

Date: 26 October 2026
Baseline: PR #29, `c719c1973b47ad881a9a0cc25d5a5391c6335bdc`.
Local runtime build revision: `25f90656a27f1c0dd4d8295bb25b15ff581e575d`. Publication via the GitHub API may assign a different commit ID; source hashes and the final published tree identify the actual files.

## Outcome

General-route queries improved **1.484×** over PR #29 at the median of 92 seed/stratum cells; 91 improved. Across all 76 native graph/stratum aggregates, query speedup is **1.390×** and lifecycle speedup **1.114×**. Table payload and retained capacity are exactly equal in every final paired trial.

The external campaign wins **46/76** graph/stratum cells against the fastest of five executed competitors per trial. The worst current gap is **1.333× slower**, on Agrocyc negative queries. The median external/candidate query ratio is **1.460×**. In the same campaign, PR #29 wins 42/76 and has a worst gap of 2.244×; historical phase29 measurements (39/76 and 1.89×) came from a different run and are not interchangeable with this paired control.

**Limitation:** single-pass forest queries regress. The original two-graph median ratio was 0.700×; a separately frozen 12-trial replication found 0.920× overall, with CiteSeer 0.882× and UniProt 0.957×. Replication lifecycle ratio is 1.000×. Both original and replication results remain included. Warm CiteSeer positive queries initially regressed to 0.787×; a separate fixed eight-trial replication over all warm cells measured 1.020× for that cell and 1.001× overall, so the large warm regression did not reproduce. Fresh cross-chain positive queries at 1000 replays retain a 0.873× ratio. These results do not establish parity on every workload or global SOTA.

## Implementation and correctness

The change moves the residual interval binary search and all noninterval query paths into private helpers. Endpoint validation, the Bloom subset rejection, cached-range membership and the single-range negative answer remain in the small common function. GCC/Clang and MSVC receive guarded noinline hints on the helpers. Unsupported compilers use their ordinary inlining policy and retain exact semantics.

This is a compiler-sensitive refactor, not a new reachability algorithm. The evidence verifier checks that construction and storage accounting are byte-for-byte unchanged, and both extracted bodies exactly match their previous text and branch order. All labels remain 32 bytes, table/scratch caps and graph-only route selection remain unchanged, and no query samples or dataset names enter the runtime. API validation and reflexive/SCC semantics are preserved.

Every execution reaching a helper has the same predecessor conditions as before: residual lookup follows Bloom acceptance, a cache miss and count greater than one; noninterval handling follows Bloom acceptance and a nonnegative group tag. Helpers use references to the same immutable labels and the same mutable fallback scratch. There is no new allocation, retention, shared mutable state or weakened memory/endpoint contract.

## Hypotheses, falsification and selection

Instrumented row diagnostics show that Bloom already rejects more than 98% of sampled negative pairs on the slow biological graphs. Additional topological rejection therefore adds little. Single-range shortcuts and a split signature array also failed to produce broad gains. Splitting signatures added 24 constant object bytes and was rejected.

Disassembly found a large out-of-line query function with register saves and a stack-protector frame even for Bloom rejection. Merely extracting a helper allowed the compiler to fold it back into the common function. Explicit helper boundaries removed the common out-of-line query symbol in the selected pilot. Forced inlining of the whole function caused direct-closure regressions. The preserved ablations support a compiler/code-layout mechanism; they do not establish identical effects on other compilers or call sites.

| Pilot | Variant | Median paired query speedup | Wins / cells | Decision |
|---|---|---:|---:|---|
| pilot1 | `topo_after` | 0.979× | 13/32 | Rejected |
| pilot1 | `topo_before` | 0.963× | 5/32 | Rejected |
| pilot1 | `topo_combined` | 0.987× | 14/32 | Rejected |
| pilot1 | `topo_nobloom_interval` | 0.942× | 9/32 | Rejected |
| pilot2 | `single` | 0.945× | 6/32 | Rejected |
| pilot2 | `single_tag` | 0.927× | 11/32 | Rejected |
| pilot2 | `partition_first` | 1.015× | 18/32 | Rejected |
| pilot2 | `tag_partition_first` | 0.952× | 3/32 | Rejected |
| pilot3 | `split` | 0.989× | 13/32 | Rejected |
| pilot3 | `split_partition_first` | 1.020× | 20/32 | Rejected |
| pilot4 | `outline` | 1.003× | 18/32 | Rejected |
| pilot4 | `forceinline` | 1.029× | 23/32 | Rejected |
| pilot5 | `outline_noinline` | 1.267× | 30/32 | Rejected |
| pilot5 | `outline_search` | 1.223× | 31/32 | Rejected |
| pilot5 | `outline_minimal` | 1.558× | 29/32 | Selected for qualification |

Five complete exploratory campaigns cover 15 alternatives plus the unchanged control. All raw trials, prototype headers/wrappers, generator scripts, compiler commands, selected dependency hashes and binary hashes are in `experiments.json.gz`. These exposed cases are selection data, not independent holdouts. The selected source was frozen before qualification; no performance retuning followed.

## Qualification protocol

All measured processes ran sequentially pinned to CPU 1 on the recorded shared AMD EPYC 9V74 host. Both arms use GCC 13.3, C++17, -O3 and the same full comparator source and external objects. Launch order rotates by trial, with trial counts divisible by arm count. PR #29 reproduces its previous binary hash exactly. No tests or builds overlapped timing. Parsing, construction and query replay are timed separately; independent BFS verification, process startup and teardown are outside lifecycle timing. Query CPU time is recorded beside wall time.

The cap is 2 MiB of table payload, with the existing default 64 MiB requested indexing scratch allowance. Neither is a total-process memory limit. Retained capacity and observed process high-water RSS are reported; comparator budgets are not total-memory Pareto matched.

| Campaign | Trials per arm | Replays | Graphs | Purpose |
|---|---:|---|---:|---|
| Native | 4 | 2000 | 19 | Same-binary paired PR29 control; 39 graph-seeds |
| External | 7 | 100 | 19 | PR29, candidate, original BFL, OReach PDFS/PBiBFS, PLL, PPL |
| Fresh synthetic | 4 | 1, 1000 | 4 | New seeds, 2048 BFS-conditioned pairs per stratum |
| Forest warm | 4 | 1000 | 2 | Existing large exposed graph inputs |
| Forest single pass | 4 | 1 | 2 | 4096 frozen query pairs per graph |
| Forest replication | 12 | 1 | 2 | Additional prespecified check after a regression; unchanged binaries |
| Forest warm replication | 8 | 1000 | 2 | One additional check of all eight warm cells; unchanged binaries |

Fresh synthetic shapes use fragmented closures, shared hubs, SCC aliases and cross-linked chains. Their seed/topology/query bytes differ from Phase XXIX, but their family design is derived from that work. No new real-world graph family or independent host was introduced. Historical filenames beginning with `heldout_` are already exposed and are not treated as fresh holdouts.

Ratios are previous/candidate times: values above one favor the candidate. Paired per-trial ratios are reduced by median, then by seed within each graph/stratum; aggregate summaries use the median across cells. External query ratios use the fastest external implementation in each trial. External build and lifecycle minima can come from different implementations. These are descriptive measurements, not independent-replication confidence intervals.

| Campaign / replays | Query speedup | Build speedup | Lifecycle speedup | Query wins / cells |
|---|---:|---:|---:|---:|
| native / 2000 | 1.390× | 0.987× | 1.114× | 66/76 |
| external / 100 | 1.318× | 0.993× | 1.005× | 66/76 |
| fresh / 1 | 1.092× | 0.992× | 1.001× | 12/16 |
| fresh / 1000 | 1.361× | 1.001× | 1.098× | 12/16 |
| forest-warm / 1000 | 0.984× | 1.035× | 1.015× | 4/8 |
| forest-fresh / 1 | 0.700× | 1.333× | 1.144× | 0/2 |
| forest-replication / 1 | 0.920× | 0.989× | 1.000× | 0/2 |
| forest-warm-replication / 1000 | 1.001× | 0.995× | 1.004× | 4/8 |

The five primary campaigns executed **9,228** timing processes. Including both forest replications: **9,404 processes**, **11,469,120 BFS pair executions**, and **4,187,436,288 repeated query calls**. Replays and repeated BFS checks are not independent unique inputs. The five pilot campaigns are additional and excluded from these qualification totals.

The prespecified numeric acceptance checks passed: general native median ≥1.05×, Ecoo-negative ≥1.10×, overall native query median ≥1.0× and lifecycle ≥0.97×. No native aggregate query ratio fell below 0.90×. The single-pass forest objection was investigated, not excluded or used to change those gates. Its original regression magnitude was unstable, but a smaller regression persisted; it remains a limitation. No claim of uniform no-regression acceptance is made.

## Full native aggregate results

| Dataset | Stratum | Query ratio | Build ratio | Lifecycle ratio |
|---|---|---:|---:|---:|
| example | balanced | 1.251× | 0.989× | 1.067× |
| example | negative | 1.181× | 0.944× | 1.035× |
| example | positive | 1.146× | 0.967× | 1.022× |
| example | uniform | 1.239× | 1.006× | 1.056× |
| generated_blocks | balanced | 0.993× | 0.988× | 1.018× |
| generated_blocks | negative | 1.035× | 0.956× | 1.033× |
| generated_blocks | positive | 1.011× | 1.034× | 1.014× |
| generated_blocks | uniform | 1.002× | 0.929× | 0.994× |
| generated_communities | balanced | 1.019× | 1.002× | 1.022× |
| generated_communities | negative | 1.018× | 0.972× | 1.020× |
| generated_communities | positive | 1.012× | 1.002× | 1.024× |
| generated_communities | uniform | 0.968× | 0.998× | 1.003× |
| generated_dag | balanced | 1.044× | 1.040× | 1.020× |
| generated_dag | negative | 1.045× | 0.963× | 1.006× |
| generated_dag | positive | 0.963× | 0.959× | 0.978× |
| generated_dag | uniform | 1.042× | 0.951× | 0.967× |
| grail_citeseer | balanced | 1.229× | 1.008× | 1.063× |
| grail_citeseer | negative | 1.387× | 0.948× | 1.063× |
| grail_citeseer | positive | 1.197× | 0.989× | 1.058× |
| grail_citeseer | uniform | 1.518× | 1.013× | 1.122× |
| grail_go | balanced | 1.394× | 0.980× | 1.160× |
| grail_go | negative | 1.619× | 1.036× | 1.181× |
| grail_go | positive | 1.234× | 0.977× | 1.129× |
| grail_go | uniform | 1.620× | 0.987× | 1.227× |
| grail_kegg | balanced | 0.997× | 0.966× | 1.006× |
| grail_kegg | negative | 1.009× | 1.010× | 1.025× |
| grail_kegg | positive | 1.001× | 0.972× | 0.994× |
| grail_kegg | uniform | 1.074× | 0.999× | 1.040× |
| grail_pubmed | balanced | 1.276× | 0.989× | 1.087× |
| grail_pubmed | negative | 1.617× | 1.013× | 1.135× |
| grail_pubmed | positive | 1.129× | 0.959× | 1.050× |
| grail_pubmed | uniform | 1.605× | 1.007× | 1.133× |
| grail_yago | balanced | 1.262× | 1.012× | 1.126× |
| grail_yago | negative | 1.564× | 0.991× | 1.114× |
| grail_yago | positive | 1.221× | 1.007× | 1.074× |
| grail_yago | uniform | 1.707× | 1.021× | 1.187× |
| heldout_agrocyc | balanced | 1.657× | 0.876× | 1.151× |
| heldout_agrocyc | negative | 1.478× | 1.026× | 1.268× |
| heldout_agrocyc | positive | 1.549× | 0.986× | 1.239× |
| heldout_agrocyc | uniform | 1.536× | 0.998× | 1.113× |
| heldout_amaze | balanced | 0.932× | 1.066× | 0.958× |
| heldout_amaze | negative | 0.954× | 0.725× | 0.909× |
| heldout_amaze | positive | 0.997× | 0.984× | 0.986× |
| heldout_amaze | uniform | 1.010× | 0.913× | 1.009× |
| heldout_anthra | balanced | 1.610× | 0.924× | 1.253× |
| heldout_anthra | negative | 1.507× | 0.952× | 1.261× |
| heldout_anthra | positive | 1.489× | 0.989× | 1.255× |
| heldout_anthra | uniform | 1.618× | 1.051× | 1.223× |
| heldout_ecoo | balanced | 1.637× | 1.023× | 1.306× |
| heldout_ecoo | negative | 1.560× | 0.976× | 1.223× |
| heldout_ecoo | positive | 1.617× | 0.928× | 1.262× |
| heldout_ecoo | uniform | 1.494× | 0.962× | 1.199× |
| heldout_human | balanced | 1.525× | 0.988× | 1.078× |
| heldout_human | negative | 1.372× | 0.933× | 0.943× |
| heldout_human | positive | 1.631× | 1.004× | 1.187× |
| heldout_human | uniform | 1.531× | 1.021× | 1.181× |
| heldout_mtbrv | balanced | 1.459× | 1.002× | 1.281× |
| heldout_mtbrv | negative | 1.682× | 1.035× | 1.366× |
| heldout_mtbrv | positive | 1.660× | 0.931× | 1.304× |
| heldout_mtbrv | uniform | 1.570× | 0.992× | 1.266× |
| heldout_nasa | balanced | 1.533× | 0.941× | 1.305× |
| heldout_nasa | negative | 1.560× | 0.948× | 1.295× |
| heldout_nasa | positive | 1.431× | 1.039× | 1.275× |
| heldout_nasa | uniform | 1.502× | 0.889× | 1.236× |
| heldout_vchocyc | balanced | 1.578× | 0.982× | 1.283× |
| heldout_vchocyc | negative | 1.539× | 1.007× | 1.258× |
| heldout_vchocyc | positive | 1.517× | 0.962× | 1.273× |
| heldout_vchocyc | uniform | 1.641× | 1.073× | 1.372× |
| heldout_xmark | balanced | 1.536× | 1.170× | 1.382× |
| heldout_xmark | negative | 1.293× | 0.825× | 1.090× |
| heldout_xmark | positive | 1.473× | 0.977× | 1.262× |
| heldout_xmark | uniform | 1.575× | 1.093× | 1.318× |
| kron_logn12 | balanced | 1.001× | 0.841× | 0.974× |
| kron_logn12 | negative | 0.978× | 0.838× | 0.999× |
| kron_logn12 | positive | 0.991× | 0.848× | 0.993× |
| kron_logn12 | uniform | 0.985× | 0.880× | 1.016× |

## Full external aggregate results

| Dataset | Stratum | PR29 / candidate query | Fastest external / candidate query | PR29 / candidate lifecycle |
|---|---|---:|---:|---:|
| example | balanced | 1.251× | 2.312× | 0.988× |
| example | negative | 1.174× | 2.051× | 1.007× |
| example | positive | 1.222× | 2.278× | 1.052× |
| example | uniform | 1.215× | 2.150× | 0.988× |
| generated_blocks | balanced | 0.950× | 1.229× | 0.982× |
| generated_blocks | negative | 1.017× | 1.001× | 0.992× |
| generated_blocks | positive | 1.019× | 1.670× | 1.002× |
| generated_blocks | uniform | 1.061× | 0.985× | 0.969× |
| generated_communities | balanced | 1.002× | 1.950× | 1.013× |
| generated_communities | negative | 1.086× | 1.091× | 1.147× |
| generated_communities | positive | 1.004× | 2.219× | 0.998× |
| generated_communities | uniform | 1.000× | 1.947× | 1.016× |
| generated_dag | balanced | 0.995× | 3.692× | 0.982× |
| generated_dag | negative | 0.980× | 3.039× | 0.953× |
| generated_dag | positive | 0.999× | 3.988× | 0.982× |
| generated_dag | uniform | 1.088× | 2.800× | 0.992× |
| grail_citeseer | balanced | 1.294× | 2.281× | 0.959× |
| grail_citeseer | negative | 1.420× | 1.440× | 0.975× |
| grail_citeseer | positive | 1.139× | 1.912× | 0.986× |
| grail_citeseer | uniform | 1.450× | 1.610× | 0.982× |
| grail_go | balanced | 1.319× | 2.084× | 0.979× |
| grail_go | negative | 1.650× | 1.727× | 1.020× |
| grail_go | positive | 1.081× | 2.402× | 0.996× |
| grail_go | uniform | 1.567× | 1.528× | 0.978× |
| grail_kegg | balanced | 0.979× | 0.952× | 0.997× |
| grail_kegg | negative | 1.002× | 0.808× | 0.961× |
| grail_kegg | positive | 1.004× | 0.965× | 0.989× |
| grail_kegg | uniform | 0.983× | 0.836× | 1.010× |
| grail_pubmed | balanced | 1.072× | 2.192× | 0.970× |
| grail_pubmed | negative | 1.555× | 1.681× | 1.014× |
| grail_pubmed | positive | 1.036× | 1.978× | 0.991× |
| grail_pubmed | uniform | 1.512× | 1.950× | 1.002× |
| grail_yago | balanced | 1.165× | 2.048× | 0.992× |
| grail_yago | negative | 1.549× | 1.539× | 1.016× |
| grail_yago | positive | 1.159× | 1.530× | 0.986× |
| grail_yago | uniform | 1.548× | 1.480× | 1.021× |
| heldout_agrocyc | balanced | 1.576× | 0.882× | 0.982× |
| heldout_agrocyc | negative | 1.256× | 0.750× | 0.923× |
| heldout_agrocyc | positive | 1.623× | 0.927× | 0.970× |
| heldout_agrocyc | uniform | 1.300× | 0.840× | 0.975× |
| heldout_amaze | balanced | 1.026× | 1.015× | 1.019× |
| heldout_amaze | negative | 1.095× | 0.794× | 1.046× |
| heldout_amaze | positive | 0.933× | 0.843× | 1.022× |
| heldout_amaze | uniform | 1.312× | 0.817× | 1.123× |
| heldout_anthra | balanced | 1.359× | 0.965× | 1.222× |
| heldout_anthra | negative | 1.702× | 1.072× | 1.041× |
| heldout_anthra | positive | 1.448× | 0.878× | 1.007× |
| heldout_anthra | uniform | 1.558× | 0.958× | 0.983× |
| heldout_ecoo | balanced | 1.358× | 0.947× | 1.051× |
| heldout_ecoo | negative | 1.528× | 0.926× | 1.014× |
| heldout_ecoo | positive | 1.434× | 0.858× | 1.146× |
| heldout_ecoo | uniform | 1.575× | 0.985× | 1.022× |
| heldout_human | balanced | 1.436× | 0.922× | 0.988× |
| heldout_human | negative | 1.868× | 0.951× | 1.014× |
| heldout_human | positive | 2.071× | 0.891× | 1.015× |
| heldout_human | uniform | 1.731× | 0.908× | 1.078× |
| heldout_mtbrv | balanced | 1.633× | 1.111× | 1.053× |
| heldout_mtbrv | negative | 1.483× | 0.922× | 1.011× |
| heldout_mtbrv | positive | 1.656× | 0.915× | 1.046× |
| heldout_mtbrv | uniform | 1.796× | 0.994× | 1.062× |
| heldout_nasa | balanced | 1.563× | 1.859× | 1.094× |
| heldout_nasa | negative | 1.558× | 1.759× | 1.063× |
| heldout_nasa | positive | 1.402× | 1.628× | 1.000× |
| heldout_nasa | uniform | 1.545× | 1.795× | 0.949× |
| heldout_vchocyc | balanced | 1.318× | 0.826× | 1.027× |
| heldout_vchocyc | negative | 1.790× | 0.935× | 1.014× |
| heldout_vchocyc | positive | 1.513× | 0.869× | 0.988× |
| heldout_vchocyc | uniform | 1.912× | 0.963× | 1.076× |
| heldout_xmark | balanced | 1.449× | 2.220× | 1.058× |
| heldout_xmark | negative | 1.527× | 1.550× | 1.034× |
| heldout_xmark | positive | 1.445× | 2.419× | 1.019× |
| heldout_xmark | uniform | 1.427× | 2.013× | 0.975× |
| kron_logn12 | balanced | 0.975× | 1.859× | 1.023× |
| kron_logn12 | negative | 0.961× | 1.296× | 1.011× |
| kron_logn12 | positive | 1.020× | 2.324× | 0.994× |
| kron_logn12 | uniform | 0.982× | 1.717× | 0.992× |

## Fresh and forest cells, including all regressions

| Campaign | Dataset | Stratum | Replays | Query ratio | Lifecycle ratio |
|---|---|---|---:|---:|---:|
| fresh | phase30_cross_chains | balanced | 1 | 0.986× | 1.046× |
| fresh | phase30_cross_chains | balanced | 1000 | 0.986× | 0.963× |
| fresh | phase30_cross_chains | negative | 1 | 0.923× | 1.133× |
| fresh | phase30_cross_chains | negative | 1000 | 0.996× | 1.009× |
| fresh | phase30_cross_chains | positive | 1 | 1.185× | 1.063× |
| fresh | phase30_cross_chains | positive | 1000 | 0.873× | 0.925× |
| fresh | phase30_cross_chains | uniform | 1 | 0.947× | 0.892× |
| fresh | phase30_cross_chains | uniform | 1000 | 0.980× | 0.991× |
| fresh | phase30_fragmented | balanced | 1 | 1.076× | 0.971× |
| fresh | phase30_fragmented | balanced | 1000 | 1.347× | 1.172× |
| fresh | phase30_fragmented | negative | 1 | 1.339× | 1.023× |
| fresh | phase30_fragmented | negative | 1000 | 1.514× | 1.147× |
| fresh | phase30_fragmented | positive | 1 | 1.009× | 1.044× |
| fresh | phase30_fragmented | positive | 1000 | 1.177× | 1.093× |
| fresh | phase30_fragmented | uniform | 1 | 1.191× | 1.011× |
| fresh | phase30_fragmented | uniform | 1000 | 1.592× | 1.221× |
| fresh | phase30_scc_aliases | balanced | 1 | 1.198× | 0.960× |
| fresh | phase30_scc_aliases | balanced | 1000 | 1.525× | 1.139× |
| fresh | phase30_scc_aliases | negative | 1 | 1.322× | 0.948× |
| fresh | phase30_scc_aliases | negative | 1000 | 1.538× | 1.104× |
| fresh | phase30_scc_aliases | positive | 1 | 1.089× | 0.979× |
| fresh | phase30_scc_aliases | positive | 1000 | 1.375× | 1.150× |
| fresh | phase30_scc_aliases | uniform | 1 | 1.024× | 0.990× |
| fresh | phase30_scc_aliases | uniform | 1000 | 1.594× | 1.130× |
| fresh | phase30_shared_hubs | balanced | 1 | 1.095× | 1.014× |
| fresh | phase30_shared_hubs | balanced | 1000 | 1.170× | 1.083× |
| fresh | phase30_shared_hubs | negative | 1 | 1.201× | 0.968× |
| fresh | phase30_shared_hubs | negative | 1000 | 1.469× | 1.088× |
| fresh | phase30_shared_hubs | positive | 1 | 0.994× | 1.018× |
| fresh | phase30_shared_hubs | positive | 1000 | 1.131× | 1.052× |
| fresh | phase30_shared_hubs | uniform | 1 | 1.153× | 0.990× |
| fresh | phase30_shared_hubs | uniform | 1000 | 1.433× | 1.122× |
| forest-warm | large_citeseer | balanced | 1000 | 0.930× | 1.039× |
| forest-warm | large_citeseer | negative | 1000 | 1.007× | 1.056× |
| forest-warm | large_citeseer | positive | 1000 | 0.787× | 1.037× |
| forest-warm | large_citeseer | uniform | 1000 | 1.010× | 0.998× |
| forest-warm | large_uniprot_22m | balanced | 1000 | 0.901× | 0.996× |
| forest-warm | large_uniprot_22m | negative | 1000 | 0.961× | 0.972× |
| forest-warm | large_uniprot_22m | positive | 1000 | 1.014× | 1.032× |
| forest-warm | large_uniprot_22m | uniform | 1000 | 1.065× | 0.968× |
| forest-fresh | large_citeseer | uniform | 1 | 0.661× | 1.111× |
| forest-fresh | large_uniprot_22m | uniform | 1 | 0.739× | 1.178× |
| forest-replication | large_citeseer | uniform | 1 | 0.882× | 1.018× |
| forest-replication | large_uniprot_22m | uniform | 1 | 0.957× | 0.982× |
| forest-warm-replication | large_citeseer | balanced | 1000 | 0.988× | 0.960× |
| forest-warm-replication | large_citeseer | negative | 1000 | 0.992× | 0.996× |
| forest-warm-replication | large_citeseer | positive | 1000 | 1.020× | 1.020× |
| forest-warm-replication | large_citeseer | uniform | 1000 | 1.094× | 1.051× |
| forest-warm-replication | large_uniprot_22m | balanced | 1000 | 1.016× | 1.045× |
| forest-warm-replication | large_uniprot_22m | negative | 1000 | 1.000× | 1.012× |
| forest-warm-replication | large_uniprot_22m | positive | 1000 | 0.941× | 0.980× |
| forest-warm-replication | large_uniprot_22m | uniform | 1000 | 1.002× | 0.988× |

## Verification and provenance

- All 35 Python/native test methods passed locally. Existing native self-tests include 18,432 exhaustive checks, 1,440 adversarial checks, 589,824 interval checks, 207,360 forest checks, 1,296 packed-coordinate checks and 153,600 cross-chain checks; test code also verifies both automatic and partitioned APIs.
- AddressSanitizer and UndefinedBehaviorSanitizer passed locally. Only local LeakSanitizer was disabled for the traced execution environment; CI retains the full sanitizer command.
- Every timed process independently BFS-verifies every sampled query after timing and checks its answer checksum against other arms.
- The verifier validates source/build/input hashes, complete case sets, unchanged memory/routes, moved-body equivalence, the exact PR29 control binary, all rejected pilot records and both supplemental forest replications.
- Frozen Phase XXIX sources preserve historical verification without rewriting previous evidence. Current CI uses that snapshot for Phase XXIX and adds Phase XXX verification. GitHub CI status is reported separately at publication; local logs alone do not prove hosted CI success.

## Remaining SOTA gaps and next work

1. Reduce the remaining negative-query gap on Agrocyc and direct-closure losses on Amaze/KEGG, using a new frozen candidate campaign.
2. Resolve the cold forest regression on dedicated hardware and compare independent call sites and compilers; do not infer an algorithmic forest regression from changed whole-program layout alone.
3. Execute MLRQ/MLRQ-O with verified author code and match total retained-memory/Pareto budgets. A fresh search found the [publisher paper](https://link.springer.com/article/10.1007/s44443-025-00310-0), but did not establish an accessible author implementation. Its reported comparisons are not substitute measurements in this harness.
4. Add unexposed real-world topologies and independent hardware replication. Many samples here share graph, generator and machine lineage.

The [OReach paper](https://doi.org/10.1145/3556540) and [original PLL/PPL repository](https://github.com/y3eadgbe/PrunedLabeling) remain primary references. Established SCC, interval, path-label and Bloom techniques are not claimed as inventions. This phase is a verified local engineering improvement with explicit regressions, not a proof of global SOTA.

## Reproduction

From `tric_research/`, run the standard test command and the archived evidence verifier:

```bash
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_native_runtime
python verify_phase29_evidence.py --source-root evidence/phase30/baseline-sources
python verify_phase30_evidence.py
python summarize_phase30.py
```

To rerun timings, build with `build_native_comparison.py --before-headers evidence/phase30/baseline-sources/tric_research`, passing the pinned OReach source/build and Boost include paths recorded in `build_manifest.json`. Use a separate checkout/output tree because the runner refuses overwriting sealed evidence. `run_phase30_qualification.py --build BUILD_DIRECTORY` executes the five original campaigns; the supplemental command is recorded in the evidence README. Environment-specific absolute paths in historical manifests are provenance, not a requirement that new machines use those directory names.

Execution used Elite AGI as an engineering lens, Knowledge Nexus for evidence and gap tracking, and Trillion Developer++ for controlled experiments and qualification. OmO bridge probing returned `installed=false`; its native recursive fallback ran. No real OmO runtime execution or additional workers are claimed.

# TRIC Phase XIX — Evidence-Gated Performance Portfolio & Source-Hotset Hypothesis

**Date:** 2026-10-22  
**Status:** Independent research/code audit + new **experimental** C++17 source-hotset accelerator. Historical Phases I–XVIII remain unmodified; `main` remains Phase III. This branch is stacked on Phase XVIII PR #16 and is deliberately **unmerged**.

## 1. Decision contract

Find a reproducible, exact reachability regime where TRIC improves substantially on credible controls without trading away correctness, disclosing neither build cost nor memory footprint, or implicitly claiming publication novelty. Report separate: latency, memory, preprocessing, workload volume, query truth ratio, correctness, and cross-graph stability. A win on an artificially hot workload against plain DFS is **not** a win against original O'Reach.

Three hypotheses are independently testable:

- H1: existing compact topological/bidirectional SCC variants are competitive but under-indexed against a mature static reachability oracle;
- H2: limited, outcome-blind dispatch based on SCC features can beat the best unconditional fallback, but current nanosecond-scale fitting is unstable and expensive;
- H3: precomputing exact bitsets for independently trained **frequently requested sources** can win on repeated-source workloads within a declared memory/build budget, but lose under hot-source drift or uniform sources.

H1 is supported within the narrow two-graph pilot; H2's unconditional economic benefit is **not** supported by Phase XVIII; H3 is **hypothetical until the new bench completes**.

## 2. Reconstructed phase lineage

| Phases | Contribution | Strongest supported result | Boundary |
|---|---|---|---|
| I–II | O'Reach-style S1/S2/S3 certificates; path Monge / sweep optimizer | Correctness and faster *internal* Python selectors | S1/S2/S3 are prior art |
| III | Backbone query sets = up to two intervals; graph construction reducing Vertex Cover; FPT orientation search | Human-readable proof, exhaustive bounded checks | Specialized problem and theorem novelty not independently established |
| IV–VII | SCC lifting, frontier-width exact DP, region decomposition, active-start quotient | Specialized exact optimization under relevant structural parameters | Worst-case exponential; cost of solving may dwarf query savings |
| VIII–IX | Ordered cost-aware probes, native C++ evaluation | Native cost-vs-latency and amortization checks | Model savings need not improve wall-clock; not external SOTA |
| X–XII | Pinned external O'Reach control, quadratic closure and compact index | Earlier compact hybrid improved from major gap to ~19–21× behind O'Reach on arXiv in Phase XII | Closure pays quadratic bits, other methods lack O'Reach's index |
| XIII–XIV | Topological and bidirectional exact condensation search | Phase XIV arXiv 387.54 ns/q versus O'Reach 268.56 ns/q; Kronecker 94.03 vs 63.14 ns/q (medians across seeds) | Only two graph sources, query-only, unmatched resources |
| XV–XVI | Positive/negative/balanced workload falsification, two-sided pruning ablation | Narrow Phase XV arXiv positive-only 551.16 ns/q TRIC versus 609.80 O'Reach; interval pruning often regressed | Class-specific sampling, data-local wins; pruning overhead often exceeds savings |
| XVII | Train-only, outcome-blind learned fallback routing | Some class-specific query-only benefits; arXiv negative route still worse than topology-only | Fit cost and instability invalidate default use |
| XVIII (#15 and #16) | Source diversity, failed synthetic upstream runs, measured training-fit break-even and hashes | Phase XVIII PR #16: no projected 1,200-query amortized selector win in 24 graph×seed×class cases; rerun disproves earlier Kronecker negative win | PR #15/#16 are two alternative draft branches; neither merged; million-query estimates are extrapolations |

**Observed head CI** for PR #16: research unit tests run 39779105520 and external comparison run 39779105550, both completed successfully at SHA `785875a22557ce44f249184ef83cecd87264c49d`. The positive arXiv result is a narrow measured observation, not a statistically established broader win.

## 3. Independent literature / source-code tribunal

1. **Hanauer, Schulz, Trummer, O'Reach: Even Faster Reachability in Large Graphs**, SEA 2021, DOI [10.4230/LIPIcs.SEA.2021.13](https://doi.org/10.4230/LIPIcs.SEA.2021.13), [original source](https://github.com/o-reach/O-Reach), [official datasets](https://oreach.taa.univie.ac.at/): direct closest competitor and origin of supportive certificates. Treat overlap as substantial, not as a renamed innovation.
2. **Zhang, Bonifati, Özsu, Indexing Techniques for Graph Reachability Queries**, ACM Computing Surveys (published December 2025), DOI [10.1145/3776737](https://doi.org/10.1145/3776737): reviews 33 approaches and frames index families: tree covers, 2-hop labeling, approximate transitive closure; their resource tradeoffs rule out naive latency-only leadership.
3. **Zhang, Gan, Yang, MLRQ: an efficient labeling scheme for reachability queries on reduced DAGs**, November 2025, DOI [10.1007/s44443-025-00310-0](https://doi.org/10.1007/s44443-025-00310-0): experimentally evaluates four outcome mixes at **one million queries each** and both index sizes and build times. Adds a modern comparator class beyond O'Reach.
4. **Incremental Reachability Index**, SEA 2025, DOI [10.4230/LIPIcs.SEA.2025.9](https://doi.org/10.4230/LIPIcs.SEA.2025.9): chain-based constant-time tradeoffs when the graph is append-only; cannot be interpreted as a pure static-index baseline.
5. Classical GRAIL, Ferrari, 2-hop labeling and BFL: candidate index classes, not evidence of relative TRIC performance until faithful, licensed implementations are built and compared.

**Novelty ruling:** certificate rules = **SUBSTANTIALLY OVERLAPPING**; standard SCC/closure/topological/bi-BFS/partial-hotset techniques = **ESTABLISHED / COMBINATIONAL**; specialized backbone geometry and graph-gadget reduction = **UNRESOLVED** under a close prior-art search. No "first" or SOTA claims from this audit.

## 4. Why no current phase wins everywhere

This is an **observed design tension, not a theorem that universal dominance is impossible**:

- Fastest static queries can require additional index bytes and preprocessing. Linear-size partial indexes sometimes need costly fallback, especially for positive queries that traverse many arcs.
- Different DAG structure (paths, trees, dense SCCs, Kronecker and social/citation graphs) changes the selectivity of topological bounds, witnesses and hubs.
- Negative and positive query classes exercise distinct traversal termination paths; a method tuned on the true answer would leak a heldout label and is not deployable.
- Instruction/cache locality and branch overhead matter as much as edge counts at nanosecond scale; Phase XVI's two-sided filter scanned fewer edges but was often slower.
- Training policy selection can overfit hosted-runner noise. Spending milliseconds to save tens of nanoseconds pays only beyond a potentially large volume of **similarly distributed actual queries**.
- The difference between `main` and stacked research heads, and two concurrent Phase XVIII heads, also means any aggregate "TRIC latest" claim needs an exact SHA.

## 5. Phase XIX experiment: train-only source-hotset bitsets

The new `hot_source_cache.h` implements deterministic frequency selection of source vertices from **training pairs only**. For selected source `s`, it materializes a full exact reachable-vertex bitmap; any heldout `(s,t)` with a cached source becomes a single lookup with an exact Boolean answer. Uncached sources must use the unchanged exact DFS control. This is **selective materialized transitive closure**, known and explicitly non-novel.

- **Safety:** no false positives or negatives, including self pairs and cyclic graphs. Finite exhaustive C++ testing covers all 512 directed graphs with three vertices plus boundary/adversarial tests.
- **Cost:** `O(K(V+E))` worst-case bitmap filling plus `O(T+V log V)` training-source counting/sorting for `K` selected source rows and `T` training pairs. Retained bytes `O(V + K ceil(V/64))`; memory cap includes source lookup IDs and row storage, excludes temporary build buffers and allocator metadata.
- **Online time:** cached query `O(1)`, otherwise fallback `O(V+E)` worst case. Always exact. No mutation/incremental graph updates supported.
- **Falsification:** identical hot-source train/heldout, uniform heldout, and disjoint shifted-hot heldout. Each uses 14 position-balanced paired native C++ repetitions, 3 graph seeds, independent BFS, full checksums and raw samples. The new test protocol is **synthetic DAG vs plain DFS only**; O'Reach and indexed TRIC are not compared by Phase XIX. Do not sell such a synthetic DFS win as an external SOTA result.
- **Amortization:** for measured additional cache build `F`, baseline `B` ns/q, cache `S` ns/q: `Q_min = floor(F/(B-S)) + 1` if `B>S`, otherwise no finite break-even. All extrapolations assume a stationary heldout distribution.

Reproduce: `cd tric_research && python -m unittest -q test_hot_source_cache && python benchmark_hot_source_cache.py --seeds 3 --output ../research-results/phase19_hotset_results.json`. Required tools: Python 3.10+, C++17 g++. CI stores unrounded source/heldout samples and exactness results as evidence.

## 6. SOTA Research Auditor — independent gates

| Gate | Finding | Blocking evidence |
|---|---|---|
| Mathematical soundness | **Partial / promising** for specified III–VII constructions | Independently review reduction endpoints, weighted objectives, FPT parameters and worst-case bounds |
| Artifact/test correctness | **Qualified PASS** at Phase XVIII #16 head for its exact test scope | Synthetic shifted workloads and Phase XIX must be run on its own commit |
| Empirical external superiority | **NO-GO** generally; one *narrow* positive-only pilot win | Two small graphs, non-dedicated runners, unmatched index build/RSS/memory |
| Novelty | **UNRESOLVED** for specialized exact optimization; **not novel** for reused search/index components | Literature comparison against interval-bundle stabbing, path/chain covering, set-cover and graph-label variants |
| Reproducibility | **Partially supported**, pinned upstream O'Reach and raw workflows | Stronger resource alignment, repeated dedicated-machine runs, independent graph-family replicates, separately audited O'Reach answers |
| Publication readiness | **NO-GO** for an all-around faster reachability index claim | Broad comparator matrix, predeclared meaningful win criteria, reproducible end-to-end costs and theoretical contribution |

## 7. Decision-ranked next engineering stages

**P0 — Qualification:** keep experimental hotset isolated until benchmark passes; add source-conditioned real-data workloads and feed the exact same queries to original O'Reach and current compiled TRIC; qualify source drift, memory, cold-start and actual million-query replay.

**P1 — Index portfolio:** benchmark resource-capped selective closure and SCC-local closure against existing topological, bidirectional, and pivot families. Use a fixed memory envelope, not O'Reach's unknown default versus TRIC's favorable one. Permit a deployment-default choice only after true end-to-end wins including training/build.

**P2 — Independent comparisons:** implement/obtain correctly licensed MLRQ, BFL, 2-hop and a chain-aware index (when reproducible source exists). Keep graph identity, hardware, compiler flags, memory, outcomes and query source distributions paired. Preserve genuine failures.

**P3 — Paper candidates:** separately audit the Phase III graph-specific Vertex Cover reduction and the VI–VII frontier/active-start formulation for *theoretical* novelty. Do not conflate the publishability of those exact optimization problems with index performance.

**Current decision:** **GO** for Phase XIX controlled experiment; **NO-GO** for mainline default, original novelty, commercial-grade fast-index positioning, universal winner, or submission claim.

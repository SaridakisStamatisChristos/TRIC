# TRIC Phase XXII — Cross-Graph Replication and Actual Cold-Start Cost

Date: 2026-10-22. Status: preregistered research experiment, not an algorithm promotion.
Base: Phase XXI PR #20, exact unmerged head. Existing defaults and previous evidence stay unchanged.

## What this phase is intended to test

Phase XXI reported ~3.4–3.5x improved **query-only** latency for cache+pivot+indexed reachability on the matched hot-source class on the original arXiv and Kronecker graphs, but the broader result is unresolved. Phase XX's cache+plain-DFS fallback failed badly. This experiment directly challenges the stronger claim that the cache's extra memory and build time repay themselves on repeated source-conditioned workloads.

## Independent research matrix

Five distinct graph instances/topologies: two verified published inputs plus three **clearly labeled generated** graphs. The originally proposed go_sub, pubmed_sub and delaunay_n15 instances could not be retrieved from the published URLs (HTTP 404); see failed matrix attempt CI 39796683330. They are not silently replaced under the original names:

| Dataset | Vertices | Directed edges | Family |
|---|---:|---:|---|
| example / arXiv.metis | 6000 | 66707 | citation |
| kron_logn12 | 4096 | 116952 | RMAT / Kronecker DAG |
| generated_dag | 2000 | determined by fixed generator seed | synthetic topological DAG |
| generated_blocks | 2000 | determined by fixed generator seed | synthetic block DAG |
| generated_communities | 2000 | determined by fixed generator seed | synthetic cyclic communities |

Authentic graphs source: original O'Reach published catalogue: https://oreach.taa.univie.ac.at/ and bundled upstream arXiv example. Synthetic graphs: TRIC's pre-existing graph_family routine with graph seed 20261001, 2000 nodes, fixed across query seeds, exported as directed METIS and checksum-checked. Original O'Reach remains the SHA-pinned comparator for **all** graph classes. The synthetic instances do NOT reproduce the unavailable published instances. Do not equate the three query/training seeds *on one fixed graph* with independent graph samples.

For each graph × seed (20261022, 20261023, 20261024) × workload (matched 80%-hot, uniform, shifted 80%-hot from disjoint sources), use exact identical 2400 heldout pairs per method, independently train on 500 other pair draws, deterministic first-party pivot selection, 2 MiB cap for retained hot bitset vectors, and 11 candidates / pivot budget 5. The original benchmark runs native TRIC/O'Reach comparisons including control methods and preserves all data hashes.

**Expected matrix:** 15 graph-seed jobs and 45 different heldout test sets. Graph sources are five graph *instances* but only two are genuinely published benchmark sources. Synthetic families cannot substitute for independent real-world replication.

## Cold-start / real replay protocol

Phase XXII adds a stand-alone, fresh C++17 process in exactly two configurations:

- `pivot_index` — graph parsing, the same 11 pivot bitset builds and compact SCC index, then original exact certificates and bidirectional fallback; **no hot-cache allocation**.
- `cache_pivot_index` — the exact same graph, candidates, ordered policy and indexed fallback, with one extra train-only hot-source bitmap, and direct answer when that source is cached.

The C++ clock starts **before parsing the native graph/input** and stops **after the last replayed query result**. It measures input parsing, pivot building, compact index building, optional cache materialization, and actual query-loop work. Independent DFS validation of all unique heldout pairs occurs *after* the clock stops. Process max-RSS is captured with `/usr/bin/time` and includes validation overhead; it does not solely measure the index's resident bytes. Independently record extra hot-source vector bytes and native query output checksum; both modes must return identical hashes and independent answer checks.

For each class, use factors 1 and 50: **2,400 and 120,000 actual native query calls**, verified in the returned JSON; alternate independent fresh-process invocation order across two paired runs per horizon. The longer sequence **repeats the same 2400 heldout pairs**; do not present it as 120,000 unique or IID fresh queries. Compiler time, dataset download/preparation, generation and Python training are excluded from the C++ inner process measurement; Python pivot-fitting nanoseconds are disclosed separately.

Additionally rerun **unmodified, original O'Reach pDFS only** as a fresh process against exactly the same repeated query file, preserving process elapsed wall time, reported O'Reach initialization/query time and external max-RSS. The pDFS process has different parsing/I/O and native timing boundaries than TRIC. It is useful evidence, but **not matched-memory or directly equal end-to-end application cost**.

Published O'Reach algorithm source SHA: `78b3e326bbb021b7ee225ab605a4cdd074fa1d93`. Three graph truth classes recorded by independently sampled source/target pairs; O'Reach's `.query.m.txt` suffix is filename metadata, not guaranteed 50:50 class composition.

## Prospective promotion gate

No automatic/default promotion. Consider proposing one only if ALL hold on the final exact SHA:

1. **Correctness:** full native CI and all 15 research matrix jobs pass, including cache byte cap, no heldout training, identical input hashes, independent oracle and repeated-query checksums.
2. **Real lifetime:** cache-assisted median **build + 120,000 actual queries** beats indexed baseline by ≥10% in at least four of five graph families, for all three query seeds in each passing family, in the *matched-hot* class.
3. **Drift safety:** uniform and shifted classes suffer no >5% median *full lifecycle* regression for any graph/seed. If only one class wins, the product would require a rigorously tested workload selection gate or opt-in.
4. **Memory:** quantify actual max-RSS delta for each paired fresh process; require the selected cap be enforced and no unexplained extra RSS beyond up to +5 MiB per tested graph/seed. Report combined retained index sizes separately.
5. **External competitiveness:** compare O'Reach on the same exact repeated query files, and report original O'Reach build/query/RSS without conflating process wall timers. Do not claim blanket or memory-matched superiority from any narrow result.

These thresholds are engineering acceptance criteria, not formal confidence bounds. Shared GitHub runners and two trial replicates are exploratory. The 2 authentic + 3 generated matrix can validate the mechanism but is **insufficient by itself to promote a general-performance/default algorithm**; obtain additional verifiable authentic graphs and dedicated replicated runs before marketing, default promotion or publishing generalized superiority.

## Closest prior art and novelty state

Source-selective transitive-closure bitmaps, cached BFS sources, SCC condensation, interval labels, pivots, and bidirectional traversal are known mechanisms. A composite is a legitimate engineering specialization, **not an original exact-reachability primitive**. Primary references include Hanauer et al., *O'Reach: Even Faster Reachability in Large Graphs*, SEA 2021 (https://doi.org/10.4230/LIPIcs.SEA.2021.13) and Zhang et al., *Indexing Techniques for Graph Reachability Queries*, ACM Computing Surveys (2025, https://doi.org/10.1145/3776737).

## Reproducibility and outputs

`.github/workflows/research-phase22.yml` builds original pinned upstream from source and runs the complete 5 × 3 matrix. It preserves graph checksum, compiler, raw class-level input, exact measurements, independent test logs, original O'Reach CSV, and two fresh-process result files per mode/horizon/trial under each dataset × seed artifact.

Standalone test: `cd tric_research && python -m unittest -q test_phase22_lifetime`.

**State at creation:** specified and implemented, **NOT YET externally replicated**. After 15 CI jobs complete, append actual positives/negative cases, paired trial medians and final promotion decision, with exact SHA. If jobs fail, preserve evidence and repair test defects rather than weakening assertions.

## Dataset availability audit and experimental amendment

Original matrix run https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39796683330 recorded an HTTP 404 while downloading go_sub from the authors' advertised instance URL; external checks showed pubmed_sub and delaunay_n15 also returned 404. Those jobs remain failed instead of being relabeled successes or silently fed different inputs. On this subsequent code revision, the planned 5×3 replication is **2 authentic + 3 generated** families, with the original dataset list preserved here as an unexecuted/failed acquisition plan. Generated graphs are frozen to a separate deterministic graph seed so the three query seeds do not inadvertently change their topology. Publication/generalization gate therefore stays NO-GO without more real sources.

## Phase XXII comparator crash isolation — 2026-10-22

The all-runner CI at head 86af2ab69fb4050bb4142c8513a9fe42fef11dac
completed its 15 jobs with **9 successful and 6 failures**. All six
failures were in the two deterministic generated graph families
`generated_blocks` and `generated_communities`; the pinned,
unmodified original O'Reach executable returned code **139** (SIGSEGV)
on the *first* mixed workload, repetition zero, after the native
TRIC comparators and independent C++ oracle had succeeded.

Classification: verified **external comparator process crash**,
not a proven underlying root cause in upstream source. The byte-valid
generated METIS file itself is not independently proven acceptable to
every upstream O'Reach algorithm. Do not infer original O'Reach's
incorrect answers or infer that TRIC beats a process that crashes.
Upstream remains SHA-pinned and unmodified.

Evidence: https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39799773321

### Repair and scoped experiment contract

* On `generated_dag`, `generated_blocks`, and
  `generated_communities` **only**, explicit
  `--allow-upstream-segfault` authorizes catching **return code 139
  or -11** from the original comparator. Unsupported errors (including
  timeouts, bad/missing CSV, differing query count, invalid checksum,
  other exit codes) remain failures. Authentic arXiv and Kronecker
  cannot enable the tolerance; their original external results must
  be complete, or CI fails.
* The crash is preserved in a class-specific
  `oreach_unavailable.json` with return code, signal, graph/query
  hashes, repetition and stdout/stderr file paths. Any previously
  collected partial method samples are **discarded**, never pooled
  into a median. Subsequent classes record `unavailable_after...\
  rather than silently rerunning the known-crashing binary.
* The complete native cache/pivot-index and independent correctness
  tests continue through **both measured query horizons**, full
  build+query cost and peak-RSS checks. The Phase XXII lifetime runner
  records the original pDFS-only process as `unavailable` and
  `actual_calls: 0` on those generated graph families, *not* a
  zero-time external win.
* A separate artifact auditor validates all graph/seed/classes/horizons,
  exact positive resource/timing values, true replay counts, equality
  and oracle-check labels, and per-class external-completeness
  consistency. A synthetic job with unavailable original O'Reach can
  finish successfully only when all TRIC checks pass. GitHub logs
  emit a visible warning explicitly stating that the external
  comparator is **UNAVAILABLE, NOT PASSED**.
* CI regression with a deliberately exiting fake upstream command
  proves that synthetic code-139 is classified as unavailable; code 42
  must fail, and authentic graphs cannot request the exception.

No algorithm default/production promotion, no upstream source patch
and no change to the previously established scientific claim boundary.
A passing 15-job matrix **does not imply 15 successful original-O'Reach
external comparisons**. For valid external superiority comparisons
use only those real original-O'Reach methods actually measured.


## Recovery from O-Reach comparator incompatibility (2026-10-22)

The prior synthetic-only SIGSEGV tolerance was an honest fail-open *experiment* but left six external comparisons unavailable. The new compatibility path aims to **measure**, not silently skip, those comparisons. It addresses two incompatible input assumptions identified in the original pinned O-Reach source:

* `lib/reachability/oreach.cpp::sampleSupportsFromLevels` advances the candidate iterator by `NUM_SUPPORTS` and indexes the resulting candidates without first establishing that at least that many exist. On the `generated_blocks` topology all weak components are below the original `n/10` large-component threshold, so the default sampling criteria can return no candidates. This is a source-supported plausible cause of the observed 139; the exact runtime fault location was not established by a native backtrace.
* `app/reachability.cpp` constructs the O-Reach index directly from the input directed graph. Its extended topological indexes assume a DAG. The `generated_communities` family intentionally includes cycles. It must not be run through original DAG indexes without SCC condensation.

**Compatibility contract:** for the three synthetic graph families only, compute a **deterministic, exact SCC quotient DAG**, translate **every heldout original query** into its SCC pair, check original-vs-quotient truth independently by BFS on both graphs, and run the **unmodified SHA-pinned O-Reach binary with `--support 0`**. This disables only the source-unsupported support-vertex selection; interval labels and original pDFS/pBiBFS query fallbacks are still executed. The two authentic O-Reach instances keep the original raw graph, original query file and default support configuration.

Proof/regression: enumerate all 512 simple three-node digraphs including self-loops and directed cycles; check all 9 pairwise reachability outcomes on each quotient. Check complete heldout query count and original vs converted positive count, and persist graph/vertex-map/query SHA256s for independent replay. A distinct output verifier requires **15/15 genuine original-O-Reach measurements** in this revised matrix. The previous crash-tolerance switch remains a negative-test mechanism but is no longer enabled by CI.

**Crucial scientific qualification:** original and compatible O-Reach configurations are **different algorithms/settings** for performance interpretation. An original graph with N vertices and a quotient with M SCCs require different memory and build work. Record Python SCC construction time independently and do not misrepresent O-Reach's *internal* index initialization or process RSS as full application cost including that preprocessing. Synthetic results must be labeled `original_pinned_binary_support0_scc_quotient`, not published-default O-Reach or matched-index-memory results. Default promotion still NO-GO independent of run success.

Current repair branch will be accepted only after live original binary CI shows genuine measurements on all graph/seed combinations; until then these comparator claims remain UNVERIFIED.

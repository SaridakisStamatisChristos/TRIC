# TRIC Phase XXII — Cross-Graph Replication and Actual Cold-Start Cost

Date: 2026-10-22. Status: preregistered research experiment, not an algorithm promotion.
Base: Phase XXI PR #20, exact unmerged head. Existing defaults and previous evidence stay unchanged.

## What this phase is intended to test

Phase XXI reported ~3.4–3.5x improved **query-only** latency for cache+pivot+indexed reachability on the matched hot-source class on the original arXiv and Kronecker graphs, but the broader result is unresolved. Phase XX's cache+plain-DFS fallback failed badly. This experiment directly challenges the stronger claim that the cache's extra memory and build time repay themselves on repeated source-conditioned workloads.

## Independent research matrix

Five *original published* O'Reach graph instances, not new synthetic networks:

| Dataset | Vertices | Directed edges | Family |
|---|---:|---:|---|
| example / arXiv.metis | 6000 | 66707 | citation |
| kron_logn12 | 4096 | 116952 | RMAT / Kronecker DAG |
| go_sub | 6793 | 13361 | small biological ontology |
| pubmed_sub | 9000 | 40028 | biomedical |
| delaunay_n15 | 32768 | 98274 | geometric DAG |

Source: original O'Reach published instance catalogue: https://oreach.taa.univie.ac.at/.
The SHA-pinned, unmodified O'Reach implementation is the comparison source. Do not equate the three query/training seeds *on one fixed graph* with independent graph samples.

For each graph × seed (20261022, 20261023, 20261024) × workload (matched 80%-hot, uniform, shifted 80%-hot from disjoint sources), use exact identical 2400 heldout pairs per method, independently train on 500 other pair draws, deterministic first-party pivot selection, 2 MiB cap for retained hot bitset vectors, and 11 candidates / pivot budget 5. The original benchmark runs native TRIC/O'Reach comparisons including control methods and preserves all data hashes.

**Expected matrix:** 15 graph-seed jobs and 45 different heldout test sets. Graph sources are five independent graph *instances* but some are related methodologically.

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

These thresholds are engineering acceptance criteria, not formal confidence bounds. Shared GitHub runners and two trial replicates are exploratory; require dedicated or independently repeated runs before marketing/publishing generalized superiority.

## Closest prior art and novelty state

Source-selective transitive-closure bitmaps, cached BFS sources, SCC condensation, interval labels, pivots, and bidirectional traversal are known mechanisms. A composite is a legitimate engineering specialization, **not an original exact-reachability primitive**. Primary references include Hanauer et al., *O'Reach: Even Faster Reachability in Large Graphs*, SEA 2021 (https://doi.org/10.4230/LIPIcs.SEA.2021.13) and Zhang et al., *Indexing Techniques for Graph Reachability Queries*, ACM Computing Surveys (2025, https://doi.org/10.1145/3776737).

## Reproducibility and outputs

`.github/workflows/research-phase22.yml` builds original pinned upstream from source and runs the complete 5 × 3 matrix. It preserves graph checksum, compiler, raw class-level input, exact measurements, independent test logs, original O'Reach CSV, and two fresh-process result files per mode/horizon/trial under each dataset × seed artifact.

Standalone test: `cd tric_research && python -m unittest -q test_phase22_lifetime`.

**State at creation:** specified and implemented, **NOT YET externally replicated**. After 15 CI jobs complete, append actual positives/negative cases, paired trial medians and final promotion decision, with exact SHA. If jobs fail, preserve evidence and repair test defects rather than weakening assertions.

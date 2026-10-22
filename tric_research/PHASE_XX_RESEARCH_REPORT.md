# TRIC Phase XX — Paired external hot-source reachability challenge

Date: 2026-10-22. Draft research artifact, stacked on Phase XIX hot-source PR #18.
Prior versions, earlier branches, default algorithms and plugins remain unchanged.

## Problem contract and risk

Does the **train-only exact source-hotset bitset cache** beat existing fully
compiled TRIC indexed variants and pinned original O'Reach when all systems
receive exactly the SAME heldout queries on original graph sources?

This is deliberately a falsification study. The source-hotset mechanism is
**established selective materialized transitive closure**, not a novel graph
reachability algorithm. Synthetic wins against DFS from Phase XIX do not imply
wins against O'Reach or the best TRIC indexed fallback.

## Experimental setup

Original upstream O'Reach source SHA:
78b3e326bbb021b7ee225ab605a4cdd074fa1d93
Datasets: original arXiv METIS example and published kron_logn12.

For each source, select 8 distinct training hot sources and 8 disjoint
distribution-shift test hot sources deterministically without consulting
heldout queries or reachability answers. Training has 500 source-target pairs
and 80% hot-source probability. Each evaluation class has 2400 heldout pairs:
matched hot sources, uniform sources, and disjoint shifted hot sources.
Same independent training set and graph reused for the three evaluation
classes. The cache cap is 2 MiB of retained vector data, excluding temporary
scratch, graph storage and allocator metadata. Cross-method comparisons
are NOT matched for total RSS or independent index budgets.

Compare exactly these native arms:
- hot-source cache with exact DFS fallback and plain-DFS paired control;
- original TRIC compact+trained-pivots-topo and compact+trained-pivots-bidir;
- original TRIC outcome-blind learned selector;
- unmodified O'Reach pDFS and pBiBFS at pinned upstream SHA.

Run 15 position-rotated TRIC repetitions; 14 alternated cache/DFS
repetitions; five upstream O'Reach executions. Sample on same graph and
same query pairs, but in separate processes and timed loop layouts.
O'Reach classifies any file ending in .query.m.txt as mixed based only on
its file name. This DOES NOT claim a 50:50 ground-truth class composition.
The independent BFS ground truth is included in the query file, with the
observed positive count in every result. O'Reach's individual answers
are not independently exported/verified in this original upstream driver.

Track exact retained cache vector bytes, cache construction time,
TRIC pivot/index build times, Python pivot fitting cost, upstream O'Reach
reported initialization time and process max resident set. These are
separate partial cost categories; summing them without a common deployment
model would misrepresent an end-to-end index budget.

All sources, seed, query files, input fingerprints, compiler versions,
raw per-repetition latency samples, checksum checks and upstream CSV
must remain downloadable from Actions artifacts. Reject incomplete
upstream results and truth-checksum disagreements rather than hiding errors.

## Evidence hypotheses

H1: matching source reuse helps versus plain DFS (supported only by
Phase XIX synthetic DAG evidence).

H2: matching source reuse beats best currently indexed TRIC (unverified).

H3: matching source reuse beats both O'Reach query methods (unverified).

H4: cold index/build costs amortize in real sustained workloads
(unverified; Phase XIX reported algebraic projections).

H5: uniform or disjoint shifted-source queries largely erase the advantage
(falsification objective). A 1.09x isolated shifted-class timing with
almost no hits is suspicious for measurement noise, not proof of a
generalized index improvement.

## Primary literature / prior-art boundaries

Hanauer, Schulz, Trummer. O'Reach: Even Faster Reachability in Large Graphs.
SEA 2021. https://doi.org/10.4230/LIPIcs.SEA.2021.13
Source: https://oreach.taa.univie.ac.at/

Zhang, Bonifati, Ozsu. Indexing Techniques for Graph Reachability Queries.
ACM Computing Surveys 58(6), December 2025, DOI:
https://doi.org/10.1145/3776737
33 indexing techniques show trade-offs among preprocessing, size,
query time, reachability result and structural graph families.

Zhang, Gan, Yang. MLRQ: an efficient labeling scheme for reachability
queries on reduced DAGs. November 2025, DOI:
https://doi.org/10.1007/s44443-025-00310-0
Its larger, 18-dataset, million-query-per-regime comparisons remain
a high bar for independent generalized SOTA evidence.

## Research-audit gates

- Correctness: verify exact original source SHA, stable pair inputs and
  independent BFS + native checksums on Phase XX head.
- Reproducibility: preserve a complete artifact before claiming passed.
- Novelty: prior art found for SCC, topological, interval, 2-hop, and
  selective hot-source cache mechanisms.
- Strong external comparative SOTA: NO-GO from this two-graph pilot,
  even if it measures a narrow class-specific win.
- Publication: independent graph populations, matched memory and end-to-end
  lifetime comparisons, dedicated hardware, robust errors and manuscript
  theorem audits still needed.

Reproduce with the paired CI workflow research-hot-source-external.yml.
Execute the full experiments rather than extrapolating million-query claims.
Append observed results and negative cases after the CI jobs finish.

This remains a draft, unmerged evidence branch.

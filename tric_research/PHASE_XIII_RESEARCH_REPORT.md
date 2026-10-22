# Phase XIII — Topological Fallback Ablation and Cross-Graph Qualification

## Research decision
Phase XII's compact-plus-trained-pivots path substantially improved the project's
original query latency on one arXiv instance. It still trailed published O'Reach.
The next test is deliberately **falsifiable**: does a cheap, known topological
necessary condition speed up the queries that evade compact certificates and
trained pivots, or does its branch overhead make measured wall-time worse?

Do not describe topological-order pruning as original. It is a standard DAG
reachability property, and O'Reach already exploits more sophisticated
topological and supportive-vertex conditions.

## Phase XIII intervention
Given a static directed graph, collapse strongly connected components to
a DAG D and assign each component a topological rank r. When a reachability
query (s,t) reaches an as-yet unvisited component x with r(x) > r(t),
skip exploration from x. For every DAG edge (u,v), r(u) < r(v);
consequently every path starting from x visits components ranked above r(x).
No path can then reach t. The pruning rule **cannot change an answer**.

The experiment retains:
- `compact_plain`: the Phase XII plain SCC search after its certificates;
- `compact_topo`: exactly the same index, DFS and work accounting with only
  the topological-rank test added;
- `compact_pivots`: Phase XII's certificates, trained pivot probing and
  plain search;
- `compact_pivots_topo`: identical certificates/pivot order, but the
  topological fallback replaces plain DFS.

The preexisting four-permutation `compact` guided DFS remains as a separate
measured control. The topological ablation uses no new index arrays; it reuses
the already-built `topo_rank_`. A worst-case DFS remains O(C+M) time for C
condensation components and M condensation arcs; the added comparison is
O(1) per examined target-neighbor candidate. Memory is unchanged apart
from benchmark-result counters.

## Acceptance / rejection criteria
1. Zero incorrect reachability answers vs independent native graph traversal;
   pass existing exhaustive three-vertex graphs and cyclic, long-chain,
   giant SCC, and dense DAG stress tests.
2. Each topological variant must have the exact same query checksums as its
   paired plain version; pivot rescues and hybrid fallback counts must be
   identical.
3. Topological-only scan-edge count must not exceed the corresponding plain
   scan-edge count on the same query workload.
4. Report **actual CPU nanoseconds per query** for both variants. A reduced
   edge count with worse latency is a negative result, not a success.
5. Compare against the **original pinned** O'Reach executable without
   changing its algorithms or query file.

## Phase XIII dataset matrix
The PR benchmark runs the pinned O'Reach bundled arXiv example (6,000
vertices, 66,707 arcs) and the authors' published `kron_logn12`
(4,096 vertices, 116,952 arcs), using the authors' archive URL and refusing
silent substitutions. Both sources were successfully exercised in real CI.
For each dataset, the same three deterministic train/test seeds drive TRIC
and O'Reach. Only a **within-dataset** paired ratio is meaningful; do not
pool raw nanoseconds or treat the seeds as independent graph replications.
The multi-graph default PR matrix is deliberately limited to sources that
have actually been reachable, not an exhaustive reproduction of O'Reach.

These are still small-to-medium graphs. Published large-graph scaling
(`kron_logn16`, 65,536 vertices, 2,456,071 arcs; others) is an explicit
future milestone and will need resource-capped, stratified, separately
budgeted runs. Our current `read_metis` cap permits up to 150,000 vertices,
but the training and Python graph representation may become a bottleneck.

## Known limitations and novelty boundary
- O'Reach and TRIC still lack measured matched resident-memory/index-budget
  equality, and there is no end-to-end construction amortization match.
- The protocol's uniformly drawn pairs can yield almost exclusively negative
  queries on low-reachability graphs. Positive-only, negative-only, mixed and
  workload-skew experiments are missing. O'Reach's authors publish
  additional query distributions; these should be the next controlled study.
- CI runners are shared and noisy; repeat on dedicated pinned hardware.
- TRIC has an independent native oracle; the upstream O'Reach executable
  reports aggregate CSV metrics, so its per-query answers are not independently
  re-audited here.
- The first Phase XIII CI matrices found HTTP 404 from the authors'
  published URLs for `go_sub`, `pubmed_sub`, and `delaunay_n15`.
  Those graphs are excluded from the default PR matrix. They remain
  selectable manually for source diagnosis but are **not** benchmarked
  successfully. No replacement graph is relabeled as any of them.
- The native hybrid variants alternate plain-first and topology-first
  execution on successive repetitions; fixed call order could otherwise
  favor the later method through a hotter cache. Dedicated-machine
  repetition and additional positive/mixed query workloads remain necessary.
- These changes test engineering trade-offs. Neither a mathematical novelty
  claim nor a cross-system superiority claim is authorized by this phase.

## Reproduction
```bash
cd tric_research
python -m unittest -q test_compact_reachability test_closure_index test_oreach_ci
```
The paired workflow runs the complete suite and the three graph jobs.
The raw comparisons contain `tric.compact_topo` and
`tric.compact_pivots_topo` alongside both original Phase XII controls.

## Attribution
O'Reach (Hanauer, Schulz, Trummer, SEA 2021):
https://doi.org/10.4230/LIPIcs.SEA.2021.13

O'Reach published instances: https://oreach.taa.univie.ac.at/

GRAIL and PReaCH are relevant antecedents of interval and DFS pruning.
No statement of algorithmic first-use is made.

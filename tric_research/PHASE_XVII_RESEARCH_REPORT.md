# Phase XVII — Train-only, outcome-blind fallback routing pilot

## Testable goal
Select between the existing exact topological DFS fallback and exact
bidirectional SCC-BFS without using the query's unknown reachability answer.
The decision must be cheap, included in native timings, trained on
**uniform-only** training queries and evaluated on the same heldout
uniform, positive, negative and balanced queries as Phase XV.

Phase XVI refuted unconditional two-sided interval pruning as a general
optimization. We keep the original unpruned fallback intact, together with
the failed experimental pruned candidate for independent comparison.

## Offline training, online features
The benchmark input optionally appends a count and independent training
pairs after heldout pairs. The earlier on-disk format with no trailer
remains supported. The external harness supplies the same 500 uniform
training queries already used for pivot training; the heldout query
pairs are supplied separately, and heldout labels/results are never
consulted when selecting the route.

Each of nine predeclared policies maps cheap existing condensation
metadata to a route. Policy 0 always selects topological fallback; 1
always bidirectional fallback. The remaining policies dispatch on
source SCC outdegree, destination SCC indegree and SCC-topological-rank
gap. No query truth label, search result, or heldout statistic enters
the dispatch rule.

For each policy, the trainer runs the **full certificate → trained
pivot probes → fallback path**, including actual dispatch overhead,
over the 500 training queries using nine balanced-order C++17
timing repetitions. It verifies **each training answer** against an
independent graph-search oracle and chooses the lowest-median-latency
policy. Report every candidate's training median, selected ID and
total training wall time. This is a small, noisy, train-only search,
not a calibrated or theoretically optimal decision tree.

For heldout pairs, the complete selector checks only cheap SCC
metadata and calls **one already exact** fallback. Thus exactness is
preserved for every possible policy choice; worst-case bound remains
O(C+M) for a condensation graph with C vertices and M arcs.

## Fairness and risk controls
- The selector's runtime branch and both possible search paths are
  included in the heldout per-query timer.
- Baselines are original Phase XIII topological-only DFS, original
  Phase XIV bidirectional BFS, and the Phase XVI interval-pruned
  negative-result candidate; all share the same certificates and
  pivot work.
- Five hybrid arms rotate across **15 native repetitions**, each
  appearing three times in each timing position.
- The graph, three seeded splits per class, 1,200 query pairs per
  split, pinned original O'Reach benchmark and resource limitations
  are held constant within each graph/seed/class.
- Independent BFS checksums and identical pivot probe/rescue/fallback
  counters are mandatory.
- Absence of optional training input defaults to unconditional
  bidirectional fallback to keep older synthetic/naive native
  benchmark callers compatible.

## Adversarial failure possibilities
1. Tiny training batches produce unstable "winners" in sub-microsecond
   work, especially on shared GitHub-hosted runners.
2. A policy fitted on uniform training may degrade strongly on
   positive/negative-biased test classes.
3. The model may collapse to an unconditional baseline, offering no
   meaningful dispatch improvement.
4. Graph topology may make outdegree/topological distance a weak or
   misleading predictor of method cost.
5. Repeated training choices from one fixed source graph are not
   independent graph replications.

These are **failure results**, not reasons to hide the selected policy.
No selector should become the production default without repeated,
cross-graph, resource-accounted improvement.

## Evidence and novelty
Preprocessing, interval labels, pivot certificates, fallback search,
topological DAG heuristics and trained algorithm portfolios are
established prior art. No new reachability theorem or SOTA claim
is made. The first question is whether this **within-TRIC** method
performs well under the disclosed conditions.

Prerequisites: Python 3.10/3.13 all research tests green, C++ native
and O'Reach CI on both source graphs, outcome-stratified per-seed
`phase17_summary.json` preserving timing and training decisions.

Run `python -m unittest -q test_compact_reachability test_stratified_queries test_oreach_ci`
in `tric_research`, and inspect `.github/workflows/research-oreach.yml`
for the full two-graph training/heldout matrix.

**Evidence state at commit:** implementation and protocol specified;
empirical claims withheld pending CI.

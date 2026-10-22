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

**Evidence state:** exactness and paired tests verified by GitHub CI.
A narrowly positive outcome-conditioned latency effect was observed;
the general unconditional "selector beats both baselines" hypothesis
was not supported.

## Executed two-graph pilot (GitHub Actions 2026-10-22)

At code SHA `8a01f7744e92a697c2e3b2ed1b4f6bf2de1a4c4a`:
- [Expanded Python 3.10 + 3.13 CI run 39753430214](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39753430214) — success for both versions.
- [O'Reach paired research CI run 39753430016](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39753430016) — success on both original data sources.
- [Original arXiv example artifact](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39753430016/artifacts/12414691945).
- [Published Kronecker artifact](https://github.com/SaridakisStamatisChristos/TRIC/actions/runs/39753430016/artifacts/12413779481).

**Interpretation:** ratios below are medians across **three paired
seed-specific ratios** of the preceding original method's measured native
query latency divided by the new learned selector latency, **including
online dispatch**. >1 means selector faster; <1 means original wins.

| Source graph | Query class | Old bidir / selector | Old topo / selector | Selector beats bidir (seeds) |
|---|---|---:|---:|---:|
| arXiv | uniform | 1.0358× | 1.1368× | 2/3 |
| arXiv | positive | 0.9943× | 1.6122× | 1/3 |
| arXiv | negative | **1.1457×** | **0.8471×** | 3/3 |
| arXiv | balanced | 1.0496× | 1.2421× | 3/3 |
| Kronecker | uniform | **0.9663×** | 7.8789× | 1/3 |
| Kronecker | positive | 1.0214× | 9.6355× | 3/3 |
| Kronecker | negative | **1.0901×** | 1.2053× | 2/3 |
| Kronecker | balanced | 1.0024× | 8.7502× | 2/3 |

The method improves the *negative vs bidirectional baseline* on both
graphs' three-seed medians. It nevertheless remains **worse than the
topological-only fallback on arXiv negative-only queries** (0.8471×).
On Kronecker uniform queries it regresses vs the original bidirectional
baseline. There is **no unconditional superiority** even in these two
pilot datasets and no novelty claim.

### Selected policy and training reproducibility

Training candidate IDs are fixed in source:
0 = always topo, 1 = always bidir, 2 = topo if source outdegree <=1,
3 = topo if target indegree <=1, 4 = topo if sum of those degrees <=2,
5 = topo if topological rank gap <=C/8,
6 = topo if gap <=C/2, 7 = topo if gap >=C/2,
8 = topo if sum of degrees >=8.

All twelve Kronecker runs (4 strata × 3 splits) selected policy **4**.
arXiv selection varied by seed/stratum—most often policy 3,
sometimes 4 or 5—**even though the uniform training query pairs for a
given seed are identical across the heldout classes**. That variation
is a practical warning that train-batch timing noise, system load and
cache state can affect fitted policies on hosted runners. Do not claim
an invariant learned decision boundary.

The observed **incremental offline selector fitting cost** was about
6.1–9.0 milliseconds for arXiv, and about 4.4–13.1 milliseconds
for Kronecker. This excludes the existing Python pivot-training time
and SCC index-building time; it is **not included in reported query-only
ns/q**. It must be paid once per offline fit and amortized over
many future queries; on a mere 1,200 heldout queries it overwhelmingly
dominates the measured nanosecond-level query savings.

For instance, 6,000,000 ns additional offline training divided by
40 ns/query benefit requires **150,000 future similarly distributed
queries** merely to break even, excluding additional common build
costs. This is an *illustrative ratio*, not a measured throughput
forecast: fit time and query savings vary across seeds and workloads.
Where the selector is slower, it does not break even against that
baseline.

### Evidence and recommendation

**PASS:** exactness regression, independent BFS oracle, training/heldout
separation, per-method identical pivot/certificate fallback counts,
and both external graph/stratum CI jobs.

**TENTATIVE:** a low-cost online classifier may reduce negative-query
latency while preserving positive-query throughput in some workloads.

**NO-GO:** unconditional adoption in core code, low-volume query
workloads, cross-graph superiority over original O'Reach, publication
readiness, or original algorithmic novelty.

**Next discriminating experiment:** many more independent real graph
families, separately controlled target-positive rates, policy stability
on dedicated hardware, *end-to-end amortized workload throughput*
including the selector fit and index-building overhead, and
better source/target feature calibration with clear data budgets.

# TRIC Phase VIII — Exact Cost-Aware Ordered Pivot Selection

**Status:** implemented, tested; publication novelty **not established**. 2026-10-21.

## Motivation and formal objective

Phases I–VII optimize **certificate coverage**, i.e. how much query weight at least one selected pivot can answer. They do not minimize the cost of probing the pivots in an ordered index, nor the query-specific cost of an uncaught fallback. A high-coverage pivot set can be slower than no index when the fallback is already cheap. This phase treats query evaluation as the real optimization target.

Given a finite candidate pool of `c` precomputed, exact certificate pivots, `m` workload queries `q`, a weight `w_q >= 0`, a query-specific fallback work estimate `f_q >= 0`, a pivot-specific check cost `a_p >= 0`, and a budget `k<=c`, choose an **ordered list** `sigma` of at most `k` distinct pivots. Let `H_q` be the subset of pivots certifying `q`; `j_q(sigma)` is the first chosen pivot belonging to `H_q`, or infinity. The objective is:

```
C(sigma) = sum_q w_q * (
    sum_{i=1}^{min(j_q(sigma), len(sigma))} a_{sigma[i]}
    + (f_q if j_q(sigma) == infinity else 0)
)
```

This uses the *actual* certificate bitmap semantics from TRIC, which are exact (positive or negative). It optimizes a **supplied deterministic proxy**, not measured end-to-end CPU time. The optima are unconditional only for this cost model and finite training workload.

## Exact subset algorithm

Let `U(S)=sum_{q:H_q∩S=∅} w_q` and `F(S)=sum_{q:H_q∩S=∅} w_q*f_q`. For any prefix set S, the next pivot p contributes exactly `a_p U(S)`; queries already certified never examine p. Therefore, with `D[S]` the minimum probe work over permutations of S:

```
D[empty] = 0
D[S union {p}] = min(D[S union {p}], D[S] + a_p * U(S))  for p not in S
OPT = min_{|S|<=k} (D[S] + F(S))
```

The recurrence holds by optimal substructure: the incremental cost depends on the prefix *set* S, not its internal order; all prefixes to a given S have the same remaining queries. Every ordered distinct-pivot list appears as a path through the subset lattice. A parent pointer reconstructs one optimal order. This is a full mathematical correctness proof by induction on |S| for the finite deterministic objective.

For each query we store its certifier mask `H_q` as `c` bits. Aggregate `w_q` and `w_q*f_q` by equal masks. A subset-zeta transform then computes the sums over masks contained in a given set. Since `q` is uncovered by S iff `H_q⊆(all\S)`, `U(S)` and `F(S)` become O(1) table lookups. Runtime `O(cm+c*2^c)` including extraction of certifier masks, and memory `O(m+2^c)`. Arithmetic uses expected constant-time Python numeric operations; numbers are checked nonnegative and finite at input. Implementation explicitly caps candidate count at 19 by default. For each tested query, only its first hit or fallback executes.

## Tests and experimental protocol

- `python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact test_frontier_compact test_ordered_probe`
- Phase VIII test methods: exhaustive all assignments of three query masks for `c=1..4`, all budgets, against enumerations of all permutations; 180 independent seeded randomized weight/cost cases with brute-force oracle; randomized graph integration including cyclic graphs, negative certificate correctness and ordered evaluation; no-index dominance and validation tests.
- Combined suite **42 tests** passed locally in CPython.
- `python benchmark_ordered_probe.py` writes `phase8_benchmark.json` with every raw evaluation. No network, no third-party Python dependencies.
- 24 held-out synthetic evaluations: graph families random DAG, chain, disconnected blocks, and SCC communities; two graph seeds per family; train/test distribution pairs uniform/uniform, hot/hot and hot/uniform. Graph size 150; candidate pool 11 high-degree vertices; budget 5; 550 training queries; 1300 independent test queries. Hot workloads share the same fixed hotspot population, but independently draw actual samples.
- Three comparators under the *same 11 candidate pivots*: exact ordered cost, weighted coverage greedy (select five), and no-index BFS. Training estimated fallback cost = `1+BFS edge scans`, per pivot probe cost = 1 synthetic work unit. Test reports both held-out proxy costs and independently timed CPython inference, not conflated.

## Observed outcomes

Across all 24 runs:

- Median per-case `ordered / greedy` **held-out proxy cost ratio**: `0.737`; 23/24 were at most greedy, one slightly worse (`1.004` ratio).
- Median per-case `ordered / no-index BFS` proxy cost ratio: `0.501`; 23/24 beat BFS by proxy, one slightly worse (`1.062`).
- Median per-case `greedy / no-index BFS`: `0.712`; greedy worse than BFS on 12/24 cases despite better certificate coverage.
- Median per-case wall-time ratio for ordered vs greedy: `0.601` in this Python implementation, and `0.529` vs pure BFS; these are highly implementation, size and locality dependent. Summarize medians of ratios, **not ratios of medians**.
- Candidate index build time and training/selection time are recorded separately: median pivot precompute ~0.00019 s; median train-mask+fallback estimation+optimizer ~0.0078 s per run. Do not interpret query-only improvement as amortized throughput superiority.
- Every observed certificate answer matched an independent BFS reachability oracle in the graph integration tests. Synthetic graph families and workload data do **not** establish validity on large real networks.

## Novelty and related work (adversarial)

- Hanauer, Schulz and Trummer, **O'Reach: Even Faster Reachability in Large Graphs**, SEA 2021, DOI:10.4230/LIPIcs.SEA.2021.13. Our ternary positive/negative certificates are pre-existing supportive-vertex observations; O'Reach already supplies compiled C++ and standard graph benchmark inputs.
- Feige, Lovász, Tetali, **Approximating Min-Sum Set Cover**, APPROX 2002 and Algorithmica 2004, DOI:10.1007/s00453-004-1110-5. Optimizing a probe order to minimize the first covering position is closely related to classic minimum-sum set cover. This Phase VIII combination is a **limited candidate-pool exact engineering baseline**, NOT a claim of the first exact or ordered coverage algorithm.
- Al-Thani et al., **Minimum Cost Adaptive Submodular Cover**, *Mathematics of Operations Research*, published online June 4, 2026, DOI:10.1287/moor.2024.0548. Adaptivity and query/test costs are well established; TRIC uses a deterministic, nonadaptive fixed permutation.
- Our early-stop/fallback objective adds application-specific constants and option to stop early, but this alone is insufficient for a novel-method publication claim.

## Reviewer objections and gates

1. **Novelty:** known reachability certificates plus a subset DP / min-sum set cover formulation. `UNRESOLVED / likely incremental`.
2. **Comparative performance:** O'Reach has not been built, and no compiled O'Reach comparisons have been executed. `NOT MET`.
3. **Statistical significance/external validity:** 24 small synthetic cases, only two graph seeds per family. `NOT MET` for generalization.
4. **Memory/build accounting:** training optimizer cost included in raw data but not yet integrated into amortized query throughput. `PARTIAL`.
5. **Correctness:** exhaustive independent exact-ordering tests, graph differential tests and existing suite, but not machine-checked. `SUPPORTED in tested scope`.
6. **Publication:** premature to claim a novel algorithm or SOTA graph-index improvements.

## Next experimental gate

Download/build O'Reach at a **pinned commit** with C++ compiler flags; use O'Reach's published real-world graph corpora and query protocols (positive, negative, mixed, random), fair memory caps and matched preprocessing budgets. Compare: BFS alone, O'Reach, TRIC coverage-pivot ordering, TRIC cost-optimal ordering, and simple degree-ranked pivot ordering. Run repeated, randomized paired trials and include distribution-shift holdouts. Only then decide if a strong experimental paper exists.

**Reproduction note:** existing phase IV–VII PRs are intentionally still open and unmerged. Phase VIII is intended as a stacked branch based on Phase VII and does not revise old results or their archives.

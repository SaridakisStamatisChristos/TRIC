# TRIC Phase V — Frontier-Width Exact Optimization

**Research date:** 2026-10-21  
**Status:** Algorithm specified, implemented, locally tested; global literature novelty unresolved.  
**Scope:** Weighted maximum partial stabbing of a family of one- or two-interval subsets of a finite ordered vertex backbone, including SCC-compressed digraph-backbone certificates from Phase IV.

## Motivation

The Phase III selector enumerates all orientations for `r` distinct two-interval signatures, then solves a weighted single-interval hitting problem. Its worst-case exponent is `2^r`, even when separated two-interval queries are far apart and do not simultaneously impose coupled decisions.

Phase V replaces global orientation enumeration with a left-to-right **frontier-state dynamic program**. The idea exploits locality of the two-interval certificate representation, not new reachability-certificate rules. SCC condensation, supportive-vertex reachability certificates (O'Reach), and generic frontier/pathwidth dynamic programming are existing concepts.

## Definitions

Let the backbone have `h` candidate positions indexed `0..h-1`. A weighted query is `(I, weight)` where `I` is the union of at most two disjoint inclusive integer intervals and `weight >= 0`. Choose **exactly** `k` distinct positions minimizing the total weight of unhit query unions (the score corresponds to unanswered-by-pivot reachability queries, not to incorrect reachability answers). All positions have unit budget cost. Repeated identical signatures can be aggregated by summing weights.

For every distinct two-piece query `j`, let `A_j=[a_j,b_j]`, `B_j=[c_j,d_j]` with `b_j < c_j-1`. A bit for j is materialized at position `b_j` and retired at position `d_j`. Let

`w = max_{p=0..h-1} #{j: b_j <= p < d_j}`.

This is the number of distinct two-piece queries whose first interval has ended but whose second has not yet ended. Call it **frontier width**. It can be much smaller than the total `r` even on inputs where `r` grows linearly with backbone size.

## Algorithm

Sweep positions `p = 0,1,...,h-1`. A dynamic-programming state stores `(count, last, mask)`, where `count` is the number of chosen positions so far, `last` is the largest chosen index or `-1`, and `mask` holds, for each query j in the live frontier, whether its first interval was hit.

At each position, branch on choosing or skipping the pivot, updating `count` and `last`. Process all one-piece queries ending at p: query `[a,p]` is hit iff `last >= a` at that moment. At `b_j` store the bit `last >= a_j`. At `d_j`, charge query j's weight iff both its stored bit is false **and** `last < c_j`; then retire the bit. Live bits are assigned **recycled compact slots**, with second-end events processed before first-end events at each position. Consequently a state mask uses at most `w` bits, even if `r` is very large. Remove transitions that cannot meet the exact final count k. For identical state keys keep the minimum cost and a traceback predecessor.

Always return the minimum-cost terminal state whose count equals k. Empty-signature queries contribute unavoidable loss; zero-weight signatures are dropped. Two intervals that overlap or touch are normalized to a single interval.

## Correctness argument (proof for the defined computational problem)

**Lemma 1: Last-point criterion.** Immediately after considering position p, for any interval `[a,p]`, a chosen pivot lies in it exactly when `last >= a`. All selected positions are <= p, so `last` is sufficient.

**Lemma 2: Complete state.** After processing p, every one-piece query that ends at or before p has been charged exactly if unhit. A two-piece query whose second interval ended has also been charged exactly if unhit. Every remaining two-piece query that has passed its first end but not its second end can influence future cost *only* through the Boolean fact that its first interval was hit. The `mask` stores exactly those facts; all future one-interval hit tests use `last`. Therefore two partial selections with equal `(count,last,mask)` have identical feasible completions and identical future incremental loss.

**Lemma 3: Bellman optimality.** Base state is `(0,-1,0)` with cost equal to all empty-signature query weights. All feasible k-subsets correspond bijectively to choose/skip sequences along the sweep. By Lemma 2, pruning the higher-cost prefix for an equal state cannot eliminate a better completion. Each interval contributes its uncovered weight once, when its last opportunity to be hit ends. Induction over the sweep establishes the returned minimum loss is globally exact. Stored traceback choices reconstruct a k-subset attaining that loss.

**Theorem (parameterized running time):** At a sweep boundary there are <=(h+1)(k+1)2^w possible states. Every query contributes O(1) end events; the straightforward Python implementation processes at most two decisions per state per position and its event list. Thus time is `O(h(k+1)2^w (h+q))` in the unit-cost RAM model for fixed-precision weights, ignoring hash-table amortized constants; an execution-independent deterministic dictionary or sorted-map implementation adds standard comparison/log factors. Objective-only memory is `O(h(k+1)2^w+q)`; the implementation's complete traceback records occupy up to `O(h^2(k+1)2^w+q)` additional space. This is fixed-parameter tractable in frontier width w. It remains exponential when w is large.

The statement is a human-checkable proof argument, **not** formal verification by Lean/Coq.

## Verification

From the `tric_research` directory:

```shell
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp
python benchmark_frontier.py > phase5_benchmark.json
```

The tests include: a 1,500-signature width-one compact-slot regression; all pairs of permitted query signatures on each domain size h=1..4 and every pivot budget; 240 randomized weighted instances compared to Phase III's independent orientation exact solver *and* an enumerated subset oracle; ten separated queries constructed by the Phase III Vertex Cover reduction; 225 random directed cyclic graph instances (multiple budgets per graph) compared to direct per-pivot certificate oracles and brute-force optimum; invalid-input/state-cap conditions.

All 24 combined local unittest cases passed on Python 3.13.5. Test count is unittest method count, not the number of examined combinations.

## Reproducible exploratory measurements

The accompanying `phase5_benchmark.json` has the machine details, five raw timings per method/case, and benchmark parameters. Median times below are from this **local Python** run; these are not externally replicated or compared with O'Reach:

| Family | r | w | Frontier (ms) | Phase III orientation (ms) | Max DP states |
|:--|--:|--:|--:|--:|--:|
| Separated | 4 | 1 | 0.143 | 0.497 | 29 |
| Separated | 6 | 1 | 0.440 | 5.842 | 65 |
| Separated | 8 | 1 | 1.022 | 47.869 | 110 |
| Separated | 12 | 1 | 3.948 | omitted | 243 |
| Separated | 18 | 1 | 13.258 | omitted | 540 |
| Overlapping | 4 | 4 | 0.132 | 0.429 | 36 |
| Overlapping | 6 | 6 | 0.821 | 4.725 | 213 |
| Overlapping | 8 | 8 | 5.933 | 39.283 | 1,225 |
| Overlapping | 10 | 10 | 38.048 | omitted | 6,613 |

The orientation baseline is omitted above r=8 because its exponential runtime would dominate this small exploratory benchmark. The two solvers have identical selection objectives. These synthetic examples deliberately vary w/r and cannot establish typical performance on real query traces.

## Literature/novelty boundary

- Hanauer, Schulz and Trummer (SEA 2021 / ACM JEA 2022), **O'Reach: Even Faster Reachability in Large Graphs** — our certificate primitives are prior art. https://doi.org/10.4230/LIPIcs.SEA.2021.13
- **Indexing Techniques for Graph Reachability Queries**, ACM Computing Surveys, DOI 10.1145/3776737 — broader reachability-index prior art. https://doi.org/10.1145/3776737
- Damaschke, **Refined algorithms for hitting many intervals** (2017), studies refined exact partial-interval stabbing algorithms. https://doi.org/10.1016/j.ipl.2016.11.001
- Rawitz & Shahar, **Partial multicovering and the d-consecutive ones property** (2011), d-interval stabbing and partial covering. https://doi.org/10.1016/j.disopt.2011.05.004
- Acharyya et al., **Constrained hitting set problem with intervals: Hardness, FPT and approximation algorithms** (2024) — related but different constraint structure. https://doi.org/10.1016/j.tcs.2024.114402

**Novelty status: unresolved.** Frontier-state methods are well known across combinatorial DP/pathwidth algorithms. We do **not** claim the generic frontier DP pattern or this width bound is globally new based on the current search. An independent, comprehensive parameterized-complexity literature review is required before turning it into a paper's principal originality claim.

## Scientific next steps

1. Audit the frontier width parameter against broader published special cases of geometric 2-interval stabbing, d-consecutive-ones matrices, and pathwidth-based covering algorithms.
2. Compare exact objectives and resource curves on realistic held-out SCC-backbone query workloads; include `w`, `r`, preprocessing cost, traceback memory and cases where w approaches r.
3. Measure all operational costs with a compiled O'Reach baseline and a compiled TRIC implementation; no superiority claim is presently warranted.
4. Consider a hybrid exact solver choosing between Phase III's orientation enumeration and frontier DP based on input-derived width, state forecasts, and an explicit resource budget. A failed budget cap must be reported, not silently switched to an approximation.

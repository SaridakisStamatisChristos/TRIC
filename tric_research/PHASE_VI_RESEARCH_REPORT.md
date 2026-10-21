# TRIC Phase VI — Exact Budget-Profile Decomposition

**Date:** October 21, 2026  
**Status:** Executed algorithm-engineering experiment. General novelty unresolved; no external SOTA benchmark.

## Problem

Given a finite backbone with positions `0..h-1`, an exact cardinality budget `k`, and a set of nonnegative-weight queries, each certified by a union of zero, one, or two closed integer intervals, find exactly `k` **distinct** backbone pivots minimizing total weight of queries not hit by any selected pivot. On a directed graph, SCC condensation yields these interval sets by existing TRIC Phase IV methods. A query that no pivot certifies contributes an unavoidable constant to the objective. This optimization concerns *coverage by the selected certificates*, not a claim of fast exhaustive reachability queries.

## New implementation: regional budget profiles

For each nonempty positive-weight query's interval union, calculate its **hull** from first interval start to last interval end. Merge hulls that share a position into connected components. Distinct components use disjoint pivot positions, and no positive-weight query is supported in two components. Positions outside all hulls are *free*, certify no positive-weight query, and can absorb any surplus exact-cardinality pivot budget.

For component `i` and budget `b`, calculate the optimal internal uncovered weight `F_i(b)` and one achieving pivot selection. For 1-interval components, use the earlier path-sweep exact optimizer. For two-interval components, choose the earlier orientation enumeration if the count of distinct two-interval signatures is at most two; otherwise use a **new multi-budget frontier profile** that obtains `F_i(0), ..., F_i(k)` in one DP traversal (rather than rerunning the frontier DP once per budget). A caller may force either engine for tests.

Combine profiles by the min-plus recurrence:

`D_0(0)=W_empty`, `D_0(b>0)=+infinity`, and

`D_i(b) = min_{0 <= j <= min(b, |component_i|)} D_{i-1}(b-j)+F_i(j)`.

At termination, consider any budget `b` such that `0<=k-b<=free_count`, and append `k-b` free vertices. Minimize the cost over those feasible budgets. All chosen pivots are distinct and in the original backbone. For cyclic graphs, use Phase IV SCC compression and pad extra original pivots in repeated SCCs to satisfy exact original `k`.

## Correctness — direct argument

1. **Signature locality:** Every nonempty signature lies within its hull. If two hull components have no intersection, a query from one component cannot be certified by a pivot from another component. The hull merges preserve this property.
2. **Additivity:** Every positive-weight query is charged in exactly one component. Empty signatures contribute a fixed constant. Every pivot outside the union of component hulls covers no positive-weight query.
3. **Budget convolution:** Any global `k`-subset splits uniquely into subchoices inside each component and a choice of free positions, with total cost the sum of component costs and the fixed constant. Conversely, concatenating any feasible collection of optimal component subchoices and distinct free positions gives a feasible global `k`-subset with that summed cost. The recurrence enumerates all cardinality allocations; therefore minimizing it is exact.
4. **Multi-budget frontier profile:** The Phase V state `(number_selected,last_pivot,live_coverage_bits)` retains all information required for future costs. Unlike exact-one-budget Phase V, the profile DP retains *every* feasible used count up to `max_k`, then reads the minimum terminal cost for each count. Bellman-optimal state merging preserves the optimum for all budget counts simultaneously. Traceback reconstructs one witness for each count.

These are proofs for the specified **exact discrete optimization problem**, not formal-machine verification or proofs of novel complexity classes.

## Complexity and limitations

Let `B` be the number of disjoint support-hull components, `h_i` their sizes, `q_i` their query counts, `r_i` distinct two-interval signatures, and `w_i` Phase V frontier width. Let `K_i=min(k,h_i)` and `K=k`. The global min-plus budget convolution takes `O(BK^2)` worst-case time and `O(K)` objective-only memory (the current witness implementation retains selected pivot tuples and may use up to `O(BK^2)` space overall). Local cost-profile generation uses one of:

- Single-interval path sweep repeated for budgets 0..K_i; conservatively `O(K_i^2 (h_i+q_i) log(h_i+1))`.
- Orientation enumeration separately for budgets 0..K_i: `O(2^{r_i} K_i^2 (h_i+q_i) log(h_i+1))`.
- Frontier profile **once**: `O((h_i+q_i) h_i (K_i+1) 2^{w_i})` under word-size RAM bit operations and expected O(1) hash access; large Python bitsets add a factor polynomial in `r_i`. Storing per-layer traceback can require `O(h_i^2 (K_i+1)2^{w_i}+q_i)` memory. A state cap raises an error; it never silently approximates.

Preprocessing hulls takes `O(q log q + h)`. As with Phase V, the exact algorithm is exponential when a connected component has high frontier width. When all queries overlap in one connected hull component, the extra decomposition and multi-budget bookkeeping can make Phase VI slower. The automatic engine rule (`r_i <= 2` => orientation, otherwise frontier) is a conservative implementation heuristic and not a guarantee of minimal running time.

## Verification

From `tric_research/`:

```sh
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact
python benchmark_adaptive.py > phase6_benchmark.json
```

**31/31 unittest methods passed locally under Python 3.13**. The Phase VI tests compare exact objectives and reconstructed witnesses against independent combinatorial brute force on randomized 1–10-position instances, forced engine equivalence, free positions, invalid inputs, and randomized directed cyclic graphs checked via direct BFS-based certificate membership. Original Phase I–V tests remain unchanged. The JSON benchmark records five timing samples and medians per case.

## Exploratory synthetic results

| Workload family | Signatures | Independent regions | Adaptive ms | Phase V frontier ms | Phase III orientation ms |
|---|---:|---:|---:|---:|---:|
| separated | 2 | 2 | 0.062 | 0.042 | 0.026 |
| separated | 8 | 8 | 0.381 | 1.079 | 47.169 |
| separated | 12 | 12 | 0.663 | 3.786 | not run |
| overlapping | 5 | 1 | 0.239 | 0.231 | 1.089 |
| overlapping | 9 | 1 | 9.222 | 9.607 | not run |
| single | 50 | 50 | 1.156 | not run | not run |

All measurements are local CPython exploratory wall-clock numbers, 5 runs per setup, no external algorithm comparison. Small-r cases are intentionally negative results for adaptivity. Do not generalize ratios to real workloads or different implementations.

## Publication/novelty boundary

Our basic reachability certificate rules directly overlap O'Reach; SCC condensation, frontier DP, separable subproblems, and min-plus knapsack convolution are established algorithmic techniques. The present contribution is an **implemented, verified combination specialized to TRIC**, not a substantiated new computational breakthrough. Its global novelty is **unresolved and likely incremental** absent a new provable bound or meaningful external experiment. Papers examining related algorithms include:

- Hanauer, Schulz, Trummer, *O'Reach*, SEA 2021: https://doi.org/10.4230/LIPIcs.SEA.2021.13
- Rawitz & Shahar, *Partial multicovering and the d-consecutive ones property* (2011): https://doi.org/10.1016/j.disopt.2011.05.004
- Damaschke, *Refined algorithms for hitting many intervals* (2017): https://doi.org/10.1016/j.ipl.2016.11.001
- *Indexing Techniques for Graph Reachability Queries*, ACM Computing Surveys: https://doi.org/10.1145/3776737

**Next decision gate:** use real held-out cyclic and DAG workloads and compare full preprocessing/query/memory costs against compiled O'Reach/other reachability indexes before making external performance or publication claims. Include adverse regimes, code availability, raw samples, and exact semantic equivalence. Do not merge open Phase IV/V/VI branches solely because their internal tests pass.

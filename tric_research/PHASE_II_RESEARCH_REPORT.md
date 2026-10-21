# TRIC Phase II — Prior-Art Refutation and Exact Path Optimization

Date: 21 October 2026  
State: Executed research prototype with proof arguments, differential tests, and local performance measurements. **Not a novelty-certified manuscript.**

## Critical prior-art finding

The original TRIC three certificate rules are exactly the three supportive-vertex observations (S1), (S2), and (S3) appearing in Hanauer, Schulz, and Trummer's *O'Reach: Even Faster Reachability in Large Graphs*, ACM JEA 27(4), publication October 2022. O'Reach also considers supportive-vertex selection and overlap. Consequently, the original TRIC basic mechanism and three-rectangle interpretation must **not** be presented as a novel reachability algorithm. A faithful scholarly paper must present O'Reach as prior art, not an optional loose comparator.

Primary source: https://eprints.cs.univie.ac.at/7545/1/O_Reach_Even_Faster_JEA.pdf (section 4.2, observations S1–S3). Code and benchmark data: https://oreach.taa.univie.ac.at/ .

The 2025/2026 reachability survey also places partial-2-hop indexes including O'Reach among known methods: https://doi.org/10.1145/3776737 .

## Exact path optimization: statement and proof

Static directed path (or graph whose reflexive reachability is exactly the vertex order) on vertices 0,...,n-1. Query workload Q is a finite multiset of ordered endpoint pairs (s,t) with **nonnegative** weights w_q. The objective is to select **exactly k** pivots to maximize weighted certified queries, equivalently minimize uncovered weight.

For this graph family, pivot p certifies (s,t) if and only if min(s,t) <= p <= max(s,t). Each query therefore corresponds to a weighted closed interval, and a pivot is a stabbing point.

Let W(l,r) be the sum of query weights whose **both endpoints** fall in [l,r], with W(l,r)=0 for empty intervals. If pivots p_1<...<p_k are chosen, the uncovered cost is the sum W(l,r) across the k+1 pivot-free gaps. This proves exact optimal substructure.

### Quadratic reference recurrence

D[1,j]=W(0,j-1). For r>=2:

D[r,j] = min_{r-2 <= i < j} (D[r-1,i] + W(i+1,j-1)).

Finish with min_j D[k,j]+W(j+1,n-1), j>=k-1. Original prototype stores an n×n prefix-cost table and uses O(n²+|Q|+kn²) operations / O(n²+kn) memory.

### Improvement A: Monge divide-and-conquer DP

For a<=b<=c<=d and w_q >=0:

W(a,c)+W(b,d) <= W(a,d)+W(b,c).

**Proof.** The right minus left equals the total weight of queries with one endpoint in [a,b-1] and the other in [c+1,d] (counting both orientations). Nonnegativity proves the inequality. Consequently the row transition cost W(i+1,j-1) is Monge wherever transitions are feasible. Adding the predecessor D[r-1,i] to each row leaves it Monge. The earliest minimizing predecessor is nondecreasing across target columns. Divide-and-conquer optimization obtains each DP row in O(n log n) transition evaluations; W(l,r) is O(1) from a 2D prefix sum. Total O(n²+|Q|+kn log n) time and O(n²+kn) memory.

The Monge optimization methodology is well established. For example Aggarwal and Tokuyama, *Consecutive interval query and dynamic programming on intervals*, Discrete Applied Mathematics 85(1), 1998: https://doi.org/10.1016/S0166-218X(98)00021-3. **Do not claim discovering Monge interval DP.**

### Improvement B: Sweep-line lazy segment tree without quadratic table

For each query q, define lo_q=min(s,t), hi_q=max(s,t). At DP column j, its weight should contribute to transition predecessor i **exactly when** hi_q<j and i<lo_q. Hence when the sweep reaches j=hi_q+1, perform a *prefix range-add* of w_q to candidate predecessor indices i in [0,lo_q-1]. Starting the sweep with candidate costs D[r-1,i], a range-add/range-min segment tree then returns D[r,j] as the minimum over 0<=i<j. Restrict j to feasible j>=r-1 and predecessor state D[r-1,i] to i>=r-2 via infinite costs in prior DP rows.

At each DP layer, all |Q| events require at most |Q| range-add operations and all n columns require n range-min operations. Each costs O(log n). Form the final trailing-gap W(j+1,n-1) by one reverse suffix sweep over minimum query endpoints. Thus the full exact optimizer runs in

**O(k(n+|Q|) log n)** time and **O(kn+n+|Q|)** additional memory.

This complexity is for the weighted path-pivot selection task, not general graph reachability or arbitrary DAGs. The operations are classical sweep-line and lazy segment-tree primitives; new-to-TRIC does not mean globally novel.

### Assumptions and limitations

- Query weights must be nonnegative. Negative weights destroy the Monge inequality in general.
- Exactly k pivots; if the objective has different per-pivot build/storage costs, this recurrence no longer directly solves it.
- Reachability must equal order on the vertices: `s` reaches `t` iff `s<=t`. A Hamiltonian forward path with only forward shortcuts qualifies; arbitrary DAGs do not.
- Complexity counts arithmetic operations on a RAM model with O(1) integer-weight arithmetic; arbitrary-precision bit complexity is not included.

## Tests run in Phase II

`python -m unittest -q test_tric test_path_monge test_path_sweep` — **9 tests passed**. Included checks:

- 4,096 loop-free directed graphs on n=4 from `tric.exhaustive(4)`; all 262,144 pivot × pair checks passed.
- Random directed graphs n=1..8 from original suite.
- Path optimizer: random weighted workloads across n=1..17, comparison among quadratic, Monge, and sweep implementations, plus brute-force combinations for small n.
- Random nonnegative range-add and prefix-min operations against naive arrays.
- All three optimizers return identical **pivot sets and objective values** on the benchmark grids, not merely approximately equal scores.

These are local Python executions, not a proof assistant run.

## Experimental results: exact pivot optimizer

Five wall-clock repetitions per algorithm, medians in seconds; same queries, nonnegative integer weights, k=8, `|Q|=5n`, single machine/CPython. These timings include each solver's own preprocessing but not graph construction and reachability queries.

| n | Quadratic | Monge | Sweep | Quadratic / Monge | Quadratic / Sweep |
|---:|---:|---:|---:|---:|---:|
| 160 | .019991 | .003333 | .023907 | 6.00× | 0.84× |
| 320 | .090734 | .010508 | .062777 | 8.63× | 1.45× |
| 640 | .460632 | .038234 | .155978 | 12.05× | 2.95× |
| 960 | 1.087960 | .102114 | .250912 | 10.65× | 4.34× |

Sparse query scaling (`|Q|=2000`, k=8, sweep-only; median of three runs): n=2000: .159 s; n=5000: .279 s; n=10000: .493 s. **No other algorithms were timed at these larger scales, so no comparative speedup is asserted there.**

At n=1200, |Q|=2000, k=8, one `tracemalloc` run reported Monge 49.65 MiB vs sweep 0.70 MiB of traced Python peak allocations. Both reached objective 886. This is **not** whole-process RSS or compiled-language memory.

**Interpretation:** Monge has lower Python overhead on these small/moderate examples. Sweep avoids the O(n²) memory term, giving substantially better asymptotic scalability when Q is sparse. There is no proof or empirical evidence of global wall-clock superiority.

## Exact-versus-greedy selection

80 seeded scenarios each, n=50, |Q|=150, k=4, integer weights 1..6. For each scenario, greedy and exact selection are evaluated on the **same** input workload. These experiments are training-objective comparisons, not predictive held-out wins.

| Workload | Greedy suboptimal runs / 80 | Mean greedy uncovered weight | Mean optimum uncovered weight | Mean difference |
|---|---:|---:|---:|---:|
| Uniform | 61 | 62.56 | 56.83 | 5.74 |
| Clustered | 53 | 56.38 | 51.95 | 4.42 |

The differences follow from exact optimization by construction. They establish the magnitude of the greedy gap in these scenarios; they do not establish novelty over known weighted interval-stabbing optimization.

## Novelty tribunal / negative findings

| Candidate statement | State | Reason |
|---|---|---|
| Three positive/negative pivot certificates are new | **REFUTED** | O'Reach 2022 S1/S2/S3 identical |
| Selecting pivots by greedy covered-weight has new 1−1/e bound | **REFUTED as original theorem** | Classical maximum coverage |
| Monge optimization of weighted interval segmentation is new | **UNSUPPORTED** | Monge-interval DP appears in 1998 work |
| Specialized sweep-line recurrence for TRIC weighted path pivot selection is new in this exact form | **UNRESOLVED** | Mechanism follows established range-add/range-min event sweeping; broader equivalence search needed |
| The exact path-pivot optimization is useful for this research program | **SUPPORTED in bounded local experiments** | Exact objective and significant comparison gaps |
| TRIC currently beats modern reachability indexes | **UNSUPPORTED** | No actual O'Reach/DBL/GRAIL controlled baseline yet |
| Fully publishable paper presently exists | **NO** | Major novelty and externally valid benchmark gaps |

Related robust submodular selection, if investigated for distribution shift, must cite Krause et al., *Robust Submodular Observation Selection*, JMLR 9, 2008: https://www.jmlr.org/papers/v9/krause08b.html . It must not be presented as an independently discovered optimization guarantee.

## Reviewer challenges and concrete next research campaign

1. **Novelty:** Disentangle the path pivot problem from classical max-weight k-point interval stabbing and Aggarwal–Tokuyama's Monge interval DP. Determine if the sweep recurrence has prior equivalents. Be willing to publish a narrower application/system paper rather than claiming algorithmic invention.
2. **General graph applicability:** Seek a *new* exact tractable graph class or a meaningful mixed structural-class decomposition; general DAG certification is not characterized by intervals.
3. **Practical comparison:** Implement equivalent C++ representations, instrument total index build, selection, memory, and query costs; then compare to O'Reach using its official code and real datasets.
4. **Deployment:** Analyze amortized break-even query counts, robust workload drift, query distribution changes, negative and positive workload skews, and the cost of rebuilding certificates.
5. **Reproducibility:** Preserve raw results, process/CPU metadata, pinned C++ compiler, five-or-more paired repetitions and query seeds. Current benchmarks do not meet peer-review-strength standards.

## Reproduce this phase

From the `tric_research` directory:

```bash
python -m unittest -q test_tric test_path_monge test_path_sweep
python benchmark_optimizers.py
python benchmark_pivot_quality.py
python benchmark_path_monge.py
```

No third-party dependencies. Original Phase I note is `RESEARCH_NOTE.md`. New source: `path_monge.py` and `path_sweep.py`; tests: `test_path_monge.py` and `test_path_sweep.py`; original results remain unchanged.

# TRIC — Ternary Rectangular Index of Certificates
## Research candidate and reproducibility dossier — 21 October 2026

**Status:** Exact algorithmic research prototype. Correctness is supported by mathematical arguments and executable differential tests; **global novelty, superiority, and publication readiness are not established.**

### Abstract

We investigate workload-aware indexing for exact pairwise reachability in a static directed graph. A pivot stores its exact forward and backward reachability sets. These define three rectangular regions of source–target pairs with certified answers: one positive and two negative. A query is answered using a selected collection of pivots when any rectangle covers the pair, otherwise a graph search supplies the answer. Pivot selection maximizes a coverage objective on a finite training workload. Under a fixed cardinality budget, the coverage objective is monotone submodular, permitting the classical greedy `(1-1/e)` approximation for this *selection objective*, not for total latency. On directed paths, the uncovered queries decompose into disjoint pivot-free gaps, yielding an exact dynamic program with arbitrary nonnegative query weights. The implementation demonstrates favorable and unfavorable regimes; some sparse graphs run **slower** than plain graph search.

### 1. Problem contract

Input: a static finite directed graph `G=(V,E)` with `n=|V|` and `m=|E|`, a finite workload `Q` of ordered source–target queries, and a pivot budget `k`. A vertex reaches itself (reflexive reachability). A query requests exact Boolean reachability. Goal: select pivots to reduce query work for a workload while respecting `k` pivot records and allowing exact traversal fallback. Every query answer must be correct. Preprocessing and index-memory costs matter separately from query costs.

### 2. Certificate definitions

For each pivot `p` let:

- `F(p)={v: p→*v}` (exact forward reachability, including `p`)
- `A(p)={v: v→*p}` (exact reverse reachability, including `p`)

For query `(s,t)` a pivot certifies:

1. **Positive:** `s∈A(p)` and `t∈F(p)` implies `s→*t`.
2. **Negative-F:** `s∈F(p)` and `t∉F(p)` implies `s↛*t`.
3. **Negative-A:** `s∉A(p)` and `t∈A(p)` implies `s↛*t`.

These are rectangles within the universe `V×V`:

- `A(p) × F(p)` labeled reachable;
- `F(p) × (V\F(p))` labeled unreachable;
- `(V\A(p)) × A(p)` labeled unreachable.

If no selected pivot certifies the query, perform ordinary graph traversal. The certificate lookup requires at most `k` records; no probabilistic false-answer mechanism is used.

### 3. Correctness (complete argument)

Positive: `s∈A(p)` supplies a path from `s` to `p`. `t∈F(p)` supplies a path from `p` to `t`. Concatenating them proves `s→*t`.

Negative-F: suppose `p→*s`, `t∉F(p)` and, for contradiction, `s→*t`. Concatenation implies `p→*t`, so `t∈F(p)`, contradiction.

Negative-A: suppose `t→*p`, `s∉A(p)` and, for contradiction, `s→*t`. Concatenation implies `s→*p`, so `s∈A(p)`, contradiction.

A fallback graph search is exact, so every returned answer is correct regardless of candidate selection, graph cycles, and workload distribution. This argument assumes exact, fresh forward and backward reachability sets. Edge updates without recomputation would invalidate that assumption.

### 4. Complexity and guarantee

A single pivot requires two complete traversals: `O(n+m)` construction time and `2n` bits of *idealized* bitmap storage. For `k` deployed pivots the uncompressed idealized bitmap payload is `2kn` bits and the certificate-only query cost is `O(k)` membership checks on a word-RAM with constant-time bit access; fallback costs `O(n+m)` in the worst case.

If `c` candidate pivots are fully materialized for training, candidate construction costs `O(c(n+m))` and `O(cn)` bits peak before selecting `k`; scanning all candidate/workload pairs for coverage costs `O(c|Q|)` elementary certificate checks. A direct `k`-round greedy implementation additionally takes up to `O(kc|Q|)` operations, ignoring Python bigint acceleration and fixed-width word effects. This cost must be included in end-to-end benchmarking.

For a finite weighted training workload `Q`, define `C(p)⊆Q` as queries certified by pivot `p` and weights `w_q≥0`. Let `f(S)=Σ_{q∈∪_{p∈S}C(p)} w_q`. Then `f` is nonnegative, normalized, monotone and submodular, since adding a pivot covers fewer new elements when more pivots have already been chosen. Thus the familiar cardinality-constrained greedy guarantee holds: `f(S_greedy)≥(1-1/e) max_{|S|≤k} f(S)`. **This is an application of a known theorem, not claimed as newly discovered.** The guarantee is about the selected candidate pool and finite weighted workload, *not* held-out queries, running time, or all possible graph nodes when only `c<n` are candidates.

### 5. Exact dynamic programming on directed paths

For the directed path `0→1→...→n-1` (possibly with additional edges pointing strictly forward), a pivot `p` certifies query `(s,t)` **if and only if** `min(s,t)≤p≤max(s,t)`. A query remains uncertified by a set of pivots iff its two endpoints belong to the same gap of consecutive nonpivot vertices. Therefore, for arbitrary nonnegative query weights, the total uncertified penalty is additive across the `k+1` pivot-free gaps.

Define `W(l,r)=Σ_{(s,t)∈Q: l≤s,t≤r} w(s,t)`, with `W(l,r)=0` if `l>r`. For at least one pivot, let `D[j,1]=W(0,j-1)` and for `2≤r≤k`, `D[j,r]=min_{i<j}(D[i,r-1]+W(i+1,j-1))`. The optimal penalty is `min_j(D[j,k]+W(j+1,n-1))`. A 2D prefix sum computes gap costs in `O(1)` time after `O(n²+|Q|)` preprocessing; straightforward DP costs `O(kn²)` and `O(kn+n²)` memory. Backpointers recover actual pivot indices. The supplied tests brute-force all possible pivot placements on small inputs and check that the DP objective is globally minimal. No published-novelty claim is made for this recurrence.

For **uniform ordered query pairs** on a path, if `ℓ_i` denote the nonpivot gap lengths, the probability that a query remains uncertified is `Σ ℓ_i²/n²`. The optimal gaps are as balanced as possible by convexity. Let `q=n-k`, `b=k+1`, `a=floor(q/b)`, `r=q mod b`. The optimal remaining fraction is `[(b-r)a²+r(a+1)²]/n²`. This is an explicit finite-model optimum, not an asymptotic impossibility result for all graph indexes.

### 6. Executed experimental evidence

**Correctness**
- All `2^12=4,096` simple directed graphs without self-loops on four vertices, with every pivot and every ordered endpoint pair: `262,144` checks, no incorrect certificates.
- Additional seeded random directed graphs of sizes `1..8`, including cyclic examples, with differential testing against graph traversal: passed.
- Optimal directed-path DP checked against exhaustive combinatorial pivot placement on randomized small inputs: passed.

**Held-out pilot (five seeds; synthetic `n=240`; `c=48` candidates, `k=8`; 2,000 training queries and 5,000 independent held-out queries per setting)**

| Graph family | Workload | Random 8-pivot certificate rate | Greedy 8-pivot certificate rate | Greedy edge scans avoided vs BFS |
|---|---|---:|---:|---:|
| Random DAG | uniform | 49.5% | 63.7% | 45.0% |
| Random DAG | hot endpoint population | 56.6% | 89.5% | 81.6% |
| Directed chain plus forward shortcuts | uniform | 82.0% | 88.7% | 85.0% |
| Directed chain plus forward shortcuts | hot | 78.8% | 97.4% | 96.7% |
| Disconnected DAG blocks | uniform | 23.8% | 42.2% | 36.6% |
| Disconnected DAG blocks | hot | 41.5% | 77.0% | 72.0% |
| Directed SCC communities | uniform | 93.5% | 99.4% | 99.3% |
| Directed SCC communities | hot | 95.6% | 99.9% | 99.9% |

These are arithmetic means over five seeds, not production measurements. Full data, including standard deviations, negative controls and weighted-greedy results, is in `multiseed_results.json`.

**Wall clock, single seed (`n=240`, `k=8`, 20,000 test queries, median of five repetitions, CPython, ordinary traversal vs TRIC + fallback):**

| Graph family | Uniform workload speed ratio (BFS time / TRIC time) | Hot workload ratio |
|---|---:|---:|
| Random DAG | 0.96× (slower) | 1.53× |
| Chain with shortcuts | 5.46× | 15.78× |
| Disconnected DAG blocks | 0.34× (slower) | 0.55× (slower) |
| Directed SCC communities | 29.40× | 44.60× |

Preprocessing time is **not** included in these per-query ratios, and it was measured separately in `latency_results.json`. Timing is local, small-scale, interpreter-dependent, and relative only to elementary Python traversal. No comparisons against O'Reach, DBL, GRAIL, or optimized C++ BFS have yet been executed. Results must not be described as state of the art. Edge-scans avoided are a mechanistic proxy and differ from wall-clock speedups. The exact source for all observations is supplied with deterministic seeds.

### 7. Literature audit and novelty risks

Relevant original material identified in the scoped search:

- Zhang, Bonifati, Özsu, *Indexing Techniques for Graph Reachability Queries*, ACM Computing Surveys (published online December 2025), https://doi.org/10.1145/3776737 — broad index taxonomy and major closest-family references.
- Hanauer, Schulz, Trummer, *O'Reach: Even Faster Reachability in Large Graphs*, https://arxiv.org/html/2008.10932v2, implementation and datasets: https://oreach.taa.univie.ac.at/ — extremely relevant partial reachability indexing, both positive and negative answers; should be a mandatory comparator.
- Lyu et al., *DBL: Efficient Reachability Queries on Dynamic Graphs*, https://arxiv.org/abs/2101.09441 — landmarks for positives and another label family for negative pruning, demonstrating that mixing positive and negative indexes is **not novel by itself**.
- Akiba, Iwata, Yoshida, *Fast and scalable reachability queries on graphs by pruned labeling with landmarks and paths*, https://doi.org/10.1145/2505515.2505724 — pruned landmark/path labels, essential mechanism comparator.
- Bulteau et al., *Incremental Reachability Index*, SEA 2025, https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.SEA.2025.9 — relevant if the work is extended to append-only evolving graphs.
- Earlier path-hop and greedy set-cover mechanisms are discussed in the survey; cardinality-constrained coverage and set-cover selection are longstanding tools.

**Novelty verdict:** The prototype is an independently specified **combination** of exact forward/backward closure certificates, adaptive finite-workload selection, and special-case optimization. The three rectangular rules, together with the particular special-case DP and empirical trade-off, require deeper mechanism-by-mechanism prior-art analysis before any strong originality claim. Overlap with existing landmark and positive/negative filtering is material. Treat novelty as **UNRESOLVED / INCREMENTAL-COMBINATIONAL**, not established.

### 8. Simulated reviewer objections and upgrade requirements

- **Novelty:** Is three-rectangle evaluation distinct from standard forward/backward landmark labels and reachability signatures, or a notation change? Inspect algorithms in O'Reach and DBL closely and test a stronger contribution boundary.
- **Algorithmic importance:** The greedy coverage guarantee is a direct application of classical maximum coverage, so it cannot carry the main theoretical contribution. Exact path DP may be standard segmentation under another name; search this analogy thoroughly.
- **Performance:** On sparse blocks, Python overhead more than eliminates traversal savings. Develop a cost-aware policy that can skip certificates when expected BFS cost is lower; measure without training/test leakage.
- **Fairness:** Compare to real optimized baseline implementations under fixed total memory and index-build budgets, not only naive BFS or positive-only variants. Use large real directed graph benchmarks, positive-only / negative-only / mixed query distributions and distribution shift.
- **Robustness:** Study index costs for candidate construction, CPU cache locality, bitmap compression, updates, SCC condensation and graph families designed to defeat coverage.
- **Theory:** Seek a structurally new result beyond basic submodularity, e.g. an optimal algorithm under another nontrivial graph class or approximation guarantee for a different joint objective.

### 9. Recommended paper hypothesis, not yet supported

> A memory-bounded, workload-aware **mixed-polarity certification index** can outperform established partial reachability indexes on structurally clustered workloads **without losing efficiency on easy-negative sparse workloads**, using a learned but always-correct dispatch policy and an optimized certificate representation.

This is a falsifiable hypothesis, **not** an experimental finding. A publishable paper would need to establish it with fair C++ baselines, real graph corpora, total-cost accounting, statistically stable wins and a novelty claim that survives comparison with O'Reach/DBL and related indexing work. If direct mechanism overlap collapses novelty, the paper should pivot to the new dispatch/memory problem or a substantive new theorem rather than merely changing the algorithm's name.

### 10. Reproduction

Python 3.10+; no third-party libraries required.

```bash
cd tric_research
python -m unittest -v test_tric.py
python tric.py --output results.json
python benchmark_latency.py
```

The exhaustive 4-node check is included in `tric.py`. `results.json`, `multiseed_results.json`, and `latency_results.json` are original local-run outputs. `benchmark_latency.py` intentionally benchmarks a Python proof-of-concept, not a production-quality or peer-comparable C++ graph index.

**Operational note:** TRIC as implemented is for **static graphs**. No automatic update support. An edge update requires rebuilding certificates or a proven safe incremental update procedure; otherwise stale certificates may give wrong answers.

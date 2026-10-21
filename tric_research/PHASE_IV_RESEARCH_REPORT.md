# TRIC Phase IV — SCC-Condensed Exact Backbone Certificates

Date: **2026-10-21**. Status: **implemented and locally tested; independent novelty verification outstanding**.

## Research question

Can the Phase III linear-time backbone certificate extractor and its exact weighted pivot selector be extended from DAGs to **arbitrary directed graphs with cycles** without falsely equating strongly connected vertices or changing query semantics?

**Yes.** Condensing SCCs yields a DAG and a compressed designated backbone. One pivot from each backbone SCC represents all the original backbone vertices in that SCC. This is a straightforward composition of standard SCC theory, existing O'Reach supportive-vertex certificates, and the Phase III interval selector. It is an algorithmic extension and a theorem about this specialized problem, **not yet a supported claim of global novelty**.

## Precise model

Input: directed graph `G=(V,E)` with vertices `0,...,n-1`; a nonempty simple directed path `P=(p0,...,p(h-1))` where `(pi,p(i+1)) in E`; weighted reachability-query multiset `Q = ((s,t,w))` with `w >= 0`; exact selection budget `k <= h`. We may select only backbone vertices. A query counts as covered iff one chosen pivot resolves it by one of O'Reach's standard positive/negative supportive-vertex certificate rules. Objective: minimize total weight of uncertified queries. This is **not** ordinary reachability computation, and no new supportive-vertex rule is claimed.

## Lemma 1: consecutive SCC runs

Let `C(i)` denote the SCC of `pi`. If `C(i)=C(j)` for `i<j`, all intermediate vertices `pi,...,pj` lie in that same SCC: the backbone gives `pi ->* pt ->* pj`, while SCC membership gives `pj ->* pi`. Hence `pt` and `pi` are mutually reachable. Therefore backbone SCC labels occur in consecutive runs. Removing repeated labels produces a valid directed path in the condensation DAG.

## Lemma 2: certificate equivalence under condensation

Let `D` be the condensation DAG and `c:V -> V(D)` the SCC map. Then `u ->* v` in G iff `c(u) ->* c(v)` in D. Consequently for every backbone pivot `p`, the two sets used by supportive-vertex certificates (vertices reaching p, and vertices reachable from p) are unions of SCCs and depend only on `c(p)`. Any two pivots in the same SCC certify **exactly the same query pairs with the same Boolean answers**.

## Lemma 3: interval representation

Write `P'` for the compressed backbone of length `h'`. For each component x let `L[x]` be the last compressed backbone index reaching x (or -1) and `R[x]` the first index reachable from x (or h'). In the condensation DAG, the backbone order implies prefix/suffix monotonicity. For a query `(s,t)` with `a=c(s)`, `b=c(t)`, the exact certificate regions are the union of inclusive intervals:

- positive: `[R[a], L[b]]`;
- negative type 2: `[L[b]+1, L[a]]`;
- negative type 3: `[R[b], R[a]-1]`.

Clamp to `[0,h'-1]`, omit empty intervals, and merge overlapping/adjacent ones. If the positive interval is nonempty, `s ->* t`; therefore negative intervals cannot exist. If the positive interval is empty, the remaining two intervals may be disjoint. Thus every query's certifying backbone pivots form at most **two intervals**.

## Theorem: exact optimization over arbitrary directed graphs

1. Find the SCCs using iterative Kosaraju in `O(|V|+|E|)` time and memory.
2. Construct the condensation DAG and its compressed backbone, preserving one original-vertex representative per backbone SCC.
3. Find a topological order, propagate `L` forward by maximum and `R` backward by minimum in `O(|V|+|E|)`.
4. Generate the 0/1/2-interval certificate signature for each weighted query in `O(|Q|)`.
5. Optimize the signatures using Phase III's exact orientation-enumeration and interval-stabbing DP. Let `r` be the number of **distinct two-interval signatures**, `k'=min(k,h')`. This takes `O(2^r k'(h'+|Q|) log(h'+1))` time with the current implementation.
6. Map selected SCC indices to representative original backbone vertices. When `k>h'`, choose extra, *redundant* original backbone vertices to fulfill the exact-`k` interface without changing coverage.

The complete running-time bound (unit-cost RAM with fixed-size weight operations) is

`O(|V|+|E|+|Q| + 2^r k'(h'+|Q|) log(h'+1))`.

This exact solver is not polynomial on unrestricted instances; it inherits Phase III's exponential dependence on disjunctive signatures. If `b` is the number of **off-backbone SCCs** in the condensation DAG, then two-interval queries have both endpoint components off-backbone and, for each unordered pair of such components, at most one direction can have two disjoint nonempty intervals. Thus `r <= b(b-1)/2`, giving FPT in off-backbone SCC count. Query pairs in the same SCC cannot give distinct separated negative certificate intervals.

**Novelty boundary:** SCC reduction and these certificate rules are classical. Phase III already gave the DAG optimizer; Phase IV's mathematical contribution is the explicit SCC parameter and exact general-digraph extension, and should be treated as *incremental until equivalent results are ruled out*.

## Verification and benchmark

Commands (from `tric_research/`):

```
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc
python benchmark_backbone_scc.py > phase4_benchmark.json
```

Locally executed: **19 tests passed** (15 Phase I–III + four additional Phase IV tests). New tests include exhaustive all `2^10 = 1,024` directed simple graphs on four vertices with a fixed 3-vertex backbone; direct per-pivot reachability/certificate oracle agreement; random exact-weighted-optimizer comparison with full `k`-subset brute force, including `k>h'`; correctness of the `r <= b(b-1)/2` bound; and a 3,500-vertex strongly connected cycle to test iterative SCC execution without recursion limits.

The accompanying `phase4_benchmark.json` stores paired wall-clock trials, seeds, versions, and machine metadata. All timings are **Python-only and local**; they are measured against TRIC's own repeated-graph-search extractor and **not** against O'Reach or another published index. The synthetic 'forward' case is acyclic, while `cycle_blocks` and `one_giant_scc` introduce directed cycles. At `h=320`, illustrative reference-to-SCC extraction ratios ranged from roughly 31x (acyclic) to 85x (giant SCC) in this environment. Those ratios are not a claim of general performance superiority; the reference algorithm repeats many traversals, and the speedups were expected.

## Critical limitations and next experiments

- Research novelty is unestablished; compare against primary O'Reach source and other workload-aware reachability-index selection schemes.
- SCC condensation changes selection only when a path crosses repeated SCCs; on a DAG, the benefit comes solely from linear propagation, already implemented in Phase III.
- The parameter `b` can be very large on real graphs, and `2^r` can become impractical.
- Benchmark real cyclic graphs with several SCC sizes, full index build cost, equal-memory budgets, held-out query workloads, and a compiled O'Reach baseline.
- The current implementation optimizes certificates for a **known backbone**. Finding a useful backbone is outside scope.
- No formal proof assistant was run; proofs are human-checkable sketches/arguments, supported by exhaustive finite tests only within the tested bound.

## Prior art

- Hanauer, Schulz and Trummer. *O'Reach: Even Faster Reachability in Large Graphs*. SEA 2021; ACM JEA 2022. https://doi.org/10.4230/LIPIcs.SEA.2021.13 ; https://doi.org/10.1145/3556540
- Zhang et al. *Indexing Techniques for Graph Reachability Queries*. ACM Computing Surveys (2025/2026). https://doi.org/10.1145/3776737
- SCC condensation and Kosaraju's algorithm are textbook graph techniques, not novel TRIC primitives.

**Verdict:** Correctness and performance claims are supported locally for the specified experimental scope. The exact optimization extension is mathematically defensible subject to independent proof audit, but **not yet publishable as a novel contribution on these facts alone**.

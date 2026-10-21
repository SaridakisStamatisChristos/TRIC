# TRIC Phase III — Backbone Certificate Geometry, Complexity Boundary, and Exact Parameterized Optimization

**Date:** 21 October 2026  
**Status:** Constructive mathematical arguments + executable Python prototype + tests + local benchmarks.  
**Novelty:** **Unresolved.** The underlying S1/S2/S3 certificate rules were published in O'Reach. The relevant 2-interval geometry and hitting-set hardness also have deep prior art. This report proposes a precise, falsifiable *specialized formulation*, not a priority claim.

## 0. Problem contract

Input: finite **DAG** G=(V,E) with a specified simple directed backbone path P=(p_0,...,p_{h-1}); a multiset Q of ordered reachability queries (s,t) with nonnegative integer weights w_q; exactly k positions on P to select as supportive-vertex pivots. A selected pivot p certifies a query if one of O'Reach's standard S1/S2/S3 tests determines its reachability truth without fallback exploration. Objective: maximize total weighted *distinct query coverage*, or equivalently minimize total uncovered weight. Query weights do not change correctness.

Scope: the task selects **backbone-restricted** pivots. It is not a general reachability oracle, not an exact optimizer for unrestricted pivot vertices, and not a claim of end-to-end superiority to O'Reach.

## 1. Backbone interval characterization

For each graph vertex v define threshold values:

- L(v) = maximum i for which p_i can reach v, with -1 if none.
- R(v) = minimum i for which v can reach p_i, with h if none.

Because P is a directed path, the backbone vertices that can reach v form a prefix [0,L(v)], and the backbone vertices reachable from v form a suffix [R(v),h-1]. These statements are true for any directed graph containing the path, not only DAGs, though our fast extractor requires a DAG.

For q=(s,t), the backbone certificate set C_q has the following exact form, with all intervals clipped to [0,h-1] and empty ranges removed:

- **S1 positive:** [R(s),L(t)].
- **S2 negative:** [L(t)+1,L(s)].
- **S3 negative:** [R(t),R(s)-1].

S1 cannot coexist with a valid S2/S3 negative certificate for the same query, because O'Reach's individual tests are sound. Hence C_q is a union of **at most two intervals** after merging overlapping or neighboring integer intervals. All certified answers are exact.

If either endpoint is a backbone vertex, C_q is a **single interval or empty**. For example if s=p_i and t is external, S2=[L(t)+1,i] and S3=[R(t),i-1]; on a DAG, L(t)<R(t), so S3 is contained in S2 whenever it is nonempty. If t=p_i and s is external, S2=[i+1,L(s)] is contained in S3=[i,R(s)-1] whenever it is nonempty. Two backbone endpoints reduce to the ordinary path case. Thus two separated intervals require **both endpoints outside P**.

With b=|V\P|, two-separated-interval query signatures can occur for at most one orientation of any unordered distinct off-backbone pair (s,t): both nonempty negative pieces require L(s)>L(t) and R(s)>R(t), which is impossible simultaneously for the reverse orientation. Hence the number r of **distinct** two-piece query signatures (after aggregation) satisfies **r ≤ b(b-1)/2**. This upper bound does not depend on |Q|.

## 2. Linear-time certificate extraction on a DAG

Unlike the Phase I reference extractor, no graph search is needed for every pivot.

1. Verify the specified backbone edges and topologically order G; reject cyclic graphs for this method.
2. Set L(p_i)=i, R(p_i)=i, other L=-1 and R=h.
3. In forward topological order, for every u->v propagate L(v) := max(L(v),L(u)).
4. In reverse topological order, for every u->v propagate R(u) := min(R(u),R(v)).
5. For each query use the three interval formulas above and merge intervals.

Every ancestor path is covered by the forward recurrence; every descendant path by the reverse recurrence. Therefore the final L,R values equal their definitions. The total time is **O(|V|+|E|+|Q|)** and the extra space is **O(|V|+|Q|)** for the returned intervals. The implementation is `backbone_intervals_fast` in `backbone.py`; the independent reference is `backbone_intervals` based on full forward/backward graph search per pivot.

## 3. NP-completeness theorem for backbone pivot coverage

**Theorem.** Given a DAG G containing an explicitly designated directed backbone P, a finite list of query pairs, and an integer k≤|P|, deciding whether at most k backbone pivots can certify *every* designated reachability query by S1/S2/S3 is NP-complete. The statement holds when **all designated query pairs are unreachable**, every query has unit weight, and G is acyclic.

**Proof.** Membership in NP: given a k-pivot selection, compute its forward/backward reachability sets by standard graph traversal and check each query under S1/S2/S3 in polynomial time.

Reduce an arbitrary undirected **Vertex Cover** instance H=(U,F), U={0,...,n-1}, target cover size k. Create backbone edges p_i->p_{i+1} for i=0,...,n-2. For every undirected edge {i,j}∈F with i<j, create fresh vertices s_e,t_e, add edges p_i->s_e and t_e->p_j, and add p_{i-1}->t_e if i>0, and s_e->p_{j+1} if j<n-1. Designate the query (s_e,t_e).

Every auxiliary edge progresses forward along backbone indices, and auxiliary vertices participate in one gadget each. Consequently the graph is acyclic and s_e cannot reach t_e: the only possible incoming path to t_e goes via p_{i-1} (or none if i=0), whereas s_e can only reach backbone vertices with indices ≥j+1 (or none if j=n-1).

The set of backbone vertices reaching s_e is the prefix ending at i; those reaching t_e end at i-1; the vertices reachable from t_e start at j, and those from s_e start at j+1. Thus for (s_e,t_e) the S1 interval is empty, S2 certifies exactly p_i, and S3 certifies exactly p_j. Therefore a set S of backbone pivots certifies all designated queries iff its corresponding H vertices cover every edge of H. Selecting **at most** k pivots is equivalent to Vertex Cover at most k. The reduction uses n+2|F| vertices, at most (n-1)+4|F| arcs, and |F| queries, and is computable in linear time in the instance size. Since Vertex Cover is NP-complete, so is the decision problem. **QED.**

This theorem is about a specialized certificate-selection problem, **not** NP-completeness of deciding ordinary graph reachability, which remains polynomial-time solvable.

## 4. Exact FPT optimizer for backbone pivots

Queries with a single interval can be optimized using Phase II's exact O(k(h+q)log h) sweep-line interval stabbing DP. A query whose certificate set consists of two disjoint intervals A|B introduces a disjunction. Aggregate duplicate two-piece signatures, adding their weights, leaving r distinct disjunctive signatures.

Enumerate all 2^r functions that choose one of A or B for each disjunctive signature. For each function, replace every two-piece query by the chosen single interval, then solve the resulting weighted k-point interval-stabbing instance using the exact sweep DP. Return the best orientation and solution.

**Exactness:** Fix any selected pivot set S. Each two-piece query covered by S has a hit in A or B, so an orientation exists in which it is also covered by S. Conversely an orientation can never certify a query that its original union A∪B did not certify. Therefore

max_orientations max_|S|=k selected_weight(S,orientation) = max_|S|=k selected_weight(S,original),

so the algorithm returns the exact original optimum. Nonnegative weights are needed by the sweep DP's gap formulation and for the intended max-coverage semantics.

**Running time:** O(|V|+|E|+|Q| + 2^r*k*(h+|Q|)*log(h+1)), memory O(|V|+|E|+|Q|+kh) in the RAM model, allowing fixed-size weights or unit-cost arithmetic. Since r≤b(b-1)/2 on a DAG with b off-backbone vertices, this is **fixed-parameter tractable in b**. The exponential dependence is severe and does not imply efficient arbitrary-DAG optimization.

Implementation: `optimize_backbone` and `optimize_intervals` in `backbone.py`. Brute-force reference: exhaustive combinations on small instances. Additional reduction to weighted MAX-2SAT remains in `backbone_hardness.py` as a secondary, more involved construction, but the Vertex Cover proof suffices.

## 5. Executed verification

Command:

`python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone`

Result: **15 tests passed** in ~2.4 seconds on local CPython. Includes prior Phase I/II tests; all loop-free four-vertex directed graphs in the original pivot certificate test; random DAGs with a backbone, the new O(V+E+|Q|) interval extractor checked against the brute-force reference for all source-target pairs, ~20k+ endpoint pairs; exact optimizer vs brute-force k-combinations; weighted MAX-2SAT assignment score equivalences; and **every undirected graph on ≤5 vertices** for the Vertex Cover reduction (including all budgets), with direct reachability checked to ensure designated queries are unreachable.

Tests establish bounded correctness evidence and catch implementation defects. The general theorem is supported by the human-checkable proof above, not *proved by* finite testing. No Lean/Coq or other formal proof assistant was run.

## 6. Local benchmark data

`python benchmark_backbone.py` writes `phase3_results.json` with all individual timed runs. Three timing repetitions; CPython `perf_counter`, same workload per paired comparison. Units below are **milliseconds**, median over three runs. Machine/runtime metadata is included in JSON. Preprocessing and selection timed separately.

### Linear extraction vs original reference

| Graph vertices | Backbone vertices | New DAG topological extraction | Old repeated-search extraction | Ratio old/new |
|---:|---:|---:|---:|---:|
| 70 | 60 | 0.60 ms | 1.98 ms | 3.3× |
| 186 | 160 | 0.82 ms | 12.52 ms | 15.2× |
| 373 | 320 | 0.83 ms | 58.96 ms | 70.8× |
| 746 | 640 | 1.32 ms | 255.24 ms | 193.8× |

This is a comparison against our own naive Python extractor, **not** a comparison against published indexes. The results show a substantial gain from using DAG structure but not a global performance claim.

### Exact selection vs greedy

n=32 backbone pivots, k=4, 2n weighted path queries plus r two-singleton negative queries. The goal is **uncovered workload weight** (lower is better). Values are per seeded instance, not statistical generalizations.

| r distinct disjunctive queries | Exact uncovered | Greedy uncovered | Exact solver median | Greedy median |
|---:|---:|---:|---:|---:|
| 0 | 16 | 16 | 0.57 ms | 0.95 ms |
| 2 | 20 | 22 | 2.23 ms | 1.01 ms |
| 4 | 23 | 35 | 9.07 ms | 1.09 ms |
| 6 | 20 | 29 | 36.42 ms | 1.17 ms |
| 8 | 30 | 38 | 158.96 ms | 1.27 ms |
| 10 | 21 | 31 | 694.15 ms | 1.32 ms |

The selector comparison uses the **same precomputed interval representation** for both exact and greedy selection; neither timing includes DAG extraction. The exact-versus-greedy objective differences are expected: greedy is approximate. The exponential growth is also explicit; these samples do not justify production-scale performance claims. Small workload comparisons against brute-force enumeration at n=15,k=3,r=0/2/4/6 all matched the exact optimum. Brute force was faster by r=6 because the brute search space remained small.

## 7. Novelty and external-validity audit

**Known prior art and potential claim collapse:**

1. O'Reach (Hanauer, Schulz, Trummer, ACM JEA 2022, S1–S3) already published the underlying exact supportive-vertex rules. https://doi.org/10.1145/3556540 . Official source: https://oreach.taa.univie.ac.at/
2. Classical interval stabbing, Monge DP, sweep-line segment trees, fixed-parameter branching and Vertex Cover reductions are standard algorithmic devices. None should be claimed as independently invented.
3. NP-hardness of general 2-interval/bundle hitting set is established, e.g. *Minimum Hitting Set of Interval Bundles: Computational Complexity and Approximability*, Algorithmica 2022. https://doi.org/10.1007/s00453-022-00964-6 . Our domain-specific graph construction could still be an independently useful correspondence, but novelty needs deeper checking.
4. Contemporary graph reachability survey: Zhang et al., *Indexing Techniques for Graph Reachability Queries*, ACM Computing Surveys, https://doi.org/10.1145/3776737 .

**What the present evidence supports:** a precisely stated reachability-indexing optimization subproblem with a constructive NP-completeness proof, exact interval characterization, linear-time graph preprocessing for DAGs, and an executable FPT-in-off-backbone-vertices algorithm. This is a coherent theoretical research *candidate*, not a confirmed novel theorem or publishable full paper.

**Important remaining work before a real submission:** systematic theorem-equivalence search beyond keywords; independent mathematical review and formal verification if worthwhile; tighter FPT algorithms or kernelization; improved algorithms for r>20; meaningful external DAGs with long backbones; O'Reach integration at equal preprocessing and memory budgets; compiled-language cross-benchmark; honest end-to-end query cost and index amortization; independent reproduction.

## 8. Reproduction

```bash
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone
python benchmark_backbone.py
```

The previous phases and experimental records remain in the package. The new phase contains `backbone.py`, `backbone_hardness.py`, `test_backbone.py`, `benchmark_backbone.py`, `phase3_results.json`, and this report.

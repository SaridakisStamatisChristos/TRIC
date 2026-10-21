# TRIC Phase VII — Equivalence-Class Compression of Frontier DP States

**Date:** 2026-10-21  
**Status:** Implemented local algorithm-engineering experiment; exactness differentially tested. Publication novelty **not established**.

## Provenance and audit correction

The first local reconstruction used **draft** Phase VI files. Two tests failed, but the draft blob hashes did **not** match GitHub PR #3. We reconstructed the published Phase VI from `TRIC_Phase_VI_Research_Final_2026-10-21.zip` and Phase V from `TRIC_Phase_V_Research_Final_2026-10-21.zip`, matched Git blob SHAs against the GitHub PR source (`adaptive_exact.py`: `c1f69370b4ea278db01590e653091a790a8fff4f`, `frontier_dp.py`: `f4b6fb5e229cd2b75e31f9fda264870e5ae4551b`), and reran the 31-test suite successfully. No current PR defect should be inferred from the stale draft.

## Precise problem

Given a discrete domain of `h` pivot positions, query signatures consisting of zero, one, or two inclusive integer intervals, nonnegative finite weights, and an **exact** pivot budget `k`, choose `k` distinct positions minimizing the total weight of signatures hit by no pivot. Empty signatures contribute an unavoidable constant. The same problem is produced by the SCC-backbone extractor in Phases III–VI. This is **certificate coverage**, not arbitrary graph reachability query evaluation.

## Candidate and algorithm

The Phase V/VI frontier state stores `(number_selected, literal_last_selected_position, prior_first_interval_bits)`. Every future interval completion tests only `literal_last_selected_position >= interval_start`, and the stored first-interval bits handle earlier disjoint cover events. At the cut following position `p`, only intervals `[a,b]` with `a <= p < b` can still depend on a **past** pivot. For other intervals, either the cost/bit was already finalized or they start after the cut and any past pivot fails automatically.

Let `A_p` be the **set of distinct left endpoints** of such currently active intervals. Two previous last-pivot values `l1,l2 <= p` are equivalent if for every `a in A_p`, `(l1 >= a) == (l2 >= a)`. There are at most `|A_p|+1` classes. The representative for any last pivot `l` is the largest `a in A_p` such that `a <= l`, or `-1` if none exists. `frontier_compact.py` normalizes to this representative after processing all query events at each position. It respects Phase V's recycled bit slots by processing *second* events before *first* events.

`optimize_compact_profile` computes optimal uncovered cost **and a witness** for each exact budget from zero through `max_k` in a single pass, preserving Phase VI's regional knapsack composition. Phase VII adds `engine='compact'` to Phase VI's adaptive entrypoints and a conservative automatic dispatch rule: use it on sufficiently long two-interval regions with few distinct start positions; otherwise keep orientation, classical frontier, and single-interval sweep engines. The rule is empirical and may be suboptimal on untested systems.

## Correctness argument

Proceed by induction over scanned positions. At the beginning of iteration `p`, the selected-pivot count and first-interval bitset are already equal between merged states, while every active interval `[a,b]` has the same Boolean value of `last >= a`. If we take pivot `p`, both histories acquire the same literal last position `p`; if we skip, comparisons for intervals ending now remain equal: each such interval with `a<p` crossed the previous cut and its left endpoint was a tracked threshold, while `a=p` is necessarily false for a skipped pivot. Thus both branches charge the same weights and update bitsets in the same way. After completing the events, intervals that ended at `p` are irrelevant to the future; intervals starting later than `p` cannot contain any past pivot. Quotienting last positions by `A_p` therefore preserves all future continuation costs. Standard Bellman state merging retains the minimum prefix cost and a reconstructable witness. Reading each final budget yields the exact optimum and distinct selected pivot positions.

This is a **mathematical argument** for the precisely stated optimization, not a formal proof-assistant check or independent discovery of a new complexity class.

## Complexity accounting

Let `w` be maximum simultaneously live two-interval certificate signatures; let `d=max_p |A_p|` be **active-start diversity**; `q` is the query-entry count; `h` is backbone length; `K` is the maximum requested exact budget. Under expected O(1) hash lookup and word-RAM bit operations:

- States per layer: at most `(K+1)(d+1)2^w`, rather than `(K+1)(h+1)2^w`.
- Event construction costs O(h+q); active-endpoint maintenance via ordered Python lists costs O(qd) worst-case; each DP successor uses `bisect_right` O(log(d+1)).
- Conservative runtime: `O(qd + (h+q)(K+1)(d+1)2^w log(d+2))`, suppressing Python bigint costs for large live-bit masks.
- Traceback memory: `O(h(K+1)(d+1)2^w + h + q)`, with objective-only rolling DP requiring `O((K+1)(d+1)2^w + h+q)`.

The implementation does **not** eliminate exponential dependence on `w`. When `d = Theta(h)`, the asymptotic state-count improvement disappears; the active-endpoint maintenance and dispatch overhead may make it slower. Computing all `K+1` budget witnesses incurs extra traceback reconstruction cost `O(hK)`, absorbed by the displayed polynomial bound for nontrivial h.

## Verification

```
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact test_frontier_compact
python benchmark_phase7_adaptive.py > phase7_adaptive_results.json
```

- 37 unittest methods passed locally in CPython 3.13.
- Exhaustive pairs of zero/one/two-interval signatures on domains of up to 4 positions, with all pivot budgets, checked against a separate brute-force combinatorial oracle.
- Seeded randomized workloads on domains up to 11 positions and budgets up to five, checking **both exact costs and validity of the pivot witness**.
- Regression and integration checks with Phase VI `frontier`, `orientation`, `compact`, and `auto` dispatcher variants and SCC cyclic backbone inputs.
- Budget-profile and terminal pivot-count invariants.

## Local paired performance (median of five runs)

Synthetic two-interval region: six weighted signatures, same h and k=5; both methods use Phase VI decomposition and exact budget convolution. The `frontier` column forces the previous exact frontier engine; `compact` changes only the internal frontier state representation. All measured objectives and reconstructed witness losses agree.

| h | Phase VI frontier (ms) | Phase VII compact (ms) | Internal speedup |
|---:|---:|---:|---:|
| 80 | 43.076 | 3.907 | 11.03× |
| 200 | 297.533 | 7.329 | 40.60× |
| 400 | 1355.710 | 12.731 | 106.49× |

The 400-position single-interval control uses Phase VI's interval-specialized engine in all cases and showed ~11.3–12.9 ms across requested engine modes, i.e., **no improvement**. More overlapping and diverse interval starts erode the gain. All raw samples and interpreter version are in `phase7_adaptive_results.json`. No compiled baseline, O'Reach comparison, random graph dataset, hardware reproducibility suite, or production benchmark was run. This is a **narrow local microbenchmark**, not a general speedup claim.

## Research precedence and paper readiness

**Existing work:** Hanauer, Schulz, and Trummer, *O'Reach* (SEA 2021), already supports the underlying positive/negative certificates. Aggarwal & Tokuyama (1998), *Consecutive interval query and dynamic programming on intervals*, covers earlier interval-specific DP optimization. More broadly, frontier/interval sweep state compression is an established family of techniques. A recent survey (Zhang, Bonifati, Özsu, ACM Computing Surveys 2025) covers 33 graph reachability indexing techniques. The 2026 paper *Efficient algorithms for the interval maximum coverage problem* chooses **intervals covering points** rather than **pivot points stabbing interval unions**, so it is related but *not an equivalent problem formulation*. See:

- https://doi.org/10.4230/LIPIcs.SEA.2021.13
- https://doi.org/10.1016/S0166-218X(98)00021-3
- https://doi.org/10.1145/3776737
- https://doi.org/10.1016/j.tcs.2026.115802

**Publication assessment:** the quotient-state bound and practical implementation are clearly specified and locally tested, but novelty is **unresolved** and likely incremental until a thorough mechanism-level audit identifies a previously unaddressed exact variant or a new lower/upper-bound separation. Required external work includes standard graph datasets, verified compiled O'Reach, index-building cost, memory, real query throughput, unfavorable workloads, and independent repetition. Avoid presenting any synthetic speedup as SOTA reachability throughput.

## Reproducibility and governance

Changes are intended for a new *stacked PR* based on Phase VI PR #3, itself based on PR #2 and PR #1. Do not merge any of these without code/proof review. The original source branches and benchmark data should remain intact.

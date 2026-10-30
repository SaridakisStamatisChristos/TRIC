# Fidelity to the source publications

PyReachability aims to be a *faithful* implementation of each published method: same algorithmic
idea, same index semantics, same query answers. **Every method is validated for exact correctness
against the BFS/DFS oracle** (property-based tests, hundreds of random graphs each), so no method
ever returns a wrong reachability answer.

> **Executable counterpart:** `tests/paper_examples/` transcribes each paper's
> running example (graph, highlighted queries and, where printed, the index
> labels) and asserts the implementation reproduces them. Method files still
> unfilled are reported as skipped tests.

Where an implementation departs from the paper, the departure is one of four kinds:

- **Faithful** — the construction and the produced index match the paper (up to tie-breaking).
- **(B) Speed-only** — the produced index / query answers are equivalent to the paper, but a
  construction or query *subroutine* is the simpler textbook version rather than the paper's
  engineered one (slower, but same result). Often the paper itself offers the simpler option.
- **(A) Index differs** — the produced index differs in *size/structure* from the paper's
  (queries still exact), because a construction *choice* (which spanning tree, which dummy
  scheme, which parameter) was simplified.
- **(C) Correction** — the source text is *wrong as written*, and we implement the corrected
  algorithm instead. This is the only kind where being faithful to the text would be a bug.
  It demands more than the others: the defect, a counterexample, the fix, and the evidence
  that distinguishes them must all be recorded, because the code will not match its own
  citation and the next reader has to be able to check the claim rather than take it.

This page documents the per-method status. Methods not listed (BFS/DFS, TC, Tree Cover, GRAIL,
FELINE, PLL, BFL, Chain Cover, TOL, DL) are faithful.

**Among the survey's Table 1 techniques, there are no remaining (A) deviations:** every one of
them now produces the paper's index structure. Their only remaining deviations are **(B)
speed-only** — a construction or query *subroutine* is the simpler textbook version (same index,
same answers) — confined to query-time data structures (e.g. a linear residual/segment scan
instead of an O(log²k) structure) and one slower-but-equivalent build. The table rows marked
*faithful* were aligned to the publications in the course of this work.

The one **(C)** entry is Feline-PK, which is not a Table 1 technique — see its section below.

## Summary

| Method | Paper's construction / structure | Our implementation | Deviation |
|---|---|---|---|
| 2-Hop | greedy set cover; densest subgraph by linear 2-approx | greedy set cover; densest subgraph by linear 2-approx | faithful |
| 3-Hop | TC contour + factorization; rank-subgraph densest search (§4.3); O(log²) segment query | TC contour + factorization with rank-subgraph search (§4.3, rank-ordered queue); linear segment lookup | (B) query speed |
| TFL | topological folding with lazily-created **shared** dummy vertices (Procedure 1) | Procedure 1 (shared lazy dummies) | faithful |
| HL | recursive backbone with ε=2 (FastCover) | recursive FastCover backbone, ε=2 (Formulas 4-5) | faithful |
| O'Reach | slim/central supportive-vertex selection; B2/B4/B5/B6 + T1-T6 + S1-S3; pruned bidirectional BFS | same — slim-level selection, WCC (B2), all observations in the paper's test order, pruning bidirectional BFS | faithful |
| Path-Hop | **optimal** tree cover + multi-interval labeling | Agrawal optimal tree cover; greedy whole-Pred/Succ hop density | (B) slow build |
| Ferrari | Ferrari-L **and** Ferrari-G (global budget); seed + topological pruning | both variants (c-param), max-τ tree cover, seed pruning + topological level filter | faithful |
| Dual-labeling | a spanning tree + minimal-equivalent-graph reduction (§5); O(1) TLC counting via gridding/snapping | minimal-equivalent-graph + DFS spanning tree; O(1) gridded TLC query | faithful |
| Tree+SSPI | tree-cover via **DFS traversal**; SSPI | DFS tree-cover; SSPI (inheritance resolved at query) | (B) query speed |
| GRIPP | hop technique + advanced 4-case pruning | hop technique + advanced 4-case pruning (ascending-order traversal) | faithful |
| Path-Tree | **Edmonds** max-weight SP-tree; minimal-equivalent-edge-set; O(log²k) query | Edmonds max-weight SP-tree (MinPathIndex weights); all SP-tree-pair edges; linear residual scan | (B) query speed |
| IP | k-min-wise labels + Level label + Huge-Vertex label | k-min-wise + Level label (Lup+Ldown) + Huge-Vertex label | faithful |
| PReaCH | contraction hierarchies + Lemmas 2–7 pruning | contraction hierarchies + Lemmas 2–7 (all single-DFS cuts) | faithful |
| Optimal Chain Cover | minimum chains via **O(n²+bn√b)** stratification + virtual-node matching | minimum chains via **Hopcroft-Karp** matching over full reachability (no stratified bipartite graphs) | (B) speed (same minimum) |

## Notes per deviation

**2-Hop (Cohen, Halperin, Kaplan, Zwick, 2003).** Faithful. The paper casts minimum 2-hop as a set
cover and, each round, computes for every center `w` the center-graph and its densest subgraph,
chooses the best ratio, updates the uncovered set, and repeats — exactly the flow we implement. The
densest subgraph uses the paper's linear-time 2-approximation (drop the min-degree vertex, keep the
densest snapshot). Minimum 2-hop is NP-hard and this greedy is within a logarithmic factor of
optimal; construction is inherently expensive (the paper itself states this — recomputing the center
graphs each round is the published algorithm, not a simplification), so it is a small/medium-graph
method.

**3-Hop (Jin, Xiang, Ruan, Fuhry, 2009).** Construction = TC contour + greedy factorization whose
core is a densest-subgraph search. We use the paper's §4.3 method: the densest subgraph is
approximated by the **rank subgraph** (Def. 7 — the l-core/degeneracy core, a 2-approximation by
Lemma 1), and the per-round selection follows Algorithm 2 / Theorem 3 — the chain-center bipartite
graphs are held in a rank-ordered max-heap and the maximum-rank one is chosen each round, with ranks
lazily recomputed over the uncovered contour pairs. The only remaining deviation is query-side: a
per-chain anchor segment lookup rather than the paper's O(log²) structure. The survey notes 3-Hop's
indexing cost is inherently high ("less applicable" to large graphs).

**HL (Jin & Wang, 2013).** Faithful. The recursive reachability backbone is discovered by FastCover
(Jin, Ruan, Dey & Yu, *SCARAB*, SIGMOD 2012) at the paper's default locality threshold ε=2: the
one-side condition (SCARAB Lemma 5) covers every distance-ε pair through a backbone member within ε
hops on each side, with the recommended (in-degree × out-degree) selection order. Backbone edges keep
pairs within distance ε+1; the core graph is labeled with a vertex-id 2-hop and labels propagate down
by Formulas 4–5 (the ⌈ε/2⌉-hop neighbours plus the nearest-backbone label sets Bout^ε / Bin^ε). ε is
exposed as a constructor parameter (`HL(eps=...)`, default 2).

**O'Reach (Hanauer, Schulz, Trummer, 2021).** Faithful. Forward/backward topological levels,
weakly-connected components (Observation B2), `t` extended topological orderings started from
sources (Observations B4, T1–T6), and `k` supportive vertices with full R⁺/R⁻ (Observations S1–S3)
are all implemented, and the constant-time tests run in the paper's prescribed order (B5/B6 → S1 →
first ordering → S2/S3 → remaining orderings → B2). Supportive-vertex selection follows the paper's
most-successful strategy: candidates are the vertices on slim forward/backward levels (≤ `h` each),
capped at `kp` and filled at random from central forward levels, then the top-`k` by |R⁺(v)|·|R⁻(v)|.
The inconclusive-query fallback is the paper's pruning bidirectional BFS (each newly seen vertex is
tested with the observations: positive ⇒ answer yes, negative ⇒ prune). Defaults match the paper
(k=16, p=75, h=8, t=4).

**Spanning structure per paper (verified).** The tree-cover-family methods differ in which tree the
*authors* use, so we follow each one:
- **Tree Cover (Agrawal, 1989)** and **Path-Hop (Cai & Poon, 2010)** use Agrawal's *optimum tree
  cover* (Path-Hop reuses Agrawal's multi-interval labeling). We build exactly that (shared
  `optimal_tree_parent`: each node's tree parent is the in-neighbour with the largest predecessor
  set). Faithful.
- **Tree+SSPI (Chen et al., 2005)** builds its tree-cover by a *depth-first traversal*; we use a DFS
  tree-cover too. Faithful tree; the only deviation is that we store each vertex's own non-tree
  predecessors and resolve the paper's predecessor *inheritance* at query time (same answers).
- **Dual-labeling (Wang et al., 2006)** uses "a spanning tree" (no specific algorithm mandated; we
  use DFS) over the §5 *minimal-equivalent-graph* (the unique transitive reduction of the DAG), to
  shrink the non-tree edge set `t`. Queries now use the paper's Dual-I O(1) TLC counter: the count
  function `N(x,y)` is precomputed on a grid (columns = distinct link x-coordinates, rows = gaps
  between distinct link break-points), and `N(a_u,pre_v) - N(b_u,pre_v) > 0` is evaluated by two O(1)
  grid look-ups after snapping coordinates (Sec. 3.2-3.3). Faithful.
- **Path-Tree (Jin et al., 2011)** uses an *Edmonds maximum-weight* SP-tree over the weighted
  path-graph; we build exactly that (Chu-Liu/Edmonds with the paper's MinPathIndex weights
  `w_{Pi→Pj}=|Pi[→u]|`, virtual-root spanning forest). The remaining deviations are query-side only:
  cover reachability uses all edges of a tree path-pair instead of the *minimal equivalent edge set*
  (reachability-equivalent — and the per-vertex residual `Rc` is domination-minimised regardless, so
  the stored index is unaffected), and the residual is scanned linearly instead of the paper's
  O(log²k) gridding query.

**Ferrari (Seufert et al., 2013).** Faithful. The tree cover uses the paper's heuristic (each
vertex's parent is the in-neighbour with the highest topological-order number). Both indexing
variants are implemented, unified by the constant `c≥1`: `c=1` is Ferrari-L (per-vertex budget
`|I(v)|≤k`); `c>1` is Ferrari-G (Algorithm 2 — deferred merging with a `ck`-interval cover and a
degree min-heap restricting nodes to a `k`-cover once the global budget `B=kn` is exceeded; default
`c=4`). The optimal `k`-interval cover keeps the largest gaps as separators (Def. 3). Pruning uses
the GRAIL topological level filter and seed-based pruning (`seeds` max-degree seeds, default 32; the
`S⁺/S⁻` bitsets give the positive cut `S⁺(s)∩S⁻(t)≠∅⇒reachable` and negative cut "a seed reaches s
but not t ⇒ unreachable"). The only remaining deviation is query-side: the approximate-interval
fallback is a guided DFS rather than the paper's plain recursive expansion (same answers).

**GRIPP (Trißl & Leser, 2007).** Faithful. The hop technique plus the paper's advanced relative-
position pruning (Sec. 4.2): hop nodes are expanded in ascending order-tree position via a min-heap,
and each candidate hop node `h` is pruned against the set `U` of already-used hop ranges by the four
cases of Fig. 4 — (a) already used / (b) `h`'s tree instance inside some `u∈U` ⇒ skip `h`; (c) some
`u∈U` nested inside `RIS(h)` ⇒ skip that sub-range during the scan; (d) sibling ⇒ full scan.

**IP (Wei, Yu, Lu, Jin, 2014).** Faithful. The k-min-wise permutation labels plus both additional labels
of Sec. 6: the **Level label** (forward `Lup` and backward `Ldown` topological levels — negative
cuts) and the **Huge-Vertex label** `Lhv(v)` (Algorithm 3: up to `h` largest-out-degree vertices
with out-degree > `µ` that reach `v`). During the DFS, at a huge current vertex `c`: `c∈Lhv(v)` ⇒
reachable; `c∉Lhv(v)` with `Lhv(v)` not full, or `c` outranking its smallest member by out-degree, ⇒
unreachable (Algorithm 4 lines 4–7). Defaults `h=5, µ=100` (the paper's).

**PReaCH (Merz & Sanders, 2014).** Faithful. Contraction-hierarchy ordering, forward/backward
topological levels (Lemma 2), and all of the single-DFS range cuts: the DFS interval `[φ,φ̂]`
(Lemmas 3–4), the largest reachable range outside the subtree `ptree` (Lemma 5, positive), the
smallest reachable DFS number `φ_min` (Lemma 6, negative), and the empty range just left of `v`
`φ_gap` (Lemma 7, negative). All ranges are derived from a single DFS per direction and applied
aggressively (constant-time block and bidirectional search) for both forward and backward.

**Optimal Chain Cover (Chen & Chen, 2008).** The produced index is identical to the paper's: the
*minimum* chain decomposition (verified to equal the Dilworth width). The maximum matching uses the
**Hopcroft-Karp** algorithm (O(e√n)) — the matching algorithm the authors specify. We run it over
the full reachability bipartite graph rather than building their stratified bipartite graphs with
virtual nodes (a construction that reduces the edge count); same minimum number of chains, same index.

### Feline-PK — the thesis's Alg. 10 reorder is not implemented as written

**Status: faithful to the method, deliberately unfaithful to the text's reorder.**

Two coupled departures, both in the "SCC unchanged" branch, both about how finely
the reorder is applied. Everything else — the four partial δ sets, the E_DAG
update, the whole "SCC changed" branch — is the thesis as written.

**Line 11, the operator.** The thesis reorders δ with `constrói_indice(δ, E_DAG ∩ δ²)`:
a from-scratch topological sort of the induced sub-DAG, re-stamped into δ's own
slots. Unsound — a fresh order may rank two δ-vertices that are *incomparable* in
the sub-DAG differently from before, letting a δ-vertex jump over a vertex that is
inside the affected band but outside δ, which stays fixed, inverting a live edge.
We use a structured merge instead: δ_in takes the lowest of δ's own slots and δ_out
the highest, each group keeping its internal order, so δ_in only moves down and
δ_out only up and no fixed neighbour is ever crossed.

**Line 9, the granularity.** The thesis unions the four partial sets into a single δ
and permutes both axes from it. But those sets are per-axis, and the union destroys
the separation: a vertex entering δ only for violating Y still has its X slot reused
from the shared pool, which can break a live edge on X — an axis that was never
violated. We run one single-axis phase per violated axis instead.

The two are coupled: the structured merge is defined per axis, so adopting it leaves
the single δ of line 9 nowhere to go. This is also what the 2014 reference
implementation does — i.e. the design the thesis intended.

**Evidence.** An all-pairs BFS oracle, checked after every insertion over 200
randomised runs, *fails* for the text as written (counterexample 10 → 6), *fails*
for the operator alone with δ still shared (counterexample 5 → 8 on edge (11,7)),
and *passes* only for both together. Neither defect is visible by inspection: both
preserve correct answers on the small fixed examples used to illustrate them.

**Independent confirmation of the same methodology.** The thesis-reorder departure
above is the *known, deliberate* one — but our own test-writing process reproduced
its central finding independently, on an unrelated line of code. While mutation-testing
`fold_cycle`'s bookkeeping (the routine that re-wires E_DAG when an insertion folds a
cycle into one SCC), commenting out the I-side re-wiring line broke `fold_cycle`
without any *static* fixed-graph test noticing — but `test_update_sequences_agree_with_the_oracle`
(the same "all-pairs oracle, checked after every update" methodology used above)
caught it unprompted, with a 3-operation falsifying example
(`ops=[(True, 0, 2), (True, 1, 0), (True, 2, 0)]`). The reason is structural, not
incidental: `fold_cycle`'s own invariant is that folded members keep their pre-fold
coordinates, so a single `build()`-then-`query()` snapshot can look correct by pure
coordinate dominance even when the DAG bookkeeping underneath it is broken — only a
*later* structural change exposes the corruption. That is why every dynamic-method
oracle in this codebase checks after each individual update rather than once at the
end of a sequence.

Full analysis: `paper_felinepk/feline-pk-alg10.pdf` (private).

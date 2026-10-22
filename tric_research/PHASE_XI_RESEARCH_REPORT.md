# Phase XI — Bounded SCC Closure and Research CI Gap Diagnosis

## Decision
The Phase X pilot compared TRIC's small pivot-index plus exact fallback DFS to
O'Reach's considerably stronger directed-reachability index, and measured a
large gap. A single timing ratio does not reveal why the gap exists.

Phase XI adds a **separate** exact transitive-closure experiment on the graph's
strongly connected component (SCC) condensation. It does not replace the
existing pivot index, invent a new reachability method, or establish a SOTA claim.

## Algorithm
1. Iterative two-pass SCC decomposition (no recursion depth dependence).
2. Build the condensation DAG.
3. Topologically order its vertices.
4. In reverse topological order, OR outgoing components' bitsets into the
   current component's bitset; include the component itself.
5. Answer each query by testing the target SCC's bit in the source SCC's row.

For C SCCs and M condensation arcs, constructing the reachability bit-matrix
takes O((C+M)ceil(C/64)+|V|+|E|) 64-bit-word operations, plus SCC work,
with O(Cceil(C/64)) 64-bit words of matrix storage and additional O(V+E+M)
graph/SCC storage. Arc deduplication is not performed, so repeated edges
affect the build time. These bounds are word-RAM bounds; they are not novel.

The `max_bytes` guard limits **only the bit-matrix allocation**. A 64 MiB
matrix cap is the default. It does not bound whole-process RSS. If the
matrix would exceed the cap, the optional closure is unavailable and
the existing TRIC policies continue to be benchmarked unchanged.

## Test and experiment protocol
- Four tests exercise random digraphs (including cyclic), SCC collapse,
  a 4096-node directed path, cap=0, and memory-cap refusal.
- The native program additionally validates each materialized closure
  answer against its independent graph search for every held-out query.
- Native timing samples include repeated query batches (128 passes)
  to reduce timer-overhead distortion for nanosecond-scale lookups.
- Native `closure` JSON separately records availability, SCC count,
  matrix bytes, preprocessing milliseconds, latency, and checksum.
- The O'Reach-vs-TRIC driver records the closure alongside original
  pivot/BFS and O'Reach results on precisely the same query input.

## Critical limitations
- Transitive closure is a standard algorithm. Any latency win purchased
  with more memory is a trade-off, **not** matched-budget superiority.
- The construction algorithm is exact for static graphs, not dynamic
  reachability updates. Larger SCC counts may make the method unsuitable.
- Repeating the same query batch favors cache-resident lookup. Compare
  O'Reach and TRIC with cache, query count, workload and memory disclosed.
- GitHub-hosted CI runners are not dedicated machines; replicate on
  controlled hardware before publication.
- O'Reach correctness checks are still not independent per-query output
  checks in this harness; TRIC outputs are independently checked.
- End-to-end total cost must include pivot generation, TRIC training, both
  index builds, and the anticipated number of future queries.

## Reproduction

```bash
cd tric_research
python -m unittest -v test_closure_index
python -m unittest -q test_tric test_path_monge test_path_sweep \
  test_backbone test_backbone_scc test_frontier_dp test_adaptive_exact \
  test_frontier_compact test_ordered_probe test_native_benchmark \
  test_oreach_ci test_closure_index
```

The GitHub Actions workflow `.github/workflows/research-oreach.yml`
compiles O'Reach at a pinned commit and runs the research comparison.

**Research status:** exactness experimentally checked; global novelty absent
for basic closure; external reproducibility and comparative performance
depend on the CI evidence for this exact commit.

# Native exact reachability

`tric_research/tric_reachability.h` provides a C++17, standard-library-only index
for static directed graphs. Vertices are contiguous integers `[0,n)`. Cycles,
parallel edges and isolated vertices are supported. Reachability is reflexive:
every vertex reaches itself. Invalid edges or query endpoints throw exceptions.

```cpp
#include "tric_research/tric_reachability.h"
#include <iostream>
int main() {
    std::vector<std::vector<int>> graph{{1}, {2}, {}, {}};
    TricReachability index(graph, 2 * 1024 * 1024);
    std::cout << index.reaches(0, 2) << " "  // 1
              << index.reaches(2, 0) << " "  // 0
              << index.reaches(3, 3) << "\n"; // 1
}
```

Compile from the repository root: `g++ -std=c++17 -O3 example.cpp -o example`.
The index owns a snapshot; later input changes do not update it. An instance
reuses mutable fallback scratch. Use one instance per querying thread.

## Routing and budgets

The automatic index computes strongly connected components (SCCs) once. It
constructs a direct global bit matrix when that table fits. Otherwise it hands
the same decomposition to `PartitionedReachability`; there is no second SCC pass.
Routing uses the graph and budgets, with no query training or horizon input.

The partitioned index splits the SCC DAG by weak connectivity, then chooses the
smaller chain-label / bitset payload per partition. If neither fits, it first
tries exact unions of DFS intervals. These are built from complete child rows in
reverse topological order, without a dense intermediate. A failed attempt rolls
back its rows and payload before trying lossless word compression. If that also
refuses the budget, the partition retains exact topologically bounded search.

Each original vertex keeps one 32-byte label. A 64-bit descendant signature
occupies the former padding: a missing descendant bit proves a negative answer,
but a matching signature never proves reachability. DFS subtree containment is
an exact positive certificate. Remaining queries use the selected exact table or
search. The search route also retains both longest-path bounds, packed into two 16-bit
fields. Saturation weakens pruning without changing answers. Chain IDs and
search SCC IDs share one field because those routes are mutually exclusive;
the full label still occupies 32 bytes.

The default allowance is **2 MiB of table payload**, including compressed row
descriptors and IDs. This is **not a total-RSS cap**. Fixed metadata, vector
capacity, graph input, SCC / DAG construction, allocator overhead and scratch are
additional. Index construction has a distinct default **64 MiB scratch allowance**
for a dense compression matrix or the two interval-union buffers. The allowance
bounds their requested payload, not all constructor allocations. Set the third
constructor argument to zero to disable both attempts. Even 16 bytes of union
scratch can index a wide forest when its final interval payload fits.
`table_bytes()` reports payload and `retained_bytes()` reports actual retained
object/vector capacity, excluding input and allocator metadata. A refused table
changes time and space costs, never exactness.

Use `PartitionedReachability` directly to prefer its partition-local space savings
over automatic direct closure. `uses_direct_closure()` exposes automatic routing.
No single strategy is fastest on every graph or request horizon.

## Cost and evidence

For a partition with s SCCs and k covering paths, chain storage is O(s*k) 32-bit
entries; dense storage is O(s*ceil(s/64)) 64-bit words. An interval table with R
stored ranges uses 8*s + 8*R bytes on the tested toolchain. Rows are sorted,
disjoint half-open intervals in DFS preorder, including all reachable SCCs.
Interval construction merges child rows and may inspect many ranges per edge;
it is not guaranteed linear. The table and scratch budgets bound storage, and
refusal preserves exactness. Sparse-word and interval queries use binary search;
chain and dense-bit queries use constant-time membership. A refused partition
can still require linear graph search. Preprocessing can outweigh query savings.

SCCs, chain/path reachability, bitset closure, sparse storage, Bloom-style negative pruning, DFS intervals and
transitive-edge skipping are established techniques. This implementation combines
them for TRIC; it does not establish new theory, algorithmic novelty, production
readiness or generalized SOTA. See [the companion research report and raw CI
comparisons](https://github.com/SaridakisStamatisChristos/TRIC/pull/23).

Run original and new correctness tests:

```bash
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_native_runtime
```

The native checker independently BFS-verifies 18,432 exhaustive three-vertex
query/cap cases for **both** automatic and partitioned indexes, plus 1,440 larger
adversarial cases and 589,824 checks across all 4,096 members of a 12-variable-arc
DAG family extended to 160 vertices to exercise interval routing. Python tests additionally exercise random relabeled graphs,
long paths, cycles, duplicate/transitive arcs, sparse/dense representation choice,
partial refusal, interval rollback, 100,000-vertex indexing beyond the dense
scratch limit, invalid inputs and public-API boundaries. The optional original
BFL comparator is independently BFS-verified on cyclic and acyclic inputs. CI runs both Python
versions and address/undefined-behavior sanitizers. These are bounded tests and
an independent oracle, not a machine-checked proof for all graphs.

The Phase XXV comparison harness, pinned input bytes, raw trials and limits are
in `tric_research/evidence/phase25/` and `tric_research/PHASE_XXV_RESEARCH_REPORT.md`.
The benchmark-only BFL source retains its upstream MIT license and is not a
runtime dependency. Build the comparator with:

```bash
g++ -std=c++17 -O3 -DNDEBUG -DTRIC_WITH_BFL \
  tric_research/native_compare_bench.cpp -o /tmp/tric-compare
```

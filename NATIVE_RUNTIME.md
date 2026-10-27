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
constructs a direct global bit matrix when that table fits. Otherwise it checks
whether the condensation has at most one distinct predecessor per SCC or at
most one distinct successor per SCC. Such forests use exact DFS dominance
labels: one 64-bit word per original vertex, constant-time queries and no closure
table. The temporary forest payload is 20 bytes per SCC and must fit the scratch
allowance. On refusal, the same SCC decomposition goes to
`PartitionedReachability`; there is no second SCC pass. Routing uses only the
graph and budgets, with no query training or horizon input.

The partitioned index splits the SCC DAG by weak connectivity, then chooses the
smaller chain-label / bitset payload per partition. If neither fits, it first
tries exact unions of DFS intervals. These are built from complete child rows in
reverse topological order, without a dense intermediate. A failed attempt rolls
back its rows and payload before trying lossless word compression. If that also
refuses the budget, the partition retains exact topologically bounded search.
Chain construction skips a child merge only when a complete inherited row
already covers that child. The source's own-chain membership threshold is
tracked separately from inherited coverage, since membership alone does not
prove that descendants on other chains were merged. Phase XXIX repairs a
false-negative bug in this distinction and adds a 160-vertex counterexample.

The general partitioned backend keeps one 32-byte label per original vertex. Its 64-bit signature packs a
32-bit descendant filter and the complement of a 32-bit ancestor filter. One
subset check tests both necessary conditions; collisions weaken rejection and
never prove reachability. Interval-mode labels cache the widest exact closure range in existing fields,
retain the same Bloom prefix, and search only the remaining ranges on a miss.
Their negative group tag distinguishes this format; label/table sizes do not
grow. Other modes retain the original local-order and DFS fields.
After all closure unions finish, a stable rotation moves the widest range to
row position zero. The remaining ranges stay sorted; ties keep the earliest
range. Selection uses SCC-coordinate width, not observed queries or original
vertex frequency. This adds O(R) construction work over R stored ranges and no
additional allocation or retained payload.

The common query function performs endpoint validation, Bloom rejection and
cached-range membership. Residual interval search and the other representation
paths live in separate private helpers. GCC/Clang and MSVC receive a `noinline`
hint on those helpers to prevent their bodies from enlarging the common path.
Other compilers use their ordinary inlining policy. This changes neither
answers, storage, construction nor asymptotic costs; its speed benefit depends
on the compiler and workload. Phase XXX measures GCC 13.3 on one shared host.

DFS subtree containment is an exact positive
certificate. Remaining queries use the selected exact table or search.

Interval partitions copy their row offset and count into existing label fields,
avoiding a dependent row lookup. Other modes reuse those fields for the chain or
SCC ID and two saturating 16-bit longest-path bounds. Saturation weakens search
pruning without changing answers. After all labels are materialized, the interval
row directory is released. Its bytes still count during construction admission;
they are not re-spent on later partitions. This reduces retained storage without
changing the selected representations or increasing admission capacity.
Ancestor construction adds a temporary 8-byte entry per SCC and one DAG pass.
The full label still occupies 32 bytes.

The default allowance is **2 MiB of table payload**, including compressed row
descriptors and IDs. This is **not a total-RSS cap**. Fixed metadata, vector
capacity, graph input, SCC / DAG construction, allocator overhead and scratch are
additional. Index construction has a distinct default **64 MiB scratch allowance**
for the forest's component arrays, a dense compression matrix or the two
interval-union buffers. It bounds each attempt's requested temporary payload,
not all constructor allocations. Set the third argument to zero to disable
those attempts; existing chain/bitset tables and exact fallback remain available.
Even 16 bytes of union scratch can index a wide forest through the general
partitioned backend when its final interval payload fits. Forest labels reuse
less metadata than the existing 32-byte general labels; they are not an
additional closure table hidden from the payload cap.
`table_bytes()` reports payload and `retained_bytes()` reports actual retained
object/vector capacity, excluding input and allocator metadata. A refused table
changes time and space costs, never exactness.

Use `PartitionedReachability` directly to prefer its partition-local space savings
over automatic direct closure. `uses_direct_closure()` and `uses_forest_index()`
expose automatic routing.
No single strategy is fastest on every graph or request horizon.

## Cost and evidence

For a partition with s SCCs and k covering paths, chain storage is O(s*k) 32-bit
entries; dense storage is O(s*ceil(s/64)) 64-bit words. An interval table with R
stored ranges uses 8*s + 8*R bytes during construction admission and retains 8*R
table bytes after releasing the directory, on the tested toolchain. Rows contain
disjoint half-open intervals in DFS preorder, including all reachable SCCs.
They are sorted during union construction; the final row has its cached range
first and a sorted residual suffix.
Interval construction merges child rows and may inspect many ranges per edge;
it is not guaranteed linear. The table and scratch budgets bound storage, and
refusal preserves exactness. Sparse-word and interval queries use binary search;
chain and dense-bit queries use constant-time membership. A refused partition
can still require linear graph search. Its retained adjacency uses CSR offsets
and flat arcs, reducing vector-header overhead; reverse adjacency is freed
before CSR allocation. Preprocessing can outweigh query savings. Forest
construction is linear in input size, with 8 bytes per original vertex retained
plus constant object storage; shared SCC/input and temporary arrays are separate.

SCCs, chain/path reachability, bitset closure, sparse storage, Bloom-style negative pruning, DFS intervals and
transitive-edge skipping are established techniques. This implementation combines
them for TRIC; it does not establish new theory, algorithmic novelty, production
readiness or generalized SOTA. See the [latest native qualification report](tric_research/PHASE_XXX_RESEARCH_REPORT.md).

Run original and new correctness tests:

```bash
cd tric_research
python -m unittest -q test_tric test_path_monge test_path_sweep test_backbone test_native_runtime
```

The native checker independently BFS-verifies 18,432 exhaustive three-vertex
query/cap cases for **both** automatic and partitioned indexes, plus 1,440 larger
adversarial cases and 589,824 checks across all 4,096 members of a 12-variable-arc
DAG family extended to 160 vertices to exercise interval routing. Another 207,360
checks enumerate both orientations of all 720 six-SCC forests with aliases and
duplicate arcs; 1,296 coordinate cases test packed comparisons through INT_MAX.
Another 153,600 all-pairs checks cover cross-linked chains, relabeling and
three budgets to prevent recurrence of the chain inheritance error.
Python tests additionally exercise random relabeled graphs,
long paths, cycles, duplicate/transitive arcs, sparse/dense representation choice,
partial refusal, interval rollback, 100,000-vertex indexing beyond the dense
scratch limit, invalid inputs and public-API boundaries. The optional original
BFL, PLL and PPL comparators are independently BFS-verified on cyclic and acyclic inputs. CI runs both Python
versions and address/undefined-behavior sanitizers. These are bounded tests and
an independent oracle, not a machine-checked proof for all graphs.

The Phase XXV comparison harness, pinned input bytes, raw trials and limits are
in `tric_research/evidence/phase25/` and `tric_research/PHASE_XXV_RESEARCH_REPORT.md`.
The subsequent query-path comparison, complete ablations and remaining losses
are in `tric_research/PHASE_XXVI_RESEARCH_REPORT.md` and
`tric_research/evidence/phase26/`. Forest/CSR scale qualification, original PLL/PPL
comparisons, rejected variants and all regressions are documented in
`tric_research/PHASE_XXVII_RESEARCH_REPORT.md` and `tric_research/evidence/phase27/`. The subsequent first-range cache, matched
compiler-dependency checks and complete qualification are in
`tric_research/PHASE_XXVIII_RESEARCH_REPORT.md` and `tric_research/evidence/phase28/`.
The widest-range cache, rejected traversal/filter-order experiments, fresh
synthetic checks and repeated external comparisons are in
`tric_research/PHASE_XXIX_RESEARCH_REPORT.md` and `tric_research/evidence/phase29/`.
The query-function separation, 15 alternative implementations, and complete
paired qualification are in `tric_research/PHASE_XXX_RESEARCH_REPORT.md` and
`tric_research/evidence/phase30/`.
The benchmark-only BFL and PLL/PPL sources retain their upstream MIT licenses and are not
runtime dependencies. Build the comparator with:

```bash
g++ -std=c++17 -O3 -DNDEBUG -DTRIC_WITH_BFL \
  tric_research/native_compare_bench.cpp -o /tmp/tric-compare
```

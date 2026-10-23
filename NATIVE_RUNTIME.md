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

The automatic index first tries `BoundedClosure`: iterative SCC condensation and
a direct global bit matrix. If that table fits the allowance, membership takes
constant time. If refused, release it and construct `PartitionedReachability`.
Both SCC passes count toward preprocessing; no training or query horizon is used.

The partitioned index splits the SCC DAG by weak connectivity, then chooses the
smaller chain-label / bitset payload per partition. If a dense table does not fit,
it can be compressed losslessly into dense suffix or sorted nonzero-word rows.
Two longest-path level bounds reject impossible pairs before table access.
A refused partition always retains exact topologically bounded search.

The default allowance is **2 MiB of table payload**, including compressed row
descriptors and IDs. This is **not a total-RSS cap**. Fixed metadata, vector
capacity, graph input, SCC / DAG construction, allocator overhead and scratch are
additional. Compression has a distinct default **64 MiB dense scratch allowance**;
set the constructor's third argument to zero to disable that temporary matrix.
`table_bytes()` reports payload and `retained_bytes()` reports actual retained
object/vector capacity, excluding input and allocator metadata. A refused table
changes time and space costs, never exactness.

Use `PartitionedReachability` directly to prefer its partition-local space savings
over automatic direct closure. `uses_direct_closure()` exposes automatic routing.
No single strategy is fastest on every graph or request horizon.

## Cost and evidence

For a partition with s SCCs and k covering paths, chain storage is O(s*k) 32-bit
entries; dense storage is O(s*ceil(s/64)) 64-bit words. Sparse rows use binary
search in nonzero word IDs. Table queries take O(1) or O(log ceil(s/64)); a refused
partition can require linear graph search. Preprocessing and memory remain
substantial and can outweigh gains on short query streams.

SCCs, chain/path reachability, bitset closure, sparse storage, level pruning and
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
adversarial cases. Python tests additionally exercise random relabeled graphs,
long paths, cycles, duplicate/transitive arcs, sparse/dense representation choice,
partial refusal, invalid inputs and public-API boundaries. CI runs both Python
versions and address/undefined-behavior sanitizers. These are bounded tests and
an independent oracle, not a machine-checked proof for all graphs.

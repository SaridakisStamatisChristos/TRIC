# Stable SCC transpose: proof sketch and executable obligations

This is a representation change to iterative Kosaraju, not a new SCC algorithm.
The argument below is a conventional proof sketch, not a machine-checked proof.

Assume an immutable finite adjacency-list graph with `n <= INT_MAX` vertices and
valid integer endpoints. Repeated arcs and self loops are permitted. Empty graphs
return with the same empty component vector and zero component count. Invalid
endpoints still throw before DFS; excessive vertex counts still throw.

For each vertex `v`, counting builds `reverse_offsets[v+1] = indegree(v)`.
Checked prefix sums therefore give disjoint half-open ranges whose lengths equal
those indegrees and whose union contains exactly `m` entries. Copying the offsets
into cursors, then scanning original vertices and their adjacency lists in their
original order, writes each predecessor into its vertex's next unused slot.
Each cursor ends at the following offset. Thus every range equals, element for
element, the old `reverse_graph[v]` produced by `push_back` in the same scan.
The temporary cursor vector is destroyed before traversal begins.

The first DFS reads only original adjacency and is unchanged. Its finish order
is identical. In the second DFS, the outer finish iteration, stack operations,
visited conditions and predecessor iteration order are identical. Induction on
stack transitions gives identical visited/component states after every step.
Consequently both the SCC partition and the actual integer component IDs are
identical, not merely equivalent under renumbering. Existing condensation-order
assumptions remain valid. Downstream admission, vertex labels and query source
are unchanged.

The transpose takes O(n+m) time and O(n+m) temporary space. Avoiding individually
growing predecessor vectors can reduce allocator work. Performance and peak
allocation are empirical claims and must pass the separate frozen gates; this
proof does not imply a universal speedup or a universal peak-memory bound.

Executable obligations preserved with this campaign:

- 8,000 seeded multigraphs, including empty graphs and arbitrary cycles, plus
  forward and reverse 200,000-vertex paths: exact baseline component-vector and
  count equality, under UBSan.
- Two invalid-endpoint rejection checks.
- Existing exhaustive and adversarial native reachability checks using independent
  BFS, also under UBSan.
- 52 allocation cases, including zero-budget, rollback, aliases, direct, forest,
  interval, compressed and search routes. Compare retained allocations and route
  statistics; require no observed construction peak growth.
- Every timed process independently checks its query answers with BFS after the
  timed interval. Query checksums and retained storage must match across arms.

The first CSR prototype allocated 16 bytes on the empty graph, versus zero for
the baseline. That resource failure is preserved. CSR v2 adds the empty return
before allocating offsets and has a separate frozen qualification protocol.

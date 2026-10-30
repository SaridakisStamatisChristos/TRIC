#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>

namespace reachability {

// Agrawal, Borgida & Jagadish (SIGMOD 1989), Alg1 — the *optimum tree cover*: choose, as each
// node j's tree parent, the in-neighbour i whose predecessor set pred(i) (ancestors, including i)
// is largest. This minimises the total number of intervals over the whole tree cover. Returns
// parent[v] = the chosen tree parent, or -1 for a source (a forest root). Shared by the tree-cover
// family (Tree Cover, Path-Hop, Tree+SSPI, Dual-labeling).
//
// Uses reverse-reachability bitsets to size pred(i), so it is O(n^2/64) space — appropriate for
// the small/medium graphs these tree-cover methods target.
std::vector<vid_t> optimal_tree_parent(const CSRGraph& dag);

}  // namespace reachability

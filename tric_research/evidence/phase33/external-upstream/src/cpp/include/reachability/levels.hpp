#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>

namespace reachability {

// Topological level of every vertex of a DAG = longest path from any root (roots have
// level 0), computed via Kahn's algorithm. Property: u reaches v (u != v) => level[u] <
// level[v], which both GRAIL and FELINE use as an exact negative cut / DFS prune.
std::vector<vid_t> topological_levels(const CSRGraph& dag);

}  // namespace reachability

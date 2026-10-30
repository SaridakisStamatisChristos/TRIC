#pragma once
#include "reachability/csr_graph.hpp"

namespace reachability {

// Returns true iff there is a directed path from u to v in g.
//
// This is the index-free baseline: it searches the graph on every call instead
// of precomputing anything. It is also the correctness oracle every indexing
// method is tested against. Works directly on the original graph (cycles and all),
// so it needs no SCC condensation.
bool bfs_reaches(const CSRGraph& g, vid_t u, vid_t v);

}  // namespace reachability

#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>

namespace reachability {

// Result of condensing a directed graph by its strongly connected components (SCCs).
//
// Every vertex inside one SCC reaches every other vertex in the same SCC, so for
// reachability we can collapse each SCC to a single node. The resulting graph is a
// DAG, which is the precondition most reachability indexes assume. The key identity:
//
//     u reaches v in the original graph
//       <=>  comp[u] == comp[v]            (same SCC), or
//            comp[u] reaches comp[v]       (in the condensed DAG)
struct Condensation {
    std::vector<vid_t> comp;        // comp[v] = id of the SCC that vertex v belongs to
    vid_t num_comp = 0;             // number of SCCs (= number of DAG nodes)
    CSRGraph dag;                   // condensed DAG over component ids (deduped, no self-loops)
    std::vector<vid_t> topo_order;  // component ids in topological order (sources first)
};

// Compute the condensation of g. Linear time, O(V + E).
Condensation scc_condense(const CSRGraph& g);

}  // namespace reachability

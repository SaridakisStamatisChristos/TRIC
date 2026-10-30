#pragma once
#include "reachability/csr_graph.hpp"
#include "reachability/two_hop.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// 2-Hop labeling (Cohen, Halperin, Kaplan, Zwick, SIAM J. Comput. 32(5):1338-1355, 2003) on
// a DAG — the original near-minimum 2-hop cover.
//
// Covering all reachable pairs is cast as a set cover whose candidate sets are centered at a
// vertex w: Cin = vertices that reach w, Cout = vertices w reaches; choosing center w with
// subsets (Cin, Cout) covers every still-uncovered pair (u, v) with u in Cin, v in Cout. Each
// greedy step picks the center whose "center graph" (the bipartite graph of uncovered pairs
// through w) has the densest subgraph, maximising |edges| / (|Cin| + |Cout|). The densest
// subgraph is found by the paper's linear-time 2-approximation: repeatedly remove the
// minimum-degree vertex and keep the densest snapshot. The chosen w is appended to Lout of the
// kept Cin and Lin of the kept Cout, and the covered pairs are removed; iterate until none
// remain. A *complete* index (no fallback search): u reaches v iff Lout(u) meets Lin(v).
//
// Minimum 2-hop is NP-hard; this greedy cover is within a logarithmic factor of optimal but
// the build is expensive (reachability bitsets + a densest-subgraph pass per center per step),
// so it is a small/medium-graph method, like TC / TreeCover. No public reference implementation
// was available; ported from the paper and verified against the BFS oracle.
class TwoHop {
public:
    TwoHop() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    TwoHopLabels L_;
    std::vector<vid_t> level_;   // topological level (quick negative cut)
};

}  // namespace reachability

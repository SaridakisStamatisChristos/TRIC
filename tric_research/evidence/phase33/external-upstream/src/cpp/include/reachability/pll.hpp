#pragma once
#include "reachability/csr_graph.hpp"
#include "reachability/two_hop.hpp"
#include <vector>

namespace reachability {

// PLL — Pruned Landmark Labeling (Yano, Akiba, Iwata, Yoshida, CIKM 2013), on a DAG.
//
// A 2-hop labeling: each vertex v keeps L_out(v) = landmarks v reaches and L_in(v) =
// landmarks that reach v (stored as sorted landmark ranks, via the shared TwoHopLabels). u
// reaches v iff the two sets share a landmark. It is a *complete* index — no fallback search.
class PLL {
public:
    PLL() = default;

    void build(const CSRGraph& dag);

    // Exact reachability on the DAG.
    bool query(vid_t u, vid_t v) const;

    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    TwoHopLabels L_;              // L_.Lout = landmarks reached; L_.Lin = landmarks that reach
    std::vector<vid_t> level_;   // topological level (quick negative cut)
};

}  // namespace reachability

#pragma once
#include "reachability/csr_graph.hpp"
#include "reachability/two_hop.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// TOL — Total Order Labeling (Zhu, Lin, Wang, Xiao, SIGMOD 2014) on a DAG.
//
// TOL is the general 2-hop framework that generalises PLL: a strict total order ("level order")
// of the vertices uniquely determines a canonical 2-hop index, built by the same pruned-BFS
// labeling (see build_two_hop_labels). The contribution of TOL is its level order, based on the
// *contribution score* f(v) = (a*b + a + b)/(a + b), where a = |ancestors(v)| and
// b = |descendants(v)| — a vertex covering many reachable pairs should rank highest. The exact
// scores need transitive closure, so TOL approximates them with a single linear scan of the DAG
// (upper bound: Sin(v) = sum over in-neighbours u of (Sin(u)+1), computed in topological order;
// Sout symmetric in reverse). Vertices are then ordered by descending f. A *complete* index.
//
// Reference implementation exists (SourceForge "totalorderlabeling"); here the labeling is the
// shared two_hop framework and only the contribution-score order is TOL-specific. Verified vs
// the BFS oracle.
class TOL {
public:
    TOL() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    TwoHopLabels L_;
    std::vector<vid_t> level_;   // topological level (quick negative cut)
};

}  // namespace reachability

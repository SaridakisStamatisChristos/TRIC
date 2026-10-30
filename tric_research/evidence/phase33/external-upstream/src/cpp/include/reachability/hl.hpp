#pragma once
#include "reachability/csr_graph.hpp"
#include "reachability/two_hop.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// HL — Hierarchical Labeling (Jin & Wang, "Simple, Fast, and Scalable Reachability Oracle",
// PVLDB 2013) on a DAG.
//
// HL builds a 2-hop oracle through a *recursive reachability backbone*. A vertex hierarchy
// V0 = V ⊃ V1 ⊃ ... ⊃ Vh is formed where each Gi+1 is the one-side reachability backbone of Gi,
// discovered by FastCover (Jin et al., SCARAB, SIGMOD 2012) with locality threshold eps: V* covers
// every pair (u,v) at distance eps via some x in V* with d(u,x)<=eps, d(x,v)<=eps. The backbone
// graph keeps edges between backbone vertices within distance eps+1. The core graph is labeled with
// a 2-hop labeling; then labels propagate down (Algorithm 1, Formulas 4-5): for v at level i,
//   Lout(v) = N^{ceil(eps/2)}_out(v|Gi) U union of Lout(u) over u in Bout^eps(v|Gi)
// where Bout^eps(v) are the nearest backbone vertices within eps hops, and Lin symmetrically. u
// reaches v iff Lout(u) and Lin(v) intersect. A *complete* index (entries are vertex ids).
//
// Faithful to the paper with eps=2 (its default; FastCover from SCARAB). Verified vs the BFS oracle.
class HL {
public:
    HL() = default;

    void build(const CSRGraph& dag, int eps);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

    // Read-only view of the built 2-hop labels (entries are condensed-DAG ids).
    const TwoHopLabels& labels() const { return L_; }

private:
    vid_t n_ = 0;
    TwoHopLabels L_;
    std::vector<vid_t> level_;   // topological level (quick negative cut)
};

}  // namespace reachability

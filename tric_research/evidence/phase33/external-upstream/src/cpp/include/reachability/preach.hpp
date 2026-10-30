#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>

namespace reachability {

// PReaCH — Pruned Reachability Contraction Hierarchies (Merz & Sanders, ESA 2014), on a DAG.
//
// An RCH ordering is built by repeatedly contracting source/sink vertices (smallest input
// degree first). Edges split into forward (order(u)<order(v)) and backward sets; by Theorem 1,
// s reaches t iff there is an "up-down" path, found by a bidirectional search that only walks
// to higher-order vertices and must meet. The search is pruned by all of the paper's single-DFS
// cuts, applied aggressively to both directions: forward/backward topological levels (Lemma 2),
// the DFS interval range [phi, phi_hat] (Lemmas 3-4, exact positive/negative), the largest
// reachable range outside the subtree ptree (Lemma 5, positive), the smallest reachable DFS number
// phi_min (Lemma 6, negative), and the empty range just left of v, phi_gap (Lemma 7, negative).
//
// No public reference implementation was available; ported from the paper, verified against
// the BFS oracle.
class PReaCH {
public:
    PReaCH() = default;

    void build(const CSRGraph& dag);
    bool reaches(vid_t u, vid_t v);
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    CSRGraph fwd_, bwd_;            // forward up-edges; backward up-edges (v -> higher-order preds)
    std::vector<vid_t> lf_, lb_;    // forward / backward topological levels
    std::vector<vid_t> pf_, pf_hat_;  // forward DFS preorder and subtree max (Lemmas 3-4)
    std::vector<vid_t> pb_, pb_hat_;  // backward DFS preorder and subtree max
    std::vector<vid_t> pf_min_, pf_gap_, pf_plo_, pf_phi_;  // fwd Lemmas 6, 7, 5 (ptree range [plo,phi])
    std::vector<vid_t> pb_min_, pb_gap_, pb_plo_, pb_phi_;  // bwd Lemmas 6, 7, 5
    std::vector<int> vf_, vb_;      // per-query forward/backward visit stamps
    int query_cnt_ = 0;
};

}  // namespace reachability

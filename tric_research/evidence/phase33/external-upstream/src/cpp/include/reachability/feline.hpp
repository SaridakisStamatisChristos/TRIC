#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>

namespace reachability {

// FELINE reachability index (Veloso, Cerf, Meira Jr., Zaki, EDBT 2014), on a DAG.
//
// Each vertex gets a 2D coordinate (X, Y) from two topological orderings, forming a
// weak dominance drawing: r(u, v) => X[u] <= X[v] AND Y[u] <= Y[v]. The componentwise
// test is an exact negative cut; inconclusive pairs fall back to a dominance-pruned DFS.
class Feline {
public:
    Feline() = default;

    // bidirectional=true (FELINE-B) also indexes the reversed graph, giving a second
    // dominance test that prunes from the target side too — faster on hard pairs, at the
    // cost of a second coordinate pair and a reverse CSR.
    void build(const CSRGraph& dag, bool bidirectional = false);

    // Weak dominance in the normal index: i(u) <= i(v). Necessary condition (Theorem 1).
    bool dominates(vid_t u, vid_t v) const {
        return X_[u] <= X_[v] && Y_[u] <= Y_[v];
    }

    // Weak dominance in the reversed index. r(u,v) in G  =>  r(v,u) in G^T, so the reversed
    // necessary condition for r(u,v) is dominates_rev(v, u).
    bool dominates_rev(vid_t a, vid_t b) const {
        return X2_[a] <= X2_[b] && Y2_[a] <= Y2_[b];
    }

    // Topological level (longest path from a root). u reaches v (u!=v) => level(u) < level(v).
    vid_t top_level(vid_t v) const { return level_[v]; }

    // Positive cut (same min-post labeling as GRAIL, d=1): v's DFS entry/exit window nested
    // in u's means v is a tree-descendant of u, so u reaches v (exact positive). The converse
    // need not hold (non-tree paths), so it is only a filter.
    bool positive_contains(vid_t u, vid_t v) const {
        return pc_middle_[u] <= pc_middle_[v] && pc_post_[u] >= pc_post_[v];
    }

    // Exact reachability: dominance negative cut, then dominance-pruned guided DFS.
    bool reaches(vid_t u, vid_t v);

    std::size_t index_size_bytes() const;

private:
    CSRGraph dag_;
    bool bidirectional_ = false;
    vid_t n_ = 0;
    std::vector<vid_t> X_, Y_;        // two topological-order ranks per vertex (normal)
    std::vector<vid_t> X2_, Y2_;      // reversed-graph coordinates (only if bidirectional_)
    std::vector<vid_t> level_;        // topological level (longest path from a root)
    std::vector<vid_t> pc_middle_, pc_post_;  // positive-cut entry/exit (min-post, d=1)
    std::vector<int> visited_;        // per-query stamps for the guided DFS
    int query_cnt_ = 0;

    void compute_positive_cut();      // min-post labeling over a spanning forest (shared util)
    // Two complementary topological orders of g (Algorithm 1) into X, Y.
    static void compute_orders(const CSRGraph& g, std::vector<vid_t>& X,
                               std::vector<vid_t>& Y);
};

}  // namespace reachability

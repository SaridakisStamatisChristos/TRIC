#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// Tree+SSPI — Chen, Gupta & Kurul, "Stack-based Algorithms for Pattern Matching on DAGs",
// VLDB 2005, on a DAG. The reachability index combines a tree cover with a Surrogate & Surplus
// Predecessor Index (SSPI).
//
// A spanning tree is preorder interval-labelled, so tree ("ppure") reachability is interval
// containment. The remaining reachability ("pmix" paths, through >=1 non-tree edge) is carried by
// the SSPI: each vertex w keeps a predecessor list PL(w) of the tails of its non-tree in-edges
// (superfluous ones — where the tail already tree-reaches w — are dropped). By Theorem 2.1, x
// reaches y iff x is a tree-ancestor of y, or, searching the SSPI transitively, some predecessor
// u of y or of a tree-ancestor of y is reached by x (x a tree-ancestor of u, recursively). A
// *complete* index (the answer is always exact, with an online guided search for pmix paths).
// General graphs are reduced via SCC condensation.
//
// Faithful to the SSPI scheme: PL stores only own non-tree in-edge tails (O(m) total, per the
// paper), and the predecessor inheritance along the tree is realised at query time by walking
// tree ancestors. A plain DFS spanning tree is used (vs the optional optimum tree cover). Verified
// vs the BFS oracle.
class TreeSSPI {
public:
    TreeSSPI() = default;

    void build(const CSRGraph& dag);
    bool reaches(vid_t x, vid_t y);
    std::size_t index_size_bytes() const;

private:
    bool anc(vid_t u, vid_t w) const { return a_[u] <= pre_[w] && pre_[w] < b_[u]; }  // u tree-ancestor-or-self of w

    vid_t n_ = 0;
    std::vector<vid_t> parent_, pre_, a_, b_;     // tree parent; preorder; interval [a, b)
    std::vector<std::vector<vid_t>> pl_;          // SSPI: non-tree in-edge tails per vertex
    std::vector<int> stamp_;                      // guided-search per-query stamp
    int query_cnt_ = 0;
};

}  // namespace reachability

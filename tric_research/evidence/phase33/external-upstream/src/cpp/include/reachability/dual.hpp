#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// Dual Labeling — Wang, He, Yang, Yu & Yu, "Dual Labeling: Answering Graph Reachability Queries
// in Constant Time", ICDE 2006, on a DAG. Aimed at sparse graphs (few non-tree edges t).
//
// A spanning tree is preorder interval-labelled: vertex v gets [a, b) = [pre(v), pre(v)+size(v)),
// and w is a tree-descendant of v iff pre(w) in [a, b). The remaining reachability is carried by
// the *transitive link table* T: each non-tree edge (tail, head) becomes a link i -> [j, k) with
// i = pre(tail) and [j, k) = head's interval (superfluous links, where the head is already a
// tree-descendant of the tail, are dropped). T is closed under composition: links i1 -> [j1, k1)
// and i2 -> [j2, k2) with i2 in [j1, k1) yield i1 -> [j2, k2). By Theorem 1, u reaches v iff
// pre(v) in [a_u, b_u) (tree) or some link i -> [j, k) in T has i in [a_u, b_u) and pre(v) in
// [j, k). A *complete* index of size O(n + t^2). General graphs are reduced via SCC condensation.
//
// Faithful to the dual-label scheme (Dual-I). Queries run in O(1) via the TLC counting function
// N(x, y) = #{links i -> [j, k) : i >= x, y in [j, k)} with gridding/snapping (paper Sec. 3.2-3.3):
// v is reachable from u via non-tree links iff N(a_u, pre_v) - N(b_u, pre_v) > 0, and both counts
// are O(1) grid look-ups after snapping coordinates to grid cells. The spanning tree is a DFS tree
// over the minimal equivalent graph (Sec. 5 transitive reduction, to minimise t). Verified vs the
// BFS oracle.
class DualLabeling {
public:
    DualLabeling() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    struct Link { vid_t i, j, k; };        // i -> [j, k)

    vid_t n_ = 0;
    std::vector<vid_t> pre_, a_, b_;        // preorder number; interval [a, b)
    // Dual-I gridded TLC: gridN_[r*(ncols_+1)+c] = #links covering y-cell r with column index >= c.
    vid_t ncols_ = 0, ncells_ = 0;
    std::vector<vid_t> colof_, rowof_;      // coordinate -> grid column / y-cell (rowof_ = -1: none)
    std::vector<vid_t> gridN_;
};

}  // namespace reachability

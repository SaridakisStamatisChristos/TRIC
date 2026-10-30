#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// Path-Hop — Cai & Poon, "Path-Hop: Efficiently Indexing Large Graphs for Reachability Queries",
// CIKM 2010, on a DAG. The tree-cover analogue of 3-Hop: trees, instead of chains, are the
// "highways".
//
// A spanning tree (tree cover) is interval-labelled so that tree reachability is an interval
// containment Iv ⊆ Iu. The *residual transitive closure* — reachable pairs not captured by the
// tree, represented by each vertex's reachable non-tree subtree roots Succ(u) (via the
// multi-interval labeling of Agrawal et al.) — is covered by a greedy set cover of *path-hops*
// x ; y (x a tree-ancestor of y): the chosen hop adds x to Lout of every u in Pred(x) and y to
// Lin of every v in Succ(y). A query reach(u, v) returns true iff Iv ⊆ Iu, or some
// x in Lout(u) U {u} is a tree-ancestor of some y in Lin(v) U {v} U (Lin of v's tree ancestors)
// — the ancestor roll-up makes the labeling complete and exact.
//
// Construction follows the paper. A simple DFS spanning forest is used as the tree cover (the
// paper's optimal tree cover is an index-size optimisation, not a correctness requirement), and
// the greedy uses the simplified whole-Pred(x)/Succ(y) hop density (paper Eq. 4). Verified vs the
// BFS oracle. Construction materialises reachable-root sets, so this targets small/medium graphs.
class PathHop {
public:
    PathHop() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    bool anc(vid_t a, vid_t b) const { return lo_[a] <= lo_[b] && hi_[b] <= hi_[a]; }  // a tree-ancestor of b (Ib subset Ia)

    vid_t n_ = 0;
    std::vector<vid_t> parent_, lo_, hi_;       // tree parent; interval label [lo, hi]
    std::vector<std::vector<vid_t>> lout_, lin_; // Path-Hop labels (vertex ids)
};

}  // namespace reachability

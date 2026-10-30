#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// Path-Tree — Jin, Ruan, Xiang & Wang, "Path-Tree: An Efficient Reachability Indexing Scheme for
// Large Directed Graphs", ACM TODS 2011, on a DAG. A generalisation of the tree cover where the
// covering structure is a tree of *paths* (a path-tree cover).
//
// Construction: (1) decompose the DAG into paths (Simon's algorithm), giving each vertex (pid,
// sid); (2) form the weighted path-graph (a node per path, an edge per connected path-pair, with
// the MinPathIndex weight w_{Pi->Pj} = |Pi[->u]|, u the last vertex in Pi reaching Pj); (3) take the
// *maximum-weight* directed spanning tree (SP-tree) by the Chu-Liu/Edmonds algorithm, which
// minimises the residual index size (Section 2.3); (4) label the path-tree cover with a 3-tuple
// (X, I.begin, I.end): X by a post-order DFS over the cover (Algorithm 2), I the SP-tree interval
// of a vertex's path. By Lemma 4, u reaches v *within the cover* iff X(u) <= X(v) and v's path
// interval is contained in u's. (5) The reachability not captured by the cover is compressed into
// a per-vertex residual set Rc(u) (Algorithm 3). A query is then: u reaches v iff coverReach(u, v),
// or coverReach(x, v) for some x in Rc(u). A *complete* index. General graphs are reduced via SCC
// condensation.
//
// Independent implementation from the paper (no public reference code). The SP-tree is the paper's
// Edmonds maximum arborescence. Remaining deviations affect query speed, not the index or answers:
// reachability within the cover uses all edges of a tree path-pair rather than the minimal-
// equivalent edge set (reachability-equivalent, and the residual Rc is domination-minimised either
// way), and the residual is scanned linearly instead of the paper's O(log^2 k) gridding query.
// Verified vs the BFS oracle.
class PathTree {
public:
    PathTree() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    // u reaches v using only the path-tree cover (Lemma 4)
    bool cover_reach(vid_t u, vid_t v) const {
        return x_[u] <= x_[v] &&
               ib_[pid_[u]] <= ib_[pid_[v]] && ie_[pid_[v]] <= ie_[pid_[u]];
    }

    vid_t n_ = 0;
    std::vector<vid_t> pid_, x_;            // path id; DFS X label
    std::vector<vid_t> ib_, ie_;            // per-path SP-tree interval [begin, end]
    std::vector<std::vector<vid_t>> rc_;    // residual transitive-closure representatives per vertex
};

}  // namespace reachability

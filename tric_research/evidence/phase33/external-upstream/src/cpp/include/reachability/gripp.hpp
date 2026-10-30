#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// GRIPP — Trissl & Leser, "Fast and Practical Indexing and Querying of Very Large Graphs",
// SIGMOD 2007 (GRaph Indexing based on Pre- and Postorder numbering), on a DAG.
//
// A DFS over G builds the *order tree* O(G): each node gets one instance per incoming edge — the
// first is its *tree instance* (recursed into), the rest are *non-tree instances* (leaves). Every
// instance carries a pre/post interval. The reachable instance set RIS(v) is the set of instances
// in the subtree of v's tree instance. A query reach(v, w): if some instance of w lies in RIS(v),
// w is reachable; otherwise each non-tree instance in RIS(v) marks a *hop node* h, whose own RIS
// is searched recursively (a guided DFS over hop nodes) until w is found or no hop node remains.
// A *complete* index of size O(n + m) with an online guided search (worst case O(m - n)). General
// graphs are reduced via SCC condensation.
//
// Faithful to the hop technique with the paper's advanced pruning (Sec. 4.2): hop nodes are
// processed in ascending order-tree position, and each is pruned against the set U of already-used
// hop ranges by the four relative-position cases of Fig. 4 — (a) already used, (b) its tree instance
// lies inside some u in U (RIS(h) subset RIS(u)) => skip; (c) some u lies inside RIS(h) => skip that
// sub-range; (d) sibling => full scan. Verified vs the BFS oracle.
class GRIPP {
public:
    GRIPP() = default;

    void build(const CSRGraph& dag);
    bool reaches(vid_t v, vid_t w);
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    std::vector<vid_t> inode_;          // instance -> graph node (indexed by preorder id)
    std::vector<vid_t> ipost_;          // instance -> subtree end (max preorder id in subtree)
    std::vector<char> itree_;           // instance -> is it the node's tree instance?
    std::vector<vid_t> tree_inst_;      // graph node -> its tree instance id
    std::vector<int> stamp_;            // per-query visited stamp over nodes
    int query_cnt_ = 0;
};

}  // namespace reachability

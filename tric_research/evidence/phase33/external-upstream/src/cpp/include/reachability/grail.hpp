#pragma once
#include "reachability/csr_graph.hpp"
#include <cstdint>
#include <vector>

namespace reachability {

// GRAIL reachability index (Yildirim, Chaoji, Zaki, PVLDB 2010), adapted to CSR.
// Operates on a DAG; callers reduce general graphs via scc_condense() first.
class Grail {
public:
    Grail() = default;

    // Build d random interval labels over the DAG. seed makes labeling reproducible.
    // bidirectional=true also builds a reverse CSR so inconclusive queries use a
    // two-sided search (faster on hard pairs, at the cost of ~one extra edge array).
    void build(const CSRGraph& dag, int d, std::uint32_t seed = 1,
               bool bidirectional = false);

    int dim() const { return d_; }

    // Topological level (longest path from a root). u reaches v (u!=v) => level(u) < level(v).
    vid_t top_level(vid_t v) const { return top_level_[v]; }

    // Necessary condition: u reaches v  =>  contains(u, v). (No false negatives.)
    bool contains(vid_t u, vid_t v) const;

    // Three-way test with the PP positive cut (exact in both directions):
    //   -1 = definitely not reachable, 1 = definitely reachable, 0 = inconclusive.
    int contains_pp(vid_t u, vid_t v) const;

    // Exact reachability: PP cuts, then guided DFS for the inconclusive cases.
    bool reaches(vid_t u, vid_t v);

    std::size_t index_size_bytes() const;

private:
    CSRGraph dag_;
    CSRGraph rdag_;                   // reverse of dag_ (built only when bidirectional_)
    bool bidirectional_ = false;
    int d_ = 0;
    vid_t n_ = 0;
    std::vector<vid_t> pre_, post_, middle_;  // node-major labels: node v, dim k at v*d_ + k
    std::vector<vid_t> top_level_;    // topological level per node (longest path from a root)
    std::vector<int> visited_;        // per-query stamps for guided/bidirectional search
    int query_cnt_ = 0;

    void label_dimension(int k, std::uint32_t seed);
    bool reaches_guided(vid_t u, vid_t v);          // one-sided, level-pruned DFS
    bool reaches_bidirectional(vid_t u, vid_t v);   // two-sided, level-pruned search
};

}  // namespace reachability

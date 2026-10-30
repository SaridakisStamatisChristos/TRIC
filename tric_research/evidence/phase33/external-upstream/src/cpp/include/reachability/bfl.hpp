#pragma once
#include "reachability/csr_graph.hpp"
#include <cstdint>
#include <vector>

namespace reachability {

// BFL — Bloom Filter Labeling (Su, Zhu, Wei, Yu, "Reachability Querying: Can It Be Even
// Faster?", TKDE 2017), on a DAG. A *partial* index: a DFS interval label plus two per-vertex
// Bloom filters (L_out = bloom of {u} ∪ descendants; L_in = bloom of {u} ∪ ancestors, each k
// 32-bit words). The interval gives an exact positive/negative cut for tree paths; the Bloom
// subset tests give exact negative cuts (no false negatives, may have false positives), so
// inconclusive pairs fall back to a guided DFS. Faithful to the author's reference
// implementation (github.com/BoleynSu/bfl, MIT).
class BFL {
public:
    BFL() = default;

    // k = number of 32-bit Bloom words per vertex (default 5); seed for the hashing.
    void build(const CSRGraph& dag, int k = 5, std::uint32_t seed = 1);

    bool reaches(vid_t u, vid_t v);
    std::size_t index_size_bytes() const;

private:
    CSRGraph dag_, rdag_;
    int k_ = 0;
    vid_t n_ = 0;
    std::vector<std::uint32_t> lin_, lout_;   // k_ words per vertex, node-major [v*k_ + i]
    std::vector<vid_t> pre_, post_;           // DFS interval over out-edges
    std::vector<int> visited_;                // per-query stamps for guided DFS
    int query_cnt_ = 0;

    // -1 = definitely not reachable, 1 = definitely reachable, 0 = inconclusive.
    int cut(vid_t u, vid_t v) const;
};

}  // namespace reachability

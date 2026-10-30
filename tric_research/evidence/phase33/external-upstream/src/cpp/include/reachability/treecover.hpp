#pragma once
#include "reachability/csr_graph.hpp"
#include <utility>
#include <vector>

namespace reachability {

// Tree Cover (Agrawal, Borgida, Jagadish, SIGMOD 1989), on a DAG. A DFS spanning forest gives
// each vertex a post-order number; the set of post-order numbers reachable from a vertex is
// stored as merged intervals (tree descendants are contiguous, so few intervals). u reaches v
// iff post(v) lies in one of u's intervals. A transitive-closure compression baseline.
class TreeCover {
public:
    TreeCover() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    std::vector<vid_t> post_;   // post-order number per vertex
    std::vector<std::vector<std::pair<vid_t, vid_t>>> intervals_;  // sorted, merged [lo,hi]
};

}  // namespace reachability

#pragma once
#include "reachability/csr_graph.hpp"
#include <cstdint>
#include <vector>

namespace reachability {

// TC — full transitive closure materialized as per-vertex bitsets (Warshall-style), on a DAG.
// Query is a single bit test (O(1)), but the index is O(V^2/64), so this is a baseline for
// small graphs only.
class TC {
public:
    TC() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    std::size_t words_ = 0;            // 64-bit words per row = ceil(n/64)
    std::vector<std::uint64_t> bits_;  // n_ rows of words_ words; bit v of row u = u reaches v
};

}  // namespace reachability

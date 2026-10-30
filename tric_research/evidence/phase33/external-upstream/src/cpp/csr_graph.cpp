#include "reachability/csr_graph.hpp"
#include <algorithm>

namespace reachability {

// Build CSR from an edge list in three passes:
//   1. bucket each edge into its source vertex's adjacency list (skip self-loops);
//   2. sort + unique each list to remove duplicate (parallel) edges;
//   3. flatten the per-vertex lists into the offsets_/targets_ arrays.
CSRGraph::CSRGraph(vid_t n, const std::vector<vid_t>& src,
                   const std::vector<vid_t>& dst)
    : n_(n) {
    // Pass 1: temporary per-vertex adjacency. We drop self-loops here because a
    // vertex always reaches itself by reflexivity, so u->u carries no information.
    std::vector<std::vector<vid_t>> adj(static_cast<std::size_t>(n_));
    const std::size_t m = src.size();
    for (std::size_t i = 0; i < m; ++i) {
        vid_t u = src[i], v = dst[i];
        if (u == v) continue;                // drop self-loops
        adj[static_cast<std::size_t>(u)].push_back(v);
    }

    // Pass 2: sort each list and drop duplicates, so parallel edges collapse to
    // one. Sorting also gives each vertex's neighbors a deterministic order.
    // Build offsets_ as a running prefix sum of the (deduplicated) degrees.
    offsets_.assign(static_cast<std::size_t>(n_) + 1, 0);
    for (vid_t u = 0; u < n_; ++u) {
        auto& row = adj[static_cast<std::size_t>(u)];
        std::sort(row.begin(), row.end());
        row.erase(std::unique(row.begin(), row.end()), row.end());
        offsets_[static_cast<std::size_t>(u) + 1] =
            offsets_[static_cast<std::size_t>(u)] + row.size();
    }

    // Pass 3: concatenate the rows in vertex order into the flat targets_ array.
    // offsets_.back() is now the total edge count, so we can reserve exactly.
    targets_.reserve(offsets_.back());
    for (vid_t u = 0; u < n_; ++u) {
        const auto& row = adj[static_cast<std::size_t>(u)];
        targets_.insert(targets_.end(), row.begin(), row.end());
    }
}

}  // namespace reachability

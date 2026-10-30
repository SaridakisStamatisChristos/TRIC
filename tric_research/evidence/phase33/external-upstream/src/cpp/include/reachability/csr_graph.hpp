#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>

namespace reachability {

// Vertex identifier. 0-based, signed 32-bit: fits graphs up to ~2.1B vertices
// while leaving -1 available as a sentinel (used e.g. by the SCC algorithm).
using vid_t = std::int32_t;

// A directed graph in Compressed Sparse Row (CSR) form.
//
// CSR stores the adjacency lists of all vertices back-to-back in one flat array
// (`targets_`), and an `offsets_` array that marks where each vertex's list
// begins. The out-neighbors of vertex u are exactly:
//
//     targets_[ offsets_[u] .. offsets_[u+1] )
//
// Example: vertices {0,1,2} with edges 0->1, 0->2, 1->2
//     offsets_ = [0, 2, 3, 3]      // u=0 spans [0,2), u=1 spans [2,3), u=2 empty
//     targets_ = [1, 2, 2]
//
// This is compact (no per-edge object overhead) and cache-friendly (a vertex's
// neighbors are contiguous), which is what makes the reachability traversals fast.
class CSRGraph {
public:
    CSRGraph() = default;

    // Build from an edge list: edge i goes from src[i] to dst[i]. `n` is the
    // vertex count; all ids must be in [0, n). Self-loops are dropped and
    // duplicate edges removed (see the .cpp), since neither affects reachability.
    CSRGraph(vid_t n, const std::vector<vid_t>& src, const std::vector<vid_t>& dst);

    vid_t num_nodes() const { return n_; }
    std::size_t num_edges() const { return targets_.size(); }

    // Half-open range [out_begin(u), out_end(u)) over u's out-neighbors. Returning
    // raw pointers lets callers iterate the contiguous slice with no allocation.
    const vid_t* out_begin(vid_t u) const { return targets_.data() + offsets_[u]; }
    const vid_t* out_end(vid_t u) const { return targets_.data() + offsets_[u + 1]; }
    vid_t out_degree(vid_t u) const {
        return static_cast<vid_t>(offsets_[u + 1] - offsets_[u]);
    }

private:
    vid_t n_ = 0;
    std::vector<std::size_t> offsets_{0};   // size n_+1; offsets_[u]..offsets_[u+1] = u's slice
    std::vector<vid_t> targets_;            // size m; concatenated adjacency lists
};

}  // namespace reachability

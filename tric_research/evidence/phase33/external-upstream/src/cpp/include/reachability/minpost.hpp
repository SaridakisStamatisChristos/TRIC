#pragma once
#include "reachability/csr_graph.hpp"
#include <random>
#include <vector>

namespace reachability {

// One min-post interval labeling of a DAG (the labeling shared by GRAIL and FELINE's
// positive-cut filter — the only difference between their uses is the number of dimensions).
struct MinPost {
    std::vector<vid_t> pre;     // min post over the subtree, propagated through non-tree edges
                                // too: [pre, post] is GRAIL's necessary-condition interval.
    std::vector<vid_t> post;    // post-order finish number.
    std::vector<vid_t> middle;  // entry number: (middle, post] is exactly the vertex's
                                // DFS-tree descendants, used as an exact positive cut.
};

// Iterative post-order DFS labeling from the in-degree-0 roots. If rng != nullptr, the roots
// and each vertex's children are shuffled (GRAIL's randomized labeling); otherwise the order
// is deterministic (a single fixed spanning forest, as FELINE's positive cut uses).
MinPost min_post_label(const CSRGraph& dag, std::mt19937* rng);

}  // namespace reachability

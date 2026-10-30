#pragma once
#include "reachability/csr_graph.hpp"
#include <utility>
#include <vector>

namespace reachability {

// Chain Cover (Jagadish, "A Compression Technique to Materialize Transitive Closure", TODS
// 1990), on a DAG. The DAG is decomposed into chains (paths); each vertex has a (chain,
// position). Since a chain is a path, reaching a position implies reaching every later
// position on that chain, so per vertex we keep only the smallest reachable position per
// chain. u reaches v iff u's recorded min position on v's chain is ≤ pos(v). A complete
// transitive-closure-compression index (baseline for small/medium graphs).
class ChainCover {
public:
    ChainCover() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    std::vector<vid_t> chain_of_, pos_;   // per vertex: chain id and position in its chain
    // per vertex: sorted (chain, min reachable position on that chain)
    std::vector<std::vector<std::pair<vid_t, vid_t>>> reach_;
};

}  // namespace reachability

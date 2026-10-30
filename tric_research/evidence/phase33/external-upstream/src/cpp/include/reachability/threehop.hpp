#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// 3-Hop — Jin, Xiang, Ruan, Fuhry, "3-HOP: A High-Compression Indexing Scheme for Reachability
// Query", SIGMOD 2009, on a DAG.
//
// The DAG is decomposed into chains; a vertex's (cid, pos) place it on a chain. Reachability is
// answered in three hops through an intermediate chain ("highway"): u -> entry point on chain C,
// along C to an exit point, exit -> v. Concretely u reaches v iff there is a chain C with an
// entry e recorded for u and an exit x recorded for v such that e precedes x on C.
//
// Construction follows the paper: (1) compute the *transitive closure contour* — the
// pseudo-diagonal cells of each chain-pair reachability submatrix, a concise exact description
// of the transitive closure; (2) cover the contour by a greedy *factorization* that, each round,
// picks the chain whose chain-center bipartite graph (over still-uncovered contour pairs) has the
// densest subgraph (linear 2-approximation), recording entry/exit anchors for the chosen
// vertices. A query then resolves a vertex's entry/exit on a highway via its nearest anchor
// along its own chain (segment lookup), which makes the index complete and exact.
//
// A complete index. The faster rank-subgraph densest-subgraph search of the paper (Sec. 4.3) is
// replaced by the linear 2-approximation it endorses, and labels are kept as per-chain anchor
// records queried by segment lookup. Verified vs the BFS oracle. (Construction uses transitive-
// closure bitsets, so this targets small/medium graphs, like 2-Hop / TC.)
class ThreeHop {
public:
    ThreeHop() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    struct Rec { vid_t pos; vid_t hw; vid_t val; };  // anchor on this chain: (pos, highway, entry/exit pos)

    vid_t n_ = 0;
    std::vector<vid_t> cid_, pos_;
    std::vector<std::vector<Rec>> entry_recs_;   // per chain, sorted by pos: entry anchors
    std::vector<std::vector<Rec>> exit_recs_;    // per chain, sorted by pos: exit anchors
};

}  // namespace reachability

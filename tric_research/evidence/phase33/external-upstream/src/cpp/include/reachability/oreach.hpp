#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>
#include <cstdint>

namespace reachability {

// O'Reach — Hanauer, Schulz & Trummer, "O'Reach: Even Faster Reachability in Large Graphs",
// SEA 2021. A linear-size *partial* index (no false answers) on a DAG: a battery of
// constant-time observations resolves most queries, and a guided DFS fallback settles the rest.
//
// Observations implemented (paper Sec. 4), applied in the paper's test order:
//   * B2 — s and t in different weakly-connected components (negative cut).
//   * B5/B6 — forward/backward topological levels (negative cuts).
//   * S1/S2/S3 — k "supportive vertices" with full out/in-reachability stored as bitmasks:
//       S1 positive (s reaches a support that reaches t), S2/S3 negative.
//   * T1..T6 with B4 — t extended topological orderings (Tarjan back-to-front, started from
//       sources) carrying, per vertex, the high/max indices (forward orderings -> T1/T2/T3) or
//       low/min indices (reverse orderings -> T4/T5/T6), plus the plain topological cut B4.
// On an inconclusive query, a *pruning bidirectional BFS* uses the same observations on each newly
// encountered vertex to prune (negative) or shortcut (positive), guaranteeing exactness.
//
// Faithful to the paper (reference: github.com/KaHIP/O-Reach). Supportive vertices are selected by
// the paper's most-successful strategy (slim forward/backward levels capped at kp candidates,
// filled at random from central forward levels, then the top-k by |R+|*|R-|). Verified vs the BFS
// oracle.
class OReach {
public:
    OReach() = default;

    // k: #supportive vertices (capped at 64), p: candidates-per-support multiplier, h: slim-level
    // threshold, t: #extended orderings, seed: RNG seed for ordering / candidate randomization.
    void build(const CSRGraph& dag, int k, int p, int h, int t, unsigned seed);
    bool reaches(vid_t s, vid_t t);
    std::size_t index_size_bytes() const;

private:
    struct Ordering {
        bool forward;                 // forward: a=high, b=max (T1-T3); reverse: a=low, b=min (T4-T6)
        std::vector<vid_t> tau, a, b;
    };

    int apply_ord(const Ordering& o, vid_t s, vid_t t) const;  // +1 / -1 / 0 for one ordering
    int observe(vid_t s, vid_t t) const;   // +1 reachable, -1 not, 0 unknown

    vid_t n_ = 0;
    CSRGraph fwd_, rev_;
    std::vector<vid_t> F_, B_;              // forward / backward topological levels
    std::vector<vid_t> wcc_;               // weakly-connected-component id (Observation B2)
    std::vector<std::uint64_t> rin_, rout_; // supportive masks: rin[w]|j = w in R-(v_j); rout = R+
    int nsupp_ = 0;
    std::vector<Ordering> ords_;
    std::vector<int> stamp_, bstamp_;      // bidirectional-BFS per-query stamps (forward / backward)
    int query_cnt_ = 0;
};

}  // namespace reachability

#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// Shared 2-hop label storage and query, reused by PLL and 2-Hop (and the TFL/TOL/HL family).
//
// Each vertex keeps two sorted int lists: Lout (entries it can reach) and Lin (entries that
// reach it). u reaches v iff Lout(u) and Lin(v) share an entry. What an "entry" means is up
// to the method — PLL uses landmark ranks, 2-Hop uses center vertex ids — but the storage and
// the sorted-merge intersection query are identical, so they live here once.
struct TwoHopLabels {
    std::vector<std::vector<vid_t>> Lout;  // labels each vertex can reach (sorted ascending)
    std::vector<std::vector<vid_t>> Lin;   // labels that reach each vertex (sorted ascending)

    void resize(vid_t n) { Lout.assign(n, {}); Lin.assign(n, {}); }

    std::size_t size_bytes() const {
        std::size_t b = 0;
        for (const auto& l : Lout) b += l.size() * sizeof(vid_t);
        for (const auto& l : Lin) b += l.size() * sizeof(vid_t);
        return b;
    }
};

// Does Lout(u) intersect Lin(v)? Both lists must be sorted ascending. Inline so callers on the
// query hot path (PLL/2-Hop) keep the merge inlined.
inline bool two_hop_intersects(const TwoHopLabels& L, vid_t u, vid_t v) {
    const std::vector<vid_t>& a = L.Lout[u];
    const std::vector<vid_t>& b = L.Lin[v];
    std::size_t i = 0, j = 0;
    while (i < a.size() && j < b.size()) {
        if (a[i] == b[j]) return true;
        if (a[i] < b[j]) ++i; else ++j;
    }
    return false;
}

// Build the canonical 2-hop labels for a given vertex processing order via pruned BFS — the
// shared PLL / TOL labeling framework (Zhu et al., SIGMOD 2014: a level order uniquely decides
// a 2-hop index). `order` lists vertices in processing order (order[0] is processed first / has
// the highest level); each vertex stores its in/out landmarks as processing ranks (0 = first),
// so the resulting lists are sorted ascending. The level order is the only thing that
// distinguishes instances: PLL uses a degree order, TOL a contribution-score order.
void build_two_hop_labels(const CSRGraph& dag, const std::vector<vid_t>& order, TwoHopLabels& L);

}  // namespace reachability

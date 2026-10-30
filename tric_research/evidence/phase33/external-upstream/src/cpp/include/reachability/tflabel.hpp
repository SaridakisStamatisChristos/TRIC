#pragma once
#include "reachability/csr_graph.hpp"
#include "reachability/two_hop.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// TF-Label — Topological-Folding Labeling (Cheng, Huang, Wu, Fu, SIGMOD 2013) on a DAG.
//
// A 2-hop labeling whose construction is a *topological folding*: vertices are placed on
// topological levels and the DAG is repeatedly folded in half — each fold removes the
// odd-level vertices and reconnects their in-neighbours straight to their out-neighbours —
// so a vertex is processed in O(lg L) folds instead of all L levels. The "TF number" tf(v) is
// the last fold that still contains v. Labels follow Definition 5: labelout(v) is the closure
// of v under "out-neighbours in the folding graph at tf(u)" (which, by Lemma 5, always have a
// strictly larger tf, so the closure is shallow); labelin(v) symmetrically. u reaches v iff
// labelout(u) and labelin(v) intersect (Equation 1) — a *complete* index over the shared
// TwoHopLabels store.
//
// Cross-level edges are handled by the paper's transformed topological folding (Procedure 1):
// for each odd-level vertex, its far out-neighbours (and even far in-neighbours) are rerouted
// through a single shared dummy vertex created lazily at the adjacent level, so the label size
// stays compact. No public reference implementation was available; ported from the paper
// (folding + Procedure 1 + Definition 5 + Equation 1), verified vs the BFS oracle.
class TFLabel {
public:
    TFLabel() = default;

    void build(const CSRGraph& dag);
    bool query(vid_t u, vid_t v) const;
    std::size_t index_size_bytes() const;

private:
    vid_t n_ = 0;
    TwoHopLabels L_;
    std::vector<vid_t> level_;   // 0-indexed topological level (quick negative cut)
};

}  // namespace reachability

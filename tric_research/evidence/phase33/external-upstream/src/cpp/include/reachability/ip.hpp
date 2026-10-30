#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>

namespace reachability {

// IP — Wei, Yu & Lu, "Reachability Querying: An Independent Permutation Labeling Approach",
// PVLDB 2014, on a DAG. A *partial* (Label+G) index: sound negative cuts from randomized
// permutation labels, with a guided DFS settling the rest.
//
// u reaches v requires Out(v) subset Out(u) and In(u) subset In(v) (Out/In are the reachable /
// reaching sets). For each of np independent permutations pi, every vertex stores mink — the k
// smallest pi-values of its Out set and of its In set (k-min-wise). By Theorem 4.1, if
// mink(pi(Out(u))) "succ" mink(pi(Out(v))) (some pi-value in v's k-min Out is provably absent
// from u's), then Out(v) is not a subset of Out(u), hence u cannot reach v; symmetrically for In.
// Any permutation firing this test answers the query negatively in constant time. A topological
// level filter adds another sound negative cut. Inconclusive queries fall back to a guided DFS
// that prunes with the same cuts, so the answer is always exact. General graphs are reduced via
// SCC condensation.
//
// Faithful to the k-min-wise scheme and both of the paper's additional DFS-reduction labels (Sec.
// 6): the Level label (forward Lup and backward Ldown topological levels) and the Huge-Vertex label
// Lhv(v) = up to h largest-out-degree vertices (out-degree > mu) that reach v. During the DFS, when
// the current vertex c is a huge vertex (out-degree > mu): c in Lhv(v) => c reaches v (positive),
// and if c is not in Lhv(v) while Lhv(v) has room or c outranks its smallest member => c cannot
// reach v (negative). Verified vs the BFS oracle.
class IP {
public:
    IP() = default;

    // k: top-k per permutation; np: number of permutations; h: max huge vertices per label;
    // mu: out-degree threshold for a huge vertex; seed: RNG seed.
    void build(const CSRGraph& dag, int k, int np, int h, int mu, unsigned seed);
    bool reaches(vid_t u, vid_t v);
    std::size_t index_size_bytes() const;

private:
    int neg_cut(vid_t u, vid_t v) const;   // 1 if certainly u !-> v, else 0
    int hv_cut(vid_t c, vid_t v) const;    // +1 c reaches v, -1 c cannot, 0 unknown (HV-Label)

    vid_t n_ = 0;
    int k_ = 2, np_ = 2, h_ = 5, mu_ = 100;
    CSRGraph fwd_;
    std::vector<vid_t> level_, ldown_;          // forward / backward topological levels
    std::vector<vid_t> outdeg_;                  // out-degree per vertex
    std::vector<std::vector<vid_t>> lout_, lin_;  // [p*n+v] -> sorted up-to-k smallest pi-values
    std::vector<std::vector<vid_t>> lhv_;        // huge vertices reaching v (sorted by id, <= h)
    std::vector<int> stamp_;
    int query_cnt_ = 0;
};

}  // namespace reachability

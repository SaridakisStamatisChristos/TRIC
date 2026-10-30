#pragma once
#include "reachability/csr_graph.hpp"
#include <vector>
#include <cstddef>
#include <cstdint>

namespace reachability {

// FERRARI — Seufert, Anand, Bedathur & Weikum, "FERRARI: Flexible and Efficient Reachability
// Range Assignment for Graph Indexing", ICDE 2013, on a DAG. A *partial* index (no false
// answers) generalising the interval labeling of Agrawal et al. and GRAIL.
//
// The tree cover follows the paper's heuristic: each vertex's tree parent is the in-neighbour with
// the highest topological-order number (arg max_{p in N-(v)} tau(p)). The tree is post-order
// numbered; each vertex's reachable set is encoded as a set of post-order id intervals, computed
// by merging children's interval sets in reverse topological order. Adjacent intervals are merged
// across the smallest gaps (the optimal FERRARI k-interval cover), minimising false positives. An
// interval is *exact* if it contains no unreachable id, else *approximate*. A query checks the
// target's id against the source's intervals: outside all -> not reachable; inside an exact one ->
// reachable; inside only approximate ones -> a guided DFS settles it (always exact).
//
// Two indexing variants (Algorithm 1/2) unified by the constant c >= 1:
//   * c = 1  -> FERRARI-L: each vertex keeps a k-interval cover (local budget |I(v)| <= k).
//   * c > 1  -> FERRARI-G: deferred merging — each vertex first keeps a ck-interval cover; once the
//               total interval count exceeds the global budget B = kn, the lowest-degree vertices
//               are popped from a min-heap and restricted to a k-interval cover (paper default c=4).
// Extra pruning (Section V): the GRAIL topological level filter, and seed-based pruning with
// num_seeds max-degree seed vertices — bitsets S+(v)/S-(v) of reachable/reaching seeds give a
// positive cut (S+(s) & S-(t) != 0 => reachable) and a negative cut (a seed reaching s but not t
// => not reachable). Reference code (github.com/steps/Ferrari, by the first author) was consulted;
// this is an independent implementation from the paper. Verified vs the BFS oracle.
class Ferrari {
public:
    Ferrari() = default;

    void build(const CSRGraph& dag, int k, int c, int num_seeds);
    bool reaches(vid_t s, vid_t t);
    std::size_t index_size_bytes() const;

private:
    int check(vid_t v, vid_t pid) const;   // 0 none, 1 approximate, 2 exact

    vid_t n_ = 0;
    CSRGraph fwd_;
    std::vector<vid_t> pi_;                 // post-order number
    std::vector<vid_t> level_;              // topological level (quick negative cut)
    std::vector<std::vector<vid_t>> is_, ie_;  // per vertex: sorted interval starts / ends
    std::vector<std::vector<char>> iex_;       // per vertex: exact flag per interval
    int num_seeds_ = 0;
    std::vector<std::uint64_t> splus_, sminus_;  // seeds reachable from / reaching each vertex
    std::vector<int> stamp_;                // guided-DFS per-query stamp
    int query_cnt_ = 0;
};

}  // namespace reachability

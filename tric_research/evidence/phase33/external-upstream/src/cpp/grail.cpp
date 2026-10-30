#include "reachability/grail.hpp"
#include "reachability/levels.hpp"
#include "reachability/minpost.hpp"
#include <random>

namespace reachability {

void Grail::build(const CSRGraph& dag, int d, std::uint32_t seed, bool bidirectional) {
    dag_ = dag;
    bidirectional_ = bidirectional;
    d_ = d;
    n_ = dag_.num_nodes();
    pre_.assign((std::size_t)d_ * n_, 0);
    post_.assign((std::size_t)d_ * n_, 0);
    middle_.assign((std::size_t)d_ * n_, 0);
    visited_.assign(n_, 0);
    query_cnt_ = 0;
    for (int k = 0; k < d_; ++k)
        label_dimension(k, seed + (std::uint32_t)k);
    top_level_ = topological_levels(dag_);

    if (bidirectional_) {
        // Reverse CSR (in-edges) for the backward half of the bidirectional search.
        std::vector<vid_t> rs, rd;
        rs.reserve(dag_.num_edges());
        rd.reserve(dag_.num_edges());
        for (vid_t u = 0; u < n_; ++u)
            for (const vid_t* it = dag_.out_begin(u); it != dag_.out_end(u); ++it) {
                rs.push_back(*it); rd.push_back(u);
            }
        rdag_ = CSRGraph(n_, rs, rd);
    }
}

// One randomized min-post labeling (shared with FELINE's positive cut), scattered into the
// node-major label arrays for dimension k.
void Grail::label_dimension(int k, std::uint32_t seed) {
    std::mt19937 rng(seed);
    MinPost L = min_post_label(dag_, &rng);
    for (vid_t v = 0; v < n_; ++v) {
        std::size_t idx = (std::size_t)v * d_ + k;
        pre_[idx] = L.pre[v];
        post_[idx] = L.post[v];
        middle_[idx] = L.middle[v];
    }
}

bool Grail::contains(vid_t u, vid_t v) const {
    for (int k = 0; k < d_; ++k) {
        if (pre_[(std::size_t)u * d_ + k] > pre_[(std::size_t)v * d_ + k]) return false;
        if (post_[(std::size_t)u * d_ + k] < post_[(std::size_t)v * d_ + k]) return false;
    }
    return true;
}

int Grail::contains_pp(vid_t u, vid_t v) const {
    for (int k = 0; k < d_; ++k) {
        std::size_t iu = (std::size_t)u * d_ + k, iv = (std::size_t)v * d_ + k;
        if (pre_[iu] > pre_[iv]) return -1;          // exact negative cut
        if (post_[iu] < post_[iv]) return -1;        // exact negative cut
        if (middle_[iu] < post_[iv]) return 1;       // exact positive cut (tree-descendant)
    }
    return 0;                                        // inconclusive
}

bool Grail::reaches(vid_t u, vid_t v) {
    if (u == v) return true;                 // reflexive
    if (top_level_[u] >= top_level_[v]) return false;   // level filter (exact negative)
    int r = contains_pp(u, v);
    if (r == -1) return false;               // exact negative
    if (r == 1) return true;                 // exact positive
    // Inconclusive: fall back to a search (one- or two-sided).
    return bidirectional_ ? reaches_bidirectional(u, v) : reaches_guided(u, v);
}

// One-sided guided DFS from u, pruned by the PP cuts and the level filter.
bool Grail::reaches_guided(vid_t u, vid_t v) {
    const vid_t lv = top_level_[v];
    ++query_cnt_;
    std::vector<vid_t> stack;
    visited_[u] = query_cnt_;
    stack.push_back(u);
    while (!stack.empty()) {
        vid_t x = stack.back(); stack.pop_back();
        for (const vid_t* it = dag_.out_begin(x); it != dag_.out_end(x); ++it) {
            vid_t w = *it;
            if (visited_[w] == query_cnt_) continue;
            int rw = contains_pp(w, v);
            if (rw == 1) return true;        // positive cut: w (hence x) reaches v
            // rw == 0 here implies w != v, so the level prune cannot skip the target.
            if (rw == 0 && top_level_[w] < lv) {
                visited_[w] = query_cnt_;
                stack.push_back(w);
            }
            // rw == -1, or level too high: prune this branch
        }
    }
    return false;
}

// Two-sided search: a forward frontier from u (reachable-from-u) and a backward
// frontier from v (can-reach-v) grow alternately; success when they meet. Both
// sides are pruned by the PP cuts and the level filter. Forward stamps use +qc,
// backward stamps use -qc, so a node carrying the other side's stamp is a meet.
bool Grail::reaches_bidirectional(vid_t u, vid_t v) {
    ++query_cnt_;
    const int F = query_cnt_, B = -query_cnt_;
    const vid_t lu = top_level_[u], lv = top_level_[v];
    std::vector<vid_t> fq, bq;
    std::size_t fh = 0, bh = 0;
    visited_[u] = F; fq.push_back(u);
    visited_[v] = B; bq.push_back(v);
    while (fh < fq.size() && bh < bq.size()) {
        // forward: expand one reachable-from-u node toward v
        vid_t x = fq[fh++];
        if (top_level_[x] < lv) {                 // x can still reach v
            for (const vid_t* it = dag_.out_begin(x); it != dag_.out_end(x); ++it) {
                vid_t w = *it;
                if (visited_[w] == B) return true;        // met the backward frontier
                if (visited_[w] == F) continue;
                int rw = contains_pp(w, v);
                if (rw == 1) return true;
                if (rw == 0) { visited_[w] = F; fq.push_back(w); }
            }
        }
        // backward: expand one can-reach-v node toward u (over in-edges)
        vid_t y = bq[bh++];
        if (lu < top_level_[y]) {                 // u can still reach y
            for (const vid_t* it = rdag_.out_begin(y); it != rdag_.out_end(y); ++it) {
                vid_t w = *it;
                if (visited_[w] == F) return true;        // met the forward frontier
                if (visited_[w] == B) continue;
                int rw = contains_pp(u, w);
                if (rw == 1) return true;
                if (rw == 0) { visited_[w] = B; bq.push_back(w); }
            }
        }
    }
    return false;
}

std::size_t Grail::index_size_bytes() const {
    std::size_t bytes =
        (pre_.size() + post_.size() + middle_.size() + top_level_.size()) * sizeof(vid_t);
    if (bidirectional_)
        bytes += rdag_.num_edges() * sizeof(vid_t) + (std::size_t)(n_ + 1) * sizeof(std::size_t);
    return bytes;
}

}  // namespace reachability

#include "reachability/feline.hpp"
#include "reachability/levels.hpp"
#include "reachability/minpost.hpp"
#include <queue>
#include <utility>

namespace reachability {

// Algorithm 1: two complementary topological orderings of g.
//   X = a plain topological order (Kahn, FIFO).
//   Y = Kahn where, among the current roots, we always pop the one with the largest X
//       (Kornaropoulos heuristic — locally minimizes false-implied paths).
void Feline::compute_orders(const CSRGraph& g, std::vector<vid_t>& X, std::vector<vid_t>& Y) {
    const vid_t n = g.num_nodes();
    X.assign(n, 0);
    Y.assign(n, 0);
    std::vector<vid_t> indeg(n, 0);
    for (vid_t u = 0; u < n; ++u)
        for (const vid_t* it = g.out_begin(u); it != g.out_end(u); ++it)
            ++indeg[*it];

    // X: DFS reverse post-order (a topological order). A DFS order keeps a vertex close to
    // its descendants, which tightens the dominance drawing (fewer false positives) far more
    // than a BFS-layered order would.
    {
        std::vector<char> seen(n, 0);
        std::vector<vid_t> finish;          // post-order (finish) sequence
        finish.reserve(n);
        struct F { vid_t v; const vid_t* it; const vid_t* end; };
        std::vector<F> st;
        for (vid_t r = 0; r < n; ++r) {
            if (indeg[r] != 0 || seen[r]) continue;   // start DFS trees at the roots
            seen[r] = 1;
            st.push_back({r, g.out_begin(r), g.out_end(r)});
            while (!st.empty()) {
                std::size_t top = st.size() - 1;       // re-index: push() may reallocate
                if (st[top].it != st[top].end) {
                    vid_t w = *st[top].it; ++st[top].it;
                    if (!seen[w]) { seen[w] = 1; st.push_back({w, g.out_begin(w), g.out_end(w)}); }
                } else {
                    finish.push_back(st[top].v);
                    st.pop_back();
                }
            }
        }
        // topological order = reverse of finish order: a source finishes last -> rank 0.
        for (vid_t i = 0; i < n; ++i) X[finish[i]] = n - 1 - i;
    }
    // Y: Kahn with a max-heap on X (pop the available root of highest X rank).
    {
        std::vector<vid_t> ind = indeg;
        std::priority_queue<std::pair<vid_t, vid_t>> pq;   // (X[u], u), max-heap by X
        for (vid_t u = 0; u < n; ++u)
            if (ind[u] == 0) pq.push({X[u], u});
        vid_t rank = 0;
        while (!pq.empty()) {
            vid_t u = pq.top().second; pq.pop();
            Y[u] = rank++;
            for (const vid_t* it = g.out_begin(u); it != g.out_end(u); ++it)
                if (--ind[*it] == 0) pq.push({X[*it], *it});
        }
    }
}

void Feline::build(const CSRGraph& dag, bool bidirectional) {
    dag_ = dag;
    bidirectional_ = bidirectional;
    n_ = dag_.num_nodes();
    visited_.assign(n_, 0);
    query_cnt_ = 0;

    compute_orders(dag_, X_, Y_);
    level_ = topological_levels(dag_);   // shared level filter (negative cut + DFS prune)
    compute_positive_cut();

    if (bidirectional_) {
        // Reverse CSR + a second FELINE coordinate system (FELINE-B).
        std::vector<vid_t> rs, rd;
        rs.reserve(dag_.num_edges());
        rd.reserve(dag_.num_edges());
        for (vid_t u = 0; u < n_; ++u)
            for (const vid_t* it = dag_.out_begin(u); it != dag_.out_end(u); ++it) {
                rs.push_back(*it); rd.push_back(u);
            }
        CSRGraph rdag(n_, rs, rd);
        compute_orders(rdag, X2_, Y2_);
    }
}

// Positive-cut labeling: the same min-post labeling GRAIL uses, with a single (d=1) fixed
// spanning forest. We keep the entry/exit numbers (middle, post); a nested entry/exit window
// means a tree path, hence reachability.
void Feline::compute_positive_cut() {
    MinPost L = min_post_label(dag_, /*rng=*/nullptr);
    pc_middle_ = std::move(L.middle);
    pc_post_ = std::move(L.post);
}

// Algorithm 2: dominance negative cut + dominance-pruned guided DFS.
bool Feline::reaches(vid_t u, vid_t v) {
    if (u == v) return true;
    // Negative cuts first: on a mostly-negative workload this avoids the positive-cut
    // work on pairs that are already decided unreachable (a tree path implies dominance,
    // so if dominance fails the positive cut would fail too).
    if (level_[u] >= level_[v]) return false;   // level filter (exact negative)
    if (!dominates(u, v)) return false;         // dominance negative cut (Theorem 1)
    if (bidirectional_ && !dominates_rev(v, u)) return false;   // reversed-index negative cut
    if (positive_contains(u, v)) return true;   // positive cut (tree path) — exact positive

    const vid_t lv = level_[v];
    ++query_cnt_;
    std::vector<vid_t> stack;
    visited_[u] = query_cnt_;
    stack.push_back(u);
    while (!stack.empty()) {
        vid_t x = stack.back(); stack.pop_back();
        for (const vid_t* it = dag_.out_begin(x); it != dag_.out_end(x); ++it) {
            vid_t w = *it;
            if (w == v) return true;
            // expand only neighbors that dominate v, sit below its level, and (FELINE-B)
            // also lie in the target's reversed dominance region
            if (visited_[w] != query_cnt_ && level_[w] < lv && dominates(w, v)
                    && (!bidirectional_ || dominates_rev(v, w))) {
                if (positive_contains(w, v)) return true;   // positive short-circuit
                visited_[w] = query_cnt_;
                stack.push_back(w);
            }
        }
    }
    return false;
}

std::size_t Feline::index_size_bytes() const {
    return (X_.size() + Y_.size() + level_.size() + pc_middle_.size() + pc_post_.size()
            + X2_.size() + Y2_.size()) * sizeof(vid_t);
}

}  // namespace reachability

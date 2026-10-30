#include "reachability/tflabel.hpp"
#include "reachability/levels.hpp"
#include <algorithm>
#include <numeric>
#include <set>
#include <vector>

namespace reachability {

namespace {
void sort_unique(std::vector<vid_t>& v) {
    std::sort(v.begin(), v.end());
    v.erase(std::unique(v.begin(), v.end()), v.end());
}
}  // namespace

// Faithful transformed topological folding (Cheng et al., Procedure 1): cross-level edges are
// rerouted through *shared, lazily created* dummy vertices (one dummy per odd vertex per side per
// fold), so the labels stay compact — rather than subdividing every cross-level edge eagerly.
void TFLabel::build(const CSRGraph& dag) {
    n_ = dag.num_nodes();
    L_.resize(n_);
    level_ = topological_levels(dag);   // 0-indexed longest path from a source
    if (n_ == 0) return;

    std::vector<vid_t> lvl(n_);
    for (vid_t v = 0; v < n_; ++v) lvl[v] = level_[v] + 1;   // 1-indexed
    std::vector<std::set<vid_t>> out(n_), in(n_);
    for (vid_t u = 0; u < n_; ++u)
        for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) {
            out[u].insert(*it); in[*it].insert(u);
        }
    std::vector<char> alive(n_, 1);
    auto add_dummy = [&](vid_t at_level) -> vid_t {
        vid_t id = static_cast<vid_t>(lvl.size());
        lvl.push_back(at_level); out.emplace_back(); in.emplace_back(); alive.push_back(1);
        return id;
    };

    // nb*/tf are sized at the end (vertex set grows with dummies); collect into maps by id.
    std::vector<std::vector<vid_t>> nbout_tmp, nbin_tmp;
    std::vector<vid_t> tf_tmp;
    auto ensure = [&](vid_t id) {
        while ((vid_t)tf_tmp.size() <= id) { tf_tmp.push_back(0); nbout_tmp.emplace_back(); nbin_tmp.emplace_back(); }
    };

    vid_t fold = 1;
    for (;;) {
        vid_t M = 0;
        for (vid_t v = 0; v < (vid_t)lvl.size(); ++v) if (alive[v] && lvl[v] > M) M = lvl[v];

        // snapshot of alive odd-level vertices (dummies created below sit at even levels)
        std::vector<vid_t> oddV;
        for (vid_t v = 0; v < (vid_t)lvl.size(); ++v) if (alive[v] && (lvl[v] & 1)) oddV.push_back(v);

        // Step 2.1: reroute each odd v's out-neighbours above level j+1 through one dummy at j+1.
        for (vid_t v : oddV) {
            vid_t j = lvl[v];
            std::vector<vid_t> U;
            for (vid_t u : out[v]) if (lvl[u] > j + 1) U.push_back(u);
            if (U.empty()) continue;
            vid_t w = add_dummy(j + 1);
            for (vid_t u : U) { out[v].erase(u); in[u].erase(v); out[w].insert(u); in[u].insert(w); }
            out[v].insert(w); in[w].insert(v);
        }
        // Step 2.2: reroute each odd v's even in-neighbours below level j-1 through one dummy at j-1.
        for (vid_t v : oddV) {
            vid_t j = lvl[v];
            std::vector<vid_t> U;
            for (vid_t u : in[v]) if (lvl[u] < j - 1 && (lvl[u] & 1) == 0) U.push_back(u);
            if (U.empty()) continue;
            vid_t w = add_dummy(j - 1);
            for (vid_t u : U) { in[v].erase(u); out[u].erase(v); out[u].insert(w); in[w].insert(u); }
            out[w].insert(v); in[v].insert(w);
        }
        // Step 2.3: connect each odd v's level-(j-1) in-neighbours to its level-(j+1) out-neighbours.
        for (vid_t v : oddV) {
            vid_t j = lvl[v];
            std::vector<vid_t> A, B;
            for (vid_t a : in[v]) if (lvl[a] == j - 1) A.push_back(a);
            for (vid_t b : out[v]) if (lvl[b] == j + 1) B.push_back(b);
            for (vid_t a : A) for (vid_t b : B) { out[a].insert(b); in[b].insert(a); }
        }

        if (M <= 1) {   // single level remains: finalize and stop
            for (vid_t v = 0; v < (vid_t)lvl.size(); ++v)
                if (alive[v]) { ensure(v); tf_tmp[v] = fold; }
            break;
        }

        // record the odd-level vertices removed this fold (their neighbours in the transformed G*_i)
        for (vid_t v : oddV) {
            ensure(v); tf_tmp[v] = fold;
            nbout_tmp[v].assign(out[v].begin(), out[v].end());
            nbin_tmp[v].assign(in[v].begin(), in[v].end());
        }
        // fold: drop odd-level vertices and incident edges, then halve surviving (even) levels
        for (vid_t v : oddV) {
            for (vid_t u : out[v]) in[u].erase(v);
            for (vid_t u : in[v]) out[u].erase(v);
            out[v].clear(); in[v].clear(); alive[v] = 0;
        }
        for (vid_t v = 0; v < (vid_t)lvl.size(); ++v) if (alive[v]) lvl[v] /= 2;
        ++fold;
    }

    const vid_t N = static_cast<vid_t>(lvl.size());
    ensure(N - 1);

    // Label closure (Definition 5), processed in decreasing tf so dependencies are ready.
    std::vector<vid_t> order(N);
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](vid_t a, vid_t b){ return tf_tmp[a] > tf_tmp[b]; });

    std::vector<std::vector<vid_t>> lo(N), li(N);
    for (vid_t v : order) {
        std::vector<vid_t>& o = lo[v];
        o.push_back(v);
        for (vid_t w : nbout_tmp[v]) o.insert(o.end(), lo[w].begin(), lo[w].end());
        sort_unique(o);
        std::vector<vid_t>& i = li[v];
        i.push_back(v);
        for (vid_t w : nbin_tmp[v]) i.insert(i.end(), li[w].begin(), li[w].end());
        sort_unique(i);
    }

    for (vid_t v = 0; v < n_; ++v) { L_.Lout[v] = std::move(lo[v]); L_.Lin[v] = std::move(li[v]); }
}

bool TFLabel::query(vid_t u, vid_t v) const {
    if (u == v) return true;
    if (level_[u] >= level_[v]) return false;   // topological quick reject
    return two_hop_intersects(L_, u, v);
}

std::size_t TFLabel::index_size_bytes() const {
    return L_.size_bytes() + level_.size() * sizeof(vid_t);
}

}  // namespace reachability

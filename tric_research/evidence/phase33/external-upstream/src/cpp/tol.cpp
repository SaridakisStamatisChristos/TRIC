#include "reachability/tol.hpp"
#include "reachability/levels.hpp"
#include <algorithm>
#include <numeric>
#include <vector>

namespace reachability {

void TOL::build(const CSRGraph& dag) {
    n_ = dag.num_nodes();
    L_.resize(n_);
    level_ = topological_levels(dag);
    if (n_ == 0) return;

    // reverse graph (in-neighbours) + in-degrees for Kahn topological order
    std::vector<vid_t> rs, rd, indeg(n_, 0);
    rs.reserve(dag.num_edges()); rd.reserve(dag.num_edges());
    for (vid_t u = 0; u < n_; ++u)
        for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) {
            rs.push_back(*it); rd.push_back(u); ++indeg[*it];
        }
    CSRGraph rdag(n_, rs, rd);

    std::vector<vid_t> topo; topo.reserve(n_);
    {
        std::vector<vid_t> ind = indeg, q;
        for (vid_t u = 0; u < n_; ++u) if (ind[u] == 0) q.push_back(u);
        std::size_t h = 0;
        while (h < q.size()) {
            vid_t u = q[h++]; topo.push_back(u);
            for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it)
                if (--ind[*it] == 0) q.push_back(*it);
        }
    }

    // Approximate contribution scores by a linear scan (Zhu et al., Sec. 7.1, upper bound):
    //   Sin(v)  = 0 if no in-neighbour,  else sum over in-neighbours u of (Sin(u) + 1)
    //   Sout(v) = 0 if no out-neighbour, else sum over out-neighbours w of (Sout(w) + 1)
    // Sin in ascending topo order, Sout in descending. Saturate to keep f finite on big DAGs.
    const double CAP = 1e15;
    std::vector<double> sin_(n_, 0.0), sout_(n_, 0.0);
    for (vid_t v : topo) {
        double s = 0.0;
        for (const vid_t* it = rdag.out_begin(v); it != rdag.out_end(v); ++it) s += sin_[*it] + 1.0;
        sin_[v] = s > CAP ? CAP : s;
    }
    for (std::size_t i = topo.size(); i-- > 0;) {
        vid_t v = topo[i];
        double s = 0.0;
        for (const vid_t* it = dag.out_begin(v); it != dag.out_end(v); ++it) s += sout_[*it] + 1.0;
        sout_[v] = s > CAP ? CAP : s;
    }

    std::vector<double> f(n_, 0.0);
    for (vid_t v = 0; v < n_; ++v) {
        double a = sin_[v], b = sout_[v];
        f[v] = (a + b > 0.0) ? (a * b + a + b) / (a + b) : 0.0;
    }

    // level order: descending contribution score (ties by vertex id)
    std::vector<vid_t> order(n_);
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(), [&](vid_t x, vid_t y) {
        if (f[x] != f[y]) return f[x] > f[y];
        return x < y;
    });

    build_two_hop_labels(dag, order, L_);
}

bool TOL::query(vid_t u, vid_t v) const {
    if (u == v) return true;
    if (level_[u] >= level_[v]) return false;   // topological quick reject
    return two_hop_intersects(L_, u, v);
}

std::size_t TOL::index_size_bytes() const {
    return L_.size_bytes() + level_.size() * sizeof(vid_t);
}

}  // namespace reachability

#include "reachability/preach.hpp"
#include "reachability/levels.hpp"
#include <algorithm>
#include <queue>
#include <utility>

namespace reachability {

namespace {
// Single DFS computing, per node, all of the paper's ranges:
//   phi/phi_hat = preorder + subtree max (Lemmas 3-4);
//   pmin        = smallest reachable DFS number (Lemma 6);
//   pgap        = boundary of the empty range just left of v (Lemma 7);
//   [plo,phi_]  = largest reachable range outside v's subtree, ptree (Lemma 5); empty if plo>phi_.
// All are computed at a node's DFS finish from its already-finished out-neighbours.
void dfs_ranges(const CSRGraph& g, const std::vector<vid_t>& roots,
                std::vector<vid_t>& phi, std::vector<vid_t>& phi_hat,
                std::vector<vid_t>& pmin, std::vector<vid_t>& pgap,
                std::vector<vid_t>& plo, std::vector<vid_t>& phi_) {
    const vid_t n = g.num_nodes();
    phi.assign(n, 0); phi_hat.assign(n, 0);
    pmin.assign(n, 0); pgap.assign(n, (vid_t)-1);
    plo.assign(n, 1); phi_.assign(n, 0);            // ptree empty by default (plo > phi_)
    std::vector<char> seen(n, 0);
    vid_t counter = 0;
    struct F { vid_t v; const vid_t* it; const vid_t* end; };
    std::vector<F> st;
    for (vid_t r : roots) {
        if (seen[r]) continue;
        seen[r] = 1;
        phi[r] = counter++;
        st.push_back({r, g.out_begin(r), g.out_end(r)});
        while (!st.empty()) {
            std::size_t top = st.size() - 1;
            if (st[top].it != st[top].end) {
                vid_t w = *st[top].it; ++st[top].it;
                if (!seen[w]) {
                    seen[w] = 1;
                    phi[w] = counter++;
                    st.push_back({w, g.out_begin(w), g.out_end(w)});
                }
            } else {
                vid_t v = st[top].v;
                phi_hat[v] = counter - 1;            // contiguous preorder over the subtree
                vid_t mn = phi[v], gap = (vid_t)-1, blo = 1, bhi = 0;
                long long bsz = 0;
                for (const vid_t* it = g.out_begin(v); it != g.out_end(v); ++it) {
                    vid_t w = *it;
                    mn = std::min(mn, pmin[w]);                       // Lemma 6
                    gap = std::max(gap, pgap[w]);                     // Lemma 7
                    if (phi[w] < phi[v]) gap = std::max(gap, phi_hat[w]);
                    if (plo[w] <= phi_[w]) {                          // inherited ptree(w) (Lemma 5)
                        long long sz = (long long)phi_[w] - plo[w] + 1;
                        if (sz > bsz) { bsz = sz; blo = plo[w]; bhi = phi_[w]; }
                    }
                    if (phi[w] < phi[v]) {                            // cross edge: w outside subtree
                        long long sz = (long long)phi_hat[w] - phi[w] + 1;
                        if (sz > bsz) { bsz = sz; blo = phi[w]; bhi = phi_hat[w]; }
                    }
                }
                pmin[v] = mn; pgap[v] = gap; plo[v] = blo; phi_[v] = bhi;
                st.pop_back();
            }
        }
    }
}
}  // namespace

void PReaCH::build(const CSRGraph& dag) {
    n_ = dag.num_nodes();
    vf_.assign(n_, 0);
    vb_.assign(n_, 0);
    query_cnt_ = 0;

    // reverse graph
    std::vector<vid_t> rs, rd;
    rs.reserve(dag.num_edges()); rd.reserve(dag.num_edges());
    for (vid_t u = 0; u < n_; ++u)
        for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) {
            rs.push_back(*it); rd.push_back(u);
        }
    CSRGraph rdag(n_, rs, rd);

    // RCH ordering: contract source/sink vertices, smallest input total-degree first.
    std::vector<vid_t> order(n_, 0);
    {
        std::vector<vid_t> indeg(n_, 0), outdeg(n_, 0);
        for (vid_t u = 0; u < n_; ++u) {
            outdeg[u] = dag.out_degree(u);
            indeg[u] = rdag.out_degree(u);
        }
        std::vector<vid_t> deg0(n_);
        for (vid_t u = 0; u < n_; ++u) deg0[u] = indeg[u] + outdeg[u];
        std::vector<char> done(n_, 0);
        // min-heap by (input degree, id)
        std::priority_queue<std::pair<vid_t, vid_t>,
                            std::vector<std::pair<vid_t, vid_t>>,
                            std::greater<std::pair<vid_t, vid_t>>> pq;
        for (vid_t u = 0; u < n_; ++u)
            if (indeg[u] == 0 || outdeg[u] == 0) pq.push({deg0[u], u});
        vid_t next = 0;
        while (!pq.empty()) {
            vid_t v = pq.top().second; pq.pop();
            if (done[v]) continue;
            done[v] = 1;
            order[v] = next++;
            for (const vid_t* it = dag.out_begin(v); it != dag.out_end(v); ++it) {
                vid_t w = *it;
                if (done[w]) continue;
                if (--indeg[w] == 0) pq.push({deg0[w], w});       // became a source
            }
            for (const vid_t* it = rdag.out_begin(v); it != rdag.out_end(v); ++it) {
                vid_t u = *it;
                if (done[u]) continue;
                if (--outdeg[u] == 0) pq.push({deg0[u], u});      // became a sink
            }
        }
    }

    // Forward up-edges (order(u) < order(v)) and backward up-edges (v -> pred u, order(u) > order(v)).
    {
        std::vector<vid_t> fs, fd, bs, bd;
        for (vid_t u = 0; u < n_; ++u)
            for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) {
                vid_t v = *it;
                if (order[u] < order[v]) { fs.push_back(u); fd.push_back(v); }
                else { bs.push_back(v); bd.push_back(u); }   // backward: v -> u (u higher order)
            }
        fwd_ = CSRGraph(n_, fs, fd);
        bwd_ = CSRGraph(n_, bs, bd);
    }

    lf_ = topological_levels(dag);    // forward levels (longest path from a root)
    lb_ = topological_levels(rdag);   // backward levels

    // DFS ranges: forward from sources (in-degree 0), backward from sinks (in rdag, sources).
    std::vector<vid_t> froots, broots;
    for (vid_t u = 0; u < n_; ++u) {
        if (rdag.out_degree(u) == 0) froots.push_back(u);   // in-degree 0
        if (dag.out_degree(u) == 0) broots.push_back(u);    // out-degree 0
    }
    dfs_ranges(dag, froots, pf_, pf_hat_, pf_min_, pf_gap_, pf_plo_, pf_phi_);
    dfs_ranges(rdag, broots, pb_, pb_hat_, pb_min_, pb_gap_, pb_plo_, pb_phi_);
}

bool PReaCH::reaches(vid_t u, vid_t v) {
    if (u == v) return true;

    // Constant-time cuts (Lemmas 2-7), forward and backward, positives first.
    if (pf_[u] <= pf_[v] && pf_[v] <= pf_hat_[u]) return true;     // L3 fwd: DFS range (positive)
    if (pf_plo_[u] <= pf_[v] && pf_[v] <= pf_phi_[u]) return true; // L5 fwd: ptree range (positive)
    if (pb_[v] <= pb_[u] && pb_[u] <= pb_hat_[v]) return true;     // L3 bwd
    if (pb_plo_[v] <= pb_[u] && pb_[u] <= pb_phi_[v]) return true; // L5 bwd
    if (lf_[u] >= lf_[v]) return false;                            // L2 fwd: level (negative)
    if (lb_[v] >= lb_[u]) return false;                            // L2 bwd
    if (pf_[v] > pf_hat_[u]) return false;                         // L4 fwd: range (negative)
    if (pb_[u] > pb_hat_[v]) return false;                         // L4 bwd
    if (pf_[v] < pf_min_[u]) return false;                         // L6 fwd: phi_min (negative)
    if (pb_[u] < pb_min_[v]) return false;                         // L6 bwd
    if (pf_gap_[u] < pf_[v] && pf_[v] < pf_[u]) return false;      // L7 fwd: phi_gap (negative)
    if (pb_gap_[v] < pb_[u] && pb_[u] < pb_[v]) return false;      // L7 bwd

    // Bidirectional up-search; prune by levels/ranges before queueing; meet => reachable.
    ++query_cnt_;
    const int qc = query_cnt_;
    std::vector<vid_t> fq, bq;
    std::size_t fh = 0, bh = 0;
    vf_[u] = qc; fq.push_back(u);
    vb_[v] = qc; bq.push_back(v);
    const vid_t lft = lf_[v], pft = pf_[v];          // target bounds for the forward search
    const vid_t lbs = lb_[u], pbs = pb_[u];          // source bounds for the backward search
    while (fh < fq.size() || bh < bq.size()) {
        if (fh < fq.size()) {
            vid_t x = fq[fh++];
            for (const vid_t* it = fwd_.out_begin(x); it != fwd_.out_end(x); ++it) {
                vid_t w = *it;
                if (vb_[w] == qc) return true;                     // met the backward frontier
                if (vf_[w] == qc) continue;
                if (lf_[w] >= lft || pft > pf_hat_[w]) continue;   // w cannot reach v (L2/L4)
                if (pft < pf_min_[w]) continue;                    // L6: w cannot reach v
                if (pf_gap_[w] < pft && pft < pf_[w]) continue;    // L7: w cannot reach v
                if (pf_[w] <= pft && pft <= pf_hat_[w]) return true;       // L3 positive
                if (pf_plo_[w] <= pft && pft <= pf_phi_[w]) return true;   // L5 positive
                vf_[w] = qc; fq.push_back(w);
            }
        }
        if (bh < bq.size()) {
            vid_t y = bq[bh++];
            for (const vid_t* it = bwd_.out_begin(y); it != bwd_.out_end(y); ++it) {
                vid_t z = *it;
                if (vf_[z] == qc) return true;                     // met the forward frontier
                if (vb_[z] == qc) continue;
                if (lb_[z] >= lbs || pbs > pb_hat_[z]) continue;   // u cannot reach z (L2/L4)
                if (pbs < pb_min_[z]) continue;                    // L6: u cannot reach z
                if (pb_gap_[z] < pbs && pbs < pb_[z]) continue;    // L7: u cannot reach z
                if (pb_[z] <= pbs && pbs <= pb_hat_[z]) return true;       // L3 positive
                if (pb_plo_[z] <= pbs && pbs <= pb_phi_[z]) return true;   // L5 positive
                vb_[z] = qc; bq.push_back(z);
            }
        }
    }
    return false;
}

std::size_t PReaCH::index_size_bytes() const {
    return (lf_.size() + lb_.size() + pf_.size() + pf_hat_.size() + pb_.size() + pb_hat_.size() +
            pf_min_.size() + pf_gap_.size() + pf_plo_.size() + pf_phi_.size() +
            pb_min_.size() + pb_gap_.size() + pb_plo_.size() + pb_phi_.size()) * sizeof(vid_t) +
           (fwd_.num_edges() + bwd_.num_edges()) * sizeof(vid_t);
}

}  // namespace reachability

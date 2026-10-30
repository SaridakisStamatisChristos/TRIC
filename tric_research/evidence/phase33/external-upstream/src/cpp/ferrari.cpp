#include "reachability/ferrari.hpp"
#include "reachability/levels.hpp"
#include <algorithm>
#include <cstdint>
#include <queue>
#include <vector>

namespace reachability {

namespace {
struct Iv { vid_t a, b; char ex; };

// Coalesce overlapping / adjacent intervals (gap-free runs); the result stays exact iff every
// merged piece was exact. Input must be sorted by start.
void coalesce(std::vector<Iv>& cur, std::vector<Iv>& m) {
    m.clear();
    for (const Iv& iv : cur) {
        if (!m.empty() && iv.a <= m.back().b + 1) {
            if (iv.b > m.back().b) m.back().b = iv.b;
            m.back().ex = (char)(m.back().ex && iv.ex);
        } else m.push_back(iv);
    }
}

// Optimal maxc-interval cover (Def. 3): keep the maxc-1 largest gaps as real separators and merge
// everything else, which minimises the number of approximate (false-positive) ids. `m` must be a
// coalesced (disjoint, sorted) interval set.
void reduce(std::vector<Iv>& m, int maxc) {
    if ((int)m.size() <= maxc) return;
    const vid_t N = (vid_t)m.size();
    std::vector<vid_t> gi(N - 1);
    for (vid_t i = 0; i < N - 1; ++i) gi[i] = i;
    std::sort(gi.begin(), gi.end(), [&](vid_t x, vid_t y) {
        long long gx = (long long)m[x + 1].a - m[x].b - 1, gy = (long long)m[y + 1].a - m[y].b - 1;
        return gx > gy;
    });
    std::vector<char> cut(N - 1, 0);
    for (int c = 0; c < maxc - 1; ++c) cut[gi[c]] = 1;     // separators
    std::vector<Iv> r;
    vid_t a = 0;
    while (a < N) {
        vid_t b = a;
        while (b < N - 1 && !cut[b]) ++b;                  // extend group until a separator
        r.push_back({m[a].a, m[b].b, (char)(a == b ? m[a].ex : 0)});
        a = b + 1;
    }
    m.swap(r);
}
}  // namespace

void Ferrari::build(const CSRGraph& dag, int k, int c, int num_seeds) {
    if (k < 1) k = 1;
    if (c < 1) c = 1;
    if (num_seeds < 0) num_seeds = 0;
    if (num_seeds > 64) num_seeds = 64;
    n_ = dag.num_nodes();
    fwd_ = dag;
    level_ = topological_levels(dag);
    pi_.assign(n_, 0);
    is_.assign(n_, {}); ie_.assign(n_, {}); iex_.assign(n_, {});
    num_seeds_ = num_seeds;
    splus_.clear(); sminus_.clear();
    stamp_.assign(n_, 0); query_cnt_ = 0;
    if (n_ == 0) return;

    // topological order (Kahn); tau(v) = position in topo (used both as the topo number and rank).
    std::vector<vid_t> indeg(n_, 0);
    for (vid_t u = 0; u < n_; ++u)
        for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) ++indeg[*it];
    std::vector<vid_t> topo; topo.reserve(n_);
    {
        std::vector<vid_t> ind = indeg, q;
        for (vid_t u = 0; u < n_; ++u) if (ind[u] == 0) q.push_back(u);
        std::size_t h = 0;
        while (h < q.size()) { vid_t u = q[h++]; topo.push_back(u);
            for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it)
                if (--ind[*it] == 0) q.push_back(*it); }
    }
    std::vector<vid_t> tau(n_, 0);
    for (vid_t i = 0; i < (vid_t)topo.size(); ++i) tau[topo[i]] = i;

    // Tree cover (paper's heuristic): parent(v) = the in-neighbour p with the highest tau(p).
    std::vector<vid_t> parent(n_, -1), lo(n_, 0);
    std::vector<std::vector<vid_t>> children(n_);
    for (vid_t v = 0; v < n_; ++v)
        for (const vid_t* it = dag.out_begin(v); it != dag.out_end(v); ++it) {
            vid_t w = *it;                                  // edge v -> w, v is a predecessor of w
            if (parent[w] == (vid_t)-1 || tau[v] > tau[parent[w]]) parent[w] = v;
        }
    for (vid_t v = 0; v < n_; ++v) if (parent[v] != (vid_t)-1) children[parent[v]].push_back(v);

    // post-order numbering of the tree: pi (post number), lo (subtree min) -> exact interval [lo,pi]
    {
        vid_t counter = 0;
        std::vector<vid_t> sz(n_, 1);
        std::vector<std::pair<vid_t, std::size_t>> dst;
        for (vid_t r = 0; r < n_; ++r) {
            if (parent[r] != (vid_t)-1) continue;
            dst.push_back({r, 0});
            while (!dst.empty()) {
                auto& fr = dst.back();
                if (fr.second < children[fr.first].size()) dst.push_back({children[fr.first][fr.second++], 0});
                else {
                    vid_t v = fr.first;
                    pi_[v] = counter++;
                    lo[v] = pi_[v] - (sz[v] - 1);
                    if (parent[v] != (vid_t)-1) sz[parent[v]] += sz[v];
                    dst.pop_back();
                }
            }
        }
    }

    // FERRARI-G (Algorithm 2; c=1 reduces to FERRARI-L). Visit in reverse topological order, merge
    // children's interval sets, keep a ck-interval cover; defer restriction to k via a degree min-heap
    // once the running total exceeds the global budget B = kn.
    std::vector<std::vector<Iv>> lab(n_);
    std::priority_queue<std::pair<vid_t, vid_t>, std::vector<std::pair<vid_t, vid_t>>,
                        std::greater<std::pair<vid_t, vid_t>>> heap;   // (outdegree, vertex)
    const long long B = (long long)k * (long long)n_;
    long long total = 0;
    std::vector<Iv> cur, m;
    for (std::size_t i = topo.size(); i-- > 0;) {
        vid_t v = topo[i];
        cur.clear();
        cur.push_back({lo[v], pi_[v], 1});                 // exact tree interval IT(v)
        vid_t outdeg = 0;
        for (const vid_t* it = dag.out_begin(v); it != dag.out_end(v); ++it) {
            ++outdeg;
            for (const Iv& iv : lab[*it]) cur.push_back(iv);
        }
        std::sort(cur.begin(), cur.end(), [](const Iv& x, const Iv& y){ return x.a < y.a || (x.a == y.a && x.b < y.b); });
        coalesce(cur, m);
        reduce(m, c * k);
        lab[v] = m;
        total += (long long)lab[v].size();
        if ((int)lab[v].size() > k) heap.push({outdeg, v});
        while (total > B && !heap.empty()) {
            vid_t w = heap.top().second; heap.pop();
            if ((int)lab[w].size() <= k) continue;         // stale entry (already restricted)
            std::size_t old = lab[w].size();
            reduce(lab[w], k);
            total -= (long long)(old - lab[w].size());
        }
    }
    for (vid_t v = 0; v < n_; ++v) {
        is_[v].reserve(lab[v].size()); ie_[v].reserve(lab[v].size()); iex_[v].reserve(lab[v].size());
        for (const Iv& iv : lab[v]) { is_[v].push_back(iv.a); ie_[v].push_back(iv.b); iex_[v].push_back(iv.ex); }
    }

    // Seed-based pruning (Section V.A): the num_seeds highest-degree vertices (degree >= 1) are seeds.
    if (num_seeds_ > 0) {
        splus_.assign(n_, 0); sminus_.assign(n_, 0);
        std::vector<vid_t> deg(n_, 0);
        for (vid_t v = 0; v < n_; ++v) deg[v] = indeg[v];
        for (vid_t u = 0; u < n_; ++u)
            for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) ++deg[u];
        std::vector<vid_t> order(n_);
        for (vid_t v = 0; v < n_; ++v) order[v] = v;
        std::sort(order.begin(), order.end(), [&](vid_t a, vid_t b){ return deg[a] != deg[b] ? deg[a] > deg[b] : a < b; });
        int nb = 0;
        for (vid_t v : order) {
            if (nb >= num_seeds_ || deg[v] < 1) break;
            std::uint64_t bit = (std::uint64_t)1 << nb;
            splus_[v] |= bit; sminus_[v] |= bit;           // seed reaches / is reached by itself
            ++nb;
        }
        num_seeds_ = nb;
        // S+(v) = seeds reachable from v: reverse topological order (successors first)
        for (std::size_t i = topo.size(); i-- > 0;) {
            vid_t v = topo[i]; std::uint64_t mask = splus_[v];
            for (const vid_t* it = dag.out_begin(v); it != dag.out_end(v); ++it) mask |= splus_[*it];
            splus_[v] = mask;
        }
        // S-(v) = seeds that reach v: forward topological order (predecessors first)
        for (vid_t v : topo) {
            std::uint64_t mask = sminus_[v];
            for (const vid_t* it = dag.out_begin(v); it != dag.out_end(v); ++it) sminus_[*it] |= mask;
        }
    }
}

int Ferrari::check(vid_t v, vid_t pid) const {
    const std::vector<vid_t>& s = is_[v];
    // largest interval start <= pid
    std::size_t lo = 0, hi = s.size();
    while (lo < hi) { std::size_t mid = (lo + hi) / 2; if (s[mid] <= pid) lo = mid + 1; else hi = mid; }
    if (lo == 0) return 0;
    std::size_t idx = lo - 1;
    if (pid <= ie_[v][idx]) return iex_[v][idx] ? 2 : 1;
    return 0;
}

bool Ferrari::reaches(vid_t s, vid_t t) {
    if (s == t) return true;
    if (num_seeds_ > 0) {
        if (splus_[s] & sminus_[t]) return true;            // rule 1: s -> seed -> t
        if (sminus_[s] & ~sminus_[t]) return false;         // rule 2: seed reaches s but not t
    }
    if (level_[s] >= level_[t]) return false;               // topological negative cut
    int r = check(s, pi_[t]);
    if (r == 0) return false;
    if (r == 2) return true;

    // approximate: guided DFS over out-neighbours
    ++query_cnt_;
    const int qc = query_cnt_;
    std::vector<vid_t> st;
    st.push_back(s); stamp_[s] = qc;
    while (!st.empty()) {
        vid_t x = st.back(); st.pop_back();
        for (const vid_t* it = fwd_.out_begin(x); it != fwd_.out_end(x); ++it) {
            vid_t c = *it;
            if (c == t) return true;
            if (stamp_[c] == qc) continue;
            if (level_[c] >= level_[t]) continue;           // cannot reach t
            if (num_seeds_ > 0) {
                if (splus_[c] & sminus_[t]) return true;     // c -> seed -> t
                if (sminus_[c] & ~sminus_[t]) continue;      // a seed reaches c but not t -> prune
            }
            int rc = check(c, pi_[t]);
            if (rc == 2) return true;
            if (rc == 0) continue;                          // t outside c's intervals -> prune
            stamp_[c] = qc; st.push_back(c);
        }
    }
    return false;
}

std::size_t Ferrari::index_size_bytes() const {
    std::size_t b = (pi_.size() + level_.size()) * sizeof(vid_t);
    b += (splus_.size() + sminus_.size()) * sizeof(std::uint64_t);
    for (vid_t v = 0; v < n_; ++v)
        b += is_[v].size() * (2 * sizeof(vid_t) + sizeof(char));
    return b;
}

}  // namespace reachability

#include "reachability/minpost.hpp"
#include <algorithm>

namespace reachability {

MinPost min_post_label(const CSRGraph& dag, std::mt19937* rng) {
    const vid_t n = dag.num_nodes();
    MinPost L;
    L.pre.assign(n, 0);
    L.post.assign(n, 0);
    L.middle.assign(n, 0);

    std::vector<vid_t> indeg(n, 0);
    for (vid_t u = 0; u < n; ++u)
        for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it)
            ++indeg[*it];
    std::vector<vid_t> roots;
    for (vid_t u = 0; u < n; ++u) if (indeg[u] == 0) roots.push_back(u);
    if (rng) std::shuffle(roots.begin(), roots.end(), *rng);

    std::vector<char> seen(n, 0);
    vid_t counter = 0;
    const vid_t INF = n + 1;
    struct Frame { vid_t v; std::vector<vid_t> nbrs; std::size_t idx; vid_t curmin; };
    std::vector<Frame> stack;

    auto push = [&](vid_t v) {
        seen[v] = 1;
        L.middle[v] = counter;               // entry timestamp
        std::vector<vid_t> nbrs(dag.out_begin(v), dag.out_end(v));
        if (rng) std::shuffle(nbrs.begin(), nbrs.end(), *rng);
        stack.push_back(Frame{v, std::move(nbrs), 0, INF});
    };

    for (vid_t r : roots) {
        if (seen[r]) continue;
        push(r);
        while (!stack.empty()) {
            std::size_t top = stack.size() - 1;       // re-index: push() may reallocate
            if (stack[top].idx < stack[top].nbrs.size()) {
                vid_t w = stack[top].nbrs[stack[top].idx++];
                if (!seen[w]) {
                    push(w);                          // tree edge: descend
                } else {
                    // non-tree edge: pull the descendant's min up (GRAIL's negative interval)
                    stack[top].curmin = std::min(stack[top].curmin, L.pre[w]);
                }
            } else {
                vid_t v = stack[top].v, cm = stack[top].curmin;
                ++counter;
                vid_t pv = std::min(cm, counter);
                L.pre[v] = pv;
                L.post[v] = counter;
                stack.pop_back();
                if (!stack.empty())
                    stack.back().curmin = std::min(stack.back().curmin, pv);
            }
        }
    }
    return L;
}

}  // namespace reachability

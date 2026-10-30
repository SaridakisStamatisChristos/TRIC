#include "reachability/levels.hpp"

namespace reachability {

std::vector<vid_t> topological_levels(const CSRGraph& dag) {
    const vid_t n = dag.num_nodes();
    std::vector<vid_t> level(n, 0);
    std::vector<vid_t> indeg(n, 0);
    for (vid_t u = 0; u < n; ++u)
        for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it)
            ++indeg[*it];
    std::vector<vid_t> q;
    for (vid_t u = 0; u < n; ++u) if (indeg[u] == 0) q.push_back(u);
    std::size_t head = 0;
    while (head < q.size()) {
        vid_t u = q[head++];                 // popped in topological order
        for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) {
            vid_t w = *it;
            if (level[u] + 1 > level[w]) level[w] = level[u] + 1;
            if (--indeg[w] == 0) q.push_back(w);
        }
    }
    return level;
}

}  // namespace reachability

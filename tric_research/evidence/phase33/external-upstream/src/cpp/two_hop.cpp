#include "reachability/two_hop.hpp"

namespace reachability {

void build_two_hop_labels(const CSRGraph& dag, const std::vector<vid_t>& order,
                          TwoHopLabels& L) {
    const vid_t n = dag.num_nodes();
    L.resize(n);

    // reverse adjacency (in-edges) for the backward pruned BFS
    CSRGraph rdag;
    {
        std::vector<vid_t> rs, rd;
        rs.reserve(dag.num_edges());
        rd.reserve(dag.num_edges());
        for (vid_t u = 0; u < n; ++u)
            for (const vid_t* it = dag.out_begin(u); it != dag.out_end(u); ++it) {
                rs.push_back(*it); rd.push_back(u);
            }
        rdag = CSRGraph(n, rs, rd);
    }

    std::vector<char> visited(n, 0);
    std::vector<vid_t> q(n);

    for (vid_t i = 0; i < n; ++i) {
        const vid_t start = order[i];

        // forward pruned BFS over out-edges -> fills L_in
        vid_t qs = 0, qt = 0;
        q[qt++] = start;
        while (qs != qt) {
            vid_t v = q[qs++];
            if (two_hop_intersects(L, start, v)) continue;   // already decided -> prune
            L.Lin[v].push_back(i);
            for (const vid_t* it = dag.out_begin(v); it != dag.out_end(v); ++it)
                if (!visited[*it]) { visited[*it] = 1; q[qt++] = *it; }
        }
        for (vid_t j = 0; j < qt; ++j) visited[q[j]] = 0;

        // reverse pruned BFS over in-edges -> fills L_out
        qs = qt = 0;
        q[qt++] = start;
        while (qs != qt) {
            vid_t v = q[qs++];
            if (two_hop_intersects(L, v, start)) continue;   // already decided -> prune
            L.Lout[v].push_back(i);
            for (const vid_t* it = rdag.out_begin(v); it != rdag.out_end(v); ++it)
                if (!visited[*it]) { visited[*it] = 1; q[qt++] = *it; }
        }
        for (vid_t j = 0; j < qt; ++j) visited[q[j]] = 0;

        visited[start] = 1;   // canonical ordering: remove processed vertex from later BFS
    }
}

}  // namespace reachability

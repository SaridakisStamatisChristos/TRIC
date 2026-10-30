#include "reachability/scc.hpp"
#include <algorithm>
#include <stack>

namespace reachability {

// Strongly connected components via Tarjan's algorithm, written iteratively.
//
// Tarjan does a single DFS. For each vertex v it records:
//   index[v] : the order in which v was first visited (its "discovery time");
//   low[v]   : the smallest index reachable from v's DFS subtree by using at most
//              one back/cross edge to a vertex still on the Tarjan stack.
// When low[v] == index[v], v is the root of an SCC, and that SCC is exactly the
// vertices sitting above v on the Tarjan stack.
//
// We implement the DFS with explicit stacks instead of recursion so that deep or
// large graphs cannot overflow the C++ call stack. The recursion is simulated by:
//   call   : the stack of vertices currently "on the call stack";
//   cursor : for each such vertex, a pointer to its next unexplored out-edge.
Condensation scc_condense(const CSRGraph& g) {
    const vid_t n = g.num_nodes();
    Condensation c;
    c.comp.assign(n, -1);                 // -1 = not yet assigned to a component

    std::vector<vid_t> index(n, -1), low(n, 0);
    std::vector<char> on_stack(n, 0);     // is the vertex currently on tarjan_stack?
    std::vector<vid_t> tarjan_stack;      // candidate members of the SCC being built
    vid_t idx = 0;                        // next discovery time to hand out
    vid_t comp_count = 0;                 // next component id to hand out

    std::vector<vid_t> call;              // simulated recursion: vertices in progress
    std::vector<const vid_t*> cursor;     // per-frame iterator into the vertex's edges

    // Outer loop visits every vertex so disconnected graphs are fully covered.
    for (vid_t s = 0; s < n; ++s) {
        if (index[s] != -1) continue;     // already visited in an earlier DFS tree

        // "Call" DFS on s: discover it and push its frame.
        call.push_back(s);
        cursor.push_back(g.out_begin(s));
        index[s] = low[s] = idx++;
        tarjan_stack.push_back(s);
        on_stack[s] = 1;

        while (!call.empty()) {
            vid_t v = call.back();
            const vid_t* end = g.out_end(v);
            bool recursed = false;

            // Advance through v's out-edges until we either find an undiscovered
            // neighbor (simulate recursing into it) or exhaust the list.
            while (cursor.back() != end) {
                vid_t w = *cursor.back();
                ++cursor.back();          // consume this edge before (maybe) recursing
                if (index[w] == -1) {
                    // Tree edge: discover w and push its frame. Break to process w
                    // before continuing with v (this is the "recursive call").
                    index[w] = low[w] = idx++;
                    tarjan_stack.push_back(w);
                    on_stack[w] = 1;
                    call.push_back(w);
                    cursor.push_back(g.out_begin(w));
                    recursed = true;
                    break;
                } else if (on_stack[w]) {
                    // Back/cross edge to a vertex still on the stack: w can reach
                    // back into v's current SCC candidate, so pull v's low down.
                    low[v] = std::min(low[v], index[w]);
                }
                // else: w is already in a finished SCC; ignore it.
            }
            if (recursed) continue;       // go process the just-pushed child first

            // All of v's edges are done ("returning" from the recursive call).
            if (low[v] == index[v]) {
                // v is an SCC root: pop the stack down to and including v; those
                // vertices form one SCC and get the next component id.
                while (true) {
                    vid_t w = tarjan_stack.back();
                    tarjan_stack.pop_back();
                    on_stack[w] = 0;
                    c.comp[w] = comp_count;
                    if (w == v) break;
                }
                ++comp_count;
            }

            // Pop v's frame and propagate its low value to its parent (the edge
            // the parent used to reach v counts as a tree edge).
            call.pop_back();
            cursor.pop_back();
            if (!call.empty()) {
                low[call.back()] = std::min(low[call.back()], low[v]);
            }
        }
    }
    c.num_comp = comp_count;

    // Build the condensed DAG: keep only edges that cross between distinct
    // components. CSRGraph's constructor deduplicates the parallel edges that
    // collapsing creates, so each pair of components is linked at most once.
    std::vector<vid_t> csrc, cdst;
    for (vid_t u = 0; u < n; ++u) {
        for (const vid_t* it = g.out_begin(u); it != g.out_end(u); ++it) {
            vid_t cu = c.comp[u], cv = c.comp[*it];
            if (cu != cv) { csrc.push_back(cu); cdst.push_back(cv); }
        }
    }
    c.dag = CSRGraph(comp_count, csrc, cdst);

    // Tarjan finalizes SCCs in *reverse* topological order: a component is closed
    // only after every component it can reach is already closed. So component id 0
    // is a DAG sink and the highest id is a source -> topological order (sources
    // first) is simply the component ids in descending order.
    c.topo_order.resize(comp_count);
    for (vid_t i = 0; i < comp_count; ++i)
        c.topo_order[i] = comp_count - 1 - i;

    return c;
}

}  // namespace reachability

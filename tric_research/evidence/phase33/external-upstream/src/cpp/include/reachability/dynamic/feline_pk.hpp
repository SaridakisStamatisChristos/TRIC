#pragma once

#include "reachability/dynamic/graph.hpp"
#include "reachability/dynamic/index.hpp"

#include <cstddef>
#include <vector>

namespace reachability::dynamic {

// Feline-PK façade: maintains (DynamicGraph, Representative, DynIndex) under updates.
class FelinePK {
public:
    // Alg. 7: insert a disconnected vertex (O(1)).
    void insert_vertex(vertex_t v);
    // Alg. 8: remove a disconnected vertex (O(1)); v must be isolated in E.
    void remove_vertex(vertex_t v);

    // Alg. 10: insert edge (u, v). Two branches: if the edge closes no cycle the X/Y order
    // is repaired in place; if it closes one, the cycle is folded into a single component.
    //
    // The repair deliberately departs from the thesis's Alg. 10 in two coupled ways — the
    // thesis's line 11 is unsound as written. See feline_pk.cpp and docs/fidelity.md.
    void insert_edge(vertex_t u, vertex_t v);

    // Remove edge (u, v) from the digraph, updating r, E_DAG and the index. If (u,v) is
    // internal to a component, the component may split. No-op if the edge is absent.
    void remove_edge(vertex_t u, vertex_t v);

    // Dynamic reachability query. Maps both endpoints through r_ and asks the index about
    // their representatives; same representative means reachable (one SCC).
    bool reachable(vertex_t u, vertex_t v);

    // Estimated resident size of the index structures (DynIndex's coordinate maps plus
    // Representative's parent/rank maps). Not part of the reference implementation — the
    // reference had no such method — but ReachabilityIndex requires the property. See the
    // .cpp for what "estimated" means here.
    std::size_t index_size_bytes() const;

    const DynamicGraph& graph() const { return g_; }
    Representative& rep() { return r_; }
    const DynIndex& index() const { return idx_; }

private:
    void fold_cycle(vertex_t u, vertex_t v, const std::vector<vertex_t>& v_cycles);
    void reinsert_dag_edge(vertex_t u, vertex_t v);
    void split_component(vertex_t old_rep, vertex_t u, vertex_t v);

    DynamicGraph g_;
    Representative r_;
    DynIndex idx_;
};

} // namespace reachability::dynamic

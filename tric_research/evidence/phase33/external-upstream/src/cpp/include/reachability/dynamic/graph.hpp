#pragma once

#include "reachability/dynamic/representative.hpp"

#include <unordered_map>

namespace reachability::dynamic {

// Mutable digraph (E) plus its associated DAG (E_DAG), each with forward and
// inverted adjacency, all stored as hashmaps (thesis Section 4.1).
class DynamicGraph {
public:
    // --- digraph E ---
    void add_vertex(vertex_t v);
    void remove_vertex(vertex_t v);      // v must be isolated in E
    bool has_vertex(vertex_t v) const;
    void add_edge(vertex_t u, vertex_t v);
    bool has_edge(vertex_t u, vertex_t v) const;
    void remove_edge(vertex_t u, vertex_t v);   // no-op if the edge is absent
    const std::unordered_map<vertex_t, VertexSet>& out_all() const { return e_out_; }
    const VertexSet& succ(vertex_t v) const;
    const VertexSet& pred(vertex_t v) const;

    // --- associated DAG E_DAG (keys are representatives) ---
    void dag_add_vertex(vertex_t a);
    void dag_remove_vertex(vertex_t a);
    void dag_add_edge(vertex_t a, vertex_t b);
    void dag_remove_edge(vertex_t a, vertex_t b);
    const VertexSet& dag_succ(vertex_t a) const;
    const VertexSet& dag_pred(vertex_t a) const;
    const std::unordered_map<vertex_t, VertexSet>& dag_out_all() const { return dag_out_; }

private:
    std::unordered_map<vertex_t, VertexSet> e_out_, e_in_;
    std::unordered_map<vertex_t, VertexSet> dag_out_, dag_in_;
    static const VertexSet kEmpty;
};

} // namespace reachability::dynamic

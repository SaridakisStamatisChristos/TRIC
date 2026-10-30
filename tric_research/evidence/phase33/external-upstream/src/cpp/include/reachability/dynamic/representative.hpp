#pragma once

#include <cstddef>
#include <cstdint>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace reachability::dynamic {

using vertex_t = uint32_t;
using VertexSet = std::unordered_set<vertex_t>;

// Union-find over vertex ids: r(v) = SCC representative of v.
class Representative {
public:
    void make_set(vertex_t v);
    void erase(vertex_t v);              // only valid for a singleton set
    bool contains(vertex_t v) const;
    vertex_t find(vertex_t v);           // with path compression; asserts v is known (debug builds)
    // Union every member into `chosen`; returns `chosen`. All members must exist.
    // Postcondition: find(chosen) == chosen, unconditionally (even if `chosen`
    // was not its own root at call time) — `chosen` is guaranteed to be the
    // representative id of the merged set.
    vertex_t unite(const std::vector<vertex_t>& members, vertex_t chosen);

    // Un-fold: union-find has no split, so the affected members are rebuilt. Every
    // member of every partition is reset to a singleton, then each partition is
    // re-united under its FIRST element, which becomes that partition's representative.
    // Postcondition: for each partition p, find(m) == p[0] for every m in p.
    void repartition(const std::vector<std::vector<vertex_t>>& partitions);

    // Estimated resident size of parent_ and rank_ (new code, not in the reference; see
    // FelinePK::index_size_bytes for the estimate's caveats).
    std::size_t size_bytes() const;

private:
    std::unordered_map<vertex_t, vertex_t> parent_;
    std::unordered_map<vertex_t, uint32_t> rank_;
};

} // namespace reachability::dynamic

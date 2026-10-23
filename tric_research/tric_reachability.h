// C++17 graph-only static exact reachability; reflexive semantics.
// Prefer direct closure when it fits, then partitioned/compressed exact index.
#pragma once
#include "closure_index.h"
#include "partitioned_reachability.h"
#include <memory>
class TricReachability {
  std::unique_ptr<BoundedClosure> direct_;
  std::unique_ptr<PartitionedReachability> partitioned_;
public:
  template<class Graph>
  explicit TricReachability(const Graph& graph,std::size_t table_cap_bytes=2ULL*1024*1024,
                            std::size_t index_scratch_cap_bytes=64ULL*1024*1024) {
    tric_detail::SccDecomposition scc(graph);
    if (scc.closure_fits(table_cap_bytes)) {
      direct_.reset(new BoundedClosure(graph,table_cap_bytes,std::move(scc)));
    } else {
      partitioned_.reset(new PartitionedReachability(
        graph,table_cap_bytes,index_scratch_cap_bytes,std::move(scc)));
    }
  }
  bool reaches(int source,int target) {
    return direct_?direct_->reaches(source,target):partitioned_->reaches(source,target);
  }
  bool uses_direct_closure() const {return bool(direct_);}
  std::size_t table_bytes() const {return direct_?direct_->matrix_bytes():partitioned_->table_bytes();}
  std::size_t retained_bytes() const {
    return sizeof(*this)+(direct_?direct_->retained_bytes():partitioned_->retained_bytes());
  }
};

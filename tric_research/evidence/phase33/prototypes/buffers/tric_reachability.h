// Graph-only static exact reflexive reachability. One owned index per thread.
#pragma once
#include "closure_index.h"
#include "forest_reachability.h"
#include "partitioned_reachability.h"
#include <variant>
#define TRIC_HAS_FOREST_INDEX 1
class TricReachability {
  using Index=std::variant<BoundedClosure,PartitionedReachability,ForestReachability>;
  Index index_;
  template<class Graph>
  static Index construct(const Graph& graph,std::size_t cap,std::size_t scratch) {
    tric_detail::SccDecomposition scc(graph);
    if(scc.closure_fits(cap))return Index(BoundedClosure(graph,cap,std::move(scc)));
    ForestReachability forest(graph,scc,scratch);
    if(forest.built())return Index(std::move(forest));
    return Index(PartitionedReachability(graph,cap,scratch,std::move(scc)));
  }
public:
  template<class Graph>
  explicit TricReachability(const Graph& graph,std::size_t cap=2ULL*1024*1024,
                            std::size_t scratch=64ULL*1024*1024)
    :index_(construct(graph,cap,scratch)){}
  TricReachability(const TricReachability&)=delete;
  TricReachability& operator=(const TricReachability&)=delete;
  TricReachability(TricReachability&&) noexcept=default;
  TricReachability& operator=(TricReachability&&) noexcept=default;
  bool reaches(int source,int target) {
    if(auto* p=std::get_if<BoundedClosure>(&index_))return p->reaches(source,target);
    if(auto* p=std::get_if<PartitionedReachability>(&index_))return p->reaches(source,target);
    return std::get<ForestReachability>(index_).reaches(source,target);
  }
  bool uses_direct_closure()const{return index_.index()==0;}
  bool uses_forest_index()const{return index_.index()==2;}
  std::size_t table_bytes()const {
    if(auto* p=std::get_if<BoundedClosure>(&index_))return p->matrix_bytes();
    if(auto* p=std::get_if<PartitionedReachability>(&index_))return p->table_bytes();
    return 0;
  }
  std::size_t retained_bytes()const {
    return sizeof(*this)+std::visit([](const auto& p){return p.retained_bytes()-sizeof(p);},index_);
  }
};

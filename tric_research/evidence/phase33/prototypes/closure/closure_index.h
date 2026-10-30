// Optional exact reachability closure on SCC condensation. Public-domain-style
// algorithmic technique; no novelty is asserted. Memory budget applies to the
// closure bit matrix only (not input graph, SCC vectors or allocator overhead).
#pragma once
#include "scc_decomposition.h"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

class BoundedClosure {
  std::vector<int> component_;
  std::vector<std::uint64_t> bits_;
  std::size_t words_=0;
  int components_=0;
public:
  bool built() const {return !bits_.empty();}
  int components() const {return components_;}
  std::size_t matrix_bytes() const {return bits_.size()*sizeof(std::uint64_t);}
  std::size_t retained_bytes() const {
    return sizeof(*this)+component_.capacity()*sizeof(int)+bits_.capacity()*sizeof(std::uint64_t);
  }
  template<class Graph>
  explicit BoundedClosure(const Graph& graph, std::size_t max_bytes)
    : BoundedClosure(graph,max_bytes,tric_detail::SccDecomposition(graph)) {}
private:
  friend class TricReachability;
  // Internal construction route: consume already validated SCCs exactly once.
  template<class Graph>
  BoundedClosure(const Graph& graph, std::size_t max_bytes, tric_detail::SccDecomposition scc) {
    component_=std::move(scc.component); components_=scc.count;
    words_=(static_cast<std::size_t>(components_)+63)/64;
    if(words_==0 || static_cast<std::size_t>(components_)>max_bytes/(words_*sizeof(std::uint64_t)))return;
    std::vector<std::vector<int>> dag(components_);
    const int n=static_cast<int>(graph.size());
    for(int u=0;u<n;++u)for(int v:graph[u]){
      const int a=component_[u],b=component_[v];
      if(a!=b){
        if(a>=b)throw std::logic_error("SCC order is not topological");
        dag[a].push_back(b);
      }
    }
    for(auto& row:dag) {
      std::sort(row.begin(),row.end());
      row.erase(std::unique(row.begin(),row.end()),row.end());
    }
    bits_.assign(static_cast<std::size_t>(components_)*words_,0);
    for(int a=components_-1;a>=0;--a){
      auto *dst=bits_.data()+static_cast<std::size_t>(a)*words_;
      dst[a>>6]|=std::uint64_t(1)<<(a&63);
      for(int b:dag[a]){
        // Membership obtained from complete child rows proves the child's
        // entire closure is already present. Self cannot cover a distinct b.
        if((dst[b>>6]>>(b&63))&1U)continue;
        const auto *src=bits_.data()+static_cast<std::size_t>(b)*words_;
        for(std::size_t w=static_cast<std::size_t>(b)>>6;w<words_;++w)dst[w]|=src[w];
      }
    }
  }
public:
  bool reaches(int source,int target) const {
    if(!built())throw std::logic_error("closure not materialized within memory cap");
    if(static_cast<std::size_t>(source)>=component_.size()
       || static_cast<std::size_t>(target)>=component_.size())throw std::out_of_range("query endpoint");
    const int a=component_[source],b=component_[target];
    return (bits_[static_cast<std::size_t>(a)*words_+(b>>6)]>>(b&63))&std::uint64_t(1);
  }
};

// Exact SCC-condensation forest reachability; standard DFS dominance labels.
// One 64-bit label per original vertex, no closure table, C++17 only.
#pragma once
#include "scc_decomposition.h"
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>
#include <utility>

namespace tric_detail {
// Precondition: each packed lane is at most INT_MAX (no marker bit set).
inline bool forest_dominates(std::uint64_t source,std::uint64_t target) noexcept {
  constexpr std::uint64_t markers=0x8000000080000000ULL;
  return (((target|markers)-source)&markers)==markers;
}
}
class ForestReachability {
  std::vector<std::uint64_t> labels_;
  bool built_=false;
  friend class TricReachability;
  template<class Graph>
  ForestReachability(const Graph& graph,const tric_detail::SccDecomposition& scc,std::size_t scratch_cap) {
    const int count=scc.count;
    // Parent, sibling, first-child and component-coordinate arrays: 20 bytes
    // per SCC. Retained vertex labels and the shared SCC result are separate.
    if(count==0 || std::uint64_t(count)*20>scratch_cap)return;
    // Ignore duplicate arcs and arcs internal to an SCC when checking degrees.
    std::vector<int> successor(count,-1),predecessor(count,-1);
    bool toward_sinks=true,away_from_sources=true;
    for(std::size_t u=0;u<graph.size();++u) {
      const int a=scc.component[u];
      for(int v:graph[u]) {
        const int b=scc.component[v];if(a==b)continue;
        if(successor[a]<0)successor[a]=b;
        else if(successor[a]!=b)toward_sinks=false;
        if(predecessor[b]<0)predecessor[b]=a;
        else if(predecessor[b]!=a)away_from_sources=false;
        if(!toward_sinks && !away_from_sources)return;
      }
    }
    // Orient each forest away from its roots for DFS. Original reachability
    // reverses the ancestor relation when original arcs point toward sinks.
    const bool reverse=toward_sinks;
    auto parent=reverse?std::move(successor):std::move(predecessor);
    auto sibling=reverse?std::move(predecessor):std::move(successor);
    std::vector<int> first_child(count,-1);
    for(int a=0;a<count;++a) {
      sibling[a]=-1;
      if(parent[a]>=0){sibling[a]=first_child[parent[a]];first_child[parent[a]]=a;}
    }
    std::vector<std::uint64_t> coordinates(count);
    int clock=0;
    // Threaded iterative traversal uses parent/sibling links, not recursion or
    // a depth-sized stack. Each vertex enters/exits once.
    for(int root=0;root<count;++root)if(parent[root]<0) {
      int a=root;
      while(a>=0) {
        coordinates[a]=static_cast<std::uint32_t>(clock++);
        if(first_child[a]>=0){a=first_child[a];continue;}
        while(a>=0) {
          coordinates[a]|=std::uint64_t(static_cast<std::uint32_t>(clock))<<32;
          if(sibling[a]>=0){a=sibling[a];break;}
          a=parent[a];
        }
      }
    }
    if(clock!=count)throw std::logic_error("forest traversal did not cover condensation");
    for(auto& value:coordinates) {
      const auto begin=static_cast<std::uint32_t>(value);
      const auto end=static_cast<std::uint32_t>(value>>32);
      const auto x=reverse?static_cast<std::uint32_t>(count)-begin:begin;
      const auto y=reverse?end:static_cast<std::uint32_t>(count)-end;
      value=std::uint64_t(x)|(std::uint64_t(y)<<32);
    }
    labels_.resize(graph.size());
    for(std::size_t u=0;u<graph.size();++u)labels_[u]=coordinates[scc.component[u]];
    built_=true;
  }
public:
  bool built()const{return built_;}
  bool reaches(int source,int target)const {
    if(static_cast<std::size_t>(source)>=labels_.size() ||
       static_cast<std::size_t>(target)>=labels_.size())throw std::out_of_range("query endpoint");
    // Both coordinates fit 31 bits because SCC count fits int. Biasing both
    // target lanes prevents a borrow from the low lane into the high lane.
    // Their two marker bits survive iff both target coordinates dominate.
    return tric_detail::forest_dominates(labels_[source],labels_[target]);
  }
  std::size_t table_bytes()const{return 0;}
  std::size_t retained_bytes()const{return sizeof(*this)+labels_.capacity()*sizeof(std::uint64_t);}
};

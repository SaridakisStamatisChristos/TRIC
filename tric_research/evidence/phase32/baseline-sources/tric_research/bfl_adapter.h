// Benchmark adapter for unchanged BoleynSu/bfl at
// 0c837927a3f2fa3fc633abeedd56cea6e75d3a9a (MIT; see third_party/bfl).
// K=5, D=1600 upstream defaults; rand() starts at the upstream default seed 1.
// SCC conversion and adjacency allocation count toward native build time.
#pragma once
#include "scc_decomposition.h"
#include <algorithm>
#define main tric_bfl_upstream_main
#include "third_party/bfl/main.cpp"
#undef main
#undef K
#undef D
class BflAdapter {
  std::vector<int> component_;
public:
  template<class Graph>
  explicit BflAdapter(const Graph& graph) {
    if(!bs::nodes.empty())throw std::logic_error("one live BFL adapter per process");
    tric_detail::SccDecomposition scc(graph);
    component_=std::move(scc.component);
    std::vector<std::vector<int>> out(scc.count),in(scc.count);
    for(std::size_t u=0;u<graph.size();++u)for(int v:graph[u]) {
      const int a=component_[u],b=component_[v];
      if(a!=b){out[a].push_back(b);in[b].push_back(a);}
    }
    bs::nodes.resize(scc.count);bs::vis_cur=0;bs::cur=0;
    for(int u=0;u<scc.count;++u) {
      auto& node=bs::nodes[u];node.N_O_SZ=static_cast<int>(out[u].size());
      node.N_I_SZ=static_cast<int>(in[u].size());
      node.N_O=new int[out[u].size()];node.N_I=new int[in[u].size()];
      std::copy(out[u].begin(),out[u].end(),node.N_O);
      std::copy(in[u].begin(),in[u].end(),node.N_I);
    }
    bs::index_construction();
  }
  BflAdapter(const BflAdapter&)=delete;
  BflAdapter& operator=(const BflAdapter&)=delete;
  ~BflAdapter(){
    for(auto& node:bs::nodes){delete[] node.N_O;delete[] node.N_I;}
    bs::nodes.clear();
  }
  bool reaches(int source,int target) {
    if(static_cast<std::size_t>(source)>=component_.size() ||
        static_cast<std::size_t>(target)>=component_.size())throw std::out_of_range("query endpoint");
    ++bs::vis_cur;
    return bs::reach(bs::nodes[component_[source]],bs::nodes[component_[target]]);
  }
  std::size_t retained_bytes()const {
    std::size_t bytes=sizeof(*this)+component_.capacity()*sizeof(int)+bs::nodes.capacity()*sizeof(bs::node);
    for(const auto& node:bs::nodes)bytes+=(std::size_t(node.N_O_SZ)+node.N_I_SZ)*sizeof(int);
    return bytes;
  }
};

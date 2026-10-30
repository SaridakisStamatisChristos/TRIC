// Shared iterative SCC decomposition. Component IDs increase along every
// condensation edge (Kosaraju order). Construction validates all endpoints.
#pragma once
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>
namespace tric_detail {
struct SccDecomposition {
  std::vector<int> component;
  int count=0;
  template<class Graph>
  explicit SccDecomposition(const Graph& graph) {
    if(graph.size()>static_cast<std::size_t>(std::numeric_limits<int>::max()))
      throw std::length_error("graph has too many vertices");
    const int n=static_cast<int>(graph.size());
    // Stable CSR transpose: preserve the predecessor order of push_back.
    std::vector<std::size_t> reverse_offsets(static_cast<std::size_t>(n)+1,0);
    for(int u=0;u<n;++u)for(int v:graph[u]) {
      if(v<0 || v>=n)throw std::out_of_range("edge endpoint");
      ++reverse_offsets[static_cast<std::size_t>(v)+1];
    }
    for(int v=0;v<n;++v) {
      if(reverse_offsets[v+1]>std::numeric_limits<std::size_t>::max()-reverse_offsets[v])
        throw std::length_error("too many graph edges");
      reverse_offsets[v+1]+=reverse_offsets[v];
    }
    std::vector<int> reverse_edges(reverse_offsets.back());
    {
      auto cursor=reverse_offsets;
      for(int u=0;u<n;++u)for(int v:graph[u])reverse_edges[cursor[v]++]=u;
    }
    // Nonrecursive DFS finish order: safe on long directed paths.
    std::vector<unsigned char> seen(n,0);
    std::vector<int> finish;finish.reserve(n);
    std::vector<std::pair<int,std::size_t>> frames;
    for(int root=0;root<n;++root){
      if(seen[root])continue;
      frames.clear(); frames.emplace_back(root,0); seen[root]=1;
      while(!frames.empty()){
        auto &f=frames.back();
        if(f.second<graph[f.first].size()){
          int v=graph[f.first][f.second++];
          if(!seen[v]){seen[v]=1;frames.emplace_back(v,0);}
        }else{finish.push_back(f.first);frames.pop_back();}
      }
    }
    component.assign(n,-1);
    std::vector<int> stack;
    for(auto it=finish.rbegin();it!=finish.rend();++it){
      if(component[*it]>=0)continue;
      stack.assign(1,*it);component[*it]=count;
      while(!stack.empty()){
        int u=stack.back();stack.pop_back();
        for(std::size_t edge=reverse_offsets[u];edge<reverse_offsets[u+1];++edge) {
          const int v=reverse_edges[edge];
          if(component[v]<0){component[v]=count;stack.push_back(v);}
        }
      }
      ++count;
    }
  }
  bool closure_fits(std::size_t cap) const {
    const auto words=(static_cast<std::size_t>(count)+63)/64;
    return words!=0 && static_cast<std::size_t>(count)<=cap/(words*sizeof(std::uint64_t));
  }
};
} // namespace tric_detail

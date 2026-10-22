// Optional exact reachability closure on SCC condensation. Public-domain-style
// algorithmic technique; no novelty is asserted. Memory budget applies to the
// closure bit matrix only (not input graph, SCC vectors or allocator overhead).
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <queue>
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
  template<class Graph>
  explicit BoundedClosure(const Graph& graph, std::size_t max_bytes){
    const int n=static_cast<int>(graph.size());
    if(n==0)return;
    Graph reverse(n);
    for(int u=0;u<n;++u) for(int v:graph[u])reverse[v].push_back(u);
    // Nonrecursive DFS finish order: safe on long directed paths.
    std::vector<unsigned char> seen(n,0);
    std::vector<int> finish;finish.reserve(n);
    for(int root=0;root<n;++root){
      if(seen[root])continue;
      std::vector<std::pair<int,std::size_t>> stack{{root,0}}; seen[root]=1;
      while(!stack.empty()){
        auto &f=stack.back();
        if(f.second<graph[f.first].size()){
          int v=graph[f.first][f.second++];
          if(!seen[v]){seen[v]=1;stack.emplace_back(v,0);}
        }else{finish.push_back(f.first);stack.pop_back();}
      }
    }
    component_.assign(n,-1);
    for(auto it=finish.rbegin();it!=finish.rend();++it){
      if(component_[*it]>=0)continue;
      std::vector<int> stack{*it};component_[*it]=components_;
      while(!stack.empty()){
        int u=stack.back();stack.pop_back();
        for(int v:reverse[u])if(component_[v]<0){component_[v]=components_;stack.push_back(v);}
      }
      ++components_;
    }
    words_=(static_cast<std::size_t>(components_)+63)/64;
    if(words_==0 || static_cast<std::size_t>(components_)>max_bytes/(words_*sizeof(std::uint64_t)))return;
    std::vector<std::vector<int>> dag(components_);
    std::vector<int> indegree(components_,0);
    for(int u=0;u<n;++u)for(int v:graph[u]){
      const int a=component_[u],b=component_[v];
      if(a!=b){dag[a].push_back(b);++indegree[b];}
    }
    std::queue<int> ready;
    for(int c=0;c<components_;++c)if(!indegree[c])ready.push(c);
    std::vector<int> topo;topo.reserve(components_);
    while(!ready.empty()){
      int a=ready.front();ready.pop();topo.push_back(a);
      for(int b:dag[a])if(--indegree[b]==0)ready.push(b);
    }
    if(static_cast<int>(topo.size())!=components_)throw std::logic_error("condensation must be acyclic");
    bits_.assign(static_cast<std::size_t>(components_)*words_,0);
    for(auto it=topo.rbegin();it!=topo.rend();++it){
      int a=*it;
      auto *dst=bits_.data()+static_cast<std::size_t>(a)*words_;
      dst[a>>6]|=std::uint64_t(1)<<(a&63);
      for(int b:dag[a]){
        const auto *src=bits_.data()+static_cast<std::size_t>(b)*words_;
        for(std::size_t w=0;w<words_;++w)dst[w]|=src[w];
      }
    }
  }
  bool reaches(int source,int target) const {
    if(!built())throw std::logic_error("closure not materialized within memory cap");
    const int a=component_[source],b=component_[target];
    return (bits_[static_cast<std::size_t>(a)*words_+(b>>6)]>>(b&63))&std::uint64_t(1);
  }
};

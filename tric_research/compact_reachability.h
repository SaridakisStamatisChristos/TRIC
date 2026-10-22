// Phase XII: experimental compact exact reachability on SCC condensation.
// Established techniques (SCCs, DAG interval filtering, DFS-tree witnesses).
// This is NOT a novel reachability primitive. C++17; static graph only.
#pragma once
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <stdexcept>
#include <utility>
#include <vector>

class CompactReachability {
public:
  static constexpr int dimensions = 4;
  struct QueryStats {
    std::uint64_t certified_yes=0, certified_no=0, fallback=0, edges=0;
  };
private:
  std::vector<int> component_, entry_, exit_, topo_rank_, seen_;
  std::vector<std::vector<int>> dag_;
  std::array<std::vector<int>,dimensions> rank_,low_,high_;
  std::vector<int> search_stack_;
  int components_=0, epoch_=0;
  bool necessary(int a,int b) const {
    for(int d=0;d<dimensions;++d)
      if(rank_[d][b]<low_[d][a] || rank_[d][b]>high_[d][a])return false;
    return true;
  }
public:
  int components() const {return components_;}
  std::size_t labels_bytes() const {
    return static_cast<std::size_t>(components_)*dimensions*3*sizeof(int)
           +static_cast<std::size_t>(components_)*4*sizeof(int)
           +component_.size()*sizeof(int);
  }
  template<class Graph>
  explicit CompactReachability(const Graph& graph){
    const int n=static_cast<int>(graph.size());
    if(!n)return;
    Graph reverse(n);
    for(int u=0;u<n;++u)for(int v:graph[u])reverse[v].push_back(u);
    std::vector<unsigned char> seen(n,0);
    std::vector<int> finish;finish.reserve(n);
    for(int root=0;root<n;++root){
      if(seen[root])continue;
      std::vector<std::pair<int,std::size_t>> stack{{root,0}};
      seen[root]=1;
      while(!stack.empty()){
        auto &frame=stack.back();
        int u=frame.first;
        if(frame.second<graph[u].size()){
          int v=graph[u][frame.second++];
          if(!seen[v]){seen[v]=1;stack.emplace_back(v,0);}
        }else{finish.push_back(u);stack.pop_back();}
      }
    }
    component_.assign(n,-1);
    for(auto it=finish.rbegin();it!=finish.rend();++it){
      if(component_[*it]!=-1)continue;
      std::vector<int> todo{*it};component_[*it]=components_;
      while(!todo.empty()){
        int u=todo.back();todo.pop_back();
        for(int v:reverse[u])if(component_[v]==-1){component_[v]=components_;todo.push_back(v);}
      }
      ++components_;
    }
    dag_.resize(components_);
    std::vector<int> indegree(components_,0);
    for(int u=0;u<n;++u)for(int v:graph[u]){
      int a=component_[u],b=component_[v];
      if(a!=b){dag_[a].push_back(b);++indegree[b];}
    }
    std::queue<int> ready;
    for(int c=0;c<components_;++c)if(!indegree[c])ready.push(c);
    std::vector<int> topo;topo.reserve(components_);
    while(!ready.empty()){
      int a=ready.front();ready.pop();topo.push_back(a);
      for(int b:dag_[a])if(--indegree[b]==0)ready.push(b);
    }
    if(static_cast<int>(topo.size())!=components_)throw std::logic_error("SCC condensation is not a DAG");
    topo_rank_.resize(components_);
    for(int i=0;i<components_;++i)topo_rank_[topo[i]]=i;
    // Each permutation provides a sound bounding interval of *all* descendants.
    // When a ->* b, rank[b] must lie in [low[a],high[a]] in EVERY dimension.
    std::mt19937_64 random(0x123af9087c6571d0ULL);
    std::vector<int> perm(components_);std::iota(perm.begin(),perm.end(),0);
    for(int d=0;d<dimensions;++d){
      std::shuffle(perm.begin(),perm.end(),random);
      rank_[d].resize(components_);
      for(int i=0;i<components_;++i)rank_[d][perm[i]]=i;
      low_[d]=rank_[d];high_[d]=rank_[d];
      for(auto it=topo.rbegin();it!=topo.rend();++it){
        int a=*it;
        for(int b:dag_[a]){
          low_[d][a]=std::min(low_[d][a],low_[d][b]);
          high_[d][a]=std::max(high_[d][a],high_[d][b]);
        }
      }
    }
    // Directed DFS forest. Ancestor -> descendant implies a real graph path.
    entry_.assign(components_,-1);exit_.assign(components_,-1);
    int tick=0;
    for(int root:topo){
      if(entry_[root]>=0)continue;
      std::vector<std::pair<int,std::size_t>> stack{{root,0}};
      entry_[root]=tick++;
      while(!stack.empty()){
        auto &frame=stack.back();
        int a=frame.first;
        if(frame.second<dag_[a].size()){
          int b=dag_[a][frame.second++];
          if(entry_[b]<0){entry_[b]=tick++;stack.emplace_back(b,0);}
        }else{exit_[a]=tick;stack.pop_back();}
      }
    }
    seen_.assign(components_,0);
    search_stack_.reserve(components_);
  }
  // 1=True, 0=False, -1=undecided. Both decisive cases are sound.
  int certificate(int source,int target) const {
    const int s=component_.at(source),t=component_.at(target);
    if(s==t || (entry_[s]<=entry_[t] && exit_[t]<=exit_[s]))return 1;
    if(topo_rank_[s]>topo_rank_[t] || !necessary(s,t))return 0;
    return -1;
  }
  bool reaches(int source,int target,QueryStats* stats=nullptr,bool guided=true){
    const int decision=certificate(source,target);
    if(decision!=-1){
      if(stats){if(decision)++stats->certified_yes;else ++stats->certified_no;}
      return decision!=0;
    }
    const int s=component_.at(source),t=component_.at(target);
    if(stats)++stats->fallback;
    if(epoch_==std::numeric_limits<int>::max()){
      std::fill(seen_.begin(),seen_.end(),0);epoch_=0;
    }
    ++epoch_;search_stack_.clear();search_stack_.push_back(s);seen_[s]=epoch_;
    while(!search_stack_.empty()){
      int a=search_stack_.back();search_stack_.pop_back();
      for(int b:dag_[a]){
        if(stats)++stats->edges;
        if(b==t)return true;
        if(seen_[b]!=epoch_ && (!guided || necessary(b,t))){
          seen_[b]=epoch_;search_stack_.push_back(b);
        }
      }
    }
    return false;
  }
};

// Phase XXIII: exact native extraction of legacy Python pivot hit masks
// and early_reachable DFS fallback edge counts. C++17 training-only tool.
// Does NOT consume heldout pairs, decisions, or query labels.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>
using Clock=std::chrono::steady_clock;
using Graph=std::vector<std::vector<int>>;
using Bits=std::vector<std::uint64_t>;
using Pair=std::pair<int,int>;
struct Pivot{Bits fw,bw;};
static Bits reach_bits(const Graph& g,int s){
  Bits result((g.size()+63)/64,0);
  std::vector<int> stack{s};
  result[static_cast<std::size_t>(s)>>6]|=std::uint64_t(1)<<(s&63);
  while(!stack.empty()){
    const int u=stack.back();stack.pop_back();
    for(int v:g[u]){
      const auto index=static_cast<std::size_t>(v)>>6;
      const auto bit=std::uint64_t(1)<<(v&63);
      if(!(result[index]&bit)){
        result[index]|=bit;stack.push_back(v);
      }
    }
  }
  return result;
}
static bool bit(const Bits& b,int n){
  return ((b[static_cast<std::size_t>(n)>>6]>>(n&63))&1U)!=0;
}
static int fallback_scans(const Graph& graph,int source,int target,
                          std::vector<unsigned>& visited,
                          std::vector<int>& stack,unsigned& epoch){
  if(source==target)return 0;
  if(++epoch==0){std::fill(visited.begin(),visited.end(),0U);epoch=1;}
  stack.clear();stack.push_back(source);visited[source]=epoch;
  int scanned=0;
  while(!stack.empty()){
    const int u=stack.back();stack.pop_back();
    for(int v:graph[u]){
      ++scanned;
      if(v==target)return scanned;
      if(visited[v]!=epoch){
        visited[v]=epoch;stack.push_back(v);
      }
    }
  }
  return scanned;
}
static double ns(Clock::time_point a,Clock::time_point b){
  return std::chrono::duration<double,std::nano>(b-a).count();
}
int main(){
  try{
    const auto t0=Clock::now();
    int n,m,c,t;
    if(!(std::cin>>n>>m>>c>>t)||n<1||n>2000000||m<0||
       c<0||c>19||t<1||t>100000)
      throw std::invalid_argument("invalid training header");
    Graph g(n),r(n);
    for(int i=0;i<m;++i){
      int u,v;
      if(!(std::cin>>u>>v)||u<0||v<0||u>=n||v>=n)
        throw std::invalid_argument("invalid directed arc");
      g[u].push_back(v);r[v].push_back(u);
    }
    std::vector<int> candidates(c);
    for(int& x:candidates){
      if(!(std::cin>>x)||x<0||x>=n)throw std::invalid_argument("invalid pivot vertex");
    }
    std::vector<Pair> train(t);
    for(auto& q:train){
      if(!(std::cin>>q.first>>q.second)||q.first<0||q.first>=n||
         q.second<0||q.second>=n)
        throw std::invalid_argument("invalid train-only pair");
    }
    const auto parse_end=Clock::now();
    std::vector<Pivot> pivots;pivots.reserve(c);
    for(int s:candidates)
      pivots.push_back({reach_bits(g,s),reach_bits(r,s)});
    const auto pivot_end=Clock::now();
    std::vector<int> masks(t);
    for(int i=0;i<t;++i){
      const auto [s,target]=train[i];
      int mask=0;
      for(int p=0;p<c;++p){
        const auto& v=pivots[p];
        const bool fs=bit(v.fw,s), ft=bit(v.fw,target);
        const bool bs=bit(v.bw,s),bt=bit(v.bw,target);
        if((bs&&ft)||(fs&&!ft)||(bt&&!bs))
          mask|=1<<p;
      }
      masks[i]=mask;
    }
    const auto hit_end=Clock::now();
    std::vector<unsigned> visited(n,0);
    std::vector<int> stack;stack.reserve(std::min(n,10000));
    unsigned epoch=0;
    // The original Python early_reachable returns number of checked
    // outgoing edges, not visited nodes, +1 for each fallback cost.
    std::vector<int> fallback(t);
    for(int i=0;i<t;++i)
      fallback[i]=1+fallback_scans(g,train[i].first,train[i].second,
                                  visited,
                                  stack,epoch);
    const auto end=Clock::now();
    std::cout<<std::fixed<<std::setprecision(3)
      <<"{\"n\":"<<n<<",\"edges\":"<<m<<",\"candidates\":"<<c
      <<",\"train\":"<<t
      <<",\"parse_ns\":"<<ns(t0,parse_end)
      <<",\"pivot_build_ns\":"<<ns(parse_end,pivot_end)
      <<",\"mask_ns\":"<<ns(pivot_end,hit_end)
      <<",\"fallback_ns\":"<<ns(hit_end,end)
      <<",\"total_native_ns\":"<<ns(t0,end)
      <<",\"hit_masks\":[";
    for(int i=0;i<t;++i){if(i)std::cout<<',';std::cout<<masks[i];}
    std::cout<<"],\"fallback_costs\":[";
    for(int i=0;i<t;++i){if(i)std::cout<<',';std::cout<<fallback[i];}
    std::cout<<"]}\n";
    return 0;
  }catch(const std::exception& e){
    std::cerr<<e.what()<<'\n';return 2;
  }
}

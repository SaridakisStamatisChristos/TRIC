// Phase XIX isolated exact cache-vs-DFS C++17 diagnostic.
// Does not claim a memory-matched comparison to O'Reach or default TRIC.
// Input: n m train_queries heldout_queries max_sources cap_bytes,
// then arcs, train pairs and heldout pairs. No heldout information in index.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <stdexcept>
#include <utility>
#include <vector>
#include "hot_source_cache.h"
using Clock=std::chrono::steady_clock;
using Graph=std::vector<std::vector<int>>;
using Pair=std::pair<int,int>;
class DFS {
  const Graph& graph_;
  std::vector<unsigned> seen_;
  unsigned epoch_=0;
  std::vector<int> pending_;
public:
  explicit DFS(const Graph& g):graph_(g),seen_(g.size(),0){}
  bool query(int source,int target){
    if(source==target)return true;
    if(++epoch_==0){std::fill(seen_.begin(),seen_.end(),0);epoch_=1;}
    pending_.clear();pending_.push_back(source);seen_[source]=epoch_;
    while(!pending_.empty()){
      const int u=pending_.back();pending_.pop_back();
      for(int v:graph_[u]){
        if(v==target)return true;
        if(seen_[v]!=epoch_){seen_[v]=epoch_;pending_.push_back(v);}
      }
    }
    return false;
  }
};
static std::vector<unsigned char> oracle(const Graph& g,const std::vector<Pair>& qs){
  std::vector<unsigned char> out;out.reserve(qs.size());
  for(const auto& q:qs){
    std::vector<unsigned char> seen(g.size(),0);
    std::queue<int> work;work.push(q.first);seen[q.first]=1;
    while(!work.empty()){
      int u=work.front();work.pop();
      for(int v:g[u])if(!seen[v]){seen[v]=1;work.push(v);}
    }
    out.push_back(seen[q.second]);
  }
  return out;
}
static double median(std::vector<double> x){
  std::sort(x.begin(),x.end());
  const std::size_t mid=x.size()/2;
  return x.size()%2?x[mid]:(x[mid-1]+x[mid])*0.5;
}
int main(){
  try{
    int n,m,tcount,qcount;std::size_t k,cap;
    if(!(std::cin>>n>>m>>tcount>>qcount>>k>>cap)
      || n<1 || n>2000000 || m<0 || tcount<0 || qcount<1
      || k>100000)throw std::runtime_error("invalid header");
    Graph g(n);
    for(int i=0;i<m;++i){
      int u,v;if(!(std::cin>>u>>v)||u<0||v<0||u>=n||v>=n)
        throw std::runtime_error("invalid edge");
      g[u].push_back(v);
    }
    std::vector<Pair> train(tcount),test(qcount);
    for(auto& q:train)if(!(std::cin>>q.first>>q.second)
      || q.first<0||q.second<0||q.first>=n||q.second>=n)
      throw std::runtime_error("invalid training pair");
    for(auto& q:test)if(!(std::cin>>q.first>>q.second)
      || q.first<0||q.second<0||q.first>=n||q.second>=n)
      throw std::runtime_error("invalid test pair");
    const auto truth=oracle(g,test);
    auto start=Clock::now();
    HotSourceCache cache(g,train,k,cap,3);
    const auto finish=Clock::now();
    const double build_ns=std::chrono::duration<double,std::nano>(finish-start).count();
    if(cache.retained_bytes()>cap)throw std::runtime_error("retained cap breached");
    std::size_t hits=0;
    DFS preflight(g);
    for(int i=0;i<qcount;++i){
      bool answer=false;
      const bool cached=cache.lookup(test[i].first,test[i].second,answer);
      hits+=cached;
      if(!cached)answer=preflight.query(test[i].first,test[i].second);
      if(answer!=bool(truth[i]))throw std::runtime_error("cache incorrect");
      if(preflight.query(test[i].first,test[i].second)!=bool(truth[i]))
        throw std::runtime_error("DFS incorrect");
    }
    std::vector<double> baseline,accelerated;
    std::vector<int> order(qcount);std::iota(order.begin(),order.end(),0);
    std::mt19937 rng(20261022);
    std::uint64_t last_checksum=0;
    DFS plain(g),fallback(g);
    for(int rep=0;rep<14;++rep){
      std::shuffle(order.begin(),order.end(),rng);
      for(int turn=0;turn<2;++turn){
        const bool accelerated_arm=(rep+turn)%2==1;
        std::uint64_t checksum=1469598103934665603ULL;
        auto t0=Clock::now();
        for(int id:order){
          const auto [s,t]=test[id];
          bool answer=false;
          if(!accelerated_arm || !cache.lookup(s,t,answer))
            answer=(accelerated_arm?fallback:plain).query(s,t);
          checksum=(checksum*1099511628211ULL)
             ^(static_cast<std::uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        auto t1=Clock::now();
        // Independently check the same shuffled oracle checksum.
        std::uint64_t oracle_sum=1469598103934665603ULL;
        for(int id:order)oracle_sum=(oracle_sum*1099511628211ULL)
            ^(static_cast<std::uint64_t>(id)*4ULL+truth[id]);
        if(checksum!=oracle_sum)throw std::runtime_error("timed checksum mismatch");
        const double ns=std::chrono::duration<double,std::nano>(t1-t0).count()/qcount;
        (accelerated_arm?accelerated:baseline).push_back(ns);
        last_checksum=checksum;
      }
    }
    std::cout<<std::fixed<<std::setprecision(5)
      <<"{\"n\":"<<n<<",\"edges\":"<<m<<",\"training\":"<<tcount
      <<",\"heldout\":"<<qcount<<",\"cache_rows\":"<<cache.rows()
      <<",\"retained_bytes\":"<<cache.retained_bytes()
      <<",\"cap_bytes\":"<<cap<<",\"build_ns\":"<<build_ns
      <<",\"hits\":"<<hits
      <<",\"baseline_ns_per_query\":"<<median(baseline)
      <<",\"cached_ns_per_query\":"<<median(accelerated)
      <<",\"checksum\":"<<last_checksum
      <<",\"baseline_samples\":[";
    for(std::size_t i=0;i<baseline.size();++i){if(i)std::cout<<',';std::cout<<baseline[i];}
    std::cout<<"],\"cache_samples\":[";
    for(std::size_t i=0;i<accelerated.size();++i){if(i)std::cout<<',';std::cout<<accelerated[i];}
    std::cout<<"]}\n";
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}

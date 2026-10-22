// Phase XXII: full native graph-input + index construction + query-replay cost.
// Two exactly equivalent policies, run as independent fresh processes:
// pivot_index (no cache allocated) vs cache_pivot_index (cache allocated).
// Measures time from before input parsing through last answer, excluding
// compilation, Python training, dataset acquisition, validation and output.
// The replay repeats a heldout pair file: NOT fresh independent queries.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include <iomanip>
#include "hot_source_cache.h"
#include "compact_reachability.h"
using Clock=std::chrono::steady_clock;
using Graph=std::vector<std::vector<int>>;
using Bits=std::vector<std::uint64_t>;
using Pair=std::pair<int,int>;
static bool has(const Bits& b,int x){
  return (b[static_cast<std::size_t>(x)>>6]>>(x&63))&1U;
}
static Bits descendants(const Graph& g,int source){
  Bits bits((g.size()+63)/64,0);
  bits[static_cast<std::size_t>(source)>>6]|=std::uint64_t(1)<<(source&63);
  std::vector<int> stack{source};
  while(!stack.empty()){
    int u=stack.back();stack.pop_back();
    for(int v:g[u]) {
      const auto word=static_cast<std::size_t>(v)>>6;
      const auto flag=std::uint64_t(1)<<(v&63);
      if(!(bits[word]&flag)){bits[word]|=flag;stack.push_back(v);}
    }
  }
  return bits;
}
struct Pivot {Bits forward,backward;};
static int certify(const Pivot& p,int s,int t){
  bool fs=has(p.forward,s),ft=has(p.forward,t);
  bool bs=has(p.backward,s),bt=has(p.backward,t);
  if(bs&&ft)return 1;
  if((fs&&!ft)||(bt&&!bs))return 0;
  return -1;
}
static bool oracle(const Graph& g,int s,int t){
  if(s==t)return true;
  std::vector<unsigned char> seen(g.size(),0);
  std::vector<int> todo{s};
  seen[s]=1;
  while(!todo.empty()){
    const int u=todo.back();todo.pop_back();
    for(int v:g[u]) {
      if(v==t)return true;
      if(!seen[v]){seen[v]=1;todo.push_back(v);}
    }
  }
  return false;
}
int main(int argc,char** argv){
 try {
  const auto start=Clock::now();
  if(argc!=5)throw std::invalid_argument(
      "usage: lifetime <pivot_index|cache_pivot_index> <replay_factor> <max_sources> <cap_bytes>");
  const std::string mode=argv[1];
  const bool with_cache=mode=="cache_pivot_index";
  if(!with_cache && mode!="pivot_index")
    throw std::invalid_argument("invalid mode");
  const auto factor=std::stoull(argv[2]);
  const auto max_sources=std::stoull(argv[3]);
  const auto cap_bytes=std::stoull(argv[4]);
  if(factor<1 || factor>1000 || max_sources>100000 || cap_bytes>1073741824ULL)
    throw std::invalid_argument("invalid replay or byte cap");
  int n,m,c,qcount;
  if(!(std::cin>>n>>m>>c>>qcount) || n<1 || n>2000000 ||
     m<0 || c<1 || c>128 || qcount<1)
    throw std::invalid_argument("invalid native header");
  Graph graph(n),reverse(n);
  for(int i=0;i<m;++i){
    int u,v;
    if(!(std::cin>>u>>v)||u<0||u>=n||v<0||v>=n)
      throw std::invalid_argument("invalid arc");
    graph[u].push_back(v);reverse[v].push_back(u);
  }
  std::vector<int> candidates(c);
  for(int& s:candidates)if(!(std::cin>>s)||s<0||s>=n)
    throw std::invalid_argument("invalid pivot source");
  int policies;
  if(!(std::cin>>policies)||policies<1||policies>32)
    throw std::invalid_argument("invalid policy count");
  std::vector<int> selected;
  for(int i=0;i<policies;++i) {
    std::string name;int count;
    if(!(std::cin>>name>>count)||count<0||count>c)
      throw std::invalid_argument("bad policy");
    std::vector<int> ids(count);
    for(int& id:ids)if(!(std::cin>>id)||id<0||id>=c)
      throw std::invalid_argument("bad pivot ID");
    if(name=="Ordered")selected=std::move(ids);
  }
  if(selected.empty())throw std::invalid_argument("missing nonempty Ordered policy");
  std::vector<Pair> queries(qcount);
  for(auto& q:queries)if(!(std::cin>>q.first>>q.second)
      ||q.first<0||q.first>=n||q.second<0||q.second>=n)
      throw std::invalid_argument("bad query pair");
  int ntrain;
  if(!(std::cin>>ntrain)||ntrain<1||ntrain>100000)
    throw std::invalid_argument("training pairs missing");
  std::vector<Pair> training(ntrain);
  for(auto& q:training)if(!(std::cin>>q.first>>q.second)
     ||q.first<0||q.first>=n||q.second<0||q.second>=n)
    throw std::invalid_argument("bad training pair");
  const auto input_end=Clock::now();
  std::vector<Pivot> pivots;pivots.reserve(c);
  for(int source:candidates)pivots.push_back(Pivot{
    descendants(graph,source),descendants(reverse,source)});
  const auto pivot_end=Clock::now();
  CompactReachability index(graph);
  const auto index_end=Clock::now();
  // Default constructed cache occupies no lookup table in control mode.
  HotSourceCache cache;
  if(with_cache)
    cache=HotSourceCache(graph,training,static_cast<std::size_t>(max_sources),
                         static_cast<std::size_t>(cap_bytes),3);
  const auto cache_end=Clock::now();
  if(cache.retained_bytes()>cap_bytes)
    throw std::runtime_error("cache cap exceeded");
  std::uint64_t checksum=0xCBF29CE484222325ULL;
  std::uint64_t hits=0;
  for(unsigned long long epoch=0;epoch<factor;++epoch){
    for(int id=0;id<qcount;++id){
      const auto [s,t]=queries[id];
      bool answer=false,done=false;
      if(with_cache){
        done=cache.lookup(s,t,answer);
        hits+=done;
      }
      if(!done){
        int result=index.certificate(s,t);
        if(result==-1)for(int pivot_id:selected){
          result=certify(pivots[pivot_id],s,t);
          if(result!=-1)break;
        }
        answer=(result==-1)?index.reaches_bidirectional(s,t):(result!=0);
      }
      checksum=(checksum*0x100000001b3ULL)^(
          static_cast<std::uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
    }
  }
  const auto end=Clock::now();
  // Differential truth check after all timed sections (all unique heldout
  // queries); never mix expensive graph DFS oracle into full-index timing.
  for(const auto& q:queries){
    const auto [s,t]=q;
    bool ans=false,found=with_cache&&cache.lookup(s,t,ans);
    if(!found){
      int decision=index.certificate(s,t);
      if(decision==-1)for(int pid:selected){
        decision=certify(pivots[pid],s,t);
        if(decision!=-1)break;
      }
      ans=decision==-1?index.reaches_bidirectional(s,t):decision!=0;
    }
    if(ans!=oracle(graph,s,t))throw std::runtime_error("independent DFS mismatch");
  }
  const auto ns=[](auto a,auto b){
    return std::chrono::duration<double,std::nano>(b-a).count();};
  std::cout<<std::fixed<<std::setprecision(4)
    <<"{\"mode\":\""<<mode<<"\""
    <<",\"unique_queries\":"<<qcount<<",\"factor\":"<<factor
    <<",\"actual_query_calls\":"<<factor*static_cast<unsigned long long>(qcount)
    <<",\"training_pairs\":"<<ntrain<<",\"cache_hits\":"<<hits
    <<",\"cache_rows\":"<<cache.rows()
    <<",\"retained_cache_bytes\":"<<cache.retained_bytes()
    <<",\"index_label_bytes\":"<<index.labels_bytes()
    <<",\"bidirectional_extra_bytes\":"<<index.bidirectional_extra_bytes()
    <<",\"parse_input_ns\":"<<ns(start,input_end)
    <<",\"build_pivots_ns\":"<<ns(input_end,pivot_end)
    <<",\"build_compact_ns\":"<<ns(pivot_end,index_end)
    <<",\"build_cache_ns\":"<<ns(index_end,cache_end)
    <<",\"actual_query_loop_ns\":"<<ns(cache_end,end)
    <<",\"full_native_build_plus_queries_ns\":"<<ns(start,end)
    <<",\"independently_verified_queries\":"<<qcount
    <<",\"checksum\":"<<checksum<<"}\n";
  return 0;
 } catch(const std::exception& e){
  std::cerr<<e.what()<<'\n';return 2;
 }
}

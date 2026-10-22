// Phase XXI: exact hot-source bitset fast path before existing indexed fallback.
// Four arms, equal position-balanced 16-repetition C++17 measurement.
// No novel index, no default behavior change; pilot evidence only.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "compact_reachability.h"
#include "hot_source_cache.h"

using Clock=std::chrono::steady_clock;
using Graph=std::vector<std::vector<int>>;
using Bits=std::vector<std::uint64_t>;
using Pair=std::pair<int,int>;

static bool has(const Bits& b,int vertex){
  return ((b[static_cast<std::size_t>(vertex)>>6]>>(vertex&63))&1U)!=0;
}
static Bits reachable_set(const Graph& g,int source){
  Bits bits((g.size()+63)/64,0);
  bits[static_cast<std::size_t>(source)>>6] |= std::uint64_t(1)<<(source&63);
  std::vector<int> stack{source};
  while(!stack.empty()){
    const int u=stack.back();stack.pop_back();
    for(int v:g[u]){
      const std::size_t word=static_cast<std::size_t>(v)>>6;
      const std::uint64_t flag=std::uint64_t(1)<<(v&63);
      if(!(bits[word]&flag)){bits[word]|=flag;stack.push_back(v);}
    }
  }
  return bits;
}
struct Pivot {Bits forward,backward;};
static int certify(const Pivot& p,int s,int t){
  const bool fs=has(p.forward,s),ft=has(p.forward,t);
  const bool bs=has(p.backward,s),bt=has(p.backward,t);
  if(bs&&ft)return 1;
  if((fs&&!ft)||(bt&&!bs))return 0;
  return -1;
}
class IndependentBFS {
  const Graph& graph_;
  std::vector<unsigned> seen_;
  unsigned epoch_=0;
  std::vector<int> queue_;
public:
  explicit IndependentBFS(const Graph& g):graph_(g),seen_(g.size(),0){}
  bool check(int source,int target) {
    if(source==target)return true;
    if(++epoch_==0){std::fill(seen_.begin(),seen_.end(),0);epoch_=1;}
    queue_.clear();queue_.push_back(source);seen_[source]=epoch_;
    for(std::size_t head=0;head<queue_.size();++head) {
      const int u=queue_[head];
      for(int v:graph_[u]){
        if(v==target)return true;
        if(seen_[v]!=epoch_){seen_[v]=epoch_;queue_.push_back(v);}
      }
    }
    return false;
  }
};
static double median(std::vector<double> x) {
  if(x.empty())throw std::invalid_argument("no timing samples");
  std::sort(x.begin(),x.end());
  const std::size_t i=x.size()/2;
  return x.size()%2?x[i]:(x[i-1]+x[i])*0.5;
}
int main(int argc,char** argv) {
  try {
    if(argc!=4)throw std::invalid_argument("usage: binary <reps=16> <max-hot-sources> <cap-bytes>");
    const int reps=std::stoi(argv[1]);
    const unsigned long long max_sources=std::stoull(argv[2]);
    const unsigned long long cap_bytes=std::stoull(argv[3]);
    if(reps!=16 || max_sources>100000 || cap_bytes>1073741824ULL)
      throw std::invalid_argument("invalid repetitions or cache cap");
    int n,m,c,qcount;
    if(!(std::cin>>n>>m>>c>>qcount) ||
       n<1 || n>2000000 || m<0 || c<0 || c>128 || qcount<1)
      throw std::invalid_argument("invalid graph header");
    Graph graph(n),reverse(n);
    for(int i=0;i<m;++i){
      int u,v;
      if(!(std::cin>>u>>v)||u<0||u>=n||v<0||v>=n)
        throw std::invalid_argument("invalid graph edge");
      graph[u].push_back(v);
      reverse[v].push_back(u);
    }
    std::vector<int> candidates(c);
    for(int &s:candidates)
      if(!(std::cin>>s)||s<0||s>=n)throw std::invalid_argument("invalid pivot");
    int np;
    if(!(std::cin>>np)||np<1||np>32)throw std::invalid_argument("invalid policy count");
    std::vector<int> ordered;
    for(int i=0;i<np;++i){
      std::string name;int length;
      if(!(std::cin>>name>>length)||length<0||length>c)
        throw std::invalid_argument("invalid policy metadata");
      std::vector<int> ids(length);
      for(int& id:ids)if(!(std::cin>>id)||id<0||id>=c)
        throw std::invalid_argument("invalid policy pivot index");
      if(name=="Ordered")ordered=std::move(ids);
    }
    if(ordered.empty())throw std::invalid_argument("trained Ordered pivot policy is empty");
    std::vector<Pair> test(qcount);
    for(auto& q:test)if(!(std::cin>>q.first>>q.second)
       ||q.first<0||q.first>=n||q.second<0||q.second>=n)
       throw std::invalid_argument("invalid heldout pair");
    int train_count;
    if(!(std::cin>>train_count)||train_count<1||train_count>100000)
      throw std::invalid_argument("training pairs required");
    std::vector<Pair> training(train_count);
    for(auto& q:training)if(!(std::cin>>q.first>>q.second)
       ||q.first<0||q.first>=n||q.second<0||q.second>=n)
       throw std::invalid_argument("invalid training pair");
    const auto pivot_start=Clock::now();
    std::vector<Pivot> pivots;pivots.reserve(c);
    for(int s:candidates)pivots.push_back(Pivot{reachable_set(graph,s),reachable_set(reverse,s)});
    const auto pivot_end=Clock::now();
    const auto index_start=Clock::now();
    CompactReachability index(graph);
    const auto index_end=Clock::now();
    const auto cache_start=Clock::now();
    HotSourceCache cache(graph,training,static_cast<std::size_t>(max_sources),
                         static_cast<std::size_t>(cap_bytes),3);
    const auto cache_end=Clock::now();
    if(cache.retained_bytes()>cap_bytes)throw std::runtime_error("cache retained-byte cap violated");
    IndependentBFS reference(graph);
    std::vector<unsigned char> truth(qcount);
    std::uint64_t oracle_checks=0;
    for(int i=0;i<qcount;++i) {
      truth[i]=reference.check(test[i].first,test[i].second);
      oracle_checks+=(truth[i]?1U:0U);
    }
    std::size_t cache_hits=0;
    for(const auto& p:test){bool answer=false;cache_hits+=cache.lookup(p.first,p.second,answer);}
    std::array<std::vector<double>,4> timings;
    std::array<std::uint64_t,4> last_checksums{};
    std::vector<int> order(qcount);std::iota(order.begin(),order.end(),0);
    std::mt19937 rng(20261022);
    // Modes: 0=index only; 1=cache/index; 2=certificate+pivots+index;
    // 3=cache/(certificate+pivots+index).
    // Cached mode still uses a perfectly exact index on miss, not plain DFS.
    for(int rep=0;rep<reps;++rep) {
      std::shuffle(order.begin(),order.end(),rng);
      for(int rotation=0;rotation<4;++rotation) {
        const int mode=(rep+rotation)%4;
        std::uint64_t checksum=0xCBF29CE484222325ULL;
        const auto t0=Clock::now();
        for(int id:order) {
          const int source=test[id].first,target=test[id].second;
          bool answer=false;
          bool done=false;
          if(mode==1||mode==3)done=cache.lookup(source,target,answer);
          if(!done) {
            if(mode==2||mode==3) {
              int certificate=index.certificate(source,target);
              if(certificate==-1) {
                for(int pivot_id:ordered) {
                  certificate=certify(pivots[pivot_id],source,target);
                  if(certificate!=-1)break;
                }
              }
              if(certificate!=-1) {
                answer=certificate!=0;
                done=true;
              }
            }
            if(!done)answer=index.reaches_bidirectional(source,target);
          }
          checksum=(checksum*0x100000001b3ULL)^(
            static_cast<std::uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        const auto t1=Clock::now();
        std::uint64_t oracle_sum=0xCBF29CE484222325ULL;
        for(int id:order)
          oracle_sum=(oracle_sum*0x100000001b3ULL)^(
            static_cast<std::uint64_t>(id)*4ULL+truth[id]);
        if(checksum!=oracle_sum)
          throw std::runtime_error("indexed/cache/oracle mismatch mode "+std::to_string(mode));
        timings[mode].push_back(std::chrono::duration<double,std::nano>(t1-t0).count()/qcount);
        last_checksums[mode]=checksum;
      }
    }
    const double build_pivots_ns=std::chrono::duration<double,std::nano>(
      pivot_end-pivot_start).count();
    const double build_compact_ns=std::chrono::duration<double,std::nano>(
      index_end-index_start).count();
    const double build_cache_ns=std::chrono::duration<double,std::nano>(
      cache_end-cache_start).count();
    std::cout<<std::fixed<<std::setprecision(6)
      <<"{\"queries\":"<<qcount<<",\"training\":"<<train_count
      <<",\"cache_rows\":"<<cache.rows()
      <<",\"cache_hits\":"<<cache_hits
      <<",\"cache_retained_bytes\":"<<cache.retained_bytes()
      <<",\"cache_cap_bytes\":"<<cap_bytes
      <<",\"compact_labels_bytes\":"<<index.labels_bytes()
      <<",\"compact_bidir_extra_bytes\":"<<index.bidirectional_extra_bytes()
      <<",\"pivot_build_ns\":"<<build_pivots_ns
      <<",\"compact_build_ns\":"<<build_compact_ns
      <<",\"cache_build_ns\":"<<build_cache_ns
      <<",\"oracle_positive_count\":"<<oracle_checks
      <<",\"modes\":{";
    const std::array<const char*,4> labels={
      "index_only","cache_index","pivot_index","cache_pivot_index"};
    for(int mode=0;mode<4;++mode) {
      if(mode)std::cout<<',';
      std::cout<<'\"'<<labels[mode]<<"\":{\"median_ns_per_query\":"
        <<median(timings[mode])
        <<",\"checksum\":"<<last_checksums[mode]
        <<",\"samples_ns_per_query\":[";
      for(std::size_t j=0;j<timings[mode].size();++j) {
        if(j)std::cout<<',';
        std::cout<<timings[mode][j];
      }
      std::cout<<"]}";
    }
    std::cout<<"}}\n";
    return 0;
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}

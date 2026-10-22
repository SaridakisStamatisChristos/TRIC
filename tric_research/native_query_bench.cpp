// TRIC Phase IX: self-contained C++17 query-plane benchmark.
// Standard library only. Compile: g++ -std=c++17 -O3 -DNDEBUG -Wall -Wextra -pedantic -o native_query_bench native_query_bench.cpp
// Input: n m c Q; m edges (u v); c candidate pivots; B policies (name length pivot-ids...); Q test pairs.
// All timings exclude input, pivot builds, oracle evaluation, warmup and output.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
#include "closure_index.h"
#include "compact_reachability.h"
using Clock=std::chrono::steady_clock;
using Graph=std::vector<std::vector<int>>;
struct Policy {std::string name; std::vector<int> order;};
struct Counter {uint64_t probes=0, hits=0, edges=0, checksum=0;};
using Bits=std::vector<uint64_t>;
static inline bool has(const Bits& b, int v){return (b[v>>6]>>(v&63))&uint64_t(1);}
static Bits reaches(const Graph &g,int source){
  const int n=static_cast<int>(g.size());
  Bits bits((n+63)/64,0);
  std::vector<int> stack; stack.push_back(source);
  bits[source>>6] |= (uint64_t(1)<<(source&63));
  while(!stack.empty()){
    int u=stack.back();stack.pop_back();
    for(int v:g[u]){
      const uint64_t flag=uint64_t(1)<<(v&63);
      if(!(bits[v>>6]&flag)){bits[v>>6]|=flag;stack.push_back(v);}
    }
  }
  return bits;
}
class Search {
  const Graph& graph;
  std::vector<int> seen,stack;
  int epoch=0;
public:
  explicit Search(const Graph& g):graph(g),seen(g.size(),0){stack.reserve(g.size());}
  bool query(int source,int target, uint64_t& edges){
    if(source==target) return true;
    if(epoch==std::numeric_limits<int>::max()) {std::fill(seen.begin(),seen.end(),0);epoch=0;}
    ++epoch;stack.clear();stack.push_back(source);seen[source]=epoch;
    while(!stack.empty()){
      int u=stack.back();stack.pop_back();
      for(int v:graph[u]){
        ++edges;
        if(v==target)return true;
        if(seen[v]!=epoch){seen[v]=epoch;stack.push_back(v);}
      }
    }
    return false;
  }
};
struct Pivot {Bits forward, backward;};
// Independent rule implementation using exact pivot reachability bit-vectors.
static int certify(const Pivot &p,int s,int t){
  const bool fs=has(p.forward,s), ft=has(p.forward,t);
  const bool bs=has(p.backward,s),bt=has(p.backward,t);
  if(bs&&ft)return 1;
  if((fs&&!ft)||(bt&&!bs))return 0;
  return -1;
}
static Counter run(const Graph& g,const std::vector<Pivot>& pivots,const Policy &pol,
                   const std::vector<std::pair<int,int>>& q, const std::vector<int>& order,
                   const std::vector<uint8_t>& oracle){
  Search search(g);Counter out;
  for(int id:order){
    int s=q[id].first,t=q[id].second;int prediction=-1;
    for(int p:pol.order){
      ++out.probes;
      int got=certify(pivots.at(p),s,t);
      if(got!=-1){++out.hits;prediction=got;break;}
    }
    if(prediction==-1) prediction=search.query(s,t,out.edges)?1:0;
    if(prediction!=oracle[id])throw std::runtime_error("Incorrect certificate/BFS answer at query "+std::to_string(id));
    // Nonconstant checksum makes executing all queries observable to the driver.
    out.checksum = (out.checksum * 0x100000001b3ULL) ^ (static_cast<uint64_t>(id)*4ULL+prediction);
  }
  return out;
}
static double median(std::vector<double> a){
  std::sort(a.begin(),a.end());
  auto mid=a.size()/2;
  return a.size()%2 ? a[mid] : (a[mid-1]+a[mid])/2;
}
int main(int argc,char **argv){
  try{
    int reps=7;
    if(argc>1) reps=std::stoi(argv[1]);
    if(reps<3||reps>24)throw std::runtime_error("reps must be in [3,24]");
    int n,m,c,qcount;
    if(!(std::cin>>n>>m>>c>>qcount) || n<1 || m<0 || c<0 || qcount<1 || n>2000000)throw std::runtime_error("invalid graph input header");
    Graph graph(n),reverse(n);
    for(int i=0;i<m;i++){
      int u,v; if(!(std::cin>>u>>v)||u<0||v<0||u>=n||v>=n)throw std::runtime_error("bad edge");
      graph[u].push_back(v);reverse[v].push_back(u);
    }
    std::vector<int> pivot_vertices(c);
    for(int& v:pivot_vertices){if(!(std::cin>>v)||v<0||v>=n)throw std::runtime_error("bad candidate vertex");}
    int numpol; if(!(std::cin>>numpol)||numpol<1||numpol>32)throw std::runtime_error("bad number policies");
    std::vector<Policy> policies(numpol);
    for(auto& p:policies){
      int len; if(!(std::cin>>p.name>>len)||len<0||len>c)throw std::runtime_error("bad policy");
      for(int j=0;j<len;j++){
        int v;if(!(std::cin>>v)||v<0||v>=c)throw std::runtime_error("bad policy pivot id");
        if(std::find(p.order.begin(),p.order.end(),v)!=p.order.end())throw std::runtime_error("duplicate policy pivot");
        p.order.push_back(v);
      }
    }
    std::vector<std::pair<int,int>> queries(qcount);
    for(auto& v:queries){if(!(std::cin>>v.first>>v.second)||v.first<0||v.second<0||v.first>=n||v.second>=n)throw std::runtime_error("bad test query");}
    // Optional trailer: TRAINING pairs, never heldout truth labels. Missing
    // trailer is supported for backward-compatible native test inputs.
    int ntrain=0;
    if(!(std::cin>>ntrain)){
      if(!std::cin.eof())throw std::runtime_error("bad selector training header");
      std::cin.clear();
    }
    if(ntrain<0 || ntrain>100000)throw std::runtime_error("bad selector train count");
    std::vector<std::pair<int,int>> selector_train(ntrain);
    for(auto& v:selector_train)
      if(!(std::cin>>v.first>>v.second)||v.first<0||v.second<0||v.first>=n||v.second>=n)
        throw std::runtime_error("bad selector training pair");
    auto build_start=Clock::now();
    std::vector<Pivot> pivots;
    for(int v:pivot_vertices) pivots.push_back(Pivot{reaches(graph,v),reaches(reverse,v)});
    auto build_end=Clock::now();
    const double build_ms=std::chrono::duration<double,std::milli>(build_end-build_start).count();
    // Independent BFS reachability ground truth; no certificate is trusted as oracle.
    Search oracle_search(graph);std::vector<uint8_t> truth(qcount);
    uint64_t oracle_edges=0;
    for(int i=0;i<qcount;i++)truth[i]=oracle_search.query(queries[i].first,queries[i].second,oracle_edges);
    // Additional exact index: memory-capped SCC transitive closure, NOT a
    // matched-memory O'Reach comparison.
    std::size_t cap_mib=64;
    if(argc>2){
      unsigned long long x=std::stoull(argv[2]);
      if(x>1024)throw std::runtime_error("invalid closure cap MiB");
      cap_mib=static_cast<std::size_t>(x);
    }
    auto c0=Clock::now();
    BoundedClosure closure(graph,cap_mib*1024*1024);
    auto c1=Clock::now();
    const double closure_build_ms=std::chrono::duration<double,std::milli>(c1-c0).count();
    // O(|V|+|E|) SCC condensation plus four reachability-safe intervals.
    auto k0=Clock::now();
    CompactReachability compact(graph);
    auto k1=Clock::now();
    const double compact_build_ms=std::chrono::duration<double,std::milli>(k1-k0).count();
    std::vector<double> compact_samples, compact_plain_samples, compact_topo_samples, compact_bidir_samples, compact_bidir_intervals_samples, hybrid_samples, hybrid_topo_samples, hybrid_bidir_samples, hybrid_bidir_intervals_samples, hybrid_selector_samples, closure_onepass_samples;
    std::vector<double> closure_samples;
    uint64_t compact_checksum=0, compact_plain_checksum=0, compact_topo_checksum=0, compact_bidir_checksum=0, compact_bidir_intervals_checksum=0, hybrid_checksum=0, hybrid_topo_checksum=0, hybrid_bidir_checksum=0, hybrid_bidir_intervals_checksum=0, hybrid_selector_checksum=0;
    uint64_t hybrid_pivot_rescues=0, hybrid_fallback_queries=0, hybrid_probe_count=0, selector_topo_fallbacks=0, selector_bidir_fallbacks=0;
    CompactReachability::QueryStats compact_stats, compact_plain_stats, compact_topo_stats, compact_bidir_stats, compact_bidir_intervals_stats;
    uint64_t closure_checksum=0;
    std::vector<std::vector<double>> samples(numpol);
    std::vector<Counter> counters(numpol);
    const Policy* trained=&policies[0];
    for(const auto& p:policies)if(p.name=="Ordered"){trained=&p;break;}
    // Phase XVII: fit a small O(1) selector on train-only pairs.
    // The independent heldout query list is NEVER consulted by this fit.
    // Every candidate includes full certificate, pivot and dispatch costs.
    int selected_policy=1; // bidirectional default without explicit training
    double selector_training_ns=0;
    std::array<double,9> selector_training_medians{};
    if(!selector_train.empty()){
      Search training_oracle(graph);
      std::vector<uint8_t> training_truth(selector_train.size());
      std::uint64_t oracle_train_edges=0;
      for(std::size_t i=0;i<selector_train.size();++i)
        training_truth[i]=training_oracle.query(selector_train[i].first,
                                               selector_train[i].second,oracle_train_edges);
      const auto start_training=Clock::now();
      std::array<std::vector<double>,9> policy_samples;
      std::vector<int> training_order(selector_train.size());
      std::iota(training_order.begin(),training_order.end(),0);
      for(int rep=0;rep<9;++rep){
        std::mt19937_64 shuffle_gen(0xabcdef123987ULL+static_cast<uint64_t>(rep));
        std::shuffle(training_order.begin(),training_order.end(),shuffle_gen);
        for(int off=0;off<9;++off){
          const int policy=(rep+off)%9; // nine-way balanced order
          std::uint64_t sum=0;
          auto t0=Clock::now();
          for(int id:training_order){
            const int source=selector_train[id].first,target=selector_train[id].second;
            int decision=compact.certificate(source,target);
            if(decision==-1)for(int p:trained->order){
              int cert=certify(pivots.at(p),source,target);
              if(cert!=-1){decision=cert;break;}
            }
            if(decision==-1){
              const bool use_topo=compact.select_topological(source,target,policy);
              decision=(use_topo?compact.reaches(source,target,nullptr,false,true)
                                :compact.reaches_bidirectional(source,target))?1:0;
            }
            if(decision!=training_truth[id])
              throw std::runtime_error("selector training answer mismatch");
            sum=(sum*0x100000001b3ULL)
                ^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(decision));
          }
          auto t1=Clock::now();
          policy_samples[policy].push_back(
              std::chrono::duration<double,std::nano>(t1-t0).count()/selector_train.size());
          // Keep a visible effect preventing the correctness checksum from
          // being compiled out; the train data never sets heldout checksum.
          if(sum==0 && !selector_train.empty() && training_truth[0]>1)
            throw std::runtime_error("impossible training checksum state");
        }
      }
      double best=std::numeric_limits<double>::infinity();
      for(int p=0;p<9;++p){
        selector_training_medians[p]=median(policy_samples[p]);
        if(selector_training_medians[p]<best){
          best=selector_training_medians[p];selected_policy=p;
        }
      }
      selector_training_ns=std::chrono::duration<double,std::nano>(
          Clock::now()-start_training).count();
    }
    std::vector<int> query_order(qcount);std::iota(query_order.begin(),query_order.end(),0);
    // Separate untimed warmup; rotate benchmark policy execution order per repetition.
    for(int pi=0;pi<numpol;pi++)(void)run(graph,pivots,policies[pi],queries,query_order,truth);
    // Differential validation against the independent DFS/BFS oracle.
    if(closure.built())for(int i=0;i<qcount;++i)
      if(closure.reaches(queries[i].first,queries[i].second)!=bool(truth[i]))
        throw std::runtime_error("closure mismatch with independent DFS oracle at query "+std::to_string(i));
    // Independent BFS validates every index answer before timing.
    for(int i=0;i<qcount;++i)
      if(compact.reaches(queries[i].first,queries[i].second)!=bool(truth[i]))
        throw std::runtime_error("compact reachability mismatch at query "+std::to_string(i));
    for(int rep=0;rep<reps;rep++){
      std::mt19937_64 rng(0x9e3779b97f4a7c15ULL+static_cast<uint64_t>(rep));
      std::shuffle(query_order.begin(),query_order.end(),rng);
      for(int off=0;off<numpol;off++){
        int pi=(rep+off)%numpol;
        auto t0=Clock::now();
        Counter result=run(graph,pivots,policies[pi],queries,query_order,truth);
        auto t1=Clock::now();
        samples[pi].push_back(std::chrono::duration<double,std::nano>(t1-t0).count()/qcount);
        counters[pi]=result;
      }
      {
        CompactReachability::QueryStats st;
        uint64_t sum=0;
        auto t0=Clock::now();
        for(int id:query_order){
          const bool answer=compact.reaches(queries[id].first,queries[id].second,&st);
          sum=(sum*0x100000001b3ULL)^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        auto t1=Clock::now();
        compact_samples.push_back(std::chrono::duration<double,std::nano>(t1-t0).count()/qcount);
        compact_checksum=sum;
        compact_stats=st;
        if(sum!=counters[0].checksum)throw std::runtime_error("compact checksum differed from oracle");
      }
      {
        CompactReachability::QueryStats st;
        uint64_t sum=0;
        auto t0=Clock::now();
        for(int id:query_order){
          const bool answer=compact.reaches(queries[id].first,queries[id].second,&st,false);
          sum=(sum*0x100000001b3ULL)^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        auto t1=Clock::now();
        compact_plain_samples.push_back(std::chrono::duration<double,std::nano>(t1-t0).count()/qcount);
        compact_plain_checksum=sum;
        compact_plain_stats=st;
        if(sum!=compact_checksum)throw std::runtime_error("plain/filtered compact mismatch");
      }
      {
        // Ablation: one integer topological bound per unexplored SCC.
        CompactReachability::QueryStats st;
        uint64_t sum=0;
        auto t0=Clock::now();
        for(int id:query_order){
          const bool answer=compact.reaches(queries[id].first,queries[id].second,&st,false,true);
          sum=(sum*0x100000001b3ULL)^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        auto t1=Clock::now();
        compact_topo_samples.push_back(std::chrono::duration<double,std::nano>(t1-t0).count()/qcount);
        compact_topo_checksum=sum;compact_topo_stats=st;
        if(sum!=compact_checksum)throw std::runtime_error("topological compact mismatch");
      }
      {
        // Bidirectional fallback ablation with independently recorded scan work.
        CompactReachability::QueryStats st;
        uint64_t sum=0;
        auto t0=Clock::now();
        for(int id:query_order){
          const bool answer=compact.reaches_bidirectional(
              queries[id].first,queries[id].second,&st);
          sum=(sum*0x100000001b3ULL)
               ^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        auto t1=Clock::now();
        compact_bidir_samples.push_back(std::chrono::duration<double,std::nano>(t1-t0).count()/qcount);
        compact_bidir_checksum=sum;
        compact_bidir_stats=st;
        if(sum!=compact_checksum)throw std::runtime_error("bidirectional compact mismatch");
      }
      {
        // Separate non-pivot A/B for exact two-sided interval filters.
        CompactReachability::QueryStats st;
        uint64_t sum=0;
        auto t0=Clock::now();
        for(int id:query_order){
          const bool answer=compact.reaches_bidirectional(
              queries[id].first,queries[id].second,&st,true);
          sum=(sum*0x100000001b3ULL)
             ^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        auto t1=Clock::now();
        compact_bidir_intervals_samples.push_back(
            std::chrono::duration<double,std::nano>(t1-t0).count()/qcount);
        compact_bidir_intervals_checksum=sum;
        compact_bidir_intervals_stats=st;
        if(sum!=compact_checksum)
          throw std::runtime_error("interval-pruned bidirectional oracle mismatch");
      }
      {
        // Five modes, 15 repetitions: equal position exposure (3 each).
        // All hybrid methods use identical certificates and trained pivots.
        struct HybridResult {
          double ns=0;
          uint64_t checksum=0, rescues=0, fallbacks=0, probes=0, topo_fallbacks=0, bidir_fallbacks=0;
        };
        const auto measure_hybrid=[&](int fallback_mode){
          HybridResult result;
          auto t0=Clock::now();
          for(int id:query_order){
            const int source=queries[id].first,target=queries[id].second;
            int decision=compact.certificate(source,target);
            if(decision==-1){
              for(int p:trained->order){
                ++result.probes;
                int outcome=certify(pivots.at(p),source,target);
                if(outcome!=-1){decision=outcome;++result.rescues;break;}
              }
            }
            if(decision==-1){
              ++result.fallbacks;
              const bool use_topo=(fallback_mode==4)
                  ?compact.select_topological(source,target,selected_policy)
                  :fallback_mode==1;
              const bool hit=(fallback_mode==4)
                  ?(use_topo ?compact.reaches(source,target,nullptr,false,true)
                             :compact.reaches_bidirectional(source,target))
                  :(fallback_mode>=2
                    ?compact.reaches_bidirectional(source,target,nullptr,fallback_mode==3)
                    :compact.reaches(source,target,nullptr,false,fallback_mode==1));
              if(fallback_mode==4){
                if(use_topo)++result.topo_fallbacks;
                else ++result.bidir_fallbacks;
              }
              decision=hit?1:0;
            }
            result.checksum=(result.checksum*0x100000001b3ULL)
                ^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(decision));
          }
          auto t1=Clock::now();
          result.ns=std::chrono::duration<double,std::nano>(t1-t0).count()/qcount;
          return result;
        };
        std::array<HybridResult,5> ablations;
        for(int offset=0;offset<5;++offset){
          const int mode=(rep+offset)%5;
          ablations[mode]=measure_hybrid(mode);
        }
        const auto &plain=ablations[0],&topo=ablations[1],&bidir=ablations[2],
                   &intervals=ablations[3],&selector=ablations[4];
        hybrid_samples.push_back(plain.ns);
        hybrid_topo_samples.push_back(topo.ns);
        hybrid_bidir_samples.push_back(bidir.ns);
        hybrid_bidir_intervals_samples.push_back(intervals.ns);
        hybrid_selector_samples.push_back(selector.ns);
        selector_topo_fallbacks=selector.topo_fallbacks;
        selector_bidir_fallbacks=selector.bidir_fallbacks;
        hybrid_selector_checksum=selector.checksum;
        hybrid_checksum=plain.checksum;hybrid_topo_checksum=topo.checksum;
        hybrid_bidir_checksum=bidir.checksum;
        hybrid_bidir_intervals_checksum=intervals.checksum;
        hybrid_pivot_rescues=plain.rescues;
        hybrid_fallback_queries=plain.fallbacks;
        hybrid_probe_count=plain.probes;
        if(plain.checksum!=compact_checksum || topo.checksum!=compact_checksum
           || bidir.checksum!=compact_checksum || intervals.checksum!=compact_checksum
           || selector.checksum!=compact_checksum
           || plain.rescues!=topo.rescues || plain.rescues!=bidir.rescues || plain.rescues!=intervals.rescues || plain.rescues!=selector.rescues
           || plain.fallbacks!=topo.fallbacks || plain.fallbacks!=bidir.fallbacks || plain.fallbacks!=intervals.fallbacks || plain.fallbacks!=selector.fallbacks
           || plain.probes!=topo.probes || plain.probes!=bidir.probes || plain.probes!=intervals.probes || plain.probes!=selector.probes
           || selector.topo_fallbacks+selector.bidir_fallbacks!=selector.fallbacks)
          throw std::runtime_error("five-way hybrid correctness/accounting mismatch");
      }
      if(closure.built()){
        uint64_t onepass_checksum=0;
        auto a0=Clock::now();
        for(int id:query_order){
          const bool answer=closure.reaches(queries[id].first,queries[id].second);
          onepass_checksum=(onepass_checksum*0x100000001b3ULL)^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
        }
        auto a1=Clock::now();
        closure_onepass_samples.push_back(std::chrono::duration<double,std::nano>(a1-a0).count()/qcount);
        if(onepass_checksum!=compact_checksum)throw std::runtime_error("closure/compact checksum mismatch");
        auto t0=Clock::now();
        uint64_t sum=0;
        constexpr int batches=128; // suppress timer overhead at nanosecond scale
        for(int batch=0;batch<batches;++batch){
          sum=0;
          for(int id:query_order){
            const bool answer=closure.reaches(queries[id].first,queries[id].second);
            sum=(sum*0x100000001b3ULL)^(static_cast<uint64_t>(id)*4ULL+static_cast<unsigned>(answer));
          }
        }
        auto t1=Clock::now();
        closure_samples.push_back(std::chrono::duration<double,std::nano>(t1-t0).count()/(qcount*batches));
        closure_checksum=sum;
      }
    }
    std::cout<<std::fixed<<std::setprecision(7);
    std::cout<<"{\"n\":"<<n<<",\"edges\":"<<m<<",\"queries\":"<<qcount<<",\"candidate_count\":"<<c
       <<",\"index_build_ms\":"<<build_ms<<",\"repetitions\":"<<reps<<",\"policies\":[";
    for(int i=0;i<numpol;i++){
      if(i)std::cout<<',';
      auto ct=counters[i];
      std::cout<<"{\"name\":\""<<policies[i].name<<"\",\"pivots\":"<<policies[i].order.size()
               <<",\"median_ns_per_query\":"<<median(samples[i])
               <<",\"mean_probes\":"<<double(ct.probes)/qcount
               <<",\"hit_rate\":"<<double(ct.hits)/qcount
               <<",\"mean_bfs_edges\":"<<double(ct.edges)/qcount
               <<",\"checksum\":"<<ct.checksum<<",\"samples_ns_per_query\":[";
      for(size_t j=0;j<samples[i].size();j++){if(j)std::cout<<',';std::cout<<samples[i][j];}
      std::cout<<"]}";
    }
    std::cout<<"],\"compact\":{\"dimensions\":"<<CompactReachability::dimensions
             <<",\"components\":"<<compact.components()
             <<",\"labels_bytes\":"<<compact.labels_bytes()
             <<",\"build_ms\":"<<compact_build_ms
             <<",\"median_ns_per_query\":"<<median(compact_samples)
             <<",\"certified_yes\":"<<compact_stats.certified_yes
             <<",\"certified_no\":"<<compact_stats.certified_no
             <<",\"fallback_queries\":"<<compact_stats.fallback
             <<",\"fallback_edges\":"<<compact_stats.edges
             <<",\"checksum\":"<<compact_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<compact_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<compact_samples[j];
    }
    std::cout<<"]},\"compact_plain\":{\"median_ns_per_query\":"<<median(compact_plain_samples)
             <<",\"certified_yes\":"<<compact_plain_stats.certified_yes
             <<",\"certified_no\":"<<compact_plain_stats.certified_no
             <<",\"fallback_queries\":"<<compact_plain_stats.fallback
             <<",\"fallback_edges\":"<<compact_plain_stats.edges
             <<",\"checksum\":"<<compact_plain_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<compact_plain_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<compact_plain_samples[j];
    }
    std::cout<<"]},\"compact_topo\":{\"median_ns_per_query\":"<<median(compact_topo_samples)
             <<",\"certified_yes\":"<<compact_topo_stats.certified_yes
             <<",\"certified_no\":"<<compact_topo_stats.certified_no
             <<",\"fallback_queries\":"<<compact_topo_stats.fallback
             <<",\"fallback_edges\":"<<compact_topo_stats.edges
             <<",\"checksum\":"<<compact_topo_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<compact_topo_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<compact_topo_samples[j];
    }
    std::cout<<"]},\"compact_bidir\":{\"median_ns_per_query\":"<<median(compact_bidir_samples)
             <<",\"certified_yes\":"<<compact_bidir_stats.certified_yes
             <<",\"certified_no\":"<<compact_bidir_stats.certified_no
             <<",\"fallback_queries\":"<<compact_bidir_stats.fallback
             <<",\"fallback_edges\":"<<compact_bidir_stats.edges
             <<",\"extra_storage_bytes\":"<<compact.bidirectional_extra_bytes()
             <<",\"checksum\":"<<compact_bidir_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<compact_bidir_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<compact_bidir_samples[j];
    }
    std::cout<<"]},\"compact_bidir_intervals\":{\"median_ns_per_query\":"<<median(compact_bidir_intervals_samples)
             <<",\"certified_yes\":"<<compact_bidir_intervals_stats.certified_yes
             <<",\"certified_no\":"<<compact_bidir_intervals_stats.certified_no
             <<",\"fallback_queries\":"<<compact_bidir_intervals_stats.fallback
             <<",\"fallback_edges\":"<<compact_bidir_intervals_stats.edges
             <<",\"interval_rejections\":"<<compact_bidir_intervals_stats.interval_rejections
             <<",\"extra_storage_bytes\":"<<compact.bidirectional_extra_bytes()
             <<",\"checksum\":"<<compact_bidir_intervals_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<compact_bidir_intervals_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<compact_bidir_intervals_samples[j];
    }
    std::cout<<"]},\"compact_pivots\":{\"policy\":\""<<trained->name
             <<"\",\"median_ns_per_query\":"<<median(hybrid_samples)
             <<",\"pivot_rescues\":"<<hybrid_pivot_rescues
             <<",\"pivot_probes\":"<<hybrid_probe_count
             <<",\"fallback_queries\":"<<hybrid_fallback_queries
             <<",\"checksum\":"<<hybrid_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<hybrid_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<hybrid_samples[j];
    }
    std::cout<<"]},\"compact_pivots_topo\":{\"policy\":\""<<trained->name
             <<"\",\"median_ns_per_query\":"<<median(hybrid_topo_samples)
             <<",\"pivot_rescues\":"<<hybrid_pivot_rescues
             <<",\"pivot_probes\":"<<hybrid_probe_count
             <<",\"fallback_queries\":"<<hybrid_fallback_queries
             <<",\"checksum\":"<<hybrid_topo_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<hybrid_topo_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<hybrid_topo_samples[j];
    }
    std::cout<<"]},\"compact_pivots_bidir\":{\"policy\":\""<<trained->name
             <<"\",\"median_ns_per_query\":"<<median(hybrid_bidir_samples)
             <<",\"pivot_rescues\":"<<hybrid_pivot_rescues
             <<",\"pivot_probes\":"<<hybrid_probe_count
             <<",\"fallback_queries\":"<<hybrid_fallback_queries
             <<",\"checksum\":"<<hybrid_bidir_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<hybrid_bidir_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<hybrid_bidir_samples[j];
    }
    std::cout<<"]},\"compact_pivots_bidir_intervals\":{\"policy\":\""<<trained->name
             <<"\",\"median_ns_per_query\":"<<median(hybrid_bidir_intervals_samples)
             <<",\"pivot_rescues\":"<<hybrid_pivot_rescues
             <<",\"pivot_probes\":"<<hybrid_probe_count
             <<",\"fallback_queries\":"<<hybrid_fallback_queries
             <<",\"checksum\":"<<hybrid_bidir_intervals_checksum
             <<",\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<hybrid_bidir_intervals_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<hybrid_bidir_intervals_samples[j];
    }
    std::cout<<"]},\"compact_pivots_selector\":{\"median_ns_per_query\":"<<median(hybrid_selector_samples)
             <<",\"training_queries\":"<<selector_train.size()
             <<",\"training_ns\":"<<selector_training_ns
             <<",\"policy_id\":"<<selected_policy
             <<",\"topological_fallbacks\":"<<selector_topo_fallbacks
             <<",\"bidirectional_fallbacks\":"<<selector_bidir_fallbacks
             <<",\"pivot_rescues\":"<<hybrid_pivot_rescues
             <<",\"pivot_probes\":"<<hybrid_probe_count
             <<",\"fallback_queries\":"<<hybrid_fallback_queries
             <<",\"checksum\":"<<hybrid_selector_checksum
             <<",\"training_policy_medians_ns_per_query\":[";
    for(std::size_t j=0;j<selector_training_medians.size();++j){
      if(j)std::cout<<',';
      std::cout<<selector_training_medians[j];
    }
    std::cout<<"],\"samples_ns_per_query\":[";
    for(std::size_t j=0;j<hybrid_selector_samples.size();++j){
      if(j)std::cout<<',';
      std::cout<<hybrid_selector_samples[j];
    }
    std::cout<<"]},\"closure\":{\"available\":"<<(closure.built()?"true":"false")
             <<",\"components\":"<<closure.components()
             <<",\"index_matrix_bytes\":"<<closure.matrix_bytes()
             <<",\"cap_mib\":"<<cap_mib
             <<",\"build_ms\":"<<closure_build_ms
             <<",\"timed_query_repeats\":128";
    if(closure.built()){
      std::cout<<",\"median_ns_per_query\":"<<median(closure_samples)
               <<",\"median_onepass_ns_per_query\":"<<median(closure_onepass_samples)
               <<",\"checksum\":"<<closure_checksum
               <<",\"samples_ns_per_query\":[";
      for(std::size_t j=0;j<closure_samples.size();++j){
        if(j)std::cout<<',';
        std::cout<<closure_samples[j];
      }
      std::cout<<']';
    }
    std::cout<<"}}\n";
    return 0;
  }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 2;}
}

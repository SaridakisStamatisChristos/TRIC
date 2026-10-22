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
  std::sort(a.begin(),a.end());return a[a.size()/2];
}
int main(int argc,char **argv){
  try{
    int reps=7;
    if(argc>1) reps=std::stoi(argv[1]);
    if(reps<3||reps>21||reps%2!=1)throw std::runtime_error("reps must be odd in [3,21]");
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
    std::vector<double> closure_samples;
    uint64_t closure_checksum=0;
    std::vector<std::vector<double>> samples(numpol);
    std::vector<Counter> counters(numpol);
    std::vector<int> query_order(qcount);std::iota(query_order.begin(),query_order.end(),0);
    // Separate untimed warmup; rotate benchmark policy execution order per repetition.
    for(int pi=0;pi<numpol;pi++)(void)run(graph,pivots,policies[pi],queries,query_order,truth);
    // Differential validation against the independent DFS/BFS oracle.
    if(closure.built())for(int i=0;i<qcount;++i)
      if(closure.reaches(queries[i].first,queries[i].second)!=bool(truth[i]))
        throw std::runtime_error("closure mismatch with independent DFS oracle at query "+std::to_string(i));
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
      if(closure.built()){
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
    std::cout<<"],\\\"closure\\\":{\\\"available\\\":"<<(closure.built()?"true":"false")
             <<",\\\"components\\\":"<<closure.components()
             <<",\\\"index_matrix_bytes\\\":"<<closure.matrix_bytes()
             <<",\\\"cap_mib\\\":"<<cap_mib
             <<",\\\"build_ms\\\":"<<closure_build_ms
             <<",\\\"timed_query_repeats\\\":128";
    if(closure.built()){
      std::cout<<",\\\"median_ns_per_query\\\":"<<median(closure_samples)
               <<",\\\"checksum\\\":"<<closure_checksum
               <<",\\\"samples_ns_per_query\\\":[";
      for(std::size_t j=0;j<closure_samples.size();++j){
        if(j)std::cout<<',';
        std::cout<<closure_samples[j];
      }
      std::cout<<']';
    }
    std::cout<<"}}\\n";
    return 0;
  }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 2;}
}

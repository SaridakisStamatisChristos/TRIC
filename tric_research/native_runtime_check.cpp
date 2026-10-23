#include "partitioned_reachability.h"
#include "tric_reachability.h"
#include "closure_index.h"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <sys/resource.h>
using Graph=std::vector<std::vector<int>>;
using Clock=std::chrono::steady_clock;
using Pair=std::pair<int,int>;
static bool bfs(const Graph& g,int s,int t) {
  std::vector<unsigned char> seen(g.size(),0); std::vector<int> q{s}; seen[s]=1;
  for (std::size_t head=0;head<q.size();++head) {
    int u=q[head]; if(u==t)return true;
    for(int v:g[u])if(!seen[v]){seen[v]=1;q.push_back(v);}
  }
  return false;
}
static int selftest() {
  std::uint64_t checks=0;
  for(int mask=0;mask<512;++mask) {
    Graph g(3);
    for(int a=0;a<3;++a)for(int b=0;b<3;++b)if(mask&(1<<(3*a+b)))g[a].push_back(b);
    for(std::size_t cap:{std::size_t(0),std::size_t(11),std::size_t(24),std::size_t(4096)}) {
      PartitionedReachability index(g,cap);
      TricReachability automatic(g,cap);
      if(index.table_bytes()>cap)throw std::runtime_error("cap exceeded");
      for(int a=0;a<3;++a)for(int b=0;b<3;++b){
        if(index.reaches(a,b)!=bfs(g,a,b) || automatic.reaches(a,b)!=bfs(g,a,b))throw std::runtime_error("exhaustive mismatch");
        ++checks;
      }
    }
  }
  // Larger cases exercise compressed dense suffixes, sparse missing words,
  // interleaved weak components, mutable search scratch and multiword shifts
  // under the sanitizers, not only the three-vertex exhaustive domain.
  std::uint64_t adversarial=0;
  for(int shape=0;shape<3;++shape){
    Graph g(1024);
    if(shape==0)for(int v=1;v<1024;++v)g[0].push_back(v);
    if(shape==1)for(int u=0;u<1022;++u)g[u].push_back(u+2);
    if(shape==2)for(int u=0;u<1023;++u){
      g[u].push_back(u+1);if(u%9==0 && u+11<1024)g[u+11].push_back(u);
    }
    for(std::size_t cap:{std::size_t(0),std::size_t(65536),std::size_t(1048576)}){
      PartitionedReachability index(g,cap);TricReachability automatic(g,cap);
      for(int i=0;i<160;++i){
        const int a=(i*73)%1024,b=(i*197+17)%1024;const bool truth=bfs(g,a,b);
        if(index.reaches(a,b)!=truth || automatic.reaches(a,b)!=truth)throw std::runtime_error("adversarial mismatch");
        ++adversarial;
      }
    }
  }
  // A wide 160-vertex extension forces interval routing, including cross
  // edges to previously finished DFS subtrees. Exhaust all 12 variable arcs.
  std::uint64_t interval_checks=0, interval_indexes=0;
  for(int mask=0;mask<4096;++mask) {
    Graph g(160);for(int v=6;v<160;++v)g[0].push_back(v);
    int bit=0;
    for(int a=0;a<6;++a)for(int b=a+1;b<6;++b) {
      if(bit<12 && (mask&(1<<bit)))g[a].push_back(b);
      ++bit;
    }
    for(std::size_t cap:{std::size_t(2559),std::size_t(2560),std::size_t(3072)}) {
      PartitionedReachability index(g,cap);TricReachability automatic(g,cap);
      if(index.table_bytes()>cap || automatic.table_bytes()>cap)throw std::runtime_error("interval cap exceeded");
      interval_indexes+=index.interval_partitions();
      for(int a=0;a<6;++a)for(int j=0;j<8;++j) {
        const int b=j<6?j:(j==6?6:159);const bool truth=bfs(g,a,b);
        if(index.reaches(a,b)!=truth || automatic.reaches(a,b)!=truth)throw std::runtime_error("interval family mismatch");
        ++interval_checks;
      }
    }
  }
  std::uint64_t forest_checks=0;
  // Enumerate all 6! increasing-parent forests, in both arc directions, with
  // SCC aliases and duplicate external arcs. No closure table is permitted.
  for(int shape=0;shape<720;++shape)for(int reverse=0;reverse<2;++reverse) {
    Graph g(12);int code=shape;
    for(int u=0;u<6;++u) {
      g[2*u].push_back(2*u+1);g[2*u+1].push_back(2*u);
      const int choice=code%(u+1);code/=u+1;
      if(choice) {
        const int parent=choice-1,a=reverse?u:parent,b=reverse?parent:u;
        g[2*a].push_back(2*b);g[2*a+1].push_back(2*b);
      }
    }
    TricReachability index(g,0);
    if(!index.uses_forest_index() || index.table_bytes()!=0)throw std::runtime_error("forest routing mismatch");
    for(int a=0;a<12;++a)for(int b=0;b<12;++b) {
      if(index.reaches(a,b)!=bfs(g,a,b))throw std::runtime_error("forest family mismatch");
      ++forest_checks;
    }
  }
  std::uint64_t packed_checks=0;
  const std::uint32_t values[]={0,1,65535,65536,0x7ffffffeU,0x7fffffffU};
  for(auto ax:values)for(auto ay:values)for(auto bx:values)for(auto by:values) {
    const auto a=std::uint64_t(ax)|(std::uint64_t(ay)<<32),b=std::uint64_t(bx)|(std::uint64_t(by)<<32);
    if(tric_detail::forest_dominates(a,b)!=(ax<=bx && ay<=by))throw std::runtime_error("packed dominance mismatch");
    ++packed_checks;
  }
  std::cout<<"{\"exhaustive_checks\":"<<checks<<",\"adversarial_checks\":"<<adversarial<<",\"interval_checks\":"<<interval_checks<<",\"interval_indexes\":"<<interval_indexes<<",\"forest_checks\":"<<forest_checks<<",\"packed_checks\":"<<packed_checks<<"}\n"; return 0;
}
int main(int argc,char** argv) {
  try {
    if(argc==2 && std::string(argv[1])=="--self-test")return selftest();
    if(argc!=4)throw std::invalid_argument("usage: mode cap-bytes query-repeats < graph-and-queries");
    const std::string mode=argv[1];
    if(mode!="partitioned" && mode!="bounded" && mode!="auto")throw std::invalid_argument("mode");
    if(argv[2][0]=='-' || argv[3][0]=='-')throw std::invalid_argument("negative option");
    const auto cap=std::stoull(argv[2]);const auto repeats=std::stoull(argv[3]);
    if(cap>1073741824ULL || repeats<1 || repeats>1000000)throw std::invalid_argument("cap/repeat bounds");
    const auto start=Clock::now();
    int n,m,q;
    if(!(std::cin>>n>>m>>q)||n<1||n>2000000||m<0||q<1||q>1000000)throw std::invalid_argument("header");
    Graph g(n);
    for(int i=0;i<m;++i){int a,b;if(!(std::cin>>a>>b)||a<0||a>=n||b<0||b>=n)throw std::invalid_argument("edge");g[a].push_back(b);}
    std::vector<Pair> queries(q);
    for(auto& p:queries)if(!(std::cin>>p.first>>p.second)||p.first<0||p.first>=n||p.second<0||p.second>=n)throw std::invalid_argument("query");
    const auto parsed=Clock::now();
    std::unique_ptr<TricReachability> automatic;
    std::unique_ptr<PartitionedReachability> partitioned;
    std::unique_ptr<BoundedClosure> bounded;
    if(mode=="auto")automatic=std::make_unique<TricReachability>(g,cap);
    if(mode=="partitioned")partitioned=std::make_unique<PartitionedReachability>(g,cap);
    if(mode=="bounded")bounded=std::make_unique<BoundedClosure>(g,cap);
        const auto built=Clock::now();const bool available=!bounded || bounded->built();
    std::vector<unsigned char> answers(q);std::uint64_t checksum=0;
    auto replay=[&](auto&& query){
      for(std::uint64_t rep=0;rep<repeats;++rep)for(int i=0;i<q;++i){
        const bool a=query(queries[i].first,queries[i].second);
        if(rep==0)answers[i]=a;
        checksum=(checksum*0x100000001b3ULL)^(std::uint64_t(i)*4+unsigned(a));
      }
    };
    if(automatic)replay([&](int a,int b){return automatic->reaches(a,b);});
    if(partitioned)replay([&](int a,int b){return partitioned->reaches(a,b);});
    if(bounded && available)replay([&](int a,int b){return bounded->reaches(a,b);});
        const auto done=Clock::now();rusage usage{};getrusage(RUSAGE_SELF,&usage);
    if(available)for(int i=0;i<q;++i)if(answers[i]!=bfs(g,queries[i].first,queries[i].second))throw std::runtime_error("independent BFS mismatch");
    auto ns=[](auto a,auto b){return std::chrono::duration<double,std::nano>(b-a).count();};
    std::cout<<std::setprecision(15)<<"{\"mode\":\""<<mode<<"\",\"available\":"<<(available?"true":"false")
      <<",\"vertices\":"<<n<<",\"edges\":"<<m<<",\"queries\":"<<q<<",\"repeats\":"<<repeats
      <<",\"actual_calls\":"<<(available?std::uint64_t(q)*repeats:0)<<",\"checksum\":"<<checksum
      <<",\"oracle_verified_pairs\":"<<(available?q:0)<<",\"parse_ns\":"<<ns(start,parsed)
      <<",\"build_ns\":"<<ns(parsed,built)<<",\"query_ns\":"<<ns(built,done)
      <<",\"lifecycle_ns\":"<<ns(start,done)<<",\"timed_peak_rss_kib\":"<<usage.ru_maxrss;
    if(partitioned)std::cout<<",\"components\":"<<partitioned->components()<<",\"indexed_components\":"<<partitioned->indexed_components()
      <<",\"table_bytes\":"<<partitioned->table_bytes()<<",\"retained_capacity_bytes\":"<<partitioned->retained_bytes()
      <<",\"compressed_partitions\":"<<partitioned->compressed_partitions()
      <<",\"interval_partitions\":"<<partitioned->interval_partitions()

      <<",\"partitions\":"<<partitioned->partitions()<<",\"chain_partitions\":"<<partitioned->chain_partitions()
      <<",\"bit_partitions\":"<<partitioned->bit_partitions()<<",\"merged_arcs\":"<<partitioned->merged_arcs()
      <<",\"skipped_arcs\":"<<partitioned->skipped_arcs();
    if(automatic)std::cout<<",\"table_bytes\":"<<automatic->table_bytes()
      <<",\"retained_capacity_bytes\":"<<automatic->retained_bytes()
      <<",\"uses_direct_closure\":"<<(automatic->uses_direct_closure()?"true":"false");
#ifdef TRIC_HAS_FOREST_INDEX
    if(automatic)std::cout<<",\"uses_forest_index\":"<<(automatic->uses_forest_index()?"true":"false");
#endif
    if(bounded)std::cout<<",\"table_bytes\":"<<bounded->matrix_bytes();
    std::cout<<"}\n";
  } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

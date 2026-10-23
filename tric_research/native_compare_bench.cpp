#include "partitioned_reachability.h"
#ifdef TRIC_WITH_BFL
#include "bfl_adapter.h"
#endif
#include "tric_reachability.h"
#include "closure_index.h"
#ifdef TRIC_WITH_OREACH
#include "oreach_adapter.h"
#endif
#include <chrono>
#include <time.h>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <string>
#include <sys/resource.h>
using Graph=std::vector<std::vector<int>>;
using Clock=std::chrono::steady_clock;
using Pair=std::pair<int,int>;
static std::uint64_t thread_cpu_ns() {
  timespec now{};
  if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&now)!=0)throw std::runtime_error("thread CPU clock");
  return std::uint64_t(now.tv_sec)*1000000000ULL+std::uint64_t(now.tv_nsec);
}
static bool bfs(const Graph& g,int s,int t) {
  std::vector<unsigned char> seen(g.size(),0); std::vector<int> q{s}; seen[s]=1;
  for (std::size_t head=0;head<q.size();++head) {
    int u=q[head]; if(u==t)return true;
    for(int v:g[u])if(!seen[v]){seen[v]=1;q.push_back(v);}
  }
  return false;
}
int main(int argc,char** argv) {
  try {
    if(argc!=4)throw std::invalid_argument("usage: mode cap-bytes query-repeats < graph-and-queries");
    const std::string mode=argv[1];
    bool external=false,oreach_mode=false;
#ifdef TRIC_WITH_BFL
    external=mode=="bfl";
#endif
#ifdef TRIC_WITH_OREACH
    oreach_mode=mode=="oreach-pdfs" || mode=="oreach-pbibfs" || mode=="oreach-pdfs0" || mode=="oreach-pbibfs0";
#endif
    if(mode!="partitioned" && mode!="bounded" && mode!="auto" && !external && !oreach_mode)throw std::invalid_argument("mode");
    if(argv[2][0]=='-' || argv[3][0]=='-')throw std::invalid_argument("negative option");
    const auto cap=std::stoull(argv[2]);const auto repeats=std::stoull(argv[3]);
    if(cap>1073741824ULL || repeats<1 || repeats>1000000)throw std::invalid_argument("cap/repeat bounds");
    const auto start=Clock::now();const auto cpu_start=thread_cpu_ns();
    int n,m,q;
    if(!(std::cin>>n>>m>>q)||n<1||n>2000000||m<0||q<1||q>1000000)throw std::invalid_argument("header");
    Graph g(n);
    for(int i=0;i<m;++i){int a,b;if(!(std::cin>>a>>b)||a<0||a>=n||b<0||b>=n)throw std::invalid_argument("edge");g[a].push_back(b);}
    std::vector<Pair> queries(q);
    for(auto& p:queries)if(!(std::cin>>p.first>>p.second)||p.first<0||p.first>=n||p.second<0||p.second>=n)throw std::invalid_argument("query");
    const auto parsed=Clock::now();const auto cpu_parsed=thread_cpu_ns();
    std::unique_ptr<TricReachability> automatic;
    std::unique_ptr<PartitionedReachability> partitioned;
    std::unique_ptr<BoundedClosure> bounded;
    if(mode=="auto")automatic=std::make_unique<TricReachability>(g,cap);
    if(mode=="partitioned")partitioned=std::make_unique<PartitionedReachability>(g,cap);
    if(mode=="bounded")bounded=std::make_unique<BoundedClosure>(g,cap);
    #ifdef TRIC_WITH_BFL
    std::unique_ptr<BflAdapter> bfl;
    if(external)bfl=std::make_unique<BflAdapter>(g);
#endif
#ifdef TRIC_WITH_OREACH
    std::unique_ptr<OReachAdapter> oreach;
    if(oreach_mode) {
      auto* saved=std::cout.rdbuf(std::cerr.rdbuf());
      oreach=std::make_unique<OReachAdapter>(g,mode.find("pbibfs")!=std::string::npos,mode.back()=='0'?0:3);
      std::cout.rdbuf(saved);
    }
#endif
    const auto built=Clock::now();const auto cpu_built=thread_cpu_ns();const bool available=!bounded || bounded->built();
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
    #ifdef TRIC_WITH_BFL
    if(bfl)replay([&](int a,int b){return bfl->reaches(a,b);});
#endif
#ifdef TRIC_WITH_OREACH
    if(oreach)replay([&](int a,int b){return oreach->reaches(a,b);});
#endif
    const auto done=Clock::now();const auto cpu_done=thread_cpu_ns();rusage usage{};getrusage(RUSAGE_SELF,&usage);
    // VmHWM belongs to this executable's current memory image. ru_maxrss can
    // include a larger RSS inherited from the Python launcher before exec.
    std::ifstream status("/proc/self/status");std::string line;std::size_t vm_hwm=0;
    while(std::getline(status,line))if(line.compare(0,6,"VmHWM:")==0){std::istringstream in(line.substr(6));in>>vm_hwm;}
    if(!vm_hwm)throw std::runtime_error("missing process VmHWM");
    if(available)for(int i=0;i<q;++i)if(answers[i]!=bfs(g,queries[i].first,queries[i].second))throw std::runtime_error("independent BFS mismatch");
    auto ns=[](auto a,auto b){return std::chrono::duration<double,std::nano>(b-a).count();};
    std::cout<<std::setprecision(15)<<"{\"mode\":\""<<mode<<"\",\"available\":"<<(available?"true":"false")
      <<",\"vertices\":"<<n<<",\"edges\":"<<m<<",\"queries\":"<<q<<",\"repeats\":"<<repeats
      <<",\"actual_calls\":"<<(available?std::uint64_t(q)*repeats:0)<<",\"checksum\":"<<checksum
      <<",\"oracle_verified_pairs\":"<<(available?q:0)<<",\"parse_ns\":"<<ns(start,parsed)
      <<",\"build_ns\":"<<ns(parsed,built)<<",\"query_ns\":"<<ns(built,done)
      <<",\"parse_thread_cpu_ns\":"<<(cpu_parsed-cpu_start)
      <<",\"build_thread_cpu_ns\":"<<(cpu_built-cpu_parsed)
      <<",\"query_thread_cpu_ns\":"<<(cpu_done-cpu_built)
      <<",\"lifecycle_ns\":"<<ns(start,done)<<",\"timed_peak_rss_kib\":"<<vm_hwm<<",\"rusage_peak_rss_kib\":"<<usage.ru_maxrss;
    if(partitioned)std::cout<<",\"components\":"<<partitioned->components()<<",\"indexed_components\":"<<partitioned->indexed_components()
      <<",\"table_bytes\":"<<partitioned->table_bytes()<<",\"retained_capacity_bytes\":"<<partitioned->retained_bytes()
      <<",\"compressed_partitions\":"<<partitioned->compressed_partitions()
      <<",\"partitions\":"<<partitioned->partitions()<<",\"chain_partitions\":"<<partitioned->chain_partitions()
      <<",\"bit_partitions\":"<<partitioned->bit_partitions()<<",\"merged_arcs\":"<<partitioned->merged_arcs()
      <<",\"skipped_arcs\":"<<partitioned->skipped_arcs();
    if(automatic)std::cout<<",\"table_bytes\":"<<automatic->table_bytes()
      <<",\"retained_capacity_bytes\":"<<automatic->retained_bytes()
      <<",\"uses_direct_closure\":"<<(automatic->uses_direct_closure()?"true":"false");
    if(bounded)std::cout<<",\"table_bytes\":"<<bounded->matrix_bytes();
#ifdef TRIC_WITH_BFL
    if(bfl)std::cout<<",\"retained_capacity_bytes\":"<<bfl->retained_bytes();
#endif
    std::cout<<"}\n";
  } catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

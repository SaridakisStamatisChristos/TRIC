#include "tric_reachability.h"
#include "reachability/scc.hpp"
#include "reachability/feline.hpp"
#include "reachability/grail.hpp"
#include "reachability/preach.hpp"
#include "reachability/ferrari.hpp"
#include "reachability/tflabel.hpp"
#include "reachability/tol.hpp"
#include <chrono>
#include <ctime>
#include <fstream>
#include <sstream>
#include <iostream>
#include <iomanip>
#include <memory>
#include <string>
using G=std::vector<std::vector<int>>;
using Q=std::vector<std::pair<int,int>>;
static std::uint64_t cpu(){timespec t{};if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))throw std::runtime_error("clock");return std::uint64_t(t.tv_sec)*1000000000+t.tv_nsec;}
static std::uint64_t wall(){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
static bool bfs(const G& g,int a,int b){std::vector<char>s(g.size());std::vector<int>q{a};s[a]=1;for(std::size_t i=0;i<q.size();++i){int u=q[i];if(u==b)return true;for(int v:g[u])if(!s[v]){s[v]=1;q.push_back(v);}}return false;}
void build(reachability::Feline& p,const reachability::CSRGraph& g){p.build(g);}
void build(reachability::Grail& p,const reachability::CSRGraph& g){p.build(g,5,1);}
void build(reachability::PReaCH& p,const reachability::CSRGraph& g){p.build(g);}
void build(reachability::Ferrari& p,const reachability::CSRGraph& g){p.build(g,5,4,32);}
void build(reachability::TFLabel& p,const reachability::CSRGraph& g){p.build(g);}
void build(reachability::TOL& p,const reachability::CSRGraph& g){p.build(g);}
template<class M>bool ask(M& p,int a,int b){return p.reaches(a,b);}
bool ask(reachability::TFLabel& p,int a,int b){return p.query(a,b);}
bool ask(reachability::TOL& p,int a,int b){return p.query(a,b);}
template<class M>class Adapter{
 std::vector<reachability::vid_t> comp_;M index_;
public:
 explicit Adapter(const G& graph){
  std::vector<reachability::vid_t> src,dst;
  for(int u=0;u<int(graph.size());++u)for(int v:graph[u]){src.push_back(u);dst.push_back(v);}
  reachability::CSRGraph g(int(graph.size()),src,dst);auto scc=reachability::scc_condense(g);
  comp_=std::move(scc.comp);build(index_,scc.dag);
 }
 bool reaches(int a,int b){return ask(index_,comp_[a],comp_[b]);}
 std::size_t bytes()const{return index_.index_size_bytes()+comp_.capacity()*sizeof(int);}
};
struct Tric {
 TricReachability p;
 explicit Tric(const G& g):p(g,2097152){}
 bool reaches(int a,int b){return p.reaches(a,b);}
 std::size_t bytes()const{return p.retained_bytes();}
};
template<class M>void run(const G& g,const Q& qs,std::uint64_t target){
 const auto bw=wall(),bc=cpu();M index(g);const auto ec=cpu(),ew=wall();
 std::vector<unsigned char> answers(qs.size());
 // Fixed, identical untimed one-pass warmup; later calls do not change labels.
 for(std::size_t i=0;i<qs.size();++i)answers[i]=index.reaches(qs[i].first,qs[i].second);
 std::uint64_t repeats=0,checksum=0;const auto qw=wall(),qc=cpu();
 do {
  for(std::size_t i=0;i<qs.size();++i)checksum=(checksum*0x100000001b3ULL)^(std::uint64_t(i)*4+index.reaches(qs[i].first,qs[i].second));
  ++repeats;if(repeats>1000000)throw std::runtime_error("query replay limit");
 }while(cpu()-qc<target);
 const auto qe=cpu(),we=wall();
 std::size_t rss=0;std::ifstream f("/proc/self/status");std::string line;
 while(std::getline(f,line))if(line.compare(0,6,"VmHWM:")==0){std::istringstream in(line.substr(6));in>>rss;}
 std::uint64_t answer_hash=0;
 for(std::size_t i=0;i<qs.size();++i){const bool truth=bfs(g,qs[i].first,qs[i].second);if(answers[i]!=truth || index.reaches(qs[i].first,qs[i].second)!=truth)throw std::runtime_error("BFS mismatch");answer_hash=(answer_hash*0x100000001b3ULL)^(std::uint64_t(i)*4+truth);}
 std::cout<<"{\"queries\":"<<qs.size()<<",\"repeats\":"<<repeats<<",\"calls\":"<<repeats*qs.size()<<",\"checksum\":"<<checksum<<",\"answer_hash\":"<<answer_hash<<",\"verified\":"<<qs.size()<<",\"build_ns\":"<<ew-bw<<",\"build_cpu_ns\":"<<ec-bc<<",\"query_ns\":"<<we-qw<<",\"query_cpu_ns\":"<<qe-qc<<",\"reported_bytes\":"<<index.bytes()<<",\"peak_rss_kib\":"<<rss<<"}\n";
}
template<class M>std::uint64_t check(){
 std::uint64_t checks=0;
 for(int mask=0;mask<512;++mask){G g(3);for(int a=0;a<3;++a)for(int b=0;b<3;++b)if(mask&(1<<(3*a+b)))g[a].push_back(b);M index(g);for(int a=0;a<3;++a)for(int b=0;b<3;++b){if(index.reaches(a,b)!=bfs(g,a,b))throw std::runtime_error("exhaustive mismatch");++checks;}}
 return checks;
}
int main(int argc,char**argv){try{
 if(argc==2 && std::string(argv[1])=="--self-test"){
  std::uint64_t n=check<Tric>()+check<Adapter<reachability::Feline>>()+check<Adapter<reachability::Grail>>()+check<Adapter<reachability::PReaCH>>()+check<Adapter<reachability::Ferrari>>()+check<Adapter<reachability::TFLabel>>()+check<Adapter<reachability::TOL>>();std::cout<<"{\"exhaustive_checks\":"<<n<<"}\n";return 0;
 }
 if(argc!=3)throw std::invalid_argument("mode target-query-cpu-ns");std::string mode=argv[1];const auto target=std::stoull(argv[2]);
 if(target<1 || target>1000000000)throw std::invalid_argument("target");
 int n,m,q;if(!(std::cin>>n>>m>>q)||n<1||n>2000000||m<0||q<1)throw std::invalid_argument("header");G g(n);Q qs(q);
 for(int i=0;i<m;++i){int a,b;if(!(std::cin>>a>>b)||a<0||b<0||a>=n||b>=n)throw std::invalid_argument("edge");g[a].push_back(b);}
 for(auto& p:qs)if(!(std::cin>>p.first>>p.second)||p.first<0||p.second<0||p.first>=n||p.second>=n)throw std::invalid_argument("query");
 if(mode=="tric")run<Tric>(g,qs,target);
 else if(mode=="feline")run<Adapter<reachability::Feline>>(g,qs,target);
 else if(mode=="grail")run<Adapter<reachability::Grail>>(g,qs,target);
 else if(mode=="preach")run<Adapter<reachability::PReaCH>>(g,qs,target);
 else if(mode=="ferrari")run<Adapter<reachability::Ferrari>>(g,qs,target);
 else if(mode=="tflabel")run<Adapter<reachability::TFLabel>>(g,qs,target);
 else if(mode=="tol")run<Adapter<reachability::TOL>>(g,qs,target);
 else throw std::invalid_argument("mode");
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}

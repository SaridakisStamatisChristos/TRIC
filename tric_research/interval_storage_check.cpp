// Allocation instrumentation for resource checks, deliberately not a timer.
// Tracks requested C++ heap payload, including over-aligned label vectors.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <new>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#include "tric_reachability.h"

namespace allocations {
struct Header { void* base; std::size_t size; };
static std::size_t live=0, blocks=0, peak=0;
void* acquire(std::size_t size,std::size_t alignment) {
  alignment=std::max(alignment,alignof(std::max_align_t));
  const auto overhead=sizeof(Header)+alignment-1;
  if(size>std::numeric_limits<std::size_t>::max()-overhead)throw std::bad_alloc();
  void* base=std::malloc(size+overhead);
  if(!base)throw std::bad_alloc();
  auto address=(reinterpret_cast<std::uintptr_t>(base)+sizeof(Header)+alignment-1)&~(alignment-1);
  auto* header=reinterpret_cast<Header*>(address)-1;
  header->base=base;header->size=size;
  live+=size;++blocks;peak=std::max(peak,live);
  return reinterpret_cast<void*>(address);
}
void release(void* p) noexcept {
  if(!p)return;
  auto* h=static_cast<Header*>(p)-1;
  live-=h->size;--blocks;std::free(h->base);
}
}
void* operator new(std::size_t n){return allocations::acquire(n,alignof(std::max_align_t));}
void* operator new[](std::size_t n){return ::operator new(n);}
void* operator new(std::size_t n,std::align_val_t a){return allocations::acquire(n,static_cast<std::size_t>(a));}
void* operator new[](std::size_t n,std::align_val_t a){return ::operator new(n,a);}
void operator delete(void* p) noexcept {allocations::release(p);}
void operator delete[](void* p) noexcept {allocations::release(p);}
void operator delete(void* p,std::size_t) noexcept {allocations::release(p);}
void operator delete[](void* p,std::size_t) noexcept {allocations::release(p);}
void operator delete(void* p,std::align_val_t) noexcept {allocations::release(p);}
void operator delete[](void* p,std::align_val_t) noexcept {allocations::release(p);}
void operator delete(void* p,std::size_t,std::align_val_t) noexcept {allocations::release(p);}
void operator delete[](void* p,std::size_t,std::align_val_t) noexcept {allocations::release(p);}

using Graph=std::vector<std::vector<int>>;
using Queries=std::vector<std::pair<int,int>>;
struct Result {
  std::size_t table=0,retained=0,heap=0,peak=0,blocks=0,checks=0;
  std::uint64_t checksum=0;
  std::size_t components=0,indexed=0,partitions=0,chains=0,bits=0,compressed=0,intervals=0;
  std::uint64_t merged=0,skipped=0;
  bool direct=false,forest=false;
};
template<class Index>
void validate(Index& index,const Graph& graph,const Queries& queries,Result& result) {
  // Independent BFS; reuse only the last source's completed reachable set.
  std::vector<unsigned char> seen(graph.size());std::vector<int> queue;
  int previous=-1;
  for(auto [source,target]:queries) {
    if(source!=previous) {
      std::fill(seen.begin(),seen.end(),0);queue.assign(1,source);seen[source]=1;
      for(std::size_t i=0;i<queue.size();++i)
        for(int v:graph[queue[i]])if(!seen[v]){seen[v]=1;queue.push_back(v);}
      previous=source;
    }
    const bool answer=index.reaches(source,target);
    if(answer!=bool(seen[target]))throw std::runtime_error("independent BFS mismatch");
    result.checksum=(result.checksum*0x100000001b3ULL)^unsigned(answer);
    ++result.checks;
  }
}
void metadata(const PartitionedReachability& p,Result& r) {
  r.components=p.components();r.indexed=p.indexed_components();r.partitions=p.partitions();
  r.chains=p.chain_partitions();r.bits=p.bit_partitions();r.compressed=p.compressed_partitions();
  r.intervals=p.interval_partitions();r.merged=p.merged_arcs();r.skipped=p.skipped_arcs();
}
void metadata(const TricReachability& p,Result& r) {
  r.direct=p.uses_direct_closure();r.forest=p.uses_forest_index();
}
template<class Index>
Result check(const Graph& graph,const Queries& queries,std::size_t cap,std::size_t scratch) {
  Result r;
  const auto before=allocations::live,before_blocks=allocations::blocks;
  allocations::peak=before;
  {
    Index index(graph,cap,scratch);
    r.heap=allocations::live-before;r.peak=allocations::peak-before;
    r.blocks=allocations::blocks-before_blocks;
    r.table=index.table_bytes();r.retained=index.retained_bytes();metadata(index,r);
    if(r.table>cap || r.heap+sizeof(Index)!=r.retained)
      throw std::runtime_error("retained accounting differs from observed allocations");
    // Moving must preserve ownership, query labels and resource accounting.
    Index moved(std::move(index));
    if(moved.retained_bytes()!=r.retained || allocations::live!=before+r.heap)
      throw std::runtime_error("move changed retained storage");
    validate(moved,graph,queries,r);
  }
  if(allocations::live!=before || allocations::blocks!=before_blocks)
    throw std::runtime_error("index destruction leaked allocations");
  return r;
}
int main(int argc,char** argv) {
  try {
    if(argc!=4)throw std::invalid_argument("mode cap scratch < graph-and-queries");
    const std::string mode=argv[1];
    const auto cap=std::stoull(argv[2]),scratch=std::stoull(argv[3]);
    int n,m,q;
    if(!(std::cin>>n>>m>>q) || n<0 || m<0 || q<0)throw std::invalid_argument("header");
    Graph graph(n);Queries queries(q);
    for(int i=0;i<m;++i){int a,b;if(!(std::cin>>a>>b)||a<0||b<0||a>=n||b>=n)throw std::invalid_argument("edge");graph[a].push_back(b);}
    for(auto& p:queries)if(!(std::cin>>p.first>>p.second)||p.first<0||p.second<0||p.first>=n||p.second>=n)throw std::invalid_argument("query");
    Result r;
    if(mode=="partitioned")r=check<PartitionedReachability>(graph,queries,cap,scratch);
    else if(mode=="auto")r=check<TricReachability>(graph,queries,cap,scratch);
    else throw std::invalid_argument("mode");
    std::cout<<"{\"table_bytes\":"<<r.table<<",\"retained_bytes\":"<<r.retained
      <<",\"live_heap_bytes\":"<<r.heap<<",\"construction_peak_heap_bytes\":"<<r.peak
      <<",\"live_blocks\":"<<r.blocks<<",\"oracle_checks\":"<<r.checks<<",\"checksum\":"<<r.checksum
      <<",\"components\":"<<r.components<<",\"indexed\":"<<r.indexed<<",\"partitions\":"<<r.partitions
      <<",\"chains\":"<<r.chains<<",\"bits\":"<<r.bits<<",\"compressed\":"<<r.compressed
      <<",\"intervals\":"<<r.intervals<<",\"merged\":"<<r.merged<<",\"skipped\":"<<r.skipped
      <<",\"direct\":"<<r.direct<<",\"forest\":"<<r.forest<<"}\n";
  }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}

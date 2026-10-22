// Phase XIX: optional exact, train-only hot-source reachability cache.
// Selective transitive closure is established prior art, not a novel oracle.
// Does not mutate existing TRIC default or any previous research phase.
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>
#include <vector>

class HotSourceCache {
  int vertices_=0;
  std::size_t words_=0;
  std::vector<int> source_to_row_;
  std::vector<int> source_ids_;
  std::vector<std::uint64_t> rows_;
public:
  HotSourceCache()=default;

  template<class Graph>
  HotSourceCache(const Graph& graph,
                 const std::vector<std::pair<int,int>>& training,
                 std::size_t max_sources,
                 std::size_t cap_bytes,
                 unsigned min_frequency=2) {
    if(graph.size()>static_cast<std::size_t>(std::numeric_limits<int>::max()))
      throw std::invalid_argument("graph too large");
    vertices_=static_cast<int>(graph.size());
    words_=(graph.size()+63)/64;
    std::vector<unsigned> freq(graph.size(),0);
    for(const auto& q:training) {
      if(q.first<0 || q.second<0 || q.first>=vertices_ || q.second>=vertices_)
        throw std::invalid_argument("training vertex out of bounds");
      ++freq[q.first];
    }
    // Cap includes the retained O(V) direct lookup table. Transient
    // frequency/DFS scratch buffers and allocator overhead are excluded.
    const std::size_t metadata=graph.size()*sizeof(int);
    if(!max_sources || !vertices_ || cap_bytes<metadata || !words_)return;
    if(words_>std::numeric_limits<std::size_t>::max()/sizeof(std::uint64_t))
      throw std::overflow_error("cache row size overflow");
    const std::size_t row_bytes=words_*sizeof(std::uint64_t);
    const std::size_t permitted=std::min(max_sources,(cap_bytes-metadata)/(row_bytes+sizeof(int)));
    if(!permitted)return;
    std::vector<int> candidates;
    for(int s=0;s<vertices_;++s)
      if(freq[s]>=min_frequency)candidates.push_back(s);
    std::sort(candidates.begin(),candidates.end(),[&](int a,int b){
      if(freq[a]!=freq[b])return freq[a]>freq[b];
      return a<b;
    });
    if(candidates.size()>permitted)candidates.resize(permitted);
    if(candidates.empty())return;
    source_ids_=std::move(candidates);
    source_to_row_.assign(graph.size(),-1);
    rows_.assign(source_ids_.size()*words_,0);
    std::vector<int> stack;
    for(std::size_t row=0;row<source_ids_.size();++row) {
      const int source=source_ids_[row];
      source_to_row_[source]=static_cast<int>(row);
      stack.clear();
      stack.push_back(source);
      rows_[row*words_+static_cast<std::size_t>(source)/64]
        |=std::uint64_t(1)<<(source&63);
      while(!stack.empty()) {
        const int u=stack.back();stack.pop_back();
        for(int v:graph[u]) {
          if(v<0 || v>=vertices_)throw std::invalid_argument("graph edge out of bounds");
          const std::size_t offset=row*words_+static_cast<std::size_t>(v)/64;
          const std::uint64_t mask=std::uint64_t(1)<<(v&63);
          if(rows_[offset]&mask)continue;
          rows_[offset]|=mask;
          stack.push_back(v);
        }
      }
    }
  }

  bool lookup(int source,int target,bool& answer) const {
    if(source<0 || target<0 || source>=vertices_ || target>=vertices_)
      throw std::out_of_range("query vertex out of bounds");
    if(source_to_row_.empty())return false;
    const int row=source_to_row_[source];
    if(row<0)return false;
    answer=((rows_[static_cast<std::size_t>(row)*words_
                  +static_cast<std::size_t>(target)/64]>>(target&63))&1)!=0;
    return true;
  }
  std::size_t retained_bytes() const {
    return source_to_row_.capacity()*sizeof(int)
      +source_ids_.capacity()*sizeof(int)
      +rows_.capacity()*sizeof(std::uint64_t);
  }
  std::size_t rows() const {return source_ids_.size();}
  const std::vector<int>& sources() const {return source_ids_;}
};
